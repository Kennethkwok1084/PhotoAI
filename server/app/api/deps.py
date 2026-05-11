import uuid

import jwt
from fastapi import Depends, Header, status
from sqlalchemy.orm import Session

from app.common.errors import APIError
from app.common.security import decode_access_token
from app.db.session import get_db
from app.models import User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise APIError("UNAUTHORIZED", "未登录或 Token 无效", status.HTTP_401_UNAUTHORIZED)

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise APIError("UNAUTHORIZED", "未登录或 Token 无效", status.HTTP_401_UNAUTHORIZED) from exc

    if payload.get("type") != "access":
        raise APIError("UNAUTHORIZED", "Token 类型无效", status.HTTP_401_UNAUTHORIZED)

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise APIError("UNAUTHORIZED", "Token 内容无效", status.HTTP_401_UNAUTHORIZED) from exc

    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise APIError("UNAUTHORIZED", "用户不存在或已停用", status.HTTP_401_UNAUTHORIZED)
    return user

