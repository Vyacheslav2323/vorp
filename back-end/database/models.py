from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    created_at: datetime
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    last_login: Optional[datetime] = None

@dataclass
class UserCreate:
    username: str
    email: str
    password: str
    native_language: Optional[str] = None
    target_language: Optional[str] = None

@dataclass
class UserLogin:
    username: str
    password: str

@dataclass
class AuthResult:
    success: bool
    user: Optional[User] = None
    token: Optional[str] = None
    error: str = ""


