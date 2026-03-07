#!/usr/bin/env python3
"""
discord_alerts.py — Unergy Debt Tracker
=========================================
Daily alert dispatcher for obligation due dates.

For every non-conditional periodic obligation it:
  1. Computes the next due date (same logic as dashboard.py).
  2. Divides the full period into 3 equal intervals.
  3. Sends a Discord embed when TODAY matches one of those 3 dates (±1 day).

Environment variable required:
  DISCORD_WEBHOOK_URL  — Discord incoming webhook URL for the target channel.

Run:
  python discord_alerts.py
Or let GitHub Actions execute it daily (see .github/workflows/discord_alerts.yml).
"""

import calendar
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DATA_DIR    = Path(__file__).parent
TODAY       = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
TOLERANCE   = 1   # ± days: a scheduled job that slips by 1 day still fires

# ── Lookup tables ─────────────────────────────────────────────────────────────
SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

MONTH_SHORT = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

# Discord embed colours (integer, Unergy brand palette)
SEV_COLOR = {
    "critica": 0x2C2039,   # Púrpura Profundo
    "alta":    0x915BD8,   # Púrpura Enérgico
    "media":   0xB48DD9,   # Tint purple
    "baja":    0xD9CCF0,   # Soft tint
}

SEV_LABEL = {
    "critica": "Crítica 🔴",
    "alta":    "Alta 🟠",
    "media":   "Media 🟡",
    "baja":    "Baja 🟢",
}

ALERT_LABEL = {
    1: "🔔  Primera alerta — 1/3 del período cumplido",
    2: "⚠️  Segunda alerta — 2/3 del período cumplido",
    3: "🚨  Vencimiento hoy",
}

# ── Date helpers (mirrors dashboard.py) ───────────────────────────────────────

def _add_months(dt: datetime, months: int) -> datetime:
    m = dt.month - 1 + months
    year  = dt.year + m // 12
    month = m % 12 + 1
    day   = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)


def _freq_to_months(freq_str: str):
    f = freq_str.lower()
    if "mensual"     in f:                             return 1
    if "bimestral"   in f or "bimensual"   in f:       return 2
    if "trimestral"  in f or "cada 3 meses" in f:      return 3
    if "cuatrimestral" in f or "cada 4 meses" in f:    return 4
    if "semestral"   in f or "cada 6 meses" in f:      return 6
    if "anual"       in f or "annual"       in f:      return 12
    return None


def _freq_to_days(freq_str: str) -> int:
    f = freq_str.lower()
    if "semanal"    in f or "weekly"    in f: return 7
    if "quincenal"  in f or "biweekly"  in f: return 14
    if "mensual"    in f or "monthly"   in f: return 30
    if "trimestral" in f or "quarterly" in f: return 90
    if "semestral"  in f or "semi"      in f: return 180
    if "anual"      in f or "annual"    in f: return 365
    return 0


