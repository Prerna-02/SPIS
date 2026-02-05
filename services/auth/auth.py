"""
SPIS Auth Service - Password & JWT Utilities
"""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import jwt, JWTError
from config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS


def hash_password(password: str) -> str:
    """Hash password with bcrypt. Truncates to 72 bytes to avoid errors."""
    # bcrypt only uses first 72 bytes of password
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash. Truncates input to 72 bytes."""
    # bcrypt only uses first 72 bytes of password
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(user_id: str, username: str, role: str) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_user_id(token: str) -> Optional[str]:
    """Extract user_id from token."""
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None
