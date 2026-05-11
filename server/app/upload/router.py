import hashlib
import math
import mimetypes
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.common.errors import APIError
from app.common.responses import ok
from app.config.settings import get_settings
from app.db.session import get_db
from app.models import Asset, AssetFile, Library, StorageLocation, UploadPart, UploadSession, User
from app.storage.local import LocalStorageAdapter

router = APIRouter()


class CreateUploadSessionRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    file_hash: str = Field(min_length=64, max_length=128)
    file_size: int = Field(gt=0)
    mime_type: str | None = Field(default=None, max_length=128)
    chunk_size: int | None = Field(default=None, gt=0)
    device_asset_id: str | None = None
    taken_at: datetime | None = None


class CompleteUploadRequest(BaseModel):
    file_hash: str = Field(min_length=64, max_length=128)


def get_default_library(db: Session) -> Library:
    library = db.scalar(
        select(Library)
        .join(StorageLocation, StorageLocation.id == Library.storage_location_id)
        .where(Library.library_type == "managed", Library.is_readonly.is_(False), StorageLocation.status == "active")
        .order_by(Library.created_at.asc())
    )
    if library is None:
        raise APIError("STORAGE_UNAVAILABLE", "默认存储未初始化，请运行 photoai-init-storage", status.HTTP_503_SERVICE_UNAVAILABLE)
    return library


def asset_type_from_mime(mime_type: str | None) -> str:
    if mime_type and mime_type.startswith("video/"):
        return "video"
    if mime_type and mime_type.startswith("image/"):
        return "photo"
    return "unknown"


