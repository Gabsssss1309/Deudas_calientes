"""
sync_from_json.py — Unergy Debt Tracker
=========================================
Reads contract_data*.json files from the repo root and upserts every
non-conditional periodic obligation into the Supabase `obligaciones` table.

Run BEFORE starting the bot (or daily before the alert check):
    python sync_from_json.py

Safe to re-run: uses deterministic UUIDs so the same obligation always
maps to the same row (insert on first run, update on subsequent runs).
"""

import asyncio
import calendar
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db import async_session, engine
from models import Base, Deuda, Obligacion

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent   # repo root (contract_data*.json live here)

# ── Area mapping: dashboard areas → bot constraint values ─────────────────────
AREA_MAP = {
    "contable":       "compliance",
    "financiero":     "financiera",
    "legal":          "legal",
    "socioambiental": "ambiental",
    "operaciones":    "operaciones",
}

# JSON category key → bot area (direct mapping for categories that are unambiguous)
CAT_AREA_MAP = {
    "obligaciones_de_pago":                "financiera",
    "obligaciones_contables_y_de_reporte": "compliance",
    "obligaciones_financieras":            "financiera",
    "obligaciones_legales":                "legal",
    "obligaciones_ambientales_sociales":   "ambiental",
}

LEGAL_KW   = ["legal", "contrat", "ley ", "regulat", "permit", "licenci", "notif", "report"]
SUPPLY_KW  = ["suministr", "proveedor", "compra", "adquisici"]

TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# ── Date helpers ──────────────────────────────────────────────────────────────
SPANISH_MONTHS = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12,
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
}

def _add_months(dt: datetime, months: int) -> datetime:
    m    = dt.month - 1 + months
    year = dt.year + m // 12
    mon  = m % 12 + 1
    day  = min(dt.day, calendar.monthrange(year, mon)[1])
    return datetime(year, mon, day)

def _freq_to_months(f: str):
    f = f.lower()
    if "mensual"       in f:                            return 1
    if "bimestral"     in f or "bimensual"   in f:      return 2
    if "trimestral"    in f or "cada 3 meses" in f:     return 3
    if "cuatrimestral" in f or "cada 4 meses" in f:     return 4
    if "semestral"     in f or "cada 6 meses" in f:     return 6
    if "anual"         in f or "annual"       in f:     return 12
    return None

def _freq_to_days(f: str) -> int:
    f = f.lower()
    if "semanal"    in f: return 7
    if "quincenal"  in f: return 14
    if "mensual"    in f: return 30
    if "trimestral" in f: return 90
    if "semestral"  in f: return 180
    if "anual"      in f: return 365
    return 0

