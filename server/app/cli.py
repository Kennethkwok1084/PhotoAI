from pathlib import Path

from sqlalchemy import select

from app.config.settings import get_settings
from app.db.session import SessionLocal
from app.models import Library, StorageLocation


def init_storage_command() -> None:
    settings = get_settings()
    root = Path(settings.storage_root)
    for path in [
        root,
        root / "originals",
        root / "thumbnails",
        root / "previews",
        root / "cache" / "uploads",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        storage = db.scalar(select(StorageLocation).where(StorageLocation.name == "default-local"))
        if storage is None:
            storage = StorageLocation(
                name="default-local",
                type="local",
                base_path=str(root),
                is_readonly=False,
                status="active",
                config={},
            )
            db.add(storage)
            db.flush()

        library = db.scalar(select(Library).where(Library.name == "default-managed", Library.library_type == "managed"))
        if library is None:
            library = Library(
                storage_location_id=storage.id,
                name="default-managed",
                library_type="managed",
                root_path="originals",
                is_readonly=False,
                scan_enabled=True,
            )
            db.add(library)

        db.commit()

    print(f"Initialized default storage at {root}")


if __name__ == "__main__":
    init_storage_command()
