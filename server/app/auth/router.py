from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.common.errors import APIError
from app.common.responses import ok
from app.common.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from app.config.settings import get_settings
from app.db.session import get_db
from app.models import RefreshToken, User

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-.]+$")
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str
    device_name: str | None = Field(default=None, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


def user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "used_storage_bytes": user.used_storage_bytes,
        "storage_quota_bytes": user.storage_quota_bytes,
    }


def issue_tokens(db: Session, user: User, request: Request, device_name: str | None = None) -> dict:
    settings = get_settings()
    refresh_token = new_refresh_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        device_name=device_name,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh)
    db.commit()
    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": user_payload(user),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    conditions = [User.username == payload.username]
    if payload.email:
        conditions.append(User.email == str(payload.email))
    existing = db.scalar(select(User).where(or_(*conditions)))
    if existing is not None:
        raise APIError("USER_EXISTS", "用户名或邮箱已存在", status.HTTP_409_CONFLICT)

    user_count = db.scalar(select(User.id).limit(1))
    user = User(
        username=payload.username,
        email=str(payload.email) if payload.email else None,
        display_name=payload.display_name or payload.username,
        password_hash=hash_password(payload.password),
        role="admin" if user_count is None else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(request, user_payload(user))


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise APIError("INVALID_CREDENTIALS", "账号或密码错误", status.HTTP_401_UNAUTHORIZED)
    if user.status != "active":
        raise APIError("FORBIDDEN", "用户已停用", status.HTTP_403_FORBIDDEN)
    return ok(request, issue_tokens(db, user, request, payload.device_name))


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = hash_token(payload.refresh_token)
    refresh = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if refresh is None or refresh.revoked_at is not None or refresh.expires_at <= now:
        raise APIError("UNAUTHORIZED", "Refresh Token 无效", status.HTTP_401_UNAUTHORIZED)

    user = db.get(User, refresh.user_id)
    if user is None or user.status != "active":
        raise APIError("UNAUTHORIZED", "用户不存在或已停用", status.HTTP_401_UNAUTHORIZED)

    refresh.revoked_at = now
    tokens = issue_tokens(db, user, request, refresh.device_name)
    db.commit()
    return ok(request, tokens)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(UTC)
    if payload.refresh_token:
        token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
        if token is not None and token.user_id == current_user.id:
            token.revoked_at = now
    else:
        for token in db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
        ):
            token.revoked_at = now
    db.commit()
    return ok(request, {"logged_out": True})


@router.get("/me")
def me(request: Request, current_user: User = Depends(get_current_user)):
    return ok(request, user_payload(current_user))
