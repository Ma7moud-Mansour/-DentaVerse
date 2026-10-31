"""Bounded JPEGs for the local live preview; no image files are written."""
import base64
import binascii

MAX_IMAGE_CHARS = 42000  # Leave room for landmarks/trails in the 64 KiB frame.


def encode_camera_image(frame, cv2):
    height, width = frame.shape[:2]
    ratio = min(1.0, 640 / width, 480 / height)
    mirrored = cv2.flip(frame, 1)
    width, height = max(1, round(width * ratio)), max(1, round(height * ratio))
    while True:
        picture = cv2.resize(mirrored, (width, height), interpolation=cv2.INTER_AREA)
        for quality in (65, 45, 25):
            ok, encoded = cv2.imencode(".jpg", picture, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ok:
                raise ValueError("Could not encode camera preview")
            data = base64.b64encode(encoded).decode("ascii")
            if len(data) <= MAX_IMAGE_CHARS:
                return {"data": data, "width": width, "height": height}
        if width <= 160 or height <= 120:
            raise ValueError("Camera preview exceeds the frame budget")
        width, height = max(1, round(width * 0.75)), max(1, round(height * 0.75))


def validate_camera_image(image):
    if image is None:
        return None  # Older coordinate-only workers remain compatible.
    if not isinstance(image, dict):
        raise ValueError("Invalid camera preview")
    width, height, data = image.get("width"), image.get("height"), image.get("data")
    if type(width) is not int or type(height) is not int or not 1 <= width <= 640 or not 1 <= height <= 480:
        raise ValueError("Invalid camera preview dimensions")
    if not isinstance(data, str) or not 1 <= len(data) <= MAX_IMAGE_CHARS:
        raise ValueError("Invalid camera preview size")
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid camera preview encoding") from exc
    if not raw.startswith(b"\xff\xd8\xff") or not raw.endswith(b"\xff\xd9"):
        raise ValueError("Camera preview must be JPEG")
    return {"data": data, "width": width, "height": height}
