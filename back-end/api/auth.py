import json
from typing import Dict, Any
from database.models import UserCreate, UserLogin, AuthResult
from database.queries import create_user, authenticate_user

def handle_register(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        user_data = UserCreate(
            username=json_data.get('username', ''),
            email=json_data.get('email', ''),
            password=json_data.get('password', ''),
            native_language=json_data.get('native_language'),
            target_language=json_data.get('target_language')
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
                },
                'token': result.token
            }
        else:
            return {'success': False, 'error': result.error}
            
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_login(data: bytes) -> Dict[str, Any]:
    try:
        json_data = json.loads(data.decode('utf-8'))
        login_data = UserLogin(
            username=json_data.get('username', ''),
            password=json_data.get('password', '')
        )
        
        if not login_data.username or not login_data.password:
            return {'success': False, 'error': 'missing_fields'}
        
        result = authenticate_user(login_data)
        if result.success:
            return {
                'success': True,
                'user': {
                    'id': result.user.id,
                    'username': result.user.username,
                    'email': result.user.email,
                    'native_language': result.user.native_language,
                    'target_language': result.user.target_language
                },
                'token': result.token
            }
        else:
            return {'success': False, 'error': result.error}
            
    except json.JSONDecodeError:
        return {'success': False, 'error': 'invalid_json'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
