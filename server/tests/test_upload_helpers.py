from app.upload.router import asset_type_from_mime, extension_from_filename


def test_asset_type_from_mime():
    assert asset_type_from_mime("image/jpeg") == "photo"
    assert asset_type_from_mime("video/mp4") == "video"
    assert asset_type_from_mime("application/octet-stream") == "unknown"
    assert asset_type_from_mime(None) == "unknown"


def test_extension_from_filename_prefers_filename():
    assert extension_from_filename("IMG_001.JPG", "image/jpeg") == ".jpg"
    assert extension_from_filename("IMG_001", "image/jpeg") in {".jpg", ".jpe", ".jpeg"}

