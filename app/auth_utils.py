from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import uuid
import os
from typing import Optional

pwd_ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

def hash_password(password: str) -> str:
    """Hash a plaintext password (Argon2 preferred)."""
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_ctx.verify(plain, hashed)

def needs_rehash(hashed: str) -> bool:
    """Return True if an existing hash should be upgraded to the current preferred scheme."""
    return pwd_ctx.needs_update(hashed)

def create_access_token(*, sub: str, data: dict | None = None, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"sub": str(sub)}
    if data:
        to_encode.update(data)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def create_refresh_token_jti() -> uuid.UUID:
    return uuid.uuid4()
