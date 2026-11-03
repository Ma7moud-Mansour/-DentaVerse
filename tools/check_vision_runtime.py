"""Model/API smoke check with a blank image. Does not open a camera."""
from pathlib import Path


def main():
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError as exc:
        raise SystemExit(f"Incomplete vision installation: {exc}. Run tools/setup.ps1 -WithVision.") from exc
    model = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
    if not model.is_file():
        raise SystemExit("Download the model with python tools/download_pose_model.py first.")
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
        result = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((256, 256, 3), dtype=np.uint8)), 0)
    hand_model = model.with_name("hand_landmarker.task")
    if not hand_model.is_file():
        raise SystemExit("Download hand model with python tools/download_hand_model.py first.")
    hand_options = mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(hand_model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2)
    with mp.tasks.vision.HandLandmarker.create_from_options(hand_options) as detector:
        hands = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((256, 256, 3), dtype=np.uint8)), 0)
    print(f"Model initialized; blank-frame inference succeeded ({len(result.pose_landmarks)} detected bodies). OpenCV {cv2.__version__}, MediaPipe {mp.__version__}.")
    print(f"Hand model initialized for two hands; blank-frame inference succeeded ({len(hands.hand_landmarks)} hands).")
    print("This verifies model/API initialization only. No camera, live skeleton or user motion was tested.")


if __name__ == "__main__":
    main()
