from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User, Role, UserRole
import os

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/auth/token")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

async def get_current_user(token: str=Depends(oauth2_schema), db: AsyncSession=Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return user

def require_role(role_name: str):
    async def role_checker(user=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
        q = await db.execute(
            select(Role).join(UserRole).where(UserRole.user_id == user.id).where(Role.name == role_name)
        )
        role = q.scalars().first()
        if not role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return True
    return role_checker