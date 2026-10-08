# -*- coding: utf-8 -*-
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from faster_whisper import WhisperModel

app = FastAPI(title="MeMAC STT")

print("Zagruzka modeli, podozhdi...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Model gotova")

_lock = threading.Lock()


class SttReq(BaseModel):
    audio_path: str


@app.get("/health")
def health():
    return {"status": "ok", "model": "small"}


@app.post("/stt_path")
def stt_path(r: SttReq):
    if not os.path.exists(r.audio_path):
        raise HTTPException(status_code=400, detail="Net fayla: " + r.audio_path)

    size = os.path.getsize(r.audio_path)
    if size < 1000:
        return {"text": "", "duration_sec": 0.0, "empty": True}

    with _lock:
        segments, info = model.transcribe(r.audio_path, language="ru", vad_filter=True)
        parts = []
        for s in segments:
            parts.append(s.text)

    text = " ".join(parts).strip()

    return {
        "text": text,
        "duration_sec": round(float(info.duration), 2),
        "words": len(text.split()),
        "empty": len(text) == 0,
    }


import uvicorn
print("Proverka: http://localhost:8017/health")
uvicorn.run(app, host="0.0.0.0", port=8017)