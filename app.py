# -*- coding: utf-8 -*-
"""
МеМАС · Веб-интерфейс.

УСТАНОВКА (один раз):
    py -m pip install streamlit psycopg2-binary requests pandas plotly python-dotenv

ЗАПУСК:
    cd C:\\memac
    py -m streamlit run app.py

Настройки читаются из файла .env рядом с app.py (см. .env.example)
"""

import os
import json
import requests
import pandas as pd
import psycopg2
import psycopg2.extras
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

DB = dict(
    host=os.getenv("DB_HOST", ""),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", ""),
    password=os.getenv("DB_PASSWORD", ""),
)

SCHEMA     = '"ASiruk"'
N8N        = os.getenv("N8N_BASE", "")
SERVER_IP  = os.getenv("SERVER_IP", "")
APP_URL    = os.getenv("APP_URL", "http://localhost:8501")

UPLOAD_URL = "http://%s:8015/upload" % SERVER_IP
HOOK = lambda name: "%s/webhook/%s" % (N8N, name)

st.set_page_config(page_title="МеМАС", page_icon="◆", layout="wide")


# ---------------------------------------------------------------- ОФОРМЛЕНИЕ

import html as _html

def esc(t):
    return _html.escape(str(t if t is not None else ""))


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=Unbounded:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --ink:      #12161D;
  --ink-2:    #1B2230;
  --paper:    #F4F6F8;
  --card:     #FFFFFF;
  --line:     #E3E7EC;
  --line-2:   #D3D9E0;
  --muted:    #6A7380;
  --pine:     #2F6B5A;
  --pine-2:   #3E8E76;
  --pine-dim: #DFEAE5;
  --brick:    #A8322A;
  --amber:    #8A6414;
  --shadow:   0 1px 2px rgba(18,22,29,.05), 0 8px 24px -12px rgba(18,22,29,.12);
}

html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, label, li, input, textarea, button {
  font-family: 'Golos Text', -apple-system, 'Segoe UI', sans-serif;
}

.stApp { background: var(--paper); }
.block-container { padding-top: 2rem; max-width: 1160px; animation: rise .45s cubic-bezier(.22,.9,.3,1) both; }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } }

h1, h2, h3 { font-family: 'Unbounded', sans-serif !important; letter-spacing: -0.02em; color: var(--ink); }
h1 { font-size: 1.7rem !important;  font-weight: 500 !important; }
h2 { font-size: 1.12rem !important; font-weight: 500 !important; }
h3 { font-size: .95rem !important;  font-weight: 500 !important; }
code, pre, .stCode { font-family: 'IBM Plex Mono', monospace !important; font-size: .82rem !important; }

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: var(--line-2); border-radius: 9px; border: 2px solid var(--paper); }
::-webkit-scrollbar-track { background: transparent; }

/* ---------- боковая панель ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0F141B 0%, #161E29 100%);
  border-right: none; box-shadow: inset -1px 0 0 rgba(255,255,255,.04);
}
section[data-testid="stSidebar"] * { color: #B9C3CF; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.08); }
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #1D2634; border-color: #2A3546; border-radius: 4px;
}
.logo {
  width: 44px; height: 44px; border-radius: 10px;
  background: linear-gradient(135deg, var(--pine) 0%, var(--pine-2) 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 18px -6px rgba(47,107,90,.55);
  margin-bottom: .6rem;
}
.logo span { font-family: 'Unbounded'; font-weight: 700; font-size: 1.15rem; color: #fff; }
.brand { font-family: 'Unbounded'; font-weight: 500; font-size: 1.15rem; color: #fff !important; }
.brand-sub { font-size: .74rem; color: #77828F !important; margin-top: .1rem; }
.role-dot {
  display: inline-flex; align-items: center; gap: 7px;
  font-family: 'IBM Plex Mono', monospace; font-size: .72rem;
  letter-spacing: .1em; text-transform: uppercase; color: #6FB39D !important;
}
.role-dot::before { content: ''; width: 7px; height: 7px; border-radius: 50%;
  background: var(--pine-2); box-shadow: 0 0 8px rgba(62,142,118,.9); }

/* ---------- вкладки ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 1.7rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  background: transparent; padding: 0 0 .6rem 0; font-weight: 500;
  color: var(--muted); font-size: .92rem;
}
.stTabs [aria-selected="true"] { color: var(--ink) !important; }
.stTabs [data-baseweb="tab-highlight"] {
  background: linear-gradient(90deg, var(--pine), var(--pine-2)); height: 2px;
}

/* ---------- кнопки ---------- */
.stButton > button {
  border-radius: 5px; border: 1px solid var(--line-2); font-weight: 500;
  font-size: .88rem; padding: .48rem 1.15rem; background: var(--card); color: var(--ink);
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.stButton > button:hover { border-color: var(--pine); color: var(--pine); }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--pine) 0%, var(--pine-2) 100%);
  border: none; color: #fff; box-shadow: 0 1px 2px rgba(18,22,29,.1);
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 6px 18px -6px rgba(47,107,90,.55); transform: translateY(-1px); color: #fff;
}
.stButton > button:focus-visible { outline: 2px solid var(--pine-2); outline-offset: 2px; }
.stButton > button:disabled { opacity: .45; transform: none; box-shadow: none; }

/* ---------- поля ---------- */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  border-radius: 5px !important; font-size: .9rem; border-color: var(--line-2) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--pine) !important; box-shadow: 0 0 0 3px rgba(47,107,90,.12) !important;
}

