# -*- coding: utf-8 -*-
import os
import threading

import numpy as np
import librosa
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

VIDEO_DIR = r"C:\memac\media\video"
ASSETS_DIR = r"C:\memac\assets"
FPS = 12
THRESHOLD = 0.10

os.makedirs(VIDEO_DIR, exist_ok=True)

app = FastAPI(title="MeMAC Avatar")
_lock = threading.Lock()


def _load_faces():
    closed_img = Image.open(os.path.join(ASSETS_DIR, "mouth_closed.png")).convert("RGB")
    w, h = closed_img.size
    w = w - (w % 2)
    h = h - (h % 2)
    closed_img = closed_img.resize((w, h))
    open_img = Image.open(os.path.join(ASSETS_DIR, "mouth_open.png")).convert("RGB")
    open_img = open_img.resize((w, h))
    return np.array(closed_img), np.array(open_img)


FACE_CLOSED, FACE_OPEN = _load_faces()


class LipReq(BaseModel):
    audio_path: str
    out_name: str


@app.get("/health")
def health():
    return {"status": "ok", "video_dir": VIDEO_DIR, "fps": FPS}


@app.post("/lipsync")
def lipsync(r: LipReq):
    if not os.path.exists(r.audio_path):
        raise HTTPException(status_code=400, detail="Net fayla: " + r.audio_path)

    safe_name = "".join(ch for ch in r.out_name if ch.isalnum() or ch in "_-")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Pustoe out_name")

    out_path = os.path.join(VIDEO_DIR, safe_name + ".mp4")

    with _lock:
        y, sr = librosa.load(r.audio_path, sr=None, mono=True)
        duration = float(len(y)) / float(sr)

        rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=512)[0]
        peak = float(rms.max())
        if peak > 0:
            rms = rms / peak

        n_frames = int(duration * FPS)
        if n_frames < 1:
            n_frames = 1

        positions = np.linspace(0, len(rms) - 1, n_frames).astype(int)
        frames = []
        for p in positions:
            if rms[p] > THRESHOLD:
                frames.append(FACE_OPEN)
            else:
                frames.append(FACE_CLOSED)

        clip = ImageSequenceClip(frames, fps=FPS)
        audio = AudioFileClip(r.audio_path)
        clip = clip.set_audio(audio)
        clip.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            fps=FPS,
            threads=2,
            logger=None,
        )
        clip.close()
        audio.close()

    if not os.path.exists(out_path):
        raise HTTPException(status_code=500, detail="Video ne sozdalos")

    return {
        "video_path": out_path,
        "duration_sec": round(duration, 2),
        "frames": n_frames,
        "size_bytes": os.path.getsize(out_path),
    }


if __name__ == "__main__":
    import uvicorn
    print("Video:", VIDEO_DIR)
    print("Proverka: http://localhost:8013/health")
    uvicorn.run(app, host="0.0.0.0", port=8013)