from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
import json
import threading
import base64
import os
import sys
import urllib.parse
import urllib.request
import pandas as pd
from datetime import datetime
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_root)

try:
    from audio_to_text import process_frames as at_process_frames
    from audio_to_text import set_lang as at_set_lang
    from audio_to_text import set_rate as at_set_rate
    from audio_to_text import set_channels as at_set_channels
    from audio_to_text import force_final as at_force_final
except Exception as e:
    at_process_frames = None
    at_set_lang = None
    at_set_rate = None
    at_set_channels = None
    at_force_final = None
    print("asr_import_error", str(e), flush=True)

try:
    from logic.text.analysis import save_freq
except Exception as e:
    save_freq = None
    print("analysis_import_error", str(e), flush=True)

try:
    from logic.text.translate import translation_api_call
except Exception as e:
    translation_api_call = None
    print("openai_translation_import_error", str(e), flush=True)

try:
    from logic.tss.tss import speak, save_to_file
except Exception as e:
    speak = None
    save_to_file = None
    print("tss_import_error", str(e), flush=True)

try:
    from database.connection import db_pool
    from database.queries import get_user_vocab, get_global_vocab, upsert_global_vocab, increment_global_vocab_count, upsert_user_vocab, get_vocab_translation, record_remember, record_dont_remember, is_admin, save_recording
    from api.auth import handle_register, handle_login
    from api.middleware import require_auth, create_auth_response
    from api.admin import handle_admin_login, handle_admin_list_users, handle_admin_delete_user, handle_admin_add_user, handle_admin_list_vocab, handle_admin_delete_vocab, handle_admin_update_translation
except Exception as e:
    db_pool = None
    handle_register = None
    handle_login = None
    require_auth = None
    create_auth_response = None
    handle_admin_login = None
    handle_admin_list_users = None
    handle_admin_delete_user = None
    handle_admin_add_user = None
    handle_admin_list_vocab = None
    handle_admin_delete_vocab = None
    handle_admin_update_translation = None
    save_recording = None
    print("auth_import_error", str(e), flush=True)

try:
    from generate_audio import generate_audio_file
except Exception:
    generate_audio_file = None

try:
    import websockets
except Exception:
    websockets = None