def parse_contract_date(date_str: str) -> datetime:
    for fmt in ("%d de %B de %Y", "%d/%m/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            pass
    if date_str:
        low = date_str.lower()
        for mname, mnum in SPANISH_MONTHS.items():
            if mname in low:
                nums = re.findall(r"\d+", low)
                if len(nums) >= 2:
                    try:
                        return datetime(int(nums[-1]), mnum, int(nums[0]))
                    except ValueError:
                        pass
    return datetime(2025, 10, 27)   # FMO signing date fallback


# ── Conditional-obligation detection (mirrors dashboard.py) ───────────────────

_PERIODIC_KW = [
    "mensual", "bimestral", "trimestral", "cuatrimestral",
    "semestral", "anual", "annual", "quarterly", "monthly",
]

_CONDITIONAL_PATTERNS = [
    r"\bupon\s+(?:becoming\s+aware|occurrence|receipt|notification|notice|request|demand|default|delivery)\b",
    r"\bfollowing\s+(?:any\s+such|receipt|notification|notice|the\s+occurrence|such)\b",
    r"\bafter\s+(?:the\s+)?(?:occurrence|receipt|notification|notice|becoming\s+aware|such)\b",
    r"\bas\s+soon\s+as\s+(?:reasonably\s+)?practicable\b",
    r"\bpromptly\s+(?:upon|after|following)\b",
    r"\bwithin\s+\d+\s+(?:business\s+days?|calendar\s+days?|days?)\s+(?:of|after|upon|following)\b",
    r"\bdentro\s+de\s+\d+\s+días?\s*(?:hábiles?|laborales?|calendario|naturales?)?\s*"
     r"(?:de|desde|a\s+partir|contados|luego|tras|después)",
    r"\ben\s+un\s+plazo\s+de\s+\d+",
    r"\buna\s+vez\s+que\b",
    r"\buna\s+vez\s+(?:ocurrido|presentado|recibido|notificado|informado)\b",
    r"\bal\s+momento\s+de\s+(?:conocer|recibir|tener\s+conocimiento)\b",
    r"\bcuando\s+(?:ocurra|se\s+produzca|se\s+presente|tenga\s+conocimiento)\b",
    r"\btras\s+(?:la\s+)?(?:ocurrencia|notificación|recepción|conocimiento)\b",
]


def _is_conditional(item: dict) -> bool:
    text = " ".join([item.get("obligacion", ""), item.get("frecuencia", "")]).lower()
    if any(kw in text for kw in _PERIODIC_KW):
        return False
    return any(re.search(p, text) for p in _CONDITIONAL_PATTERNS)


# ── Core: compute due date + period for one obligation ────────────────────────

def compute_due_and_period(contract: dict, item: dict):
    """
    Returns (due_date, period_days) for a periodic obligation, or None if
    the obligation is conditional / one-off (no fixed calendar date).
    """
    if _is_conditional(item):
        return None

    info      = contract.get("informacion_del_contrato", {})
    start     = parse_contract_date(info.get("fecha_de_ejecucion", ""))
    freq_text = item.get("frecuencia", "")

    # 1. Explicit day+month in item texts
    month_re = "|".join(SPANISH_MONTHS.keys())
    pattern  = rf"(\d{{1,2}})\s+(?:de\s+)?({month_re})"
    candidates = []
    for text in [item.get("obligacion", ""), freq_text]:
        for day_s, mon_s in re.findall(pattern, text.lower()):
            mnum = SPANISH_MONTHS.get(mon_s)
            if not mnum:
                continue
            for yr in [TODAY.year, TODAY.year + 1]:
                try:
                    d = datetime(yr, mnum, int(day_s))
                    if d >= TODAY:
                        candidates.append(d)
                        break
                except ValueError:
                    pass
    if candidates:
        due = min(candidates)
        pm  = _freq_to_months(freq_text)
        period_days = (due - _add_months(due, -pm)).days if pm else (_freq_to_days(freq_text) or 365)
        return due, period_days

    # 2. Calendar-month arithmetic
    pm = _freq_to_months(freq_text)
    if pm:
        nxt = _add_months(start, pm)
        while nxt < TODAY:
            nxt = _add_months(nxt, pm)
        period_days = (nxt - _add_months(nxt, -pm)).days
        return nxt, period_days

    # 3. Day-based fallback
    days = _freq_to_days(freq_text)
    if days == 0:
        return None
    nxt = start + timedelta(days=days)
    while nxt < TODAY:
        nxt += timedelta(days=days)
    return nxt, days


# ── Alert date split ──────────────────────────────────────────────────────────

def alert_dates(due_date: datetime, period_days: int):
    """
    Divide the period into 3 equal parts.
      Alert 1 → due_date − ⌊period * 2/3⌋  (first early warning)
      Alert 2 → due_date − ⌊period * 1/3⌋  (halfway reminder)
      Alert 3 → due_date                    (deadline)
    """
    third = period_days / 3
    return [
        (due_date - timedelta(days=round(third * 2)), 1),
        (due_date - timedelta(days=round(third)),      2),
        (due_date,                                     3),
    ]


def is_alert_day(target: datetime) -> bool:
    return abs((target - TODAY).days) <= TOLERANCE


# ── Discord message builder ───────────────────────────────────────────────────

def build_embed(contract: dict, item: dict, due_date: datetime, alert_num: int) -> dict:
    bank    = contract.get("informacion_del_contrato", {}).get("nombre_del_banco", "—")
    ob_text = item.get("obligacion", "Sin descripción")[:200]
    freq    = item.get("frecuencia", "—")
    sev     = item.get("severidad", "media")
    due_str = f"{due_date.day} {MONTH_SHORT[due_date.month]} {due_date.year}"
    days_left = max(0, (due_date - TODAY).days)

    return {
        "title":       ALERT_LABEL.get(alert_num, f"Alerta {alert_num}/3"),
        "description": f"**{ob_text}**",
        "color":       SEV_COLOR.get(sev, 0x915BD8),
        "fields": [
            {"name": "📅 Fecha de vencimiento", "value": due_str,                          "inline": True},
            {"name": "⏳ Días restantes",        "value": str(days_left),                   "inline": True},
            {"name": "🏦 Acreedor",              "value": bank,                             "inline": True},
            {"name": "🔁 Frecuencia",            "value": freq,                             "inline": True},
            {"name": "⚡ Severidad",             "value": SEV_LABEL.get(sev, sev.title()),  "inline": True},
        ],
        "footer":    {"text": "Unergy Debt Tracker · Obligaciones"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ── HTTP send ─────────────────────────────────────────────────────────────────

def send_embed(embed: dict) -> None:
    if not WEBHOOK_URL:
        print("  [WARN] DISCORD_WEBHOOK_URL not set — message not sent")
        return
    payload = json.dumps({"embeds": [embed]}).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"  → Sent  HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"  → ERROR HTTP {e.code}: {e.read().decode()}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(test_mode: bool = False) -> None:
    print(f"Unergy Discord Alerts — {TODAY.date()}\n{'─'*50}")
    if test_mode:
        print("⚠️  TEST MODE — sending first available obligation regardless of date\n")

    contract_files = sorted(DATA_DIR.glob("contract_data*.json"))
    if not contract_files:
        print("[ERROR] No contract_data*.json files found in", DATA_DIR)
        sys.exit(1)

    total_sent = 0

    for fp in contract_files:
        with open(fp, "r", encoding="utf-8") as fh:
            contract = json.load(fh)

        bank = contract.get("informacion_del_contrato", {}).get("nombre_del_banco", fp.name)
        print(f"\n[{bank}]")

        resp = contract.get("responsabilidades", {})
        for items in resp.values():
            for item in items:
                result = compute_due_and_period(contract, item)
                if result is None:
                    continue
                due_date, period_days = result

                # Test mode: send the first obligation we find, using alert 1
                if test_mode and total_sent == 0:
                    label = item.get("obligacion", "")[:60]
                    print(f"  TEST ALERT 1/3 | vence {due_date.date()} | {label}")
                    embed = build_embed(contract, item, due_date, 1)
                    embed["title"] = "🧪 [PRUEBA] " + embed["title"]
                    send_embed(embed)
                    total_sent += 1
                    continue

                for alert_date, alert_num in alert_dates(due_date, period_days):
                    if is_alert_day(alert_date):
                        label = item.get("obligacion", "")[:60]
                        print(f"  ALERT {alert_num}/3 | vence {due_date.date()} | {label}")
                        embed = build_embed(contract, item, due_date, alert_num)
                        send_embed(embed)
                        total_sent += 1

        if test_mode and total_sent > 0:
            break  # one test message is enough

    # Always send a daily heartbeat so the team knows the bot ran
    if total_sent == 0:
        heartbeat = {
            "title": "✅ Sin alertas pendientes hoy",
            "description": (
                f"El bot revisó todas las obligaciones el **{TODAY.strftime('%d/%m/%Y')}** "
                f"y no hay vencimientos próximos que requieran notificación."
            ),
            "color": 0x2C2039,
            "footer": {"text": "Unergy Debt Tracker · Revisión diaria"},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        send_embed(heartbeat)
        print("  → Heartbeat enviado (sin alertas hoy)")

    print(f"\n{'─'*50}")
    print(f"✅  {total_sent} alert(s) dispatched for {TODAY.date()}")


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    run(test_mode=test_mode)
