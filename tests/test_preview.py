import base64
from pathlib import Path

import pytest

from backend.preview import encode_camera_image, validate_camera_image, MAX_IMAGE_CHARS
from backend.protocol import encode_frame, Message, MAX_FRAME


def test_only_bounded_jpeg_images_are_accepted():
    data = base64.b64encode((Path(__file__).parent / "fixtures/preview-synthetic.jpg").read_bytes()).decode()
    image = {"data": data, "width": 320, "height": 180}
    assert validate_camera_image(image) == image
    assert validate_camera_image(None) is None
    for bad in [dict(image, data="not base64"), dict(image, data=base64.b64encode(b"<svg/>").decode()),
            dict(image, data="A" * (MAX_IMAGE_CHARS + 4)), dict(image, width=1920), dict(image, height=True)]:
        with pytest.raises(ValueError):
            validate_camera_image(bad)


def test_encoder_preserves_aspect_and_mirrors_before_overlay():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :640] = (240, 0, 0)
    frame[:, 640:] = (0, 0, 240)
    image = encode_camera_image(frame, cv2)
    assert (image["width"], image["height"]) == (640, 360)
    decoded = cv2.imdecode(np.frombuffer(base64.b64decode(image["data"]), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded[100, 100, 2] > 200 and decoded[100, 540, 0] > 200
    # High-detail noise must still fit alongside the longest displayed path.
    noise = np.random.default_rng(9).integers(0, 256, (720, 1280, 3), dtype=np.uint8)
    image = encode_camera_image(noise, cv2)
    validate_camera_image(image)
    packet = encode_frame(Message(source="vision", type="POSE_FRAME", payload={"image": image,
        "landmarks": [{"x": 0.12345678901234567, "y": 0.8765432109876543, "visibility": 0.9876543210987654}] * 33,
        "trail": [[0.12345678901234567, 0.8765432109876543]] * 200}))
    assert len(packet) - 4 <= MAX_FRAME
