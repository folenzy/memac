# -*- coding: utf-8 -*-
import os
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

ANSWERS_DIR = r"C:\memac\media\answers"
os.makedirs(ANSWERS_DIR, exist_ok=True)

app = FastAPI(title="MeMAC Upload")


@app.get("/health")
def health():
    return {"status": "ok", "dir": ANSWERS_DIR}


@app.post("/upload")
def upload(session_id: int = Form(...),
           question_id: int = Form(...),
           file: UploadFile = File(...)):
    name = "s%d_q%d.wav" % (session_id, question_id)
    path = os.path.join(ANSWERS_DIR, name)

    with open(path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    size = os.path.getsize(path)
    if size < 1000:
        raise HTTPException(status_code=400, detail="Fayl pustoy: %d bytes" % size)

    return {"audio_path": path, "size_bytes": size}


import uvicorn
print("Otvety:", ANSWERS_DIR)
print("Proverka: http://localhost:8015/health")
uvicorn.run(app, host="0.0.0.0", port=8015)