/* ---------- карточка-метрика ---------- */
.mgrid { display: flex; gap: 12px; flex-wrap: wrap; margin: .3rem 0 1rem 0; }
.mcard {
  flex: 1 1 150px; background: var(--card); border: 1px solid var(--line);
  border-radius: 6px; padding: .85rem 1.05rem; box-shadow: var(--shadow);
  position: relative; overflow: hidden;
}
.mcard::after {
  content: ''; position: absolute; inset: 0 auto 0 0; width: 3px;
  background: linear-gradient(180deg, var(--pine), var(--pine-2));
}
.mlab {
  font-family: 'IBM Plex Mono', monospace; font-size: .68rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted); margin-bottom: .3rem;
}
.mval { font-family: 'Unbounded'; font-size: 1.55rem; font-weight: 500; color: var(--ink); line-height: 1; }
.mval span { font-size: .8rem; color: var(--muted); font-family: 'Golos Text'; margin-left: .3rem; }
.mcard.alert::after { background: var(--brick); }
.mcard.alert .mval { color: var(--brick); }

/* ---------- лестница карьерных уровней ---------- */
.ku { display: inline-flex; gap: 3px; align-items: flex-end; vertical-align: middle; }
.ku i { display: block; width: 15px; border-radius: 2px 2px 0 0; background: var(--pine-dim); transform-origin: bottom; }
.ku i:nth-child(1) { height: 7px; }  .ku i:nth-child(2) { height: 10px; }
.ku i:nth-child(3) { height: 13px; } .ku i:nth-child(4) { height: 16px; }
.ku i:nth-child(5) { height: 19px; }
.ku i.on { background: linear-gradient(180deg, var(--pine-2), var(--pine)); animation: kfill .45s cubic-bezier(.22,.9,.3,1) backwards; }
.ku i.on:nth-child(1) { animation-delay: .03s; } .ku i.on:nth-child(2) { animation-delay: .09s; }
.ku i.on:nth-child(3) { animation-delay: .15s; } .ku i.on:nth-child(4) { animation-delay: .21s; }
.ku i.on:nth-child(5) { animation-delay: .27s; }
@keyframes kfill { from { transform: scaleY(.25); opacity: .3; } }
.ku b { font-family: 'IBM Plex Mono', monospace; font-size: .78rem; color: var(--muted); font-weight: 500; margin-left: 8px; }

