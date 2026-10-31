import math

import pytest

from backend.gestures import GestureLibrary, validate_path


def circle():
    return [[math.cos(i * math.tau / 40), math.sin(i * math.tau / 40)] for i in range(41)]


def test_empty_library_does_not_fake_recognition(tmp_path):
    library = GestureLibrary(tmp_path / "templates.json")
    result = library.recognize(circle())
    assert not result["accepted"]
    assert result["name"] is None
    assert all(count == 0 for count in library.counts.values())


def test_dollarpy_classifies_synthetic_fixture_and_roundtrips_file(tmp_path):
    # Synthetic test coordinates are created only in pytest's temporary folder.
    path = tmp_path / "fixture.json"
    library = GestureLibrary(path)
    library.add("circle", circle())
    reloaded = GestureLibrary(path)
    shifted = [[x * 0.8 + 0.1, y * 0.8 - 0.05] for x, y in circle()]
    result = reloaded.recognize(shifted)
    assert result["accepted"] and result["name"] == "circle"
    assert reloaded.counts["circle"] == 1


@pytest.mark.parametrize("path", [[[0, 0]] * 30, [[float("nan"), 0]] * 20, [[1, 2]] * 2])
def test_incomplete_or_stationary_paths_are_rejected(path):
    with pytest.raises(ValueError):
        validate_path(path)
