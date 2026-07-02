import pytest

from vulnconsole.shared.security import (
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("a-long-example-password")
    assert hashed != "a-long-example-password"
    assert verify_password("a-long-example-password", hashed)
    assert not verify_password("wrong-password-entirely", hashed)


def test_jwt_roundtrip() -> None:
    token = create_token(subject="user-1", role="viewer", kind="access")
    claims = decode_token(token, expected_kind="access")
    assert claims.sub == "user-1"
    assert claims.role == "viewer"


def test_jwt_kind_mismatch_rejected() -> None:
    refresh = create_token(subject="user-1", role="viewer", kind="refresh")
    with pytest.raises(InvalidTokenError):
        decode_token(refresh, expected_kind="access")


def test_garbage_token_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.token", expected_kind="access")
