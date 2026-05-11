from pathlib import Path
from shutil import move
from typing import BinaryIO

from app.common.errors import APIError
from app.config.settings import get_settings


class LocalStorageAdapter:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def get_abs_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise APIError("VALIDATION_ERROR", "非法文件路径")
        return candidate

    def save_file(self, relative_path: str, fileobj: BinaryIO) -> str:
        target = self.get_abs_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            while chunk := fileobj.read(1024 * 1024):
                out.write(chunk)
        return relative_path

    def write_bytes(self, relative_path: str, content: bytes) -> str:
        target = self.get_abs_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative_path

    def exists(self, relative_path: str) -> bool:
        return self.get_abs_path(relative_path).exists()

    def open_file(self, relative_path: str):
        return self.get_abs_path(relative_path).open("rb")

    def move_file(self, source_relative_path: str, target_relative_path: str) -> str:
        source = self.get_abs_path(source_relative_path)
        target = self.get_abs_path(target_relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        move(str(source), str(target))
        return target_relative_path

    def delete_file(self, relative_path: str) -> None:
        self.get_abs_path(relative_path).unlink(missing_ok=True)

