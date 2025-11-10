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
    from logic.text.translate import translation_api_call, translate_vocab_batch
except Exception as e:
    translation_api_call = None
    translate_vocab_batch = None
    print("translate_import_error", str(e), flush=True)

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
            out = handle_recording_save(b, user['id'])
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
    try:
        if translation_api_call:
            if source == 'auto':
                source = 'en'
            result = translation_api_call(text, source, target)
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
    
    base_pos_pairs = [(str(row['base']), str(row['pos'])) for _, row in df.iterrows()]
    
    if not base_pos_pairs:
        return {'success': False, 'error': 'no_words'}
    
    target_languages = ['en', 'ru', 'zh', 'vi']
    existing_vocab = {}
    missing_pairs = []
    
    for base, pos in base_pos_pairs:
        global_vocab = get_global_vocab(base, pos) if get_global_vocab else None
        if global_vocab:
            existing_vocab[(base, pos)] = global_vocab
        else:
            missing_pairs.append((base, pos))
    
    translations = {}
    if missing_pairs and translate_vocab_batch:
        translations = translate_vocab_batch(text, missing_pairs, target_languages)
    
    for _, row in df.iterrows():
        base = str(row['base'])
        pos = str(row['pos'])
        count_delta = int(row['count'])
        
        if (base, pos) in existing_vocab:
            increment_global_vocab_count(base, pos) if increment_global_vocab_count else None
        else:
            if (base, pos) in translations:
                trans_dict = translations[(base, pos)]
                for lang in target_languages:
                    if lang in trans_dict and trans_dict[lang]:
                        upsert_global_vocab(base, pos, trans_dict[lang], '', lang) if upsert_global_vocab else None
            
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

def handle_recording_save(b: bytes, user_id: int) -> dict:
    try:
        j = json.loads(b.decode('utf-8'))
    except Exception:
        return {'success': False, 'error': 'bad_json'}
    audio_base64 = j.get('audio', '')
    role = str(j.get('role', '')).strip()
    transcript = str(j.get('transcript', '')).strip() or None
    language = str(j.get('language', '')).strip() or None
    if not audio_base64 or not role or save_recording is None:
        return {'success': False, 'error': 'missing_fields'}
    try:
        import uuid
        audio_data = base64.b64decode(audio_base64)
        recordings_dir = os.path.join(os.path.dirname(__file__), '..', 'database', 'data', 'recordings')
        os.makedirs(recordings_dir, exist_ok=True)
        filename = f'recording_{user_id}_{uuid.uuid4().hex}.webm'
        audio_path = os.path.join(recordings_dir, filename)
        with open(audio_path, 'wb') as f:
            f.write(audio_data)
        relative_path = f'recordings/{filename}'
        success = save_recording(user_id, role, relative_path, transcript, language)
        if success:
            return {'success': True, 'error': ''}
        else:
            try:
                os.remove(audio_path)
            except Exception:
                pass
            return {'success': False, 'error': 'db_save_failed'}
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
