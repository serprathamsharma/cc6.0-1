"""Auth router: register, login."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.db import get_db
from api.models.workspace import User, Workspace
from api.auth import create_token, hash_password, verify_password
from api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create workspace
    ws = Workspace(
        name=body.workspace_name,
        slug=body.workspace_name.lower().replace(" ", "-")[:64],
    )
    db.add(ws)
    await db.flush()

    # Create user
    user = User(
        workspace_id=ws.id,
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    token = create_token(user.id, ws.id)
    return TokenResponse(
        access_token=token, user_id=user.id, workspace_id=ws.id,
        name=user.name, email=user.email
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.workspace_id)
    return TokenResponse(
        access_token=token, user_id=user.id, workspace_id=user.workspace_id,
        name=user.name, email=user.email
    )
