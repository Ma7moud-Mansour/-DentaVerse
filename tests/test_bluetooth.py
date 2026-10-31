import pytest

from backend.workers.bluetooth import parse_user_id


def test_application_userid_is_explicit_utf8_data():
    assert parse_user_id(b"DV-STUDENT-01") == "DV-STUDENT-01"


@pytest.mark.parametrize("data", [b"", b"x" * 65, b"\xff", b"Name <unsafe>", b"../../identity"])
def test_invalid_userid_rejected(data):
    with pytest.raises((ValueError, UnicodeDecodeError)):
        parse_user_id(data)
