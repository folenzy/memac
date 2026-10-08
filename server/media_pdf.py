import os
import json
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", ""),
    password=os.getenv("DB_PASSWORD", ""),
)

OUT_DIR = "/home/asiruk/memac/media/reports"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/home/asiruk/memac/arial.ttf",
]

FONT = "Helvetica"
for p in FONT_PATHS:
    if os.path.exists(p):
        pdfmetrics.registerFont(TTFont("Cyr", p))
        FONT = "Cyr"
        break

app = FastAPI(title="MeMAC PDF")


class PdfReq(BaseModel):
    session_id: int
    level: int = 2


def styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=FONT,
                             fontSize=16, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=FONT,
                             fontSize=12, spaceBefore=10, spaceAfter=6),
        "p":  ParagraphStyle("p", parent=ss["Normal"], fontName=FONT,
                             fontSize=10, leading=14, spaceAfter=4),
        "small": ParagraphStyle("small", parent=ss["Normal"], fontName=FONT,
                                fontSize=8, textColor=colors.grey),
    }


@app.get("/health")
def health():
    return {"status": "ok", "font": FONT, "dir": OUT_DIR}


@app.post("/report_pdf")
def report_pdf(r: PdfReq):
    conn = psycopg2.connect(**DB, connect_timeout=5)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT rep.content, rep.status, rep.level, rep.published_at,
               s.id AS session_id, s.finished_at, s.is_training,
               u.full_name AS employee_name
        FROM "ASiruk".reports rep
        JOIN "ASiruk".interview_sessions s ON s.id = rep.session_id
        LEFT JOIN "ASiruk".users u ON u.id = s.employee_id
        WHERE rep.session_id = %s AND rep.level = %s
    """, (r.session_id, r.level))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Otchet ne nayden")

    if r.level == 3 and row["status"] != "published":
        raise HTTPException(status_code=403, detail="Otchet ne opublikovan")

    c = row["content"] or {}
    if isinstance(c, str):
        c = json.loads(c)

    st = styles()
    path = os.path.join(OUT_DIR, "report_s%d_l%d.pdf" % (r.session_id, r.level))
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    fl = []

    titles = {1: "Транскрипция сессии", 2: "Отчёт по результатам собеседования",
              3: "Обратная связь по итогам собеседования"}
    fl.append(Paragraph(titles.get(r.level, "Отчёт"), st["h1"]))

    meta = "Сотрудник: %s | Сессия №%d" % (row["employee_name"] or "-", row["session_id"])
    if row["finished_at"]:
        meta += " | " + row["finished_at"].strftime("%d.%m.%Y")
    if row["is_training"]:
        meta += " | ТРЕНИРОВОЧНАЯ"
    fl.append(Paragraph(meta, st["small"]))
    fl.append(Spacer(1, 8))

    if r.level == 1:
        fl.append(Paragraph("Дословная запись", st["h2"]))
        for line in str(c.get("text", "")).split("\n"):
            if line.strip():
                fl.append(Paragraph(line.replace("<", "&lt;"), st["p"]))

    elif r.level == 2:
        data = [["Показатель", "Значение"],
                ["Средний уровень", str(c.get("avg_ku", "-")) + " из 5"],
                ["Ответов", str(c.get("answers_count", "-"))],
                ["Темп речи", str(c.get("behavior", {}).get("avg_wpm", "-")) + " слов/мин"],
                ["Паузы", str(c.get("behavior", {}).get("pause_total_sec", "-")) + " сек"],
                ["Красных флагов", str(c.get("red_flags_count", 0))]]
        t = Table(data, colWidths=[70*mm, 90*mm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), FONT),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8e8e8")),
        ]))
        fl.append(t)
        fl.append(Spacer(1, 10))

        comps = c.get("competencies", [])
        if comps:
            fl.append(Paragraph("Компетенции", st["h2"]))
            d2 = [["Компетенция", "Уровень"]]
            for x in comps:
                d2.append([str(x.get("competency", "-")), str(x.get("ku", "-"))])
            t2 = Table(d2, colWidths=[120*mm, 40*mm])
            t2.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), FONT),
                ("FONTSIZE", (0,0), (-1,-1), 9),
                ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8e8e8")),
            ]))
            fl.append(t2)

        for key, title in [("strengths", "Сильные стороны"),
                           ("gaps", "Зоны роста"),
                           ("recommendations", "Рекомендации")]:
            items = c.get(key, [])
            if items:
                fl.append(Paragraph(title, st["h2"]))
                for it in items:
                    fl.append(Paragraph("— " + str(it), st["p"]))

    else:
        fl.append(Paragraph(str(c.get("summary", "")), st["p"]))
        fl.append(Spacer(1, 6))
        for key, title in [("strengths", "Ваши сильные стороны"),
                           ("next_steps", "Что развивать дальше")]:
            items = c.get(key, [])
            if items:
                fl.append(Paragraph(title, st["h2"]))
                for it in items:
                    fl.append(Paragraph("— " + str(it), st["p"]))
        if row["published_at"]:
            fl.append(Spacer(1, 10))
            fl.append(Paragraph("Проверено ответственным за развитие " +
                                row["published_at"].strftime("%d.%m.%Y"), st["small"]))

    doc.build(fl)

    return {"pdf_path": path, "level": r.level,
            "size_bytes": os.path.getsize(path)}


import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8025)