class SimpleHandler(BaseHTTPRequestHandler):
    def _set_cors(self):
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        if path in ('/', '/debug'):
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'base.html')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                body = b'OK'
                ct = 'text/plain; charset=utf-8'
        elif path == '/app':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'base.html')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                body = b'OK'
                ct = 'text/plain; charset=utf-8'
        elif path.startswith('/src/'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                if fname.endswith('.js'):
                    ct = 'application/javascript; charset=utf-8'
                else:
                    ct = 'text/plain; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path == '/style.css':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'style.css')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/css; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path.endswith('.js'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'application/javascript; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path == '/admin' or path == '/admin.html':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'admin.html')
                abs_path = os.path.abspath(p)
                if not os.path.exists(abs_path):
                    print(f"Admin file not found at: {abs_path}", flush=True)
                    self.send_error(404)
                    return
                with open(abs_path, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception as e:
                print(f"Error serving admin.html: {e}", flush=True)
                import traceback
                traceback.print_exc()
                self.send_error(404)
                return
        elif path.endswith('.html'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                if not os.path.exists(p):
                    print(f"File not found: {p} (requested: {path})", flush=True)
                    self.send_error(404)
                    return
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception as e:
                print(f"Error serving HTML file {path}: {e}", flush=True)
                self.send_error(404)
                return
        elif path.startswith('/templates/'):
            try:
                fname = path[len('/templates/'):]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'templates', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path.startswith('/data/'):
            fname = urllib.parse.unquote(path[6:])
            try:
                fpath = os.path.join(os.path.dirname(__file__), '..', 'database', 'data', fname)
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    with open(fpath, 'rb') as f:
                        body = f.read()
                    if fname.endswith('.csv'):
                        ct = 'text/csv; charset=utf-8'
                    elif fname.endswith('.mp3'):
                        ct = 'audio/mpeg'
                    else:
                        ct = 'application/octet-stream'
                else:
                    print(f"File not found: {fpath} (requested: {path})", flush=True)
                    self.send_error(404)
                    return
            except Exception as e:
                print(f"Error serving file {path}: {e}", flush=True)
                self.send_error(404)
                return
        elif path == '/vocab/list':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'items': [], 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                native_lang = user.get('native_language', 'en') or 'en'
                rows = get_user_vocab(user['id'], native_lang) if get_user_vocab else []
                body = json.dumps({'items': rows}, ensure_ascii=False).encode('utf-8')
                ct = 'application/json; charset=utf-8'
            except Exception:
                body = json.dumps({'items': []}).encode('utf-8')
                ct = 'application/json; charset=utf-8'
        else:
            body = b'OK'
            ct = 'text/plain; charset=utf-8'
        
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == '/register':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_register(b) if handle_register else {'success': False, 'error': 'auth_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/login':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            print(f"Login request received: {len(b)} bytes", flush=True)
            try:
                import json as json_module
                req_data = json_module.loads(b.decode('utf-8'))
                print(f"Login attempt for user: {req_data.get('username', 'unknown')}", flush=True)
            except Exception as e:
                print(f"Error parsing login request: {e}", flush=True)
            out = handle_login(b) if handle_login else {'success': False, 'error': 'auth_not_available'}
            print(f"Login response: success={out.get('success', False)}, error={out.get('error', 'none')}", flush=True)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/upload':
            n = int(self.headers.get('Content-Length', 0))
            _ = self.rfile.read(n)
            body = b'audio received'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(body)
            return
        elif self.path == '/translate':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_translate(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/analyze':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'words': [], 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_analyze(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/vocab/ingest':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            native_lang = user.get('native_language', 'en') or 'en'
            out = handle_vocab_ingest(b, user['id'], native_lang)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/learn/remember':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                base = str(j.get('base', ''))
                pos = str(j.get('pos', ''))
                if base and pos:
                    success = record_remember(user['id'], base, pos) if record_remember else False
                    out = {'success': success}
                else:
                    out = {'success': False, 'error': 'missing_fields'}
            except Exception:
                out = {'success': False, 'error': 'bad_json'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/learn/dont-remember':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                base = str(j.get('base', ''))
                pos = str(j.get('pos', ''))
                if base and pos:
                    success = record_dont_remember(user['id'], base, pos) if record_dont_remember else False
                    out = {'success': success}
                else:
                    out = {'success': False, 'error': 'missing_fields'}
            except Exception:
                out = {'success': False, 'error': 'bad_json'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/tts':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_tts(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/recording/save':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                audio_base64 = j.get('audio', '')
                role = j.get('role', 'speak')
                transcript = j.get('transcript')
                language = j.get('language')
                
                if not audio_base64:
                    out = {'success': False, 'error': 'no_audio'}
                else:
                    # Save audio file
                    import uuid
                    recordings_dir = os.path.join(backend_root, 'database', 'data', 'recordings')
                    os.makedirs(recordings_dir, exist_ok=True)
                    
                    audio_filename = f"{user['id']}_{uuid.uuid4().hex}.webm"
                    audio_path = os.path.join(recordings_dir, audio_filename)
                    
                    audio_data = base64.b64decode(audio_base64)
                    with open(audio_path, 'wb') as f:
                        f.write(audio_data)
                    
                    # Save to database
                    relative_path = os.path.join('recordings', audio_filename)
                    success = save_recording(user['id'], role, relative_path, transcript, language) if save_recording else False
                    out = {'success': success}
            except Exception as e:
                print(f"Error saving recording: {e}", flush=True)
                import traceback
                traceback.print_exc()
                out = {'success': False, 'error': str(e)[:100]}
            
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/login':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_admin_login(b) if handle_admin_login else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n) if n > 0 else b'{}'
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('username', '')
                password = j.get('password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_list_users() if handle_admin_list_users else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users/delete':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('admin_username', '')
                password = j.get('admin_password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_delete_user(b) if handle_admin_delete_user else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users/add':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('admin_username', '')
                password = j.get('admin_password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_add_user(b) if handle_admin_add_user else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/vocab':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n) if n > 0 else b'{}'
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('username', '')
                    password = j.get('password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_list_vocab() if handle_admin_list_vocab else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
        elif self.path == '/admin/vocab/delete':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n)
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('admin_username', '')
                    password = j.get('admin_password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_delete_vocab(b) if handle_admin_delete_vocab else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
        elif self.path == '/admin/translations/update':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n)
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('admin_username', '')
                    password = j.get('admin_password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_update_translation(b) if handle_admin_update_translation else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return

        body = json.dumps({'success': False, 'error': 'not_found'}).encode('utf-8')
        self.send_response(404)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

def start_http(port: int):
    HTTPServer(('', port), SimpleHandler).serve_forever()

def build_msg(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)

def parse_json(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {}

async def ws_handler(websocket, path):
    try:
        async for message in websocket:
            data = parse_json(message)
            if data.get('type') == 'ping':
                await websocket.send(build_msg({'type': 'pong'}))
            elif data.get('type') == 'audio':
                frames = data.get('frames', [])
                if at_process_frames:
                    result = at_process_frames(frames)
                    await websocket.send(build_msg({'type': 'transcript', 'text': result}))
    except Exception as e:
        print(f"ws_error: {e}", flush=True)

def handle_translate(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'text': '', 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    source = str(j.get('source', 'auto')).strip()
    target = str(j.get('target', 'en')).strip()
    if not text:
        return {'text': '', 'error': 'no_text'}
    
    # Try OpenAI API first (for Browser STT transcripts)
    if translation_api_call:
        try:
            # Map language codes if needed
            source_lang = source if source != 'auto' else 'en'
            result = translation_api_call(text, source_lang, target)
            return {'text': result, 'error': ''}
        except Exception as e:
            print(f"OpenAI translation failed: {e}, falling back to Google Translator", flush=True)
            # Fall through to Google Translator fallback
    
    # Fallback to Google Translator if OpenAI fails or is unavailable
    try:
        if GoogleTranslator:
            result = GoogleTranslator(source=source, target=target).translate(text)
            return {'text': result, 'error': ''}
        else:
            return {'text': 'Translation service unavailable', 'error': 'no_translator'}
    except Exception as e:
        return {'text': '', 'error': str(e)[:100]}

def handle_analyze(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'words': [], 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    if not text or save_freq is None:
        return {'words': [], 'error': 'no_text_or_deps'}
    try:
        df = save_freq(text)
        words = df[['word']].to_dict('records')
        return {'words': words, 'error': ''}
    except Exception as e:
        return {'words': [], 'error': str(e)[:100]}

def get_translation(word: str, existing_translation, target_lang: str = 'en'):
    if existing_translation:
        return existing_translation
    if GoogleTranslator:
        try:
            return GoogleTranslator(source='ko', target=target_lang).translate(word)
        except Exception:
            return ''
    return ''

async def translate_base_to_all_languages(base: str, pos: str):
    global_vocab = get_global_vocab(base, pos) if get_global_vocab else None
    if not global_vocab:
        return
    
    translations = {
        'en': global_vocab.get('translation_en'),
        'ru': global_vocab.get('translation_ru'),
        'zh': global_vocab.get('translation_zh'),
        'vi': global_vocab.get('translation_vi')
    }
    
    has_any_translation = any(translations.values())
    if not has_any_translation:
        return
    
    source_lang = None
    source_text = None
    for lang, text in translations.items():
        if text:
            source_lang = lang
            source_text = text
            break
    
    if not source_text or not GoogleTranslator:
        return
    
    def translate_to_lang_sync(target_lang: str):
        if translations[target_lang]:
            return
        try:
            translated = GoogleTranslator(source=source_lang, target=target_lang).translate(source_text)
            if translated:
                upsert_global_vocab(base, pos, translated, '', target_lang)
        except Exception:
            pass
    
    target_langs = [lang for lang in ['en', 'ru', 'zh', 'vi'] if not translations[lang]]
    if target_langs:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        await asyncio.gather(*[loop.run_in_executor(None, translate_to_lang_sync, lang) for lang in target_langs])

def handle_vocab_ingest(b: bytes, user_id: int, native_language: str = 'en') -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'success': False, 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    if not text or save_freq is None:
        return {'success': False, 'error': 'no_text_or_deps'}
    df = save_freq(text)
    df = df.rename(columns={'word': 'base'})[['base','pos','count']]
    for _, row in df.iterrows():
        base = str(row['base'])
        pos = str(row['pos'])
        count_delta = int(row['count'])
        
        global_vocab = get_global_vocab(base, pos) if get_global_vocab else None
        
        if global_vocab:
            increment_global_vocab_count(base, pos) if increment_global_vocab_count else None
            existing_translation = get_vocab_translation(base, pos, native_language) if get_vocab_translation else None
            if not existing_translation:
                translation = get_translation(base, None, native_language)
                if translation:
                    upsert_global_vocab(base, pos, translation, '', native_language) if upsert_global_vocab else None
            
            threading.Thread(target=lambda: asyncio.run(translate_base_to_all_languages(base, pos)), daemon=True).start()
        else:
            existing_translation = get_vocab_translation(base, pos, native_language) if get_vocab_translation else None
            translation = get_translation(base, existing_translation, native_language)
            upsert_global_vocab(base, pos, translation, '', native_language) if upsert_global_vocab else None
            
            if generate_audio_file:
                threading.Thread(target=lambda: generate_audio_and_update(base, pos), daemon=True).start()
        
        upsert_user_vocab(user_id, base, pos, count_delta) if upsert_user_vocab else None
    
    return {'success': True}

def generate_audio_and_update(base, pos):
    if generate_audio_file:
        generate_audio_file(base, pos)

def handle_tts(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'success': False, 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    lang = str(j.get('lang', 'ko')).strip()
    if not text or save_to_file is None:
        return {'success': False, 'error': 'no_text_or_deps'}
    try:
        import tempfile
        import uuid
        temp_filename = os.path.join(tempfile.gettempdir(), f'tts_{uuid.uuid4().hex}.mp3')
        filename = save_to_file(text, lang=lang, filename=temp_filename)
        with open(filename, 'rb') as f:
            audio_data = f.read()
        import base64
        encoded = base64.b64encode(audio_data).decode('utf-8')
        try:
            os.remove(filename)
        except Exception:
            pass
        return {'success': True, 'audio': encoded, 'error': ''}
    except Exception as e:
        return {'success': False, 'error': str(e)[:100]}

def start_ws(port: int):
    if not websockets:
        return
    
    async def run_ws():
        # Create the server while an event loop is running to satisfy websockets' get_running_loop
        await websockets.serve(ws_handler, 'localhost', port)
        # Keep the coroutine alive forever
        await asyncio.Event().wait()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ws())

if __name__ == '__main__':
    if db_pool:
        db_pool.init_pool()
    
    http_thread = threading.Thread(target=start_http, args=(8000,), daemon=True)
    ws_thread = threading.Thread(target=start_ws, args=(8765,), daemon=True)
    
    http_thread.start()
    ws_thread.start()
        
    http_thread.join()
    ws_thread.join()

from http.server import BaseHTTPRequestHandler, HTTPServer
import asyncio
import json
import threading
import base64
import os
import sys
import urllib.parse
import urllib.request
import pandas as pd
from datetime import datetime
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_root)

try:
    from audio_to_text import process_frames as at_process_frames
    from audio_to_text import set_lang as at_set_lang
    from audio_to_text import set_rate as at_set_rate
    from audio_to_text import set_channels as at_set_channels
    from audio_to_text import force_final as at_force_final
except Exception as e:
    at_process_frames = None
    at_set_lang = None
    at_set_rate = None
    at_set_channels = None
    at_force_final = None
    print("asr_import_error", str(e), flush=True)

try:
    from logic.text.analysis import save_freq
except Exception as e:
    save_freq = None
    print("analysis_import_error", str(e), flush=True)

try:
    from logic.text.translate import translation_api_call
except Exception as e:
    translation_api_call = None
    print("openai_translation_import_error", str(e), flush=True)

try:
    from logic.tss.tss import speak, save_to_file
except Exception as e:
    speak = None
    save_to_file = None
    print("tss_import_error", str(e), flush=True)

try:
    from database.connection import db_pool
    from database.queries import get_user_vocab, get_global_vocab, upsert_global_vocab, increment_global_vocab_count, upsert_user_vocab, get_vocab_translation, record_remember, record_dont_remember, is_admin
    from api.auth import handle_register, handle_login
    from api.middleware import require_auth, create_auth_response
    from api.admin import handle_admin_login, handle_admin_list_users, handle_admin_delete_user, handle_admin_add_user, handle_admin_list_vocab, handle_admin_delete_vocab, handle_admin_update_translation
except Exception as e:
    db_pool = None
    handle_register = None
    handle_login = None
    require_auth = None
    create_auth_response = None
    handle_admin_login = None
    handle_admin_list_users = None
    handle_admin_delete_user = None
    handle_admin_add_user = None
    handle_admin_list_vocab = None
    handle_admin_delete_vocab = None
    handle_admin_update_translation = None
    print("auth_import_error", str(e), flush=True)

try:
    from generate_audio import generate_audio_file
except Exception:
    generate_audio_file = None

try:
    import websockets
except Exception:
    websockets = None

class SimpleHandler(BaseHTTPRequestHandler):
    def _set_cors(self):
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '3600')

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        if path in ('/', '/debug'):
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'base.html')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                body = b'OK'
                ct = 'text/plain; charset=utf-8'
        elif path == '/app':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'base.html')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                body = b'OK'
                ct = 'text/plain; charset=utf-8'
        elif path.startswith('/src/'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                if fname.endswith('.js'):
                    ct = 'application/javascript; charset=utf-8'
                else:
                    ct = 'text/plain; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path == '/style.css':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'style.css')
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/css; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path.endswith('.js'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'application/javascript; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path == '/admin' or path == '/admin.html':
            try:
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'admin.html')
                abs_path = os.path.abspath(p)
                if not os.path.exists(abs_path):
                    print(f"Admin file not found at: {abs_path}", flush=True)
                    self.send_error(404)
                    return
                with open(abs_path, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception as e:
                print(f"Error serving admin.html: {e}", flush=True)
                import traceback
                traceback.print_exc()
                self.send_error(404)
                return
        elif path.endswith('.html'):
            try:
                fname = path[1:]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', fname)
                if not os.path.exists(p):
                    print(f"File not found: {p} (requested: {path})", flush=True)
                    self.send_error(404)
                    return
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception as e:
                print(f"Error serving HTML file {path}: {e}", flush=True)
                self.send_error(404)
                return
        elif path.startswith('/templates/'):
            try:
                fname = path[len('/templates/'):]
                p = os.path.join(os.path.dirname(__file__), '..', '..', 'front-end', 'templates', fname)
                with open(p, 'rb') as f:
                    body = f.read()
                ct = 'text/html; charset=utf-8'
            except Exception:
                self.send_error(404)
                return
        elif path.startswith('/data/'):
            fname = urllib.parse.unquote(path[6:])
            try:
                fpath = os.path.join(os.path.dirname(__file__), '..', 'database', 'data', fname)
                if os.path.exists(fpath) and os.path.isfile(fpath):
                    with open(fpath, 'rb') as f:
                        body = f.read()
                    if fname.endswith('.csv'):
                        ct = 'text/csv; charset=utf-8'
                    elif fname.endswith('.mp3'):
                        ct = 'audio/mpeg'
                    else:
                        ct = 'application/octet-stream'
                else:
                    print(f"File not found: {fpath} (requested: {path})", flush=True)
                    self.send_error(404)
                    return
            except Exception as e:
                print(f"Error serving file {path}: {e}", flush=True)
                self.send_error(404)
                return
        elif path == '/vocab/list':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'items': [], 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            try:
                native_lang = user.get('native_language', 'en') or 'en'
                rows = get_user_vocab(user['id'], native_lang) if get_user_vocab else []
                body = json.dumps({'items': rows}, ensure_ascii=False).encode('utf-8')
                ct = 'application/json; charset=utf-8'
            except Exception:
                body = json.dumps({'items': []}).encode('utf-8')
                ct = 'application/json; charset=utf-8'
        else:
            body = b'OK'
            ct = 'text/plain; charset=utf-8'
        
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == '/register':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_register(b) if handle_register else {'success': False, 'error': 'auth_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/login':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            print(f"Login request received: {len(b)} bytes", flush=True)
            try:
                import json as json_module
                req_data = json_module.loads(b.decode('utf-8'))
                print(f"Login attempt for user: {req_data.get('username', 'unknown')}", flush=True)
            except Exception as e:
                print(f"Error parsing login request: {e}", flush=True)
            out = handle_login(b) if handle_login else {'success': False, 'error': 'auth_not_available'}
            print(f"Login response: success={out.get('success', False)}, error={out.get('error', 'none')}", flush=True)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/upload':
            n = int(self.headers.get('Content-Length', 0))
            _ = self.rfile.read(n)
            body = b'audio received'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(body)
            return
        elif self.path == '/translate':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_translate(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/analyze':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'words': [], 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_analyze(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/vocab/ingest':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            native_lang = user.get('native_language', 'en') or 'en'
            out = handle_vocab_ingest(b, user['id'], native_lang)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/learn/remember':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                base = str(j.get('base', ''))
                pos = str(j.get('pos', ''))
                if base and pos:
                    success = record_remember(user['id'], base, pos) if record_remember else False
                    out = {'success': success}
                else:
                    out = {'success': False, 'error': 'missing_fields'}
            except Exception:
                out = {'success': False, 'error': 'bad_json'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/learn/dont-remember':
            user = require_auth(dict(self.headers)) if require_auth else None
            if not user:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                base = str(j.get('base', ''))
                pos = str(j.get('pos', ''))
                if base and pos:
                    success = record_dont_remember(user['id'], base, pos) if record_dont_remember else False
                    out = {'success': success}
                else:
                    out = {'success': False, 'error': 'missing_fields'}
            except Exception:
                out = {'success': False, 'error': 'bad_json'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/tts':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_tts(b)
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/login':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            out = handle_admin_login(b) if handle_admin_login else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n) if n > 0 else b'{}'
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('username', '')
                password = j.get('password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_list_users() if handle_admin_list_users else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users/delete':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('admin_username', '')
                password = j.get('admin_password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_delete_user(b) if handle_admin_delete_user else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/users/add':
            n = int(self.headers.get('Content-Length', 0))
            b = self.rfile.read(n)
            try:
                j = json.loads(b.decode('utf-8'))
                username = j.get('admin_username', '')
                password = j.get('admin_password', '')
                if not is_admin(username, password) if is_admin else False:
                    body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception:
                body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
            out = handle_admin_add_user(b) if handle_admin_add_user else {'success': False, 'error': 'admin_not_available'}
            data = json.dumps(out, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        elif self.path == '/admin/vocab':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n) if n > 0 else b'{}'
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('username', '')
                    password = j.get('password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_list_vocab() if handle_admin_list_vocab else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
        elif self.path == '/admin/vocab/delete':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n)
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('admin_username', '')
                    password = j.get('admin_password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_delete_vocab(b) if handle_admin_delete_vocab else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return
        elif self.path == '/admin/translations/update':
            try:
                n = int(self.headers.get('Content-Length', 0))
                b = self.rfile.read(n)
                try:
                    j = json.loads(b.decode('utf-8'))
                    username = j.get('admin_username', '')
                    password = j.get('admin_password', '')
                    if not is_admin(username, password) if is_admin else False:
                        body = json.dumps({'success': False, 'error': 'unauthorized'}).encode('utf-8')
                        self.send_response(401)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self._set_cors()
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except Exception as e:
                    body = json.dumps({'success': False, 'error': 'unauthorized', 'details': str(e)}).encode('utf-8')
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self._set_cors()
                    self.end_headers()
                    self.wfile.write(body)
                    return
                out = handle_admin_update_translation(b) if handle_admin_update_translation else {'success': False, 'error': 'admin_not_available'}
                data = json.dumps(out, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                body = json.dumps({'success': False, 'error': 'server_error', 'details': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self._set_cors()
                self.end_headers()
                self.wfile.write(body)
                return

        body = json.dumps({'success': False, 'error': 'not_found'}).encode('utf-8')
        self.send_response(404)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

def start_http(port: int):
    HTTPServer(('', port), SimpleHandler).serve_forever()

def build_msg(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)

def parse_json(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {}

async def ws_handler(websocket, path):
    try:
        async for message in websocket:
            data = parse_json(message)
            if data.get('type') == 'ping':
                await websocket.send(build_msg({'type': 'pong'}))
            elif data.get('type') == 'audio':
                frames = data.get('frames', [])
                if at_process_frames:
                    result = at_process_frames(frames)
                    await websocket.send(build_msg({'type': 'transcript', 'text': result}))
    except Exception as e:
        print(f"ws_error: {e}", flush=True)

def handle_translate(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'text': '', 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    source = str(j.get('source', 'auto')).strip()
    target = str(j.get('target', 'en')).strip()
    if not text:
        return {'text': '', 'error': 'no_text'}
    
    # Try OpenAI API first (for Browser STT transcripts)
    if translation_api_call:
        try:
            # Map language codes if needed
            source_lang = source if source != 'auto' else 'en'
            result = translation_api_call(text, source_lang, target)
            return {'text': result, 'error': ''}
        except Exception as e:
            print(f"OpenAI translation failed: {e}, falling back to Google Translator", flush=True)
            # Fall through to Google Translator fallback
    
    # Fallback to Google Translator if OpenAI fails or is unavailable
    try:
        if GoogleTranslator:
            result = GoogleTranslator(source=source, target=target).translate(text)
            return {'text': result, 'error': ''}
        else:
            return {'text': 'Translation service unavailable', 'error': 'no_translator'}
    except Exception as e:
        return {'text': '', 'error': str(e)[:100]}

def handle_analyze(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'words': [], 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    if not text or save_freq is None:
        return {'words': [], 'error': 'no_text_or_deps'}
    try:
        df = save_freq(text)
        words = df[['word']].to_dict('records')
        return {'words': words, 'error': ''}
    except Exception as e:
        return {'words': [], 'error': str(e)[:100]}

def get_translation(word: str, existing_translation, target_lang: str = 'en'):
    if existing_translation:
        return existing_translation
    if GoogleTranslator:
        try:
            return GoogleTranslator(source='ko', target=target_lang).translate(word)
        except Exception:
            return ''
    return ''

async def translate_base_to_all_languages(base: str, pos: str):
    global_vocab = get_global_vocab(base, pos) if get_global_vocab else None
    if not global_vocab:
        return
    
    translations = {
        'en': global_vocab.get('translation_en'),
        'ru': global_vocab.get('translation_ru'),
        'zh': global_vocab.get('translation_zh'),
        'vi': global_vocab.get('translation_vi')
    }
    
    has_any_translation = any(translations.values())
    if not has_any_translation:
        return
    
    source_lang = None
    source_text = None
    for lang, text in translations.items():
        if text:
            source_lang = lang
            source_text = text
            break
    
    if not source_text or not GoogleTranslator:
        return
    
    def translate_to_lang_sync(target_lang: str):
        if translations[target_lang]:
            return
        try:
            translated = GoogleTranslator(source=source_lang, target=target_lang).translate(source_text)
            if translated:
                upsert_global_vocab(base, pos, translated, '', target_lang)
        except Exception:
            pass
    
    target_langs = [lang for lang in ['en', 'ru', 'zh', 'vi'] if not translations[lang]]
    if target_langs:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        await asyncio.gather(*[loop.run_in_executor(None, translate_to_lang_sync, lang) for lang in target_langs])

def handle_vocab_ingest(b: bytes, user_id: int, native_language: str = 'en') -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'success': False, 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    if not text or save_freq is None:
        return {'success': False, 'error': 'no_text_or_deps'}
    df = save_freq(text)
    df = df.rename(columns={'word': 'base'})[['base','pos','count']]
    for _, row in df.iterrows():
        base = str(row['base'])
        pos = str(row['pos'])
        count_delta = int(row['count'])
        
        global_vocab = get_global_vocab(base, pos) if get_global_vocab else None
        
        if global_vocab:
            increment_global_vocab_count(base, pos) if increment_global_vocab_count else None
            existing_translation = get_vocab_translation(base, pos, native_language) if get_vocab_translation else None
            if not existing_translation:
                translation = get_translation(base, None, native_language)
                if translation:
                    upsert_global_vocab(base, pos, translation, '', native_language) if upsert_global_vocab else None
            
            threading.Thread(target=lambda: asyncio.run(translate_base_to_all_languages(base, pos)), daemon=True).start()
        else:
            existing_translation = get_vocab_translation(base, pos, native_language) if get_vocab_translation else None
            translation = get_translation(base, existing_translation, native_language)
            upsert_global_vocab(base, pos, translation, '', native_language) if upsert_global_vocab else None
            
            if generate_audio_file:
                threading.Thread(target=lambda: generate_audio_and_update(base, pos), daemon=True).start()
        
        upsert_user_vocab(user_id, base, pos, count_delta) if upsert_user_vocab else None
    
    return {'success': True}

def generate_audio_and_update(base, pos):
    if generate_audio_file:
        generate_audio_file(base, pos)

def handle_tts(b: bytes) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'success': False, 'error': 'bad_json'}
    text = str(j.get('text', '')).strip()
    lang = str(j.get('lang', 'ko')).strip()
    if not text or save_to_file is None:
        return {'success': False, 'error': 'no_text_or_deps'}
    try:
        import tempfile
        import uuid
        temp_filename = os.path.join(tempfile.gettempdir(), f'tts_{uuid.uuid4().hex}.mp3')
        filename = save_to_file(text, lang=lang, filename=temp_filename)
        with open(filename, 'rb') as f:
            audio_data = f.read()
        import base64
        encoded = base64.b64encode(audio_data).decode('utf-8')
        try:
            os.remove(filename)
        except Exception:
            pass
        return {'success': True, 'audio': encoded, 'error': ''}
    except Exception as e:
        return {'success': False, 'error': str(e)[:100]}

def start_ws(port: int):
    if websockets:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server = loop.run_until_complete(websockets.serve(ws_handler, 'localhost', port))
        loop.run_forever()

if __name__ == '__main__':
    if db_pool:
        db_pool.init_pool()
    
    http_thread = threading.Thread(target=start_http, args=(8000,), daemon=True)
    ws_thread = threading.Thread(target=start_ws, args=(8765,), daemon=True)
    
    http_thread.start()
    ws_thread.start()
        
    http_thread.join()
    ws_thread.join()
