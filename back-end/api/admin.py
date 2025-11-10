import json
from typing import Dict, Any
from database.models import UserCreate, AuthResult
from database.queries import is_admin, get_all_users, delete_user, create_user, get_all_global_vocab, delete_global_vocab, update_global_vocab_translation

def handle_admin_login(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        username = json_data.get('username', '')
        password = json_data.get('password', '')
        
        if is_admin(username, password):
            return {'success': True, 'admin': True}
        else:
            return {'success': False, 'error': 'invalid_credentials'}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_list_users() -> Dict[str, Any]:
    try:
        users = get_all_users()
        return {'success': True, 'users': users}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_delete_user(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        user_id = json_data.get('user_id')
        
        if user_id is None:
            return {'success': False, 'error': 'missing_user_id'}
        
        success = delete_user(user_id)
        if success:
            return {'success': True}
        else:
            return {'success': False, 'error': 'user_not_found'}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_add_user(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        user_data = UserCreate(
            username=json_data.get('username', ''),
            email=json_data.get('email', ''),
            password=json_data.get('password', ''),
            native_language=json_data.get('native_language'),
            target_language=json_data.get('target_language', 'ko')
        )
        
        if not user_data.username or not user_data.email or not user_data.password:
            return {'success': False, 'error': 'missing_fields'}
        
        result = create_user(user_data)
        if result.success:
            return {
                'success': True,
                'user': {
                    'id': result.user.id,
                    'username': result.user.username,
                    'email': result.user.email,
                    'native_language': result.user.native_language,
                    'target_language': result.user.target_language
                }
            }
        else:
            return {'success': False, 'error': result.error}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_list_vocab() -> Dict[str, Any]:
    try:
        vocab = get_all_global_vocab()
        return {'success': True, 'vocab': vocab}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_delete_vocab(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        base = json_data.get('base')
        pos = json_data.get('pos')
        
        if not base or not pos:
            return {'success': False, 'error': 'missing_fields'}
        
        success = delete_global_vocab(base, pos)
        if success:
            return {'success': True}
        else:
            return {'success': False, 'error': 'vocab_not_found'}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_admin_update_translation(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        base = json_data.get('base')
        pos = json_data.get('pos')
        translation = json_data.get('translation', '')
        target_lang = json_data.get('target_lang', 'en')
        
        if not base or not pos:
            return {'success': False, 'error': 'missing_fields'}
        
        success = update_global_vocab_translation(base, pos, translation, target_lang)
        if success:
            return {'success': True}
        else:
            return {'success': False, 'error': 'vocab_not_found'}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