def parse_contract_date(s: str) -> datetime:
    for fmt in ("%d de %B de %Y", "%d/%m/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    if s:
        low = s.lower()
        for mname, mnum in SPANISH_MONTHS.items():
            if mname in low:
                nums = re.findall(r"\d+", low)
                if len(nums) >= 2:
                    try:
                        return datetime(int(nums[-1]), mnum, int(nums[0]))
                    except ValueError:
                        pass
    return datetime(2025, 10, 27)

# ── Conditional detection ─────────────────────────────────────────────────────
_PERIODIC_KW = ["mensual","bimestral","trimestral","cuatrimestral","semestral","anual","annual","quarterly","monthly"]
_COND_PATTERNS = [
    r"\bupon\s+(?:becoming\s+aware|occurrence|receipt|notification|notice|request|demand|default|delivery)\b",
    r"\bfollowing\s+(?:any\s+such|receipt|notification|notice|the\s+occurrence|such)\b",
    r"\bas\s+soon\s+as\s+(?:reasonably\s+)?practicable\b",
    r"\bpromptly\s+(?:upon|after|following)\b",
    r"\bwithin\s+\d+\s+(?:business\s+days?|calendar\s+days?|days?)\s+(?:of|after|upon|following)\b",
    r"\bdentro\s+de\s+\d+\s+días?\s*(?:hábiles?|laborales?|calendario|naturales?)?\s*(?:de|desde|a\s+partir|contados|luego|tras|después)",
    r"\ben\s+un\s+plazo\s+de\s+\d+",
    r"\buna\s+vez\s+que\b",
    r"\buna\s+vez\s+(?:ocurrido|presentado|recibido|notificado|informado)\b",
    r"\bcuando\s+(?:ocurra|se\s+produzca|se\s+presente|tenga\s+conocimiento)\b",
    r"\btras\s+(?:la\s+)?(?:ocurrencia|notificación|recepción|conocimiento)\b",
]

def _is_conditional(item: dict) -> bool:
    text = " ".join([item.get("obligacion",""), item.get("frecuencia","")]).lower()
    if any(kw in text for kw in _PERIODIC_KW):
        return False
    return any(re.search(p, text) for p in _COND_PATTERNS)

# ── Area assignment ───────────────────────────────────────────────────────────
def _assign_area(cat_key: str, item: dict) -> str:
    if cat_key in CAT_AREA_MAP:
        return CAT_AREA_MAP[cat_key]
    text = (item.get("obligacion","") + " " + item.get("frecuencia","")).lower()
    if "obligaciones_operativas" in cat_key:
        if any(k in text for k in LEGAL_KW):
            return "legal"
        if any(k in text for k in SUPPLY_KW):
            return "ambiental"
        return "operaciones"
    return "operaciones"

# ── Due date + period computation ─────────────────────────────────────────────
def _compute_due_and_period(contract: dict, item: dict):
    """Returns (due_date, period_days) or None if conditional/one-off."""
    if _is_conditional(item):
        return None

    info  = contract.get("informacion_del_contrato", {})
    start = parse_contract_date(info.get("fecha_de_ejecucion",""))
    freq  = item.get("frecuencia","")

    # 1. Explicit day+month in item texts
    month_re = "|".join(SPANISH_MONTHS.keys())
    pattern  = rf"(\d{{1,2}})\s+(?:de\s+)?({month_re})"
    candidates = []
    for txt in [item.get("obligacion",""), freq]:
        for day_s, mon_s in re.findall(pattern, txt.lower()):
            mnum = SPANISH_MONTHS.get(mon_s)
            if not mnum:
                continue
            for yr in [TODAY.year, TODAY.year+1]:
                try:
                    d = datetime(yr, mnum, int(day_s))
                    if d >= TODAY:
                        candidates.append(d)
                        break
                except ValueError:
                    pass
    if candidates:
        due = min(candidates)
        pm  = _freq_to_months(freq)
        period_days = (due - _add_months(due, -pm)).days if pm else (_freq_to_days(freq) or 365)
        return due, period_days

    # 2. Calendar-month arithmetic
    pm = _freq_to_months(freq)
    if pm:
        nxt = _add_months(start, pm)
        while nxt < TODAY:
            nxt = _add_months(nxt, pm)
        period_days = (nxt - _add_months(nxt, -pm)).days
        return nxt, period_days

    # 3. Day-based fallback
    days = _freq_to_days(freq)
    if days == 0:
        return None
    nxt = start + timedelta(days=days)
    while nxt < TODAY:
        nxt += timedelta(days=days)
    return nxt, days

# ── Deterministic UUID ────────────────────────────────────────────────────────
def _obligation_uuid(bank_name: str, ob_text: str, freq: str) -> UUID:
    """Same obligation always gets the same UUID — enables safe re-runs."""
    seed = f"{bank_name}|{ob_text[:120]}|{freq[:60]}"
    return uuid5(NAMESPACE_URL, seed)

def _deuda_uuid(bank_name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"deuda|{bank_name}")

# ── Main sync ─────────────────────────────────────────────────────────────────
async def sync():
    contract_files = sorted(DATA_DIR.glob("contract_data*.json"))
    if not contract_files:
        print(f"[ERROR] No contract_data*.json found in {DATA_DIR}")
        sys.exit(1)

    # Ensure the periodo_dias column exists (idempotent)
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE obligaciones ADD COLUMN IF NOT EXISTS periodo_dias INTEGER"
        ))

    total_upserted = 0

    for fp in contract_files:
        with open(fp, "r", encoding="utf-8") as fh:
            contract = json.load(fh)

        info      = contract.get("informacion_del_contrato", {})
        bank_name = info.get("nombre_del_banco", fp.stem)
        deuda_id  = _deuda_uuid(bank_name)

        async with async_session() as session:
            # Ensure Deuda row exists
            existing_deuda = await session.get(Deuda, deuda_id)
            if not existing_deuda:
                session.add(Deuda(
                    id       = deuda_id,
                    nombre   = bank_name,
                    acreedor = bank_name,
                ))
                await session.flush()
                print(f"  [+] Created deuda: {bank_name}")

            resp = contract.get("responsabilidades", {})
            for cat_key, items in resp.items():
                for item in items:
                    result = _compute_due_and_period(contract, item)
                    if result is None:
                        continue

                    due_date, period_days = result
                    ob_text  = item.get("obligacion","")
                    freq     = item.get("frecuencia","")
                    area_bot = _assign_area(cat_key, item)
                    ob_id    = _obligation_uuid(bank_name, ob_text, freq)

                    existing = await session.get(Obligacion, ob_id)
                    if existing:
                        # Update due date and period (may have shifted)
                        existing.fecha_vencimiento = due_date.date()
                        existing.periodo_dias      = period_days
                        existing.actualizado_en    = datetime.utcnow()
                    else:
                        session.add(Obligacion(
                            id                  = ob_id,
                            deuda_id            = deuda_id,
                            descripcion         = ob_text[:500],
                            area                = area_bot,
                            fecha_vencimiento   = due_date.date(),
                            periodo_dias        = period_days,
                            estatus             = "pendiente",
                            notas               = f"Frecuencia: {freq}",
                        ))
                        total_upserted += 1

            await session.commit()
            print(f"[{bank_name}] sync complete")

    print(f"\n✅  {total_upserted} new obligations synced — {TODAY.date()}")


if __name__ == "__main__":
    asyncio.run(sync())
