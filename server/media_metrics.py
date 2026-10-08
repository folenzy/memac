# -*- coding: utf-8 -*-
import os

import numpy as np
import librosa
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="MeMAC Metrics")


class Answer(BaseModel):
    answer_id: int
    audio_path: str
    transcript: str = ""


class MetricsReq(BaseModel):
    answers: List[Answer]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/metrics")
def metrics(r: MetricsReq):
    out = []

    for a in r.answers:
        if not os.path.exists(a.audio_path):
            continue

        y, sr = librosa.load(a.audio_path, sr=None, mono=True)
        dur = float(len(y)) / float(sr)
        if dur <= 0:
            continue

        rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=512)[0]

        intervals = librosa.effects.split(y, top_db=30)
        speech = 0.0
        for s, e in intervals:
            speech += float(e - s) / float(sr)

        pause_total = dur - speech
        pause_count = max(len(intervals) - 1, 0)

        words = len(str(a.transcript).split())
        wpm = 0.0
        if speech > 0:
            wpm = words / (speech / 60.0)

        out.append({
            "answer_id":       a.answer_id,
            "wpm":             round(wpm, 2),
            "pause_count":     pause_count,
            "pause_total_sec": round(pause_total, 2),
            "rms_mean":        round(float(np.mean(rms)), 5),
            "rms_std":         round(float(np.std(rms)), 5),
        })

    return {"metrics": out, "count": len(out)}


import uvicorn
print("Proverka: http://localhost:8019/health")
uvicorn.run(app, host="0.0.0.0", port=8019)