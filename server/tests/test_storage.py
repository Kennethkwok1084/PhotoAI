import io

import pytest

from app.common.errors import APIError
from app.storage.local import LocalStorageAdapter


def test_local_storage_write_and_read(tmp_path):
    storage = LocalStorageAdapter(tmp_path)

    storage.save_file("originals/u/2026/05/a.jpg", io.BytesIO(b"photo"))

    assert storage.exists("originals/u/2026/05/a.jpg")
    with storage.open_file("originals/u/2026/05/a.jpg") as file:
        assert file.read() == b"photo"


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorageAdapter(tmp_path)

    with pytest.raises(APIError):
        storage.get_abs_path("../outside.txt")

