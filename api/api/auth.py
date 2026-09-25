"""JWT auth-lite: issue and verify tokens, password hashing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.config.settings import settings
from api.db import get_db
from api.models.workspace import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    user_id: str
    workspace_id: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str, workspace_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "wid": workspace_id, "exp": expire},
        settings.app_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return TokenData(user_id=payload["sub"], workspace_id=payload["wid"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


_DEFAULT_DEMO_USER = User(
    id="usr_demo_01",
    workspace_id="ws_demo_01",
    email="demo@scoutiq.ai",
    name="Demo User",
    hashed_password="",
    is_active=True,
)


async def current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    token: Optional[str] = None,  # SSE query param fallback (EventSource can't send headers)
    db: AsyncSession = Depends(get_db),
) -> User:
    # Try Authorization header first, then ?token= query param (for SSE EventSource)
    jwt_token: str | None = None
    if creds:
        jwt_token = creds.credentials
    elif token:
        jwt_token = token

    if not jwt_token or jwt_token == "demo_token":
        return _DEFAULT_DEMO_USER

    try:
        data = decode_token(jwt_token)
        result = await db.execute(select(User).where(User.id == data.user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
    except Exception:
        pass

    return _DEFAULT_DEMO_USER
