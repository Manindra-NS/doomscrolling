# Doomscrolling Stopper

A webcam-based attention monitor. If it detects you've looked away from your
screen for too long, it plays a video to pull your focus back — and once
triggered, the video keeps playing until you manually dismiss it.

**Live GitHub repo:** [github.com/Manindra-NS/doomscrolling](https://github.com/Manindra-NS/doomscrolling.git)

**Documentation:** [https://drive.google.com/file/d/1xmag0IrvzQ9AAdUNZML2TlTNPCcQLWD_/view?usp=sharing](https://drive.google.com/file/d/1xmag0IrvzQ9AAdUNZML2TlTNPCcQLWD_/view?usp=sharing)

## How it works

1. Your webcam feed is analyzed frame-by-frame using **MediaPipe Face Mesh**
   to get facial landmarks.
2. Those landmarks are fed into **OpenCV's `solvePnP`** to estimate your head's
   3D orientation (yaw = left/right turn, pitch = up/down tilt).
3. You're considered **"looking at the screen"** only if:
   - a face is detected, **and**
   - yaw and pitch both fall within set limits (see [Configuration](#configuration)).
4. To avoid false triggers from a quick head tilt or shake, "looking away" only
   resets once you've held a steady, confirmed gaze at the screen for **1 full
   second** (adjustable).
5. If you stay "away" continuously for **60 seconds** (adjustable), a nudge
   video starts playing in its own window, with audio.
6. **The video does not stop on its own.** Once triggered, it ignores your
   gaze entirely — you must press **`SPACE`** to dismiss it and resume
   monitoring.

## Requirements

- Python **3.11 or 3.12** (MediaPipe does not currently support 3.13+)
- A working webcam
- Packages:
  ```
  pip install mediapipe opencv-python numpy ffpyplayer
  ```

> **Note:** If `mediapipe` fails to import with
> `AttributeError: module 'mediapipe' has no attribute 'solutions'`, this is a
> known packaging bug in some recent mediapipe releases. Fix it with:
> ```
> pip uninstall mediapipe -y
> pip install mediapipe==0.10.21
> ```

## Usage

```
python doomscroll_stopper.py --video path/to/your_video.mp4
```

`--video` is required — point it at any normal video file (a downloaded clip,
phone recording, etc.). Screen recordings from tools like Xbox Game Bar
sometimes use codecs OpenCV can't open; if your video window stays blank,
re-encode it first with:

```
ffmpeg -i input.mp4 -c:v libx264 -pix_fmt yuv420p -c:a aac output.mp4
```

### Controls

| Key     | Action                                      |
|---------|----------------------------------------------|
| `SPACE` | Dismiss the nudge video and resume monitoring |
| `q`     | Quit the program                              |

### On-screen readout

The "Webcam Monitor" window shows:
- **ATTENTIVE** / **LOOKING AWAY** status
- A live **away-timer** counting up toward the 60-second trigger
- Live **yaw / pitch** values, for calibration
- **"Press SPACE to dismiss"** while the nudge video is active

## Configuration

All key settings are constants at the top of the script:

| Constant                | Default | Meaning                                                        |
|-------------------------|---------|------------------------------------------------------------------|
| `LOOK_AWAY_THRESHOLD_SEC` | `60`    | Seconds of continuous "away" before the video triggers          |
| `ATTENTIVE_CONFIRM_SEC`   | `1.0`   | Seconds of continuous steady gaze needed to count as "back"     |
| `YAW_LIMIT_DEG`           | `25`    | Max left/right head turn still counted as "looking at screen"   |
| `PITCH_LIMIT_DEG`         | `20`    | Max up/down head tilt still counted as "looking at screen"      |
| `CAM_INDEX`               | `0`     | Which webcam to use, if you have more than one                  |

### Calibrating for your setup

Webcam position, desk distance, and face shape all affect what "normal"
yaw/pitch values look like for you. If detection feels off:

1. Run the script and watch the live `yaw` / `pitch` readout.
2. Look straight at the screen, centered, and note the values.
3. Look away as you naturally would, and note those values too.
4. Adjust `YAW_LIMIT_DEG` / `PITCH_LIMIT_DEG` so the "looking at screen"
   numbers fall comfortably inside the limits, and "looking away" numbers
   fall outside.

## Known limitations

- **Lighting matters.** Face detection degrades in low light.
- **Multiple monitors** aren't distinguished — glancing at a second monitor
  currently counts as "looking away."
- **Single face only** — the script tracks one face at a time.
- Video looping/dismissal state resets on quit; there's no persistent stats
  logging (yet).

## Possible next steps

- Calibration mode that suggests thresholds automatically
- Run as a background service / system tray app instead of a console window
- Log attention stats over time
- Per-monitor attention zones
