import pytest

from vulnconsole.shared.pagination import clamp_limit, decode_cursor, encode_cursor
from vulnconsole.shared.problems import ProblemError


def test_cursor_roundtrip() -> None:
    payload = {"f": "2026-07-02T12:00:00+00:00", "i": "0197fc00-0000-7000-8000-000000000000"}
    assert decode_cursor(encode_cursor(payload)) == payload


def test_malformed_cursor_rejected() -> None:
    with pytest.raises(ProblemError):
        decode_cursor("!!!not-base64!!!")


def test_non_object_cursor_rejected() -> None:
    with pytest.raises(ProblemError):
        decode_cursor(encode_cursor_list())


def encode_cursor_list() -> str:
    import base64

    return base64.urlsafe_b64encode(b"[1,2,3]").decode()


def test_clamp_limit() -> None:
    assert clamp_limit(0) == 1
    assert clamp_limit(50) == 50
    assert clamp_limit(10_000) == 200
