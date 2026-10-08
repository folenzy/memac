import os
import json
import re
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", ""),
    password=os.getenv("DB_PASSWORD", ""),
)

ALLOWED_TABLES = ['sandbox_orders', 'sandbox_products', 'sandbox_order_items']

FORBIDDEN = ['insert', 'update', 'delete', 'drop', 'create', 'alter',
             'truncate', 'grant', 'revoke', 'copy', 'pg_read_file',
             'pg_sleep', 'dblink', 'pg_ls_dir', 'lo_import', 'pg_catalog',
             'information_schema', 'pg_user', 'pg_shadow', 'current_setting']

app = FastAPI(title="MeMAC SQL Runner")


class RunReq(BaseModel):
    code: str
    expected: Optional[List[dict]] = None


def reject(msg):
    return {"status": "rejected", "output": msg, "rows": []}


@app.get("/health")
def health():
    return {"status": "ok", "tables": ALLOWED_TABLES}


@app.post("/run_sql")
def run_sql(r: RunReq):
    code = r.code.strip().rstrip(';').strip()
    low = code.lower()

    if len(code) > 3000:
        return reject("Запрос слишком длинный")

    if ';' in code:
        return reject("Разрешён только один запрос")

    if '--' in code or '/*' in code:
        return reject("Комментарии в запросе запрещены")

    if not low.startswith('select') and not low.startswith('with'):
        return reject("Запрос должен начинаться с SELECT или WITH")

    for word in FORBIDDEN:
        if word in low:
            return reject("Запрещённая операция: " + word)

    refs = re.findall(r'(?:from|join)\s+([\"\w.]+)', low)
    for ref in refs:
        name = ref.replace('"', '').split('.')[-1]
        if name not in ALLOWED_TABLES:
            return reject("Доступ разрешён только к таблицам песочницы: " + name)

    if len(refs) == 0:
        return reject("Запрос должен обращаться к таблице песочницы")

    try:
        conn = psycopg2.connect(**DB, connect_timeout=5)
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '5s'")
        cur.execute(code)
        cols = [d[0] for d in cur.description]
        raw = cur.fetchmany(200)
        cur.close()
        conn.close()
    except Exception as e:
        return {"status": "error", "output": str(e)[:400], "rows": []}

    rows = []
    for row in raw:
        d = {}
        for i, c in enumerate(cols):
            v = row[i]
            if hasattr(v, 'quantize'):
                d[c] = float(v)
            elif v is None or isinstance(v, (int, float, str)):
                d[c] = v
            else:
                d[c] = str(v)
        rows.append(d)

    status = "executed"
    if r.expected is not None:
        exp = json.loads(json.dumps(r.expected))
        status = "passed" if rows == exp else "failed"

    return {"status": status,
            "output": "строк: " + str(len(rows)),
            "rows": rows,
            "columns": cols}


import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8021)
