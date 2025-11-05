import json
from typing import Optional, Dict, Any
from database.queries import verify_token, get_user_by_id

def extract_token_from_header(headers: Dict[str, str]) -> Optional[str]:
    auth_header = headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None

def get_current_user(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    token = extract_token_from_header(headers)
    if not token:
        return None
    
    user_id = verify_token(token)
    if not user_id:
        return None
    
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'native_language': user.native_language
    }

def require_auth(headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    user = get_current_user(headers)
    if not user:
        return None
    return user

def create_auth_response(success: bool, user: Optional[Dict[str, Any]] = None, 
                       token: Optional[str] = None, error: str = "") -> Dict[str, Any]:
    response = {'success': success}
    if user:
        response['user'] = user
    if token:
        response['token'] = token
    if error:
        response['error'] = error
    return response
