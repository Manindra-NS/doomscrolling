import argparse
import time

import cv2
import mediapipe as mp
import numpy as np
from ffpyplayer.player import MediaPlayer

LOOK_AWAY_THRESHOLD_SEC = 20  
ATTENTIVE_CONFIRM_SEC = 1.0    
YAW_LIMIT_DEG = 25               
PITCH_LIMIT_DEG = 15             
CAM_INDEX = 0

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # Nose tip = landmark 1
    (0.0, -63.6, -12.5),      # Chin = landmark 152
    (-43.3, 32.7, -26.0),     # Left eye left corner = landmark 33
    (43.3, 32.7, -26.0),      # Right eye right corner = landmark 263
    (-28.9, -28.9, -24.1),    # Left mouth corner = landmark 61
    (28.9, -28.9, -24.1),     # Right mouth corner = landmark 291
], dtype=np.float64)

LANDMARK_IDS = [1, 152, 33, 263, 61, 291]


def get_head_pose(landmarks, frame_w, frame_h):
    """Return (yaw_deg, pitch_deg) estimated from face landmarks, or None if invalid."""
    image_points = []
    for idx in LANDMARK_IDS:
        lm = landmarks[idx]
        image_points.append((lm.x * frame_w, lm.y * frame_h))
    image_points = np.array(image_points, dtype=np.float64)

    focal_length = frame_w
    center = (frame_w / 2, frame_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))  # assume no lens distortion

    success, rotation_vec, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
        return None

    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = cv2.hconcat((rotation_mat, np.zeros((3, 1))))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)

    pitch, yaw, _roll = [float(np.ravel(a)[0]) for a in euler_angles]
    if pitch > 90:
        pitch = 180 - pitch
    elif pitch < -90:
        pitch = -180 - pitch

    return yaw, pitch


class VideoPlayer:
    """Plays a nudge video (with audio) in its own window using ffpyplayer.
    Call step() each loop, stop() to end."""

    def __init__(self, path):
        self.path = path
        self.player = None
        self.window = "Look Back at the Screen!"

    def start(self):
        self.player = MediaPlayer(self.path, ff_opts={"out_fmt": "rgb24"})

    def step(self):
        if self.player is None:
            return
        frame, val = self.player.get_frame()
        if val == 'eof':
            # loop the video from the start
            self.player.seek(0, relative=False)
            return
        if frame is None:
            return 
        img, _pts = frame
        w, h = img.get_size()
        buf = img.to_bytearray()[0]
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 3))
        frame_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        cv2.imshow(self.window, frame_bgr)

    def stop(self):
        if self.player is not None:
            self.player.close_player()
            self.player = None
        try:
            cv2.destroyWindow(self.window)
        except cv2.error:
            pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to the nudge video file")
    args = parser.parse_args()

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(CAM_INDEX)
    player = VideoPlayer(args.video)

    away_since = None       
    attentive_since = None  
    video_playing = False

    print("Starting monitor. Press 'q' in the camera window to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        looking_at_screen = False
        yaw_display, pitch_display = None, None
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            pose = get_head_pose(landmarks, w, h)
            if pose is not None:
                yaw, pitch = pose
                yaw_display, pitch_display = yaw, pitch
                looking_at_screen = (
                    abs(yaw) <= YAW_LIMIT_DEG and abs(pitch) <= PITCH_LIMIT_DEG
                )

        now = time.time()
        if video_playing:
            confirmed_attentive = False
        elif looking_at_screen:
            if attentive_since is None:
                attentive_since = now
            confirmed_attentive = (now - attentive_since) >= ATTENTIVE_CONFIRM_SEC
        else:
            attentive_since = None
            confirmed_attentive = False

        if video_playing:
            pass
        elif confirmed_attentive:
            away_since = None
        else:
            if away_since is None:
                away_since = now
            elif (now - away_since) >= LOOK_AWAY_THRESHOLD_SEC:
                player.start()
                video_playing = True

        # HUD overlay
        status = "ATTENTIVE" if confirmed_attentive else "LOOKING AWAY"
        color = (0, 200, 0) if confirmed_attentive else (0, 0, 220)
        cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        if away_since and not confirmed_attentive and not video_playing:
            elapsed = now - away_since
            cv2.putText(frame, f"Away: {elapsed:.0f}s", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        if video_playing:
            cv2.putText(frame, "Press SPACE to dismiss", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2)

        if yaw_display is not None:
            cv2.putText(frame, f"yaw: {yaw_display:+.1f}  pitch: {pitch_display:+.1f}",
                        (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        else:
            cv2.putText(frame, "no face detected", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Webcam Monitor", frame)

        if video_playing:
            player.step()

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' ') and video_playing:
            player.stop()
            video_playing = False
            away_since = None       
            attentive_since = None  

    cap.release()
    if video_playing:
        player.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()