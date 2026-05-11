import base64
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.common.errors import APIError
from app.common.responses import ok
from app.db.session import get_db
from app.models import Asset, AssetFile, User
from app.storage.local import LocalStorageAdapter

router = APIRouter()


def file_url(asset_id: uuid.UUID, role: str) -> str:
    return f"/api/assets/{asset_id}/{role}"


def asset_payload(asset: Asset, detail: bool = False) -> dict:
    files = {file.file_role: file for file in asset.files}
    payload = {
        "id": str(asset.id),
        "asset_type": asset.asset_type,
        "original_filename": asset.original_filename,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "width": asset.width,
        "height": asset.height,
        "duration_ms": asset.duration_ms,
        "taken_at": asset.taken_at.isoformat() if asset.taken_at else None,
        "imported_at": asset.imported_at.isoformat(),
        "favorite": asset.favorite,
        "ai_status": asset.ai_status,
        "thumbnail_url": file_url(asset.id, "thumbnail") if "thumbnail" in files else None,
    }
    if detail:
        payload["file_hash"] = asset.file_hash
        payload["files"] = {
            "thumbnail_url": file_url(asset.id, "thumbnail") if "thumbnail" in files else None,
            "preview_url": file_url(asset.id, "preview") if "preview" in files else None,
            "original_url": file_url(asset.id, "original") if "original" in files else None,
        }
    return payload


def encode_cursor(asset: Asset) -> str:
    raw = json.dumps({"imported_at": asset.imported_at.isoformat(), "id": str(asset.id)})
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
        return datetime.fromisoformat(data["imported_at"]), uuid.UUID(data["id"])
    except Exception as exc:
        raise APIError("VALIDATION_ERROR", "游标无效") from exc


@router.get("")
def list_assets(
    request: Request,
    cursor: str | None = None,
    limit: int = 100,
    type: str | None = None,
    favorite: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 200)
    stmt = (
        select(Asset)
        .options(selectinload(Asset.files))
        .where(Asset.owner_user_id == current_user.id, Asset.deleted_at.is_(None), Asset.hidden.is_(False))
    )
    if type:
        stmt = stmt.where(Asset.asset_type == type)
    if favorite is not None:
        stmt = stmt.where(Asset.favorite.is_(favorite))
    if cursor:
        cursor_imported_at, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Asset.imported_at < cursor_imported_at,
                and_(Asset.imported_at == cursor_imported_at, Asset.id < cursor_id),
            )
        )

    return_assets = list(db.scalars(stmt.order_by(Asset.imported_at.desc(), Asset.id.desc()).limit(limit + 1)))
    if not return_assets:
        return ok(request, {"items": [], "next_cursor": None, "has_more": False})
    has_more = len(return_assets) > limit
    items = return_assets[:limit]
    next_cursor = encode_cursor(items[-1]) if has_more and items else None
    return ok(request, {"items": [asset_payload(asset) for asset in items], "next_cursor": next_cursor, "has_more": has_more})


@router.get("/{asset_id}")
def get_asset(
    asset_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = db.scalar(
        select(Asset)
        .options(selectinload(Asset.files))
        .where(Asset.id == asset_id, Asset.owner_user_id == current_user.id, Asset.deleted_at.is_(None))
    )
    if asset is None:
        raise APIError("ASSET_NOT_FOUND", "照片不存在或无权访问", status.HTTP_404_NOT_FOUND)
    return ok(request, asset_payload(asset, detail=True))


def asset_file_response(asset_id: uuid.UUID, role: str, current_user: User, db: Session):
    asset_file = db.scalar(
        select(AssetFile)
        .join(Asset, Asset.id == AssetFile.asset_id)
        .where(
            Asset.id == asset_id,
            Asset.owner_user_id == current_user.id,
            Asset.deleted_at.is_(None),
            AssetFile.file_role == role,
        )
    )
    if asset_file is None:
        raise APIError("ASSET_NOT_FOUND", "文件不存在或无权访问", status.HTTP_404_NOT_FOUND)
    storage = LocalStorageAdapter()
    path = storage.get_abs_path(asset_file.relative_path)
    return FileResponse(path, media_type=asset_file.mime_type, filename=None)


@router.get("/{asset_id}/original")
def get_original(asset_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return asset_file_response(asset_id, "original", current_user, db)


@router.get("/{asset_id}/thumbnail")
def get_thumbnail(asset_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return asset_file_response(asset_id, "thumbnail", current_user, db)


@router.get("/{asset_id}/preview")
def get_preview(asset_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return asset_file_response(asset_id, "preview", current_user, db)


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.owner_user_id == current_user.id))
    if asset is None or asset.deleted_at is not None:
        raise APIError("ASSET_NOT_FOUND", "照片不存在或无权访问", status.HTTP_404_NOT_FOUND)
    asset.deleted_at = datetime.utcnow()
    asset.status = "deleted"
    db.commit()
    return ok(request, {"deleted": True})