/* ---------- статусные метки ---------- */
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: .18rem .6rem; border-radius: 999px;
  font-size: .74rem; font-weight: 500; letter-spacing: .01em;
  border: 1px solid; white-space: nowrap;
}
.pill::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pill.ok   { color: var(--pine);  border-color: #BCD5CC; background: #F0F6F3; }
.pill.warn { color: var(--amber); border-color: #DCC896; background: #FBF6E9; }
.pill.bad  { color: var(--brick); border-color: #DDB0AB; background: #FBF0EF; }
.pill.neu  { color: var(--muted); border-color: var(--line-2); background: #F1F3F6; }

/* ---------- строка-карточка ---------- */
.crow {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: .6rem 1rem; background: var(--card);
  border: 1px solid var(--line); border-radius: 6px; margin-bottom: 6px;
  box-shadow: 0 1px 2px rgba(18,22,29,.04);
  transition: border-color .15s, transform .15s, box-shadow .15s;
}
.crow:hover { border-color: var(--pine); transform: translateX(3px); box-shadow: var(--shadow); }
.crow .nm { font-size: .9rem; color: var(--ink); font-weight: 500; }
.crow .kd { font-size: .74rem; color: var(--muted); margin-left: .55rem; }

/* ---------- шапка страницы ---------- */
.eyebrow {
  font-family: 'IBM Plex Mono', monospace; font-size: .72rem;
  letter-spacing: .14em; text-transform: uppercase; color: var(--pine);
  margin-bottom: .25rem; display: flex; align-items: center; gap: 8px;
}
.eyebrow::before { content: ''; width: 18px; height: 1px; background: var(--pine); }
.lede { color: var(--muted); font-size: .89rem; margin: -.35rem 0 1.3rem 0; }

/* ---------- пустое состояние ---------- */
.empty {
  border: 1px dashed var(--line-2); border-radius: 6px; background: var(--card);
  padding: 1.7rem; text-align: center; color: var(--muted); font-size: .88rem;
}
.empty b { display: block; color: var(--ink); font-weight: 500; margin-bottom: .3rem; font-size: .95rem; }

/* ---------- прочее ---------- */
.stExpander { border: 1px solid var(--line) !important; border-radius: 6px !important; background: var(--card); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
hr { border-color: var(--line); }
.stProgress > div > div { background: linear-gradient(90deg, var(--pine), var(--pine-2)) !important; }
.stAlert { border-radius: 6px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# CSS комнаты: инжектируется поверх основного только на странице по токену
ROOM_CSS = """
<style>
.stApp { background: radial-gradient(1100px 520px at 18% -8%, #17222E 0%, #0C1117 55%) !important; }
.block-container { max-width: 880px; }
h1, h2, h3 { color: #EEF2F6 !important; }
p, span, div, label, li { color: #AEB8C4; }
.eyebrow { color: #6FB39D; } .eyebrow::before { background: #6FB39D; }
.lede { color: #7C8794; }
.qcard {
  background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.1);
  border-radius: 10px; padding: 1.25rem 1.45rem; margin: .4rem 0 1rem 0;
  font-size: 1.04rem; line-height: 1.55; color: #E7ECF1;
  box-shadow: 0 18px 50px -22px rgba(0,0,0,.65);
  backdrop-filter: blur(5px);
}
.pbar { height: 4px; border-radius: 999px; background: rgba(255,255,255,.09); overflow: hidden; margin: .2rem 0 1rem 0; }
.pbar i { display: block; height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, var(--pine-2), #6FE0BC);
  box-shadow: 0 0 12px rgba(76,214,168,.5); transition: width .4s cubic-bezier(.22,.9,.3,1); }
.stTabs [data-baseweb="tab-list"] { border-color: rgba(255,255,255,.1); }
.stTabs [data-baseweb="tab"] { color: #77828F; }
.stTabs [aria-selected="true"] { color: #EEF2F6 !important; }
.stButton > button { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.14); color: #DDE4EA; }
.stButton > button:hover { border-color: var(--pine-2); color: #fff; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, var(--pine), var(--pine-2)); }
.stTextArea textarea { background: rgba(255,255,255,.05) !important; color: #E7ECF1 !important;
  border-color: rgba(255,255,255,.14) !important; }
.stExpander { background: rgba(255,255,255,.04) !important; border-color: rgba(255,255,255,.1) !important; }
[data-baseweb="select"] > div { background: rgba(255,255,255,.05) !important;
  border-color: rgba(255,255,255,.14) !important; color: #E7ECF1; }
video { border-radius: 10px; box-shadow: 0 22px 60px -24px rgba(0,0,0,.75); }
.stAlert { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); color: #DDE4EA; }
.hint { font-size: .8rem; color: #78838F; line-height: 1.5; margin-top: .7rem;
        padding-left: .8rem; border-left: 2px solid rgba(255,255,255,.12); }
.empty { background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.14); color: #8994A1; }
.empty b { color: #E7ECF1; }
</style>
"""


def head(eyebrow, title, lede=None):
    st.markdown("<div class='eyebrow'>%s</div>" % esc(eyebrow), unsafe_allow_html=True)
    st.markdown("# %s" % title)
    if lede:
        st.markdown("<div class='lede'>%s</div>" % esc(lede), unsafe_allow_html=True)


def ku(level, show_num=True):
    try:
        n = int(round(float(level)))
    except Exception:
        n = 0
    seg = "".join("<i class='%s'></i>" % ("on" if i <= n else "") for i in range(1, 6))
    num = "<b>%s / 5</b>" % esc(level) if show_num else ""
    return "<span class='ku'>%s%s</span>" % (seg, num)


def metric(label, value, unit="", alert=False):
    cls = "mcard alert" if alert else "mcard"
    return ("<div class='%s'><div class='mlab'>%s</div>"
            "<div class='mval'>%s<span>%s</span></div></div>"
            % (cls, esc(label), esc(value), esc(unit)))


def metrics_row(items):
    st.markdown("<div class='mgrid'>%s</div>" % "".join(items), unsafe_allow_html=True)


PILL_CLASS = {
    "confirmed": "ok", "approved": "ok", "published": "ok", "free": "ok", "passed": "ok",
    "in_progress": "warn", "draft": "warn", "planned": "warn", "booked": "warn",
    "rejected": "bad", "failed": "bad", "error": "bad",
    "not_started": "neu", "completed": "neu", "evaluated": "neu",
}


def pill(status):
    return "<span class='pill %s'>%s</span>" % (
        PILL_CLASS.get(status, "neu"), esc(STATUS_RU.get(status, status or "—")))


def crow(left, right="", sub=""):
    subh = "<span class='kd'>%s</span>" % esc(sub) if sub else ""
    return ("<div class='crow'><div><span class='nm'>%s</span>%s</div>"
            "<div>%s</div></div>" % (esc(left), subh, right))


def empty(title, hint=""):
    st.markdown("<div class='empty'><b>%s</b>%s</div>" % (esc(title), esc(hint)),
                unsafe_allow_html=True)


# ---------------------------------------------------------------- БД

def q(sql, params=None):
    with psycopg2.connect(**DB) as c:
        with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def x(sql, params=None):
    with psycopg2.connect(**DB) as c:
        with c.cursor() as cur:
            cur.execute(sql, params or ())
            c.commit()


def call(name, payload, timeout=120):
    try:
        r = requests.post(HOOK(name), json=payload, timeout=timeout)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "error": "нечитаемый ответ: " + r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


KIND_RU = {"competency": "компетенция", "task": "задача", "principle": "принцип"}
STATUS_RU = {
    "planned": "запланирована", "in_progress": "идёт", "completed": "завершена",
    "evaluated": "оценена", "published": "отчёт опубликован",
    "not_started": "не начата", "confirmed": "подтверждена",
    "draft": "черновик", "approved": "одобрен", "rejected": "отклонён",
    "free": "свободен", "booked": "забронирован",
}
ru = lambda v: STATUS_RU.get(v, v or "—")


# ================================================================ КОМНАТА

def page_room(token):
    st.markdown(ROOM_CSS, unsafe_allow_html=True)
    room = q("""
        SELECT r.session_id, r.role, r.expires_at,
               s.status, s.employee_id, s.is_training, s.duration_min,
               u.full_name AS employee_name
        FROM {s}.rooms r
        JOIN {s}.interview_sessions s ON s.id = r.session_id
        LEFT JOIN {s}.users u ON u.id = s.employee_id
        WHERE r.token = %s
    """.format(s=SCHEMA), (token,))

    if room.empty:
        st.error("Ссылка недействительна.")
        return
    row = room.iloc[0]

    if pd.Timestamp(row["expires_at"]) < pd.Timestamp.now(tz="UTC"):
        st.error("Срок действия ссылки истёк. Попросите новую у ответственного за развитие.")
        return
    if row["status"] in ("completed", "evaluated", "published"):
        st.success("Собеседование уже пройдено.")
        st.caption("Обратная связь появится после проверки ответственным за развитие.")
        return

    head("Собеседование", "Комната")
    cap = "%s · сессия №%d" % (row["employee_name"] or "—", row["session_id"])
    if row["is_training"]:
        cap += " · тренировочная"
    st.caption(cap)

    if "started" not in st.session_state:
        res = call("start-session", {"token": token})
        st.session_state.started = True
        st.session_state.qi = 0
        if not res.get("ok"):
            st.error("Не удалось начать сессию: %s" % res.get("error", "?"))

    plan = q("""
        SELECT sq.order_no, sq.question_id, q.question_text,
               c.name AS competency, m.video_path, m.audio_path
        FROM {s}.session_questions sq
        JOIN {s}.interview_questions q ON q.id = sq.question_id
        LEFT JOIN {s}.competencies c   ON c.id = sq.competency_id
        LEFT JOIN {s}.media_assets m   ON m.question_id = sq.question_id
        WHERE sq.session_id = %s ORDER BY sq.order_no
    """.format(s=SCHEMA), (int(row["session_id"]),))

    if plan.empty:
        st.warning("У сессии нет плана вопросов.")
        return

    tab_q, tab_code = st.tabs(["Вопросы", "Практическое задание"])

    with tab_q:
        i = st.session_state.get("qi", 0)
        if i >= len(plan):
            st.success("Все вопросы пройдены.")
            if st.button("Завершить собеседование", type="primary"):
                with st.spinner("Обработка ответов..."):
                    call("finish-session", {"session_id": int(row["session_id"])}, 300)
                st.success("Собеседование завершено. Спасибо!")
                st.caption("Обратная связь появится после проверки ответственным за развитие.")
            return

        cur = plan.iloc[i]
        pct = int((i + 1) / len(plan) * 100)
        st.markdown("<div class='eyebrow'>Вопрос %d из %d</div>"
                    "<div class='pbar'><i style='width:%d%%'></i></div>"
                    % (i + 1, len(plan), pct), unsafe_allow_html=True)
        st.markdown("## %s" % esc(cur["competency"] or "—"))

        if cur["video_path"] and os.path.exists(str(cur["video_path"])):
            st.video(str(cur["video_path"]))
        st.markdown("<div class='qcard'>%s</div>" % esc(cur["question_text"]),
                    unsafe_allow_html=True)

        st.markdown("<div class='eyebrow'>Ваш ответ</div>", unsafe_allow_html=True)

        # ключ привязан к вопросу — иначе запись прошлого вопроса
        # останется в поле и уйдёт повторно
        audio = st.audio_input("Нажмите на микрофон, ответьте, затем нажмите снова",
                               key="rec_%d_%d" % (int(row["session_id"]),
                                                  int(cur["question_id"])))

        c_next, c_skip = st.columns([2, 1])

        if c_next.button("Ответил, следующий вопрос", type="primary",
                         disabled=audio is None, use_container_width=True):
            with st.spinner("Сохраняем и расшифровываем..."):
                try:
                    up = requests.post(
                        UPLOAD_URL,
                        files={"file": ("answer.wav", audio.getvalue(), "audio/wav")},
                        data={"session_id": int(row["session_id"]),
                              "question_id": int(cur["question_id"])},
                        timeout=120,
                    ).json()
                    call("save-answer", {
                        "session_id": int(row["session_id"]),
                        "question_id": int(cur["question_id"]),
                        "audio_path": up["audio_path"],
                    }, 300)
                except Exception as e:
                    st.error("Ошибка сохранения: %s" % e)
                    return
            st.session_state.qi = i + 1
            st.rerun()

        if c_skip.button("Пропустить вопрос", use_container_width=True):
            try:
                x("""INSERT INTO {s}.session_answers
                         (session_id, question_id, audio_path, transcript,
                          started_at, finished_at)
                     VALUES (%s, %s, NULL, %s, now(), now())"""
                  .format(s=SCHEMA),
                  (int(row["session_id"]), int(cur["question_id"]),
                   "[ВОПРОС ПРОПУЩЕН] Кандидат не дал ответа по существу."))
                x("""UPDATE {s}.session_questions
                     SET asked_at = coalesce(asked_at, now())
                     WHERE session_id = %s AND question_id = %s"""
                  .format(s=SCHEMA),
                  (int(row["session_id"]), int(cur["question_id"])))
            except Exception as e:
                st.error("Не удалось отметить пропуск: %s" % e)
                return
            st.session_state.qi = i + 1
            st.rerun()

        st.markdown(
            "<div class='hint'>Пропуск фиксируется в отчёте как отсутствие ответа "
            "по существу. Лучше сказать вслух, что вы не знаете ответа, и объяснить "
            "ход своих рассуждений — это оценивается выше молчания.</div>",
            unsafe_allow_html=True)

    with tab_code:
        tasks = q("""
            SELECT ct.id, ct.language, ct.statement, ct.starter_code
            FROM {s}.coding_tasks ct
            JOIN {s}.session_competencies sc ON sc.competency_id = ct.competency_id
            WHERE sc.session_id = %s
        """.format(s=SCHEMA), (int(row["session_id"]),))

        if tasks.empty:
            tasks = q("SELECT id, language, statement, starter_code FROM {s}.coding_tasks LIMIT 3"
                      .format(s=SCHEMA))
        if tasks.empty:
            empty("Практических заданий нет",
                  "Для выбранных компетенций они не заведены.")
            return

        t = tasks.iloc[st.selectbox("Задание", range(len(tasks)),
                                    format_func=lambda k: "Задание %d" % (k + 1))]
        st.markdown(t["statement"])
        code = st.text_area("Ваше решение (%s)" % t["language"],
                            value=t["starter_code"] or "", height=200,
                            key="code_%d" % t["id"])

        if st.button("Проверить решение"):
            with st.spinner("Выполняем..."):
                res = call("check-code", {
                    "session_id": int(row["session_id"]),
                    "task_id": int(t["id"]),
                    "code": code,
                    "timeline": [],
                }, 120)
            last = q("""SELECT exec_status, exec_output, llm_review
                        FROM {s}.coding_submissions
                        WHERE session_id = %s AND task_id = %s
                        ORDER BY id DESC LIMIT 1""".format(s=SCHEMA),
                     (int(row["session_id"]), int(t["id"])))
            if not last.empty:
                stt = last.iloc[0]["exec_status"]
                if stt == "passed":
                    st.success("Решение верное")
                elif stt == "rejected":
                    st.error("Запрос отклонён: %s" % last.iloc[0]["exec_output"])
                elif stt == "error":
                    st.warning("Ошибка выполнения: %s" % last.iloc[0]["exec_output"])
                else:
                    st.warning("Решение не совпало с ожидаемым результатом")
                if last.iloc[0]["llm_review"]:
                    st.caption(last.iloc[0]["llm_review"])


# ================================================================ ОР

def page_or(me):
    head("Ответственный за развитие", "Кабинет",
         "Назначайте собеседования, проверяйте вопросы и публикуйте обратную связь.")
    t1, t2, t3, t4, t5 = st.tabs(
        ["Назначить", "Мои сессии", "Банк вопросов", "Аналитика", "Напоминания"])

    # --- назначение
    with t1:
        emps = q("SELECT id, full_name, specialty FROM {s}.users WHERE role='employee' ORDER BY full_name"
                 .format(s=SCHEMA))
        if emps.empty:
            empty("Сотрудников нет",
                  "Добавьте их в разделе администрирования.")
        else:
            name = st.selectbox("Сотрудник", emps["full_name"])
            emp = emps[emps["full_name"] == name].iloc[0]

            comps = q("""
                SELECT c.id, c.name, c.kind, ec.status,
                       (SELECT count(*) FROM {s}.interview_questions q
                         WHERE q.competency_id = c.id AND q.status='approved') AS n_q
                FROM {s}.employee_competencies ec
                JOIN {s}.competencies c ON c.id = ec.competency_id
                WHERE ec.employee_id = %s AND ec.status <> 'confirmed'
                ORDER BY c.kind, c.name
            """.format(s=SCHEMA), (int(emp["id"]),))

            if comps.empty:
                empty("Все компетенции подтверждены",
                      "Собеседование назначать не по чему.")
            else:
                ready = comps[comps["n_q"] > 0].copy()
                if len(ready) < len(comps):
                    st.caption("Скрыто %d компетенций без одобренных вопросов."
                               % (len(comps) - len(ready)))
                if ready.empty:
                    empty("Нет одобренных вопросов",
                          "Проверьте банк вопросов на соседней вкладке.")
                else:
                    ready["label"] = (ready["name"] + "  ·  "
                                      + ready["kind"].map(KIND_RU).fillna("")
                                      + "  ·  вопросов: " + ready["n_q"].astype(str))
                    picked = st.multiselect("Фокусные компетенции (от 3 до 5)", ready["label"])
                    st.caption("Выбрано %d из 3–5" % len(picked))
                    dur = st.select_slider("Длительность, мин", [20, 25, 30], value=30)
                    tr = st.checkbox("Тренировочная — не входит в корпоративную отчётность")

                    ok = 3 <= len(picked) <= 5
                    if st.button("Создать сессию", type="primary", disabled=not ok):
                        ids = ready[ready["label"].isin(picked)]["id"].astype(int).tolist()
                        res = call("create-session", {
                            "employee_id": int(emp["id"]), "or_id": int(me["id"]),
                            "competency_ids": ids, "duration_min": int(dur),
                            "is_training": bool(tr)})
                        if res.get("token"):
                            st.success("Сессия №%s создана" % res.get("session_id"))
                            st.code("%s/?token=%s" % (APP_URL, res["token"]))
                        else:
                            st.error(res.get("error", "не удалось"))

    # --- сессии
    with t2:
        ses = q("""
            SELECT s.id AS "№", u.full_name AS "Сотрудник", s.status AS st,
                   s.duration_min AS "Мин", s.is_training AS "Трен.",
                   s.created_at AS "Создана"
            FROM {s}.interview_sessions s
            LEFT JOIN {s}.users u ON u.id = s.employee_id
            WHERE s.or_id = %s ORDER BY s.id DESC
        """.format(s=SCHEMA), (int(me["id"]),))
        if ses.empty:
            empty("Сессий пока нет", "Назначьте первую на вкладке «Назначить».")
        else:
            for _, r in ses.head(15).iterrows():
                tr = " <span class='pill neu'>тренировочная</span>" if r["Трен."] else ""
                st.markdown(crow("№%d · %s" % (r["№"], r["Сотрудник"] or "—"),
                                 pill(r["st"]) + tr, "%s мин" % r["Мин"]),
                            unsafe_allow_html=True)

            sid = st.selectbox("Открыть отчёт по сессии", ses["№"])
            show_reports(int(sid), int(me["id"]))

    # --- банк вопросов
    with t3:
        page_review(me)

    # --- аналитика
    with t4:
        page_analytics()

    # --- напоминания
    with t5:
        rem = q("""SELECT employee_name AS "Сотрудник", due_at AS "Срок", state AS "Состояние"
                   FROM {s}.v_or_reminders WHERE or_id = %s ORDER BY due_at"""
                .format(s=SCHEMA), (int(me["id"]),))
        if rem.empty:
            empty("Напоминаний нет",
                  "Появятся через 10 рабочих дней после завершённой сессии.")
        else:
            st.dataframe(rem, use_container_width=True, hide_index=True)


def show_reports(sid, or_id):
    reps = q("""SELECT level, content, status, published_at
                FROM {s}.reports WHERE session_id = %s ORDER BY level""".format(s=SCHEMA), (sid,))
    if reps.empty:
        empty("Отчёты ещё не сформированы",
              "Сначала оцените сессию, затем сформируйте отчёты.")
        c1, c2 = st.columns(2)
        if c1.button("Оценить сессию"):
            with st.spinner("Оценка..."):
                call("evaluate-session", {"session_id": sid}, 600)
            st.rerun()
        if c2.button("Сформировать отчёты"):
            with st.spinner("Формирование..."):
                call("build-reports", {"session_id": sid}, 600)
            st.rerun()
        return

    r1, r2, r3 = st.tabs(["Транскрипция", "Отчёт для руководителя", "Обратная связь сотруднику"])

    def content(level):
        row = reps[reps["level"] == level]
        if row.empty:
            return None, None
        c = row.iloc[0]["content"]
        if isinstance(c, str):
            c = json.loads(c)
        return c, row.iloc[0]

    with r1:
        c, _ = content(1)
        if c:
            st.text(c.get("text", ""))

    with r2:
        c, _ = content(2)
        if c:
            flags = c.get("red_flags_count", 0)
            metrics_row([
                metric("Средний уровень", c.get("avg_ku", "—"), "/ 5"),
                metric("Ответов", c.get("answers_count", "—")),
                metric("Темп речи", c.get("behavior", {}).get("avg_wpm", "—"), "сл/мин"),
                metric("Красных флагов", flags, "", alert=bool(flags)),
            ])

            if c.get("red_flags_count", 0):
                fl = q("SELECT flag_type AS Тип, evidence AS Фрагмент FROM {s}.red_flags WHERE session_id = %s"
                       .format(s=SCHEMA), (sid,))
                st.error("Зафиксированы красные флаги")
                st.dataframe(fl, use_container_width=True, hide_index=True)

            if c.get("competencies"):
                st.markdown("### Компетенции")
                for it in c["competencies"]:
                    st.markdown(crow(it.get("competency", "—"), ku(it.get("ku", 0))),
                                unsafe_allow_html=True)

            for key, title in [("strengths", "Сильные стороны"),
                               ("gaps", "Зоны роста"),
                               ("recommendations", "Рекомендации")]:
                if c.get(key):
                    st.markdown("**%s**" % title)
                    for it in c[key]:
                        st.markdown("- %s" % it)

            if st.button("Выгрузить PDF", key="pdf2"):
                res = call("export-pdf", {"session_id": sid, "level": 2,
                                          "requester_id": or_id, "role": "or"}, 120)
                st.success(res.get("pdf_path", res.get("error", "?")))

    with r3:
        c, meta = content(3)
        if c:
            published = meta["status"] == "published"
            st.caption("Опубликовано %s" % meta["published_at"] if published
                       else "Черновик — сотруднику пока не виден")
            txt = st.text_area("Текст обратной связи", value=c.get("summary", ""), height=160)
            if c.get("strengths"):
                st.markdown("**Сильные стороны**")
                for it in c["strengths"]:
                    st.markdown("- %s" % it)
            if c.get("next_steps"):
                st.markdown("**Что развивать**")
                for it in c["next_steps"]:
                    st.markdown("- %s" % it)

            if st.button("Опубликовать сотруднику", type="primary"):
                res = call("publish-report", {"session_id": sid, "or_id": or_id, "summary": txt})
                if res.get("ok") is not False:
                    st.success("Опубликовано")
                    st.rerun()
                else:
                    st.error(res.get("error"))


def page_review(me):
    qs = q("""SELECT question_id, competency_name, kind, question_type,
                     question_text, reference_answer, status, original_text
              FROM {s}.v_questions_to_review LIMIT 100""".format(s=SCHEMA))
    if qs.empty:
        empty("Банк вопросов пуст", "Запустите генератор вопросов в n8n.")
        return

    only_draft = st.checkbox("Только непроверенные", value=True)
    view = qs[qs["status"] == "draft"] if only_draft else qs
    if view.empty:
        st.success("Все вопросы проверены.")
        return

    st.caption("Показано %d из %d" % (len(view), len(qs)))

    for _, r in view.head(20).iterrows():
        with st.expander("[%s] %s — %s" % (ru(r["status"]), r["competency_name"] or "—",
                                            str(r["question_text"])[:70])):
            if r["original_text"]:
                st.caption("Исходный текст: %s" % r["original_text"])
            qt = st.text_area("Вопрос", value=r["question_text"],
                              key="qt%d" % r["question_id"], height=80)
            ra = st.text_area("Эталонный ответ", value=r["reference_answer"] or "",
                              key="ra%d" % r["question_id"], height=80)
            cm = st.text_input("Комментарий", key="cm%d" % r["question_id"])
            c1, c2, c3 = st.columns(3)

            def send(action, **kw):
                p = {"question_id": int(r["question_id"]), "or_id": int(me["id"]),
                     "action": action, "comment": cm}
                p.update(kw)
                call("review-question", p)
                st.rerun()

            if c1.button("Одобрить", key="ap%d" % r["question_id"]):
                send("approve")
            if c2.button("Отклонить", key="rj%d" % r["question_id"]):
                send("reject")
            if c3.button("Сохранить правку", key="ed%d" % r["question_id"]):
                send("edit", question_text=qt, reference_answer=ra)


def page_analytics():
    prog = q("SELECT * FROM {s}.v_competency_progress WHERE is_training = false".format(s=SCHEMA))
    if prog.empty:
        empty("Данных пока нет",
              "График появится после первой оценённой сессии.")
    else:
        emps = prog["employee_name"].dropna().unique().tolist()
        who = st.selectbox("Сотрудник", emps)
        d = prog[prog["employee_name"] == who]
        try:
            import plotly.express as px
            fig = px.line(d, x="session_date", y="ku_level", color="competency_name",
                          markers=True, labels={"session_date": "Дата",
                                                "ku_level": "Уровень",
                                                "competency_name": "Компетенция"})
            fig.update_yaxes(range=[0, 5.5])
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.line_chart(d.pivot_table(index="session_date", columns="competency_name",
                                        values="ku_level"))

        delta = q("SELECT * FROM {s}.v_competency_delta".format(s=SCHEMA))
        if not delta.empty:
            st.markdown("**Динамика по компетенциям**")
            st.dataframe(delta, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Импорт внешнего собеседования**")
    emps = q("SELECT id, full_name FROM {s}.users WHERE role='employee'".format(s=SCHEMA))
    if not emps.empty:
        e = st.selectbox("Сотрудник ", emps["full_name"], key="ext_emp")
        eid = int(emps[emps["full_name"] == e].iloc[0]["id"])
        comp = st.text_input("Компания")
        dt = st.date_input("Дата")
        cmt = st.text_area("Комментарий", height=70)
        if st.button("Импортировать"):
            res = call("import-external", {"employee_id": eid, "company": comp,
                                           "held_at": str(dt), "comment": cmt,
                                           "imported_by": 1, "scores": []})
            if res.get("ok") is not False:
                st.success("Импортировано")
            else:
                st.error(res.get("error"))

    ext = q("""SELECT тип AS "Тип", компания AS "Компания", дата AS "Дата"
               FROM {s}.v_all_interviews ORDER BY дата DESC""".format(s=SCHEMA))
    if not ext.empty:
        st.dataframe(ext, use_container_width=True, hide_index=True)


# ================================================================ АССИСТЕНТ

def page_assistant(me):
    head("Ассистент", "Кабинет",
         "Бронирование времени и выдача ссылок. Оценки и вопросы недоступны.")

    free = q("""SELECT slot_id, время, or_name, or_id FROM {s}.v_slots_calendar
                WHERE status='free' ORDER BY starts_at LIMIT 40""".format(s=SCHEMA))
    ses = q("""SELECT s.id, u.full_name AS emp, s.or_id
               FROM {s}.interview_sessions s
               LEFT JOIN {s}.users u ON u.id = s.employee_id
               WHERE s.status='planned' AND s.slot_id IS NULL AND s.or_id IS NOT NULL
               ORDER BY s.id DESC""".format(s=SCHEMA))

    if ses.empty:
        empty("Всё назначено", "Новые сессии появятся здесь после создания.")
    elif free.empty:
        empty("Свободных слотов нет", "Календарь заполнен на две недели вперёд.")
    else:
        c1, c2 = st.columns(2)
        s_lab = ses["id"].astype(str) + " — " + ses["emp"].fillna("—")
        pick_s = c1.selectbox("Сессия", s_lab)
        srow = ses.iloc[list(s_lab).index(pick_s)]

        fit = free[free["or_id"] == srow["or_id"]]
        if fit.empty:
            c2.error("Нет слотов у этого ОР")
        else:
            f_lab = fit["время"] + " — " + fit["or_name"].fillna("")
            pick_f = c2.selectbox("Слот", f_lab)
            frow = fit.iloc[list(f_lab).index(pick_f)]

            if st.button("Забронировать", type="primary"):
                res = call("book-slot", {"slot_id": int(frow["slot_id"]),
                                         "session_id": int(srow["id"]),
                                         "assistant_id": int(me["id"])})
                if res.get("token"):
                    st.success("Забронировано")
                    st.code("%s/?token=%s" % (APP_URL, res["token"]))
                else:
                    st.error(res.get("error", "не удалось"))

    st.divider()
    booked = q("""SELECT время AS "Время", employee_name AS "Сотрудник", or_name AS "ОР"
                  FROM {s}.v_slots_calendar WHERE status='booked' ORDER BY starts_at"""
               .format(s=SCHEMA))
    st.markdown("**Забронированные встречи**")
    if not booked.empty:
        st.dataframe(booked, use_container_width=True, hide_index=True)
    else:
        st.caption("пока нет")


# ================================================================ СОТРУДНИК

def page_employee(me):
    head("Сотрудник", "Мой кабинет",
         "Назначенные собеседования, прогресс по компетенциям и обратная связь.")
    t1, t2, t3 = st.tabs(["Приглашения", "Мои компетенции", "Обратная связь"])

    with t1:
        inv = q("""SELECT s.id, s.status, s.is_training, r.token, sl.starts_at
                   FROM {s}.interview_sessions s
                   LEFT JOIN {s}.rooms r ON r.session_id = s.id
                   LEFT JOIN {s}.slots sl ON sl.id = s.slot_id
                   WHERE s.employee_id = %s AND s.status IN ('planned','in_progress')
                   ORDER BY s.id DESC""".format(s=SCHEMA), (int(me["id"]),))
        if inv.empty:
            empty("Назначенных собеседований нет",
                  "Можно запустить тренировочное — кнопка ниже.")
        else:
            for _, r in inv.iterrows():
                lbl = "Сессия №%d — %s" % (r["id"], ru(r["status"]))
                if r["is_training"]:
                    lbl += " (тренировочная)"
                if pd.notna(r["starts_at"]):
                    lbl += " · %s" % pd.Timestamp(r["starts_at"]).strftime("%d.%m %H:%M")
                st.write(lbl)
                if r["token"]:
                    st.code("%s/?token=%s" % (APP_URL, r["token"]))

        st.divider()
        st.markdown("**Тренировочное собеседование**")
        st.caption("Запускается самостоятельно, результат виден только вам.")
        dur = st.select_slider("Длительность", [20, 25, 30], value=20, key="tr_dur")
        if st.button("Начать тренировку"):
            res = call("start-training", {"employee_id": int(me["id"]), "duration_min": int(dur)})
            if res.get("token"):
                st.success("Тренировка создана")
                st.code("%s/?token=%s" % (APP_URL, res["token"]))
            else:
                st.error(res.get("error", "не удалось"))

    with t2:
        comp = q("""SELECT c.name AS "Название", c.kind, ec.status
                    FROM {s}.employee_competencies ec
                    JOIN {s}.competencies c ON c.id = ec.competency_id
                    WHERE ec.employee_id = %s ORDER BY ec.status, c.name"""
                 .format(s=SCHEMA), (int(me["id"]),))
        if not comp.empty:
            metrics_row([
                metric("Подтверждено", int((comp["status"] == "confirmed").sum())),
                metric("В работе", int((comp["status"] == "in_progress").sum())),
                metric("Не начато", int((comp["status"] == "not_started").sum())),
            ])
            for _, r in comp.iterrows():
                st.markdown(crow(r["Название"], pill(r["status"]),
                                 KIND_RU.get(r["kind"], "")),
                            unsafe_allow_html=True)

    with t3:
        fb = q("""SELECT session_id, content, published_at, is_training
                  FROM {s}.v_reports_employee WHERE employee_id = %s
                  ORDER BY session_id DESC""".format(s=SCHEMA), (int(me["id"]),))
        if fb.empty:
            empty("Обратной связи пока нет",
                  "Она появится после проверки ответственным за развитие.")
        else:
            for _, r in fb.iterrows():
                c = r["content"]
                if isinstance(c, str):
                    c = json.loads(c)
                caption = "Сессия №%d" % r["session_id"]
                if r["is_training"]:
                    caption += " · тренировочный отчёт"
                with st.expander(caption, expanded=True):
                    st.write(c.get("summary", ""))
                    if c.get("strengths"):
                        st.markdown("**Ваши сильные стороны**")
                        for it in c["strengths"]:
                            st.markdown("- %s" % it)
                    if c.get("next_steps"):
                        st.markdown("**Что развивать дальше**")
                        for it in c["next_steps"]:
                            st.markdown("- %s" % it)
                    if r["published_at"]:
                        st.caption("Проверено ответственным за развитие")


def page_admin(me):
    head("Администратор", "Управление системой")
    st.dataframe(q("SELECT id, full_name, email, role, specialty FROM {s}.users ORDER BY id"
                   .format(s=SCHEMA)), use_container_width=True, hide_index=True)
    st.markdown("**Состояние системы**")
    st.dataframe(q("""
        SELECT 'компетенции' AS "Объект", count(*) AS "Кол-во" FROM {s}.competencies
        UNION ALL SELECT 'вопросов одобрено', count(*) FROM {s}.interview_questions WHERE status='approved'
        UNION ALL SELECT 'вопросов с видео', count(*) FROM {s}.media_assets
        UNION ALL SELECT 'сессий', count(*) FROM {s}.interview_sessions
        UNION ALL SELECT 'отчётов', count(*) FROM {s}.reports
        UNION ALL SELECT 'слотов свободных', count(*) FROM {s}.slots WHERE status='free'
    """.format(s=SCHEMA)), use_container_width=True, hide_index=True)


# ================================================================ ВХОД

token = st.query_params.get("token")

if token:
    page_room(token)
else:
    try:
        users = q("SELECT id, full_name, role FROM {s}.users ORDER BY role, full_name".format(s=SCHEMA))
    except Exception as e:
        st.error("Нет связи с базой данных: %s" % e)
        st.stop()

    if users.empty:
        st.error("Таблица пользователей пуста.")
        st.stop()

    with st.sidebar:
        st.markdown("<div class='logo'><span>М</span></div>"
                    "<div class='brand'>МеМАС</div>"
                    "<div class='brand-sub'>Мультимодальная агентная система</div>",
                    unsafe_allow_html=True)
        st.markdown("---")
        who = st.selectbox("Кто вы", users["full_name"])
        me = users[users["full_name"] == who].iloc[0]
        ROLE_RU = {"or": "Отв. за развитие", "assistant": "Ассистент",
                   "employee": "Сотрудник", "admin": "Администратор"}
        st.markdown("<div class='role-dot'>%s</div>"
                    % ROLE_RU.get(me["role"], me["role"]), unsafe_allow_html=True)

    {"or": page_or, "assistant": page_assistant,
     "employee": page_employee, "admin": page_admin}.get(me["role"], page_admin)(me)
