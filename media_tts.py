# -*- coding: utf-8 -*-
import os
import wave
import threading

import pyttsx3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MEDIA_DIR = r"C:\memac\media\audio"
VOICE_HINT = "Pavel"
SPEECH_RATE = 170

os.makedirs(MEDIA_DIR, exist_ok=True)
app = FastAPI(title="MeMAC TTS")
_lock = threading.Lock()


def _pick_voice(engine):
    voices = engine.getProperty("voices")
    for v in voices:
        if VOICE_HINT.lower() in str(v.name).lower():
            return v.id
    for v in voices:
        text = (str(v.id) + str(v.name)).lower()
        if "ru" in text:
            return v.id
    if voices:
        return voices[0].id
    return None


class TTSReq(BaseModel):
    text: str
    out_name: str


@app.get("/health")
def health():
    return {"status": "ok", "media_dir": MEDIA_DIR}


@app.get("/voices")
def voices():
    e = pyttsx3.init()
    result = [{"name": str(v.name), "id": str(v.id)} for v in e.getProperty("voices")]
    try:
        e.stop()
    except Exception:
        pass
    return {"voices": result}


@app.post("/tts")
def tts(r: TTSReq):
    safe_name = "".join(ch for ch in r.out_name if ch.isalnum() or ch in "_-")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Pustoe out_name")

    path = os.path.join(MEDIA_DIR, safe_name + ".wav")

    with _lock:
        engine = pyttsx3.init()
        voice_id = _pick_voice(engine)
        if voice_id:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate", SPEECH_RATE)
        engine.save_to_file(r.text, path)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass

    if not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Fayl ne sozdalsya: " + path)

    try:
        with wave.open(path) as w:
            duration = round(w.getnframes() / float(w.getframerate()), 2)
    except Exception:
        duration = 0.0

    return {
        "audio_path": path,
        "duration_sec": duration,
        "size_bytes": os.path.getsize(path),
    }


if __name__ == "__main__":
    import uvicorn
    print("Papka:", MEDIA_DIR)
    print("Proverka: http://localhost:8011/health")
    uvicorn.run(app, host="0.0.0.0", port=8011)