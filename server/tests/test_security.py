from app.common.security import create_access_token, decode_access_token, hash_password, hash_token, verify_password


def test_password_hash_and_verify():
    password_hash = hash_password("ChangeMe123")

    assert password_hash != "ChangeMe123"
    assert verify_password("ChangeMe123", password_hash)
    assert not verify_password("WrongPassword", password_hash)


def test_token_hash_is_deterministic_sha256():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abcd")
    assert len(hash_token("abc")) == 64


def test_access_token_roundtrip():
    token = create_access_token("user-id")
    payload = decode_access_token(token)

    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"