def extension_from_filename(filename: str, mime_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix:
        return suffix
    guessed = mimetypes.guess_extension(mime_type or "")
    return guessed or ".bin"


def upload_session_payload(session: UploadSession, parts: list[UploadPart] | None = None) -> dict:
    uploaded_parts = sorted(part.part_index for part in (parts or session.parts))
    return {
        "id": str(session.id),
        "filename": session.filename,
        "file_hash": session.file_hash,
        "file_size": session.file_size,
        "chunk_size": session.chunk_size,
        "total_chunks": session.total_chunks,
        "uploaded_chunks": session.uploaded_chunks,
        "uploaded_parts": uploaded_parts,
        "status": session.status,
        "asset_id": str(session.asset_id) if session.asset_id else None,
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateUploadSessionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if payload.file_size > settings.max_upload_size:
        raise APIError("VALIDATION_ERROR", "文件超过最大上传限制", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    existing = db.scalar(
        select(Asset).where(
            Asset.owner_user_id == current_user.id,
            Asset.file_hash == payload.file_hash,
            Asset.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return ok(
            request,
            {"session_id": None, "status": "completed", "asset_exists": True, "asset_id": str(existing.id)},
        )

    chunk_size = payload.chunk_size or settings.default_chunk_size
    library = get_default_library(db)
    session = UploadSession(
        user_id=current_user.id,
        filename=payload.filename,
        file_hash=payload.file_hash,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        chunk_size=chunk_size,
        total_chunks=math.ceil(payload.file_size / chunk_size),
        target_library_id=library.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ok(
        request,
        {
            "session_id": str(session.id),
            "status": session.status,
            "chunk_size": session.chunk_size,
            "total_chunks": session.total_chunks,
            "uploaded_parts": [],
            "asset_exists": False,
            "asset_id": None,
        },
    )


@router.put("/sessions/{session_id}/parts/{part_index}")
async def upload_part(
    session_id: uuid.UUID,
    part_index: int,
    request: Request,
    x_part_checksum: str | None = Header(default=None, alias="X-Part-Checksum"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(UploadSession).where(UploadSession.id == session_id, UploadSession.user_id == current_user.id)
    )
    if session is None:
        raise APIError("UPLOAD_SESSION_NOT_FOUND", "上传会话不存在", status.HTTP_404_NOT_FOUND)
    if session.status != "uploading":
        raise APIError("VALIDATION_ERROR", "上传会话状态不允许上传分片")
    if part_index < 0 or part_index >= session.total_chunks:
        raise APIError("VALIDATION_ERROR", "分片序号超出范围")

    content = await request.body()
    checksum = hashlib.sha256(content).hexdigest()
    if x_part_checksum and x_part_checksum.lower() != checksum:
        raise APIError("HASH_MISMATCH", "分片 hash 不一致")

    relative_path = f"cache/uploads/{current_user.id}/{session.id}/{part_index}"
    storage = LocalStorageAdapter()
    storage.write_bytes(relative_path, content)

    part = db.scalar(
        select(UploadPart).where(UploadPart.upload_session_id == session.id, UploadPart.part_index == part_index)
    )
    if part is None:
        part = UploadPart(
            upload_session_id=session.id,
            part_index=part_index,
            part_size=len(content),
            checksum=checksum,
            temp_path=relative_path,
        )
        db.add(part)
    else:
        part.part_size = len(content)
        part.checksum = checksum
        part.temp_path = relative_path

    session.uploaded_chunks = db.scalar(
        select(func.count()).select_from(UploadPart).where(UploadPart.upload_session_id == session.id)
    ) or 0
    session.updated_at = datetime.now(UTC)
    db.commit()
    return ok(request, {"session_id": str(session.id), "part_index": part_index, "part_size": len(content), "status": "uploaded"})


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: uuid.UUID,
    payload: CompleteUploadRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(UploadSession).where(UploadSession.id == session_id, UploadSession.user_id == current_user.id)
    )
    if session is None:
        raise APIError("UPLOAD_SESSION_NOT_FOUND", "上传会话不存在", status.HTTP_404_NOT_FOUND)
    if session.status == "completed" and session.asset_id:
        return ok(request, {"asset_id": str(session.asset_id), "status": "completed", "original_file_id": None})
    if payload.file_hash != session.file_hash:
        raise APIError("HASH_MISMATCH", "文件 hash 不一致")

    parts = list(
        db.scalars(select(UploadPart).where(UploadPart.upload_session_id == session.id).order_by(UploadPart.part_index))
    )
    indexes = {part.part_index for part in parts}
    missing = [idx for idx in range(session.total_chunks) if idx not in indexes]
    if missing:
        raise APIError("UPLOAD_PART_MISSING", f"缺少上传分片: {missing}")

    library = db.get(Library, session.target_library_id)
    if library is None:
        raise APIError("STORAGE_UNAVAILABLE", "上传目标图库不存在", status.HTTP_503_SERVICE_UNAVAILABLE)

    storage = LocalStorageAdapter()
    merged_relative_path = f"cache/uploads/{current_user.id}/{session.id}/merged"
    merged_path = storage.get_abs_path(merged_relative_path)
    merged_path.parent.mkdir(parents=True, exist_ok=True)

    sha = hashlib.sha256()
    with merged_path.open("wb") as out:
        for part in parts:
            part_path = storage.get_abs_path(part.temp_path)
            with part_path.open("rb") as src:
                while chunk := src.read(1024 * 1024):
                    sha.update(chunk)
                    out.write(chunk)

    if sha.hexdigest() != session.file_hash:
        storage.delete_file(merged_relative_path)
        raise APIError("HASH_MISMATCH", "文件 hash 不一致")

    asset_id = uuid.uuid4()
    now = datetime.now(UTC)
    ext = extension_from_filename(session.filename, session.mime_type)
    final_relative_path = f"originals/{current_user.id}/{now:%Y}/{now:%m}/{asset_id}{ext}"
    storage.move_file(merged_relative_path, final_relative_path)

    asset = Asset(
        id=asset_id,
        owner_user_id=current_user.id,
        library_id=library.id,
        asset_type=asset_type_from_mime(session.mime_type),
        original_filename=session.filename,
        file_hash=session.file_hash,
        mime_type=session.mime_type,
        file_size=session.file_size,
    )
    db.add(asset)
    original_file = AssetFile(
        asset_id=asset.id,
        file_role="original",
        storage_location_id=library.storage_location_id,
        relative_path=final_relative_path,
        file_size=session.file_size,
        mime_type=session.mime_type,
        checksum=session.file_hash,
    )
    db.add(original_file)
    session.status = "completed"
    session.asset_id = asset.id
    session.updated_at = now
    current_user.used_storage_bytes += session.file_size
    db.commit()
    db.refresh(original_file)
    return ok(request, {"asset_id": str(asset.id), "status": "completed", "original_file_id": str(original_file.id)})


@router.get("/sessions/{session_id}")
def get_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(UploadSession).where(UploadSession.id == session_id, UploadSession.user_id == current_user.id)
    )
    if session is None:
        raise APIError("UPLOAD_SESSION_NOT_FOUND", "上传会话不存在", status.HTTP_404_NOT_FOUND)
    parts = list(db.scalars(select(UploadPart).where(UploadPart.upload_session_id == session.id)))
    return ok(request, upload_session_payload(session, parts))
