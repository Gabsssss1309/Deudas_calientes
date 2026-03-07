import streamlit as st
import json
import base64
import random
import re
from pathlib import Path
from datetime import datetime, timedelta
import io

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import requests as http_req
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ══════════════════════════════════════════════════════════════════════════════
# Page config
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Unergy · Debt Tracker",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# Brand constants
# ══════════════════════════════════════════════════════════════════════════════
PURPLE      = "#915BD8"
DEEP_PURPLE = "#2C2039"
CREAM       = "#FDFAF7"
SOLAR_YELLOW = "#F6FF72"

RISK_META = {
    "critica": {"label": "Crítica", "color": "#ef4444", "bg": "#fee2e2", "text": "#991b1b"},
    "alta":    {"label": "Alta",    "color": "#f59e0b", "bg": "#fef3c7", "text": "#92400e"},
    "media":   {"label": "Media",   "color": "#915BD8", "bg": "#ede9fe", "text": "#6d28d9"},
    "baja":    {"label": "Baja",    "color": "#22c55e", "bg": "#dcfce7", "text": "#166534"},
}

STATUS_OPTIONS      = ["Pendiente", "Incompleto", "En Gestión", "Completo"]
CARD_STATUS_OPTIONS = ["Pendiente", "Completo"]   # only these two in card dropdown
STATUS_META = {
    "Pendiente":  {"color": "#94a3b8", "bg": "#f1f5f9", "icon": "–",  "text": "#475569"},
    "Incompleto": {"color": "#f59e0b", "bg": "#fef3c7", "icon": "!",  "text": "#92400e"},
    "En Gestión": {"color": "#915BD8", "bg": "#ede9fe", "icon": "→",  "text": "#5b21b6"},
    "Completo":   {"color": "#10b981", "bg": "#d1fae5", "icon": "✓",  "text": "#065f46"},
}

AREA_CATEGORIES = [
    ("contable",        "Contable"),
    ("financiero",      "Financiero"),
    ("legal",           "Legal"),
    ("socioambiental",  "Socioambiental"),
    ("operaciones",     "Operaciones"),
]
AREA_LABEL_MAP = {key: lbl for key, lbl in AREA_CATEGORIES}

# ── Solarview / Solenium API configuration ──────────────────────────────────
SOLARVIEW_BASE = "https://data.solenium.co/api"
SOLARVIEW_PROJECTS = {
    "FMO": [
        {"name": "La Paz Leyenda",   "id": 1, "cap_kw": 990},
        {"name": "Merengue",         "id": 2, "cap_kw": 990},
        {"name": "Cumbia",           "id": 3, "cap_kw": 990},
        {"name": "Joropo",           "id": 4, "cap_kw": 990},
        {"name": "San Diego Sur",    "id": 5, "cap_kw": 990},
        {"name": "Copey Occidente",  "id": 6, "cap_kw": 990},
        {"name": "Valencia 1",       "id": 7, "cap_kw": 990},
        {"name": "Valencia 2",       "id": 8, "cap_kw": 990},
    ],
    "Davivienda": [
        {"name": "Cacica",    "id": 9,  "cap_kw": 2970},
        {"name": "Piloneras", "id": 10, "cap_kw": 2970},
    ],
}

SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
MONTH_SHORT = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
DATA_DIR = Path(__file__).parent


# ── Supabase client (cached, shared across reruns) ───────────────────────────
@st.cache_resource
def get_supabase():
    """Return a cached Supabase client. Returns None if not configured."""
    if not HAS_SUPABASE:
        return None
    try:
        cfg = st.secrets.get("supabase", {})
        url = cfg.get("url", "")
        key = cfg.get("key", "")
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


def load_statuses() -> dict:
    """Load obligation statuses from Supabase. Falls back to {} on any error."""
    client = get_supabase()
    if client is None:
        return {}
    try:
        response = client.table("obligation_statuses").select("key, status").execute()
        return {row["key"]: row["status"] for row in (response.data or [])}
    except Exception:
        return {}


def save_one_status(key: str, status: str) -> None:
    """Upsert a single obligation status to Supabase. Silent on error."""
    client = get_supabase()
    if client is None:
        return
    try:
        client.table("obligation_statuses").upsert(
            {"key": key, "status": status}
        ).execute()
    except Exception:
        pass


def load_links() -> dict:
    """Load obligation links from Supabase. Falls back to {} on any error."""
    client = get_supabase()
    if client is None:
        return {}
    try:
        response = client.table("obligation_statuses").select("key, link").execute()
        return {row["key"]: row.get("link", "") or "" for row in (response.data or [])}
    except Exception:
        return {}


def save_one_link(key: str, link: str) -> None:
    """Upsert a single obligation link to Supabase. Silent on error."""
    client = get_supabase()
    if client is None:
        return
    try:
        client.table("obligation_statuses").upsert(
            {"key": key, "link": link}
        ).execute()
    except Exception:
        pass


def get_base64_image(filename):
    try:
        with open(DATA_DIR / filename, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except (FileNotFoundError, IOError):
        return ""


def get_bank_display_name(contract):
    """Extract clean bank/lender name from contract JSON."""
    name = contract.get("partes_involucradas", {}).get("prestamista", {}).get("nombre", "Banco")
    known = {"FMO": "FMO", "Davivienda": "Davivienda", "Bancolombia": "Bancolombia",
             "BBVA": "BBVA", "Colpatria": "Colpatria", "Itaú": "Itaú",
             "Scotiabank": "Scotiabank", "Citibank": "Citibank", "IFC": "IFC",
             "BID": "BID", "CAF": "CAF", "KfW": "KfW"}
    for key, display in known.items():
        if key.lower() in name.lower():
            return display
    # Fallback: try parentheses (skip NIT patterns)
    if "(" in name:
        paren = name.split("(")[-1].replace(")", "").strip()
        if not paren.upper().startswith("NIT"):
            return paren
    parts = name.replace(",", "").split()
    skip = {"banco", "s.a.", "s.a.s.", "n.v.", "ltd", "ltda", "sociedad"}
    for p in parts:
        if p.lower() not in skip and len(p) > 2:
            return p
    return name[:20]


def severity_counts(items):
    counts = {"critica": 0, "alta": 0, "media": 0, "baja": 0}
    for item in items:
        s = item.get("severidad", "media")
        if s in counts:
            counts[s] += 1
    return counts


def fmt_money(val):
    if val >= 1_000_000_000:
        return f"COP {val/1_000_000_000:,.1f}B"
    if val >= 1_000_000:
        return f"USD {val:,.0f}"
    return f"{val:,.0f}"


def safe_get(d, *keys, default="N/A"):
    current = d
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current if current is not None else default


def parse_contract_date(date_str):
    """Parse Spanish date like '27 de octubre de 2025'."""
    try:
        clean = date_str.lower().strip()
        if "[•]" in clean or "por definir" in clean:
            return datetime(2026, 3, 1)
        if "(" in clean:
            clean = clean[:clean.index("(")].strip()
        parts = re.findall(r'\b(\d{1,2})\b.*?(\w+).*?(\d{4})', clean)
        if parts:
            day, month_str, year = parts[0]
            month = SPANISH_MONTHS.get(month_str, 1)
            return datetime(int(year), month, int(day))
    except Exception:
        pass
    return datetime(2025, 10, 27)


def freq_to_days(freq_str):
    """Convert obligation frequency string to approximate days interval. Returns 0 for event-driven."""
    f = freq_str.lower()
    if any(k in f for k in ["inmediato", "al cierre", "al momento", "antes del primer",
                             "ante cada evento", "ante modificaciones", "ante cambios",
                             "una vez", "según solicitud", "según se incurran"]):
        return 0
    if "diario" in f or "diaria" in f:
        return 1
    if "semanal" in f:
        return 7
    if "quincenal" in f:
        return 15
    if "mensual" in f:
        return 30
    if "bimestral" in f or "bimensual" in f:
        return 60
    if "trimestral" in f:
        return 90
    if "cuatrimestral" in f:
        return 120
    if "semestral" in f or "cada 6 meses" in f or "fecha de cálculo" in f:
        return 180
    if "anual" in f or "annual" in f:
        return 365
    if "continuo" in f or "periódico" in f:
        return 30  # Treat continuous monitoring as monthly
    # Extract explicit day counts
    m = re.search(r'(\d+)\s*d[ií]as?', f)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*meses?', f)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r'dentro de (\d+)', f)
    if m:
        return int(m.group(1))
    return 30


def risk_to_calendar_color(severidad):
    """Map severity to Unergy brand colour for day-circle accents."""
    if severidad == "critica":
        return "#2C2039"   # Púrpura Profundo — most severe
    if severidad == "alta":
        return "#915BD8"   # Púrpura Enérgico — high priority
    if severidad == "media":
        return "#B48DD9"   # Tint del púrpura — medium
    return "#D9CCF0"       # Tint muy suave — low priority


def assign_area(cat_key, item):
    """Map old JSON category + obligation text to new area classification."""
    text = (item.get("obligacion", "") + " " + item.get("frecuencia", "")).lower()
    if cat_key == "obligaciones_de_pago":
        return "contable"
    if cat_key == "obligaciones_financieras_covenants":
        return "financiero"
    if cat_key == "obligaciones_de_reporte":
        if any(k in text for k in ["financier", "dscr", "ratio", "covenant"]):
            return "financiero"
        return "contable"
    if cat_key == "obligaciones_ambientales_sociales":
        return "socioambiental"
    if cat_key == "obligaciones_operativas_legales":
        legal_kw = ["legal", "judicial", "leyes", "ley ", "norma", "reglamento",
                    "autoriza", "contrato", "agreement", "trust", "security",
                    "land right", "permiso", "derecho", "objectionable",
                    "deadlock", "mou", "offtake", "pari passu", "impuesto",
                    "ranking", "existencia corporativa"]
        if any(k in text for k in legal_kw):
            return "legal"
        if any(k in text for k in ["suministr", "proveedor", "compra", "adquisici"]):
            return "socioambiental"
        return "operaciones"
    return "contable"


def compute_upcoming_30d(contract, items_with_area):
    """Count obligations with next due date within 30 days."""
    info = contract.get("informacion_del_contrato", {})
    start_date = parse_contract_date(info.get("fecha_de_ejecucion", ""))
    today = datetime.now()
    threshold = today + timedelta(days=30)
    count = 0
    for _cat_key, _oi, item, _area in items_with_area:
        days = freq_to_days(item.get("frecuencia", "mensual"))
        if days == 0:
            if today <= start_date <= threshold:
                count += 1
        else:
            current = start_date + timedelta(days=days)
            while current < today:
                current += timedelta(days=days)
            if current <= threshold:
                count += 1
    return count


def is_upcoming_item(contract, item):
    """Return True if this obligation has a due date within the next 30 days."""
    info = contract.get("informacion_del_contrato", {})
    start_date = parse_contract_date(info.get("fecha_de_ejecucion", ""))
    today = datetime.now()
    threshold = today + timedelta(days=30)
    days = freq_to_days(item.get("frecuencia", "mensual"))
    if days == 0:
        return today <= start_date <= threshold
    current = start_date + timedelta(days=days)
    while current < today:
        current += timedelta(days=days)
    return current <= threshold


def _add_months(dt: datetime, months: int) -> datetime:
    """Add an exact number of calendar months, clamping day to month-end if needed."""
    import calendar
    m = dt.month - 1 + months
    year = dt.year + m // 12
    month = m % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime(year, month, day)


def _freq_to_months(freq_str: str):
    """Return period in calendar months, or None if frequency isn't month-based."""
    f = freq_str.lower()
    if "mensual" in f:                                          return 1
    if "bimestral" in f or "bimensual" in f:                   return 2
    if "trimestral" in f or "cada 3 meses" in f:               return 3
    if "cuatrimestral" in f or "cada 4 meses" in f:            return 4
    if "semestral" in f or "cada 6 meses" in f \
            or "fecha de cálculo" in f:                         return 6
    if "anual" in f or "annual" in f:                          return 12
    return None


# Keywords that unambiguously mark a periodic (calendar-based) obligation
_PERIODIC_KW = [
    "mensual", "bimestral", "trimestral", "cuatrimestral",
    "semestral", "anual", "annual", "quarterly", "monthly",
]

# Trigger phrases that indicate the deadline starts AFTER an event occurs
_CONDITIONAL_TRIGGER_PATTERNS = [
    # English
    r'\bupon\s+(?:becoming\s+aware|occurrence|receipt|notification|notice|request|demand|default|delivery)\b',
    r'\bfollowing\s+(?:any\s+such|receipt|notification|notice|the\s+occurrence|such)\b',
    r'\bafter\s+(?:the\s+)?(?:occurrence|receipt|notification|notice|becoming\s+aware|such)\b',
    r'\bas\s+soon\s+as\s+(?:reasonably\s+)?practicable\b',
    r'\bpromptly\s+(?:upon|after|following)\b',
    r'\bwithin\s+\d+\s+(?:business\s+days?|calendar\s+days?|days?)\s+(?:of|after|upon|following)\b',
    r'\bupon\s+the\s+occurrence\b',
    # Spanish
    r'\bdentro\s+de\s+\d+\s+días?\s*(?:hábiles?|laborales?|calendario|naturales?)?\s*(?:de|desde|a\s+partir|contados|luego|tras|después)',
    r'\ben\s+un\s+plazo\s+de\s+\d+',
    r'\buna\s+vez\s+que\b',
    r'\buna\s+vez\s+(?:ocurrido|presentado|recibido|notificado|informado)\b',
    r'\bal\s+momento\s+de\s+(?:conocer|recibir|tener\s+conocimiento)\b',
    r'\bcuando\s+(?:ocurra|se\s+produzca|se\s+presente|tenga\s+conocimiento)\b',
    r'\btras\s+(?:la\s+)?(?:ocurrencia|notificación|recepción|conocimiento)\b',
    r'\ba\s+partir\s+de\s+(?:la\s+)?(?:ocurrencia|notificación|recepción|fecha\s+en\s+que)\b',
    r'\bcontados?\s+(?:a\s+partir\s+de|desde)\s+(?:la\s+)?(?:fecha\s+en\s+que|ocurrencia|recepción|notificación)\b',
]


def _detect_conditional(item) -> str | None:
    """
    Returns a human-readable label if the obligation is event-triggered
    (deadline starts counting AFTER a condition occurs), e.g.:
      '5 días hábiles tras condición'
      'Plazo sujeto a condición'
    Returns None if it's a regular periodic obligation.
    """
    text = " ".join([
        item.get("obligacion", ""),
        item.get("frecuencia", ""),
    ]).lower()

    # 1. If it has a clear periodic frequency, treat as periodic (not conditional)
    if any(kw in text for kw in _PERIODIC_KW):
        return None

    # 2. Check for conditional trigger phrases
    has_trigger = any(re.search(pat, text) for pat in _CONDITIONAL_TRIGGER_PATTERNS)
    if not has_trigger:
        return None

    # 3. Extract the stated timeframe
    # "five (5) Business Days", "5 días hábiles", "3 Business Days", etc.
    m = re.search(
        r'(\d+)\s*(?:\(\d+\))?\s*(?:business\s+days?|b\.?d\.?|días?\s+hábiles?|días?\s+laborales?|días?\s+útiles?)',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)} días hábiles tras condición"

    m = re.search(
        r'(\d+)\s*(?:\(\d+\))?\s*(?:calendar\s+days?|días?\s+calendario|días?\s+naturales?)',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)} días calendario tras condición"

    # Generic "N days"
    m = re.search(r'(\d+)\s*(?:\(\d+\))?\s*días?', text)
    if m:
        return f"{m.group(1)} días tras condición"

    return "Plazo sujeto a condición"


def compute_next_due_date(contract, item) -> str:
    """Return the next exact due date as a short string (e.g. '15 Jul 2026'),
    OR a conditional label like '5 días hábiles tras condición' when the
    deadline is triggered by an external event rather than a calendar period.

    Priority:
    0. Conditional-trigger detection → return descriptive label, not a date.
    1. Explicit day+month mentioned in the item's own texts.
    2. Calendar-month arithmetic from the contract signing date.
    3. Day-based arithmetic for weekly / fortnightly items.
    """
    # 0. Detect event-triggered obligations (deadline starts after a condition)
    conditional_label = _detect_conditional(item)
    if conditional_label:
        return conditional_label

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_names = "|".join(SPANISH_MONTHS.keys())
    pattern = rf'(\d{{1,2}})\s+(?:de\s+)?({month_names})'

    # 1. Search for explicit day-month dates in the item's own texts only
    #    (contract-level payment dates are intentionally excluded so they don't
    #    bleed into obligations that have nothing to do with interest payments)
    search_texts = [
        item.get("obligacion", ""),
        item.get("frecuencia", ""),
    ]
    candidates = []
    for text in search_texts:
        for day_str, month_str in re.findall(pattern, text.lower()):
            month_num = SPANISH_MONTHS.get(month_str)
            if not month_num:
                continue
            day = int(day_str)
            for yr in [today.year, today.year + 1]:
                try:
                    d = datetime(yr, month_num, day)
                    if d >= today:
                        candidates.append(d)
                        break
                except ValueError:
                    pass
    if candidates:
        best = min(candidates)
        return f"{best.day} {MONTH_SHORT[best.month]} {best.year}"

    # Anchor: contract signing date (e.g. 27 oct 2025)
    info = contract.get("informacion_del_contrato", {})
    start = parse_contract_date(info.get("fecha_de_ejecucion", ""))
    freq_text = item.get("frecuencia", "")

    # 2. Calendar-month arithmetic (exact months from signing date)
    period_months = _freq_to_months(freq_text)
    if period_months is not None:
        nxt = _add_months(start, period_months)
        while nxt < today:
            nxt = _add_months(nxt, period_months)
        return f"{nxt.day} {MONTH_SHORT[nxt.month]} {nxt.year}"

    # 3. Day-based fallback (weekly, fortnightly, event-driven)
    days = freq_to_days(freq_text)
    if days == 0:
        return "Fecha puntual"
    nxt = start + timedelta(days=days)
    while nxt < today:
        nxt += timedelta(days=days)
    return f"{nxt.day} {MONTH_SHORT[nxt.month]} {nxt.year}"


def build_calendar_data(contract, bank_idx):
    """Compute due-date milestones for obligations, grouped by month.
    Uses proper calendar-month arithmetic (same logic as compute_next_due_date).
    """
    info = contract.get("informacion_del_contrato", {})
    start_date = parse_contract_date(info.get("fecha_de_ejecucion", ""))
    resp = contract.get("responsabilidades", {})
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_window = today + timedelta(days=365)
    milestones = []

    month_names = "|".join(SPANISH_MONTHS.keys())
    explicit_pattern = rf'(\d{{1,2}})\s+(?:de\s+)?({month_names})'

    for cat_key, items in resp.items():
        for item in items:
            # Skip obligations whose deadline is event-triggered (no fixed date)
            if _detect_conditional(item) is not None:
                continue

            freq  = item.get("frecuencia", "mensual")
            sev   = item.get("severidad", "media")
            color = risk_to_calendar_color(sev)
            label = item.get("obligacion", "")[:60]

            # Check for explicit calendar dates in item texts only
            candidates = []
            for text in [item.get("obligacion", ""), freq]:
                for day_str, month_str in re.findall(explicit_pattern, text.lower()):
                    mnum = SPANISH_MONTHS.get(month_str)
                    if not mnum:
                        continue
                    day = int(day_str)
                    for yr in [today.year, today.year + 1, today.year + 2]:
                        try:
                            d = datetime(yr, mnum, day)
                            if today - timedelta(days=15) <= d <= end_window:
                                candidates.append(d)
                                break
                        except ValueError:
                            pass

            if candidates:
                for d in candidates:
                    milestones.append({"date": d, "label": label, "color": color, "sev": sev})
                continue

            # Calendar-month arithmetic
            period_months = _freq_to_months(freq)
            if period_months is not None:
                nxt = _add_months(start_date, period_months)
                added = 0
                while nxt <= end_window and added < 4:
                    if nxt >= today - timedelta(days=15):
                        milestones.append({"date": nxt, "label": label, "color": color, "sev": sev})
                        added += 1
                    nxt = _add_months(nxt, period_months)
                continue

            # Day-based fallback
            days_val = freq_to_days(freq)
            if days_val == 0:
                if today - timedelta(days=30) <= start_date <= end_window:
                    milestones.append({"date": start_date, "label": label, "color": color, "sev": sev})
                continue
            nxt = start_date + timedelta(days=days_val)
            added = 0
            while nxt <= end_window and added < 4:
                if nxt >= today - timedelta(days=15):
                    milestones.append({"date": nxt, "label": label, "color": color, "sev": sev})
                    added += 1
                nxt += timedelta(days=days_val)

    # Group by month key
    months_data = {}
    for m in milestones:
        mk = m["date"].strftime("%Y-%m")
        months_data.setdefault(mk, []).append(m)
    for mk in months_data:
        months_data[mk].sort(key=lambda x: x["date"])

    # Only months that have at least one event, next 12 months
    month_keys = []
    for i in range(13):
        d = _add_months(today.replace(day=1), i)
        mk = d.strftime("%Y-%m")
        if mk not in month_keys:
            month_keys.append(mk)
    return month_keys[:13], months_data


# ── Solarview data helpers ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_solarview_data(project_id, scale, token):
    """Fetch real energy data from Solenium API. Returns None on failure."""
    if not HAS_REQUESTS or not token:
        return None
    try:
        resp = http_req.get(
            f"{SOLARVIEW_BASE}/project/{project_id}/energy/",
            params={"scale": scale},
            headers={"Authorization": f"Token {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def generate_solarview_mock(projects, scale="month"):
    """Generate realistic solar energy mock data for Cesar, Colombia."""
    random.seed(42)
    solar_monthly = [1.12, 1.08, 0.95, 0.88, 0.82, 0.85, 0.92, 1.0, 0.90, 0.82, 0.78, 0.95]
    result = {}
    for proj in projects:
        cap = proj["cap_kw"]
        base_daily = cap * 4.5  # ~4.5 kWh/kWp/day in Cesar
        if scale == "month":
            labels = list(MONTH_SHORT.values())
            data = [round(base_daily * 30 * f * (1 + random.uniform(-0.04, 0.04))) for f in solar_monthly]
        else:
            labels = [f"{i+1}" for i in range(30)]
            data = [round(base_daily * (1 + random.uniform(-0.15, 0.15))) for _ in range(30)]
        result[proj["name"]] = {"labels": labels, "energy_kwh": data}
    return result


def fetch_financial_data_from_sheets(bank_name):
    """
    Descarga y extrae los datos reales desde las pestañas de Google Sheets para el banco dado.
    Utiliza búsqueda dinámica por índices en pandas usando gspread csv exports.
    Fallback de datos a valores por defecto si no tienen hoja mapeada.
    """
    # Mapeo de Google Sheets por Banco
    # Configuración base con los GIDs correctos de "Insumos FMO"
    SHEETS_MAP = {
        "FMO": {
            "book_id": "1y400zt6ubAEd3Odyb0iZgNL7aut7_RER6DqwgqsmCck",
            "gids": {
                "Data": "2047805244",
                "Assumptions & Results": "1041006504",
                "Cash Flow annual COP": "114256082",
                "Debt": "353648052"
            }
        }
        # Podrán agregar más bancos (ej. Davivienda) aquí luego
    }
    
    # Valores base (fallback) para evitar que rompa la vista si falla o no hay datos
    financial_data = {
        "valor_portafolio": 0, "roi_proyectado": 0.0, "generacion_anual_mwh": 0,
        "co2_evitado_ton": 38700, # Valor estandar
        "tir_real": 0.0, "payback_anos": 0.0, 
        "factor_planta": 18.5, # Valor estandar
        "margen_ebitda": 0.0,
        "historico_dscr": [1.0] * 12,
        "riesgo_score": 28,
        "cashflow": {
            "labels": list(MONTH_SHORT.values())[:12], # Defaults as fallback
            "ingresos": [0] * 12,
            "opex": [0] * 12,
            "ds": [0] * 12,
            "fcl": [0] * 12
        }
    }
    
    if not HAS_PANDAS:
        st.error("🚨 Error crítico: Pandas no está instalado en este entorno (Streamlit Cloud). Revisar requirements.txt")
        return financial_data
        
    if bank_name not in SHEETS_MAP:
        st.info(f"ℹ️ El banco '{bank_name}' no tiene una hoja de Google Sheets vinculada. Mostrando valores por defecto 0.0.")
        return financial_data
        
    config = SHEETS_MAP[bank_name]
    base_url = f"https://docs.google.com/spreadsheets/d/{config['book_id']}/export?format=csv&gid="
    
    def _get_sheet_df(gid):
        url = base_url + gid
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        r = http_req.get(url, headers=headers)
        r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text))
    
    try:
        # ------- 1. DATA (Valor Portafolio) -------
        df_data = _get_sheet_df(config['gids']['Data'])
        # Buscar 'Portfolio Value' en la primera o segunda columna
        for i, row in df_data.iterrows():
            row_str = str(row.values).lower()
            if 'portfolio value' in row_str:
                # Normalmente está en la columna B o C (índice 1 o 2) iteraremos para pillar el primero numérico contiguo
                for val in row.values:
                    try:
                        v = str(val).replace(',', '').replace(r'$', '').strip()
                        if v and v != 'nan' and v.replace('.','',1).isdigit():
                            financial_data["valor_portafolio"] = float(v)
                            break
                    except: pass
                break
                
        # ------- 2. ASSUMPTIONS & RESULTS (TIR, Payback, ROI) -------
        df_assum = _get_sheet_df(config['gids']['Assumptions & Results'])
        for i, row in df_assum.iterrows():
            row_str = str(row.values).lower()
            if 'results with debt - cop' in row_str or 'irr' in row_str:
                for val in row.values:
                    if isinstance(val, str) and '%' in val:
                        financial_data["tir_real"] = float(val.replace('%','').strip())
                        financial_data["roi_proyectado"] = financial_data["tir_real"] # Approximation based on IRR
                        break
            if 'payback' in row_str:
                for val in row.values:
                    try:
                        v = str(val)
                        if v != 'nan' and (v.replace('.','',1).isdigit()):
                            financial_data["payback_anos"] = float(v)
                            break
                    except: pass
                    
        # ------- 3. CASH FLOW ANNUAL COP (Ingresos, Opex, Margen, Service Debt) -------
        df_cf = _get_sheet_df(config['gids']['Cash Flow annual COP'])
        
        # Extracción de la evolución a lo largo del plazo
        years_cols = [] # Para almacenar las columnas de años a graficar
        cf_gen, cf_rev, cf_opex, cf_prin, cf_int, cf_marg = [], [], [], [], [], []
        
        # En la hoja CF, usualmente la primera columna es de Etiquetas, la 2da o 3ra empiezan los periodos (números)
        for i, row in df_cf.iterrows():
            row_vals = [str(x) for x in row.values]
            row_str = " ".join(row_vals).lower()
            
            # Buscar métricas exactas
            if 'generation (kwh)' in row_str and not cf_gen:
                cf_gen = [float(v.replace(',', '')) for v in row_vals if v.replace(',','').replace('.','',1).isdigit()]
                
            elif 'total revenues' in row_str and not cf_rev:
                cf_rev = [float(v.replace(',', '')) for v in row_vals if v.replace(',','').replace('.','',1).isdigit()]
                
            elif 'total costs and expenses' in row_str and not cf_opex:
                cf_opex = [float(v.replace(',', '')) for v in row_vals if v.replace(',','').replace('.','',1).isdigit()]
                
            elif 'principal payments' in row_str and not cf_prin:
                cf_prin = [float(v.replace(',', '')) for v in row_vals if v.replace(',','').replace('.','',1).isdigit()]
                
            elif 'interest' in row_str and 'income' not in row_str and not cf_int:
                cf_int = [float(v.replace(',', '')) for v in row_vals if v.replace(',','').replace('.','',1).isdigit()]
                
            elif ('ebitda margin' in row_str or 'margen ebitda' in row_str) and not cf_marg:
                for v in row_vals:
                    if '%' in v:
                        cf_marg.append(float(v.replace('%','').strip()))
                        
        # Procesar los arrays extraídos
        if cf_gen: 
            financial_data["generacion_anual_mwh"] = sum(cf_gen) / 1000  # kWh a MWh aproximado sumado total, adaptamos abajo al promedio
            if len(cf_gen) > 0: financial_data["generacion_anual_mwh"] = (sum(cf_gen) / len(cf_gen)) / 1000 
            
        if cf_marg:
            financial_data["margen_ebitda"] = sum(cf_marg) / len(cf_marg)
            
        # Preparar data para el gráfico de Cash Flow Consolidated de hasta 15 años
        chart_len = min(len(cf_rev), len(cf_opex), 15)
        if chart_len > 0:
            labels = [f"Año {j+1}" for j in range(chart_len)]
            rev_c = cf_rev[:chart_len]
            opex_c = cf_opex[:chart_len]
            
            # Servicio deuda es interes + principal
            ds_c = [0] * chart_len
            for j in range(chart_len):
                p = cf_prin[j] if j < len(cf_prin) else 0
                i_ = cf_int[j] if j < len(cf_int) else 0
                ds_c[j] = p + i_
                
            fcl_c = [rev_c[j] - opex_c[j] - ds_c[j] for j in range(chart_len)]
            
            financial_data["cashflow"] = {
                "labels": labels, "ingresos": rev_c, "opex": opex_c, 
                "ds": ds_c, "fcl": fcl_c
            }
            
        # ------- 4. DEBT (DSCR) -------
        df_debt = _get_sheet_df(config['gids']['Debt'])
        cf_dscr = []
        for i, row in df_debt.iterrows():
            row_vals = [str(x) for x in row.values]
            row_str = " ".join(row_vals).lower()
            # Buscar el ratio de Cobertura
            if 'dscr' in row_str and 'calculated' not in row_str:
                cf_dscr = [float(v) for v in row_vals if v.replace('.','',1).isdigit()]
                break
                
        if cf_dscr:
            financial_data["historico_dscr"] = cf_dscr[:len(financial_data["cashflow"]["labels"])]
            
    except Exception as e:
        import traceback
        st.error(f"⚠️ Error procesando Sheet de {bank_name}: {e}")
        st.expander("Ver detalles técnicos del error (Traceback)").code(traceback.format_exc())
        
    return financial_data



# Pre-load logos
LOGO_SIDEBAR = get_base64_image("Logo_avena.png")
LOGO_PURPLE  = get_base64_image("Logo_lineal_purpura_energico.png")


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Brand tokens ──────────────────────────────────── */
:root {
    --u-purple: #915BD8;
    --u-deep: #2C2039;
    --u-cream: #FDFAF7;
    --u-yellow: #F6FF72;
    --u-purple-10: rgba(145, 91, 216, 0.10);
    --u-purple-15: rgba(145, 91, 216, 0.15);
    --u-purple-25: rgba(145, 91, 216, 0.25);
}

/* ── Global ──────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Lato:wght@400;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Lato', 'Open Sans', sans-serif; color: var(--u-deep); }
.stApp { background: var(--u-cream); }
.block-container { padding-top: 0.8rem; padding-bottom: 1rem; max-width: 1320px; }

/* ── Sidebar ─────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2C2039 0%, #1e1529 100%);
    border-right: 1px solid rgba(145,91,216,0.2);
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
section[data-testid="stSidebar"] .stRadio label span,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
    color: rgba(255,255,255,0.75) !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(145,91,216,0.25); }
section[data-testid="stSidebar"] .stRadio > div { gap: 0.15rem; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 0.55rem 0.85rem; border-radius: 10px;
    font-size: 0.88rem; font-weight: 600; transition: background 0.2s;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(145,91,216,0.2); }
section[data-testid="stSidebar"] .stRadio label:has(input:checked) {
    background: linear-gradient(135deg, #915BD8, #a66de0) !important;
}
section[data-testid="stSidebar"] .stRadio label:has(input:checked) span,
section[data-testid="stSidebar"] .stRadio label:has(input:checked) p {
    color: #FDFAF7 !important; font-weight: 700;
}
/* Hide radio dots in sidebar entirely */
section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
    display: none !important;
}

/* ── Hamburger / sidebar toggle ──────────────────── */
button[kind="headerNoPadding"],
[data-testid="collapsedControl"] > button,
[data-testid="stSidebarCollapseButton"] button {
    background: var(--u-purple) !important;
    border-radius: 10px !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(145,91,216,0.3);
    border: none !important;
    min-width: 36px; min-height: 36px;
}
button[kind="headerNoPadding"]:hover,
[data-testid="collapsedControl"] > button:hover {
    background: #7c4dc0 !important;
    box-shadow: 0 4px 14px rgba(145,91,216,0.45);
}

/* ── VG Header ───────────────────────────────────── */
.vg-header {
    display: flex; align-items: center; gap: 0.8rem;
    padding: 0.6rem 0 0.8rem; border-bottom: 2px solid var(--u-purple-15);
    margin-bottom: 1rem;
}
.vg-logo-title { display: flex; align-items: center; gap: 0.7rem; }
.vg-logo-title img { height: 28px; }
.vg-logo-title .tracker-label {
    font-family: 'Lato', sans-serif; font-size: 1.2rem; font-weight: 400;
    color: var(--u-deep); opacity: 0.7; margin-left: -0.15rem;
}

/* ── KPI cards ──────────────────────────────────── */
.kpi-card {
    background: rgba(145,91,216,0.10); border: 1px solid rgba(145,91,216,0.18);
    border-radius: 14px; padding: 1.1rem 1.3rem;
    text-align: center; transition: all 0.2s; height: 100%;
}
.kpi-card:hover { box-shadow: 0 4px 14px rgba(145,91,216,0.12); }
.kpi-card .kpi-value {
    font-family: 'Poppins', sans-serif; font-size: 2rem;
    font-weight: 800; color: var(--u-deep); line-height: 1.1;
}
.kpi-card .kpi-label {
    font-size: 0.72rem; font-weight: 700; color: #5b3a8a;
    text-transform: uppercase; letter-spacing: 0.04em; margin-top: 0.2rem;
}

/* ── Bank debt card ──────────────────────────────── */
.bank-card {
    background: #fff; border: 1.5px solid var(--u-purple-25);
    border-radius: 16px; padding: 1.5rem 1.8rem;
    box-shadow: 0 2px 8px rgba(44,32,57,0.06);
    transition: all 0.25s; margin: 0.6rem 0;
}
.bank-card:hover { box-shadow: 0 6px 20px rgba(145,91,216,0.12); transform: translateY(-2px); }
.bank-card .bank-name {
    font-family: 'Poppins', sans-serif; font-size: 1.3rem;
    font-weight: 800; color: var(--u-purple); margin-bottom: 0.8rem;
}
.bank-card .bank-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem 2.5rem; }
.bank-card .bank-row {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 0.3rem 0; border-bottom: 1px solid rgba(145,91,216,0.06);
}
.bank-card .bank-row-label { font-size: 0.78rem; font-weight: 700; color: #374151; }
.bank-card .bank-row-value { font-size: 0.82rem; font-weight: 700; color: var(--u-deep); }
.bank-card .bank-row-value.highlight { color: var(--u-purple); font-size: 0.88rem; }

/* ── Section title ───────────────────────────────── */
.section-title {
    font-family: 'Poppins', sans-serif; font-size: 1.05rem;
    font-weight: 700; color: var(--u-deep);
    margin: 1.8rem 0 0.8rem 0; padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--u-purple-15);
}
.section-icon { margin-right: 0.5rem; }

/* ── Page heading ────────────────────────────────── */
.page-heading {
    font-family: 'Poppins', sans-serif; font-size: 1.4rem;
    font-weight: 800; color: var(--u-deep); margin-bottom: 0.2rem;
}
.page-subheading { font-size: 0.8rem; color: #475569; margin-bottom: 1.2rem; }

/* ── Obligation card ─────────────────────────────── */
.ob-card {
    background: #fff; border: 1px solid var(--u-purple-15);
    border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 0.15rem;
    box-shadow: 0 1px 3px rgba(44,32,57,0.04); transition: all 0.2s ease;
    border-left: 4px solid;
}
.ob-card:hover { box-shadow: 0 5px 18px rgba(145,91,216,0.12); transform: translateY(-1px); }
.ob-badges { display: flex; gap: 0.4rem; align-items: center; margin-bottom: 0.45rem; flex-wrap: wrap; }
.ob-clause {
    display: inline-block; background: var(--u-deep); color: #FDFAF7;
    font-size: 0.62rem; font-weight: 700; padding: 0.15rem 0.6rem; border-radius: 6px;
}
.ob-risk {
    display: inline-block; font-size: 0.6rem; font-weight: 700;
    padding: 0.13rem 0.55rem; border-radius: 20px; text-transform: uppercase;
}
.ob-desc {
    font-size: 0.82rem; color: var(--u-deep); font-weight: 500;
    line-height: 1.5; margin-bottom: 0.4rem;
    word-wrap: break-word; overflow-wrap: break-word; white-space: normal;
}
.ob-freq { font-size: 0.72rem; color: #475569; font-weight: 600; }
.ob-area-tag {
    display: inline-block; font-size: 0.58rem; font-weight: 700;
    padding: 0.12rem 0.55rem; border-radius: 20px;
    background: var(--u-purple-10); color: var(--u-purple);
    border: 1px solid var(--u-purple-25);
    text-transform: uppercase; letter-spacing: 0.04em;
}
.ob-file-label {
    font-size: 0.7rem; font-weight: 700; color: var(--u-deep);
    margin-bottom: 0.3rem; padding-top: 0.35rem;
}

/* ── Obligation stats row ────────────────────────── */
.ob-stats-row {
    display: flex; gap: 0.6rem; flex-wrap: wrap;
    margin-bottom: 0.9rem; align-items: stretch;
}
.ob-stat-card {
    flex: 1; min-width: 130px;
    background: #fff; border: 1px solid var(--u-purple-15);
    border-radius: 16px; padding: 0.75rem 1rem;
    display: flex; align-items: center; gap: 0.8rem;
    box-shadow: 0 1px 4px rgba(44,32,57,0.04);
}
.ob-stat-circle {
    width: 46px; height: 46px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: Poppins, sans-serif; font-size: 1.15rem; font-weight: 800;
    flex-shrink: 0;
}
.ob-stat-label {
    font-size: 0.63rem; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.04em; line-height: 1.3;
}

/* ── Area filter header ──────────────────────────── */
.area-filter-header {
    font-size: 0.68rem; font-weight: 800; color: var(--u-deep);
    text-transform: uppercase; letter-spacing: 0.07em;
    margin-bottom: 0.5rem; padding-top: 0.2rem;
}

/* ── st.pills override ───────────────────────────── */
div[data-testid="stPills"] { margin-bottom: 0.5rem; }
div[data-testid="stPills"] button {
    border-radius: 20px !important;
    border: 1.5px solid var(--u-purple-25) !important;
    font-size: 0.78rem !important; font-weight: 600 !important;
    transition: all 0.18s ease !important;
    background: #fff !important; color: var(--u-deep) !important;
}
div[data-testid="stPills"] button:hover {
    border-color: var(--u-purple) !important;
    background: var(--u-purple-10) !important;
}
div[data-testid="stPills"] button[aria-pressed="true"] {
    background: var(--u-purple) !important;
    border-color: var(--u-purple) !important;
    color: #FDFAF7 !important; font-weight: 700 !important;
}

/* ── Area filter radio (main content, pill look) ─── */
[data-testid="stMain"] [data-testid="stRadio"] label {
    display: block;
    padding: 0.42rem 0.9rem;
    border-radius: 20px;
    border: 1.5px solid var(--u-purple-25);
    font-size: 0.8rem; font-weight: 600;
    color: var(--u-deep); background: #fff;
    cursor: pointer; transition: all 0.18s ease;
    margin-bottom: 0.28rem;
}
[data-testid="stMain"] [data-testid="stRadio"] label:hover {
    border-color: var(--u-purple);
    background: var(--u-purple-10) !important;
}
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg, #915BD8, #a66de0) !important;
    border-color: #915BD8 !important;
    color: #FDFAF7 !important;
}
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) span {
    color: #FDFAF7 !important; font-weight: 700;
}
/* Hide only the radio indicator dot (first child div), leave text div visible */
[data-testid="stMain"] [data-testid="stRadio"] label > div:first-child {
    display: none !important;
}
/* Force black text on unselected area pills */
[data-testid="stMain"] [data-testid="stRadio"] label span,
[data-testid="stMain"] [data-testid="stRadio"] label p,
[data-testid="stMain"] [data-testid="stRadio"] label div {
    color: #2C2039 !important;
}
/* Hide the radio group label ("Área") — it renders as a pill due to our CSS */
[data-testid="stMain"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {
    display: none !important;
}

/* ── Summary chips ───────────────────────────────── */
.summary-row { display: flex; gap: 0.45rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.8rem; }
.summary-chip {
    display: inline-flex; align-items: center; gap: 0.3rem;
    background: #fff; border: 1px solid var(--u-purple-15);
    border-radius: 20px; padding: 0.3rem 0.75rem;
    font-size: 0.72rem; font-weight: 600; color: var(--u-deep);
}
.summary-chip .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Category progress ───────────────────────────── */
.cat-progress {
    display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.8rem;
    padding: 0.6rem 0.8rem; background: var(--u-cream); border-radius: 10px;
    border: 1px solid var(--u-purple-10);
}
.cat-progress-item { display: flex; align-items: center; gap: 0.25rem; font-size: 0.7rem; font-weight: 600; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.3rem; flex-shrink: 0; }

/* ── Dark dropdown (selectbox) ───────────────────── */
div[data-baseweb="select"] > div {
    background: #2C2039 !important;
    border-radius: 10px !important;
    border: 1.5px solid rgba(145,91,216,0.35) !important;
}
div[data-baseweb="select"] > div > div {
    color: #FDFAF7 !important; font-weight: 600 !important; font-size: 0.82rem !important;
}
div[data-baseweb="select"] svg { fill: #FDFAF7 !important; }
/* Dropdown menu */
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul { background: #2C2039 !important; border: 1px solid rgba(145,91,216,0.3) !important; border-radius: 10px !important; }
[data-baseweb="popover"] li { color: #FDFAF7 !important; font-weight: 600 !important; }
[data-baseweb="popover"] li:hover,
[data-baseweb="popover"] li[aria-selected="true"] { background: rgba(145,91,216,0.35) !important; }

/* ── Metric cards ────────────────────────────────── */
.metric-card {
    background: #fff; border: 1px solid var(--u-purple-15);
    border-radius: 14px; padding: 1.25rem 1.3rem; text-align: center;
    box-shadow: 0 1px 4px rgba(44,32,57,0.04); transition: all 0.2s; height: 100%;
}
.metric-card:hover { box-shadow: 0 6px 16px rgba(145,91,216,0.10); }
.metric-card .icon { font-size: 1.5rem; margin-bottom: 0.25rem; }
.metric-card .label {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: #374151; margin-bottom: 0.2rem; font-weight: 700;
}
.metric-card .value {
    font-family: 'Poppins', sans-serif; font-size: 1.5rem;
    font-weight: 800; color: var(--u-deep); line-height: 1.2;
}
.metric-card .sub { font-size: 0.7rem; color: #6b7280; margin-top: 0.15rem; }

/* ── Guarantee / info / event / prepay ─────────── */
.guarantee-card {
    background: #fff; border: 1px solid var(--u-purple-15); border-radius: 14px;
    padding: 1rem 1.2rem; margin-bottom: 0.6rem; box-shadow: 0 1px 2px rgba(44,32,57,0.03);
    display: flex; align-items: flex-start; gap: 0.8rem; transition: all 0.2s;
}
.guarantee-card:hover { box-shadow: 0 4px 12px rgba(145,91,216,0.08); }
.guarantee-card .g-icon { font-size: 1.3rem; flex-shrink: 0; width: 2.1rem; height: 2.1rem; display: flex; align-items: center; justify-content: center; background: var(--u-purple-10); border-radius: 8px; }
.guarantee-card .g-title { font-size: 0.8rem; font-weight: 700; color: var(--u-deep); margin-bottom: 0.1rem; }
.guarantee-card .g-desc { font-size: 0.72rem; color: #475569; line-height: 1.5; }

.info-box { background: var(--u-cream); border: 1px solid var(--u-purple-10); border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.5rem; }
.info-box .ib-label { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7280; font-weight: 700; margin-bottom: 0.12rem; }
.info-box .ib-value { font-size: 0.8rem; color: var(--u-deep); font-weight: 600; }

.event-pill { display: inline-block; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 0.68rem; font-weight: 600; padding: 0.28rem 0.65rem; border-radius: 20px; margin: 0.15rem; }

.prepay-table { width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 10px; overflow: hidden; border: 1px solid var(--u-purple-15); font-size: 0.78rem; }
.prepay-table th { background: var(--u-deep); color: var(--u-cream); font-weight: 700; padding: 0.6rem 0.9rem; text-align: left; font-size: 0.68rem; text-transform: uppercase; }
.prepay-table td { padding: 0.6rem 0.9rem; border-top: 1px solid var(--u-purple-10); color: var(--u-deep); font-weight: 600; }
.prepay-table .highlight { color: #dc2626; font-weight: 700; }
.prepay-table .ok { color: #16a34a; font-weight: 700; }

/* ── Calendar ────────────────────────────────────── */
.cal-grid {
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.6rem; margin-top: 0.8rem;
}
.cal-month {
    background: #fff; border: 1px solid var(--u-purple-15); border-radius: 12px;
    padding: 0.65rem 0.5rem; text-align: center; transition: all 0.2s;
}
.cal-month:hover { box-shadow: 0 3px 10px rgba(145,91,216,0.1); }
.cal-month-name { font-family: 'Poppins', sans-serif; font-size: 0.7rem; font-weight: 700; color: var(--u-deep); margin-bottom: 0.35rem; }
.cal-dots { display: flex; gap: 3px; flex-wrap: wrap; justify-content: center; min-height: 16px; }
.cal-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; cursor: help; transition: transform 0.15s; }
.cal-dot:hover { transform: scale(1.6); }
.cal-count { font-size: 0.58rem; color: #6b7280; margin-top: 0.25rem; font-weight: 600; }
.cal-legend { display: flex; gap: 1.5rem; justify-content: center; margin-top: 0.6rem; font-size: 0.72rem; font-weight: 700; color: var(--u-deep); align-items: center; }
.cal-legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 0.3rem; vertical-align: middle; }

/* ── Expanders ───────────────────────────────────── */
div[data-testid="stExpander"] { border: 1px solid var(--u-purple-15) !important; border-radius: 14px !important; margin-bottom: 0.6rem; box-shadow: 0 1px 3px rgba(44,32,57,0.04); overflow: hidden; background: #fff; }
div[data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p { font-family: 'Poppins', sans-serif !important; font-weight: 700 !important; font-size: 0.88rem !important; color: var(--u-deep) !important; }
/* Restore Material Symbols on ALL icon elements (prevent Poppins inheritance) */
[data-testid="stIconMaterial"], [translate="no"][class*="cache"] { font-family: 'Material Symbols Rounded' !important; font-size: 1.1rem !important; font-weight: 300 !important; }

/* ── Tabs custom ──────────────────────────────────── */
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 0.82rem;
    color: #475569; padding: 0.6rem 1.2rem; border-radius: 10px 10px 0 0;
    transition: all 0.15s;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--u-deep) !important;
    border-bottom: 3px solid #F6FF72 !important;
    font-weight: 800;
}
/* Suppress Streamlit's default baseweb tab highlight (the red line) */
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: #F6FF72 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
    background-color: rgba(145,91,216,0.12) !important;
}

/* ── Footer ──────────────────────────────────────── */
.footer { text-align: center; padding: 1.5rem 0; color: #6b7280; font-size: 0.68rem; border-top: 1px solid var(--u-purple-10); margin-top: 2rem; }

/* ── Hide Streamlit chrome (keep sidebar toggle) ── */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stDecoration"] { display: none; }

/* ── Proj stats panel ────────────────────────────── */
.proj-stats-card {
    background: #fff; border: 1.5px solid var(--u-purple-25);
    border-radius: 14px; padding: 1.2rem; height: 100%;
}
.proj-stat-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 0.6rem; border-radius: 8px; margin-bottom: 0.3rem; transition: background 0.15s;
}
.proj-stat-row:nth-child(odd) { background: rgba(246,255,114,0.15); }
.proj-stat-row:hover { background: rgba(145,91,216,0.08); }
.proj-stat-row .psr-label { font-size: 0.78rem; font-weight: 700; color: var(--u-deep); }
.proj-stat-row .psr-value {
    font-family: 'Poppins', sans-serif; font-size: 1.05rem; font-weight: 800; color: var(--u-purple);
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Load data — DYNAMIC multi-contract
# ══════════════════════════════════════════════════════════════════════════════
if "contracts" not in st.session_state:
    contract_files = sorted(DATA_DIR.glob("contract_data*.json"))
    st.session_state.contracts = []
    for fp in contract_files:
        with open(fp, "r", encoding="utf-8") as f:
            st.session_state.contracts.append(json.load(f))

contracts = st.session_state.contracts

if not contracts:
    st.error("No se encontraron archivos `contract_data*.json`.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
if "obligation_statuses" not in st.session_state:
    st.session_state.obligation_statuses = load_statuses()
if "obligation_links" not in st.session_state:
    st.session_state.obligation_links = load_links()
if "solarview_token" not in st.session_state:
    st.session_state.solarview_token = None

# Fill in any keys not yet on disk (new contracts / new obligations)
for bidx, c in enumerate(contracts):
    resp = c.get("responsabilidades", {})
    for cat_key, items in resp.items():
        for idx in range(len(items)):
            key = f"{bidx}_{cat_key}_{idx}"
            if key not in st.session_state.obligation_statuses:
                st.session_state.obligation_statuses[key] = "Pendiente"


# ══════════════════════════════════════════════════════════════════════════════
# Prepare bank data
# ══════════════════════════════════════════════════════════════════════════════
def build_banks():
    banks = []
    for bidx, c in enumerate(contracts):
        p    = c.get("partes_involucradas", {})
        f    = c.get("condiciones_financieras", {})
        pl   = c.get("plazos_y_pagos", {})
        proj = c.get("descripcion_del_proyecto", {})
        resp = c.get("responsabilidades", {})

        total_obs = sum(len(v) for v in resp.values())
        pending = sum(1 for k, v in st.session_state.obligation_statuses.items()
                      if k.startswith(f"{bidx}_") and v == "Pendiente")
        completed = sum(1 for k, v in st.session_state.obligation_statuses.items()
                        if k.startswith(f"{bidx}_") and v == "Completo")
        upcoming = 0
        for cat_items in resp.values():
            for item in cat_items:
                freq = item.get("frecuencia", "").lower()
                if any(kw in freq for kw in ["inmediato", "dentro de", "mensual"]):
                    upcoming += 1
        upcoming = min(upcoming, 15)

        name = get_bank_display_name(c)

        monto_data = f.get("monto_total_del_credito", {})
        monto_val = monto_data.get("valor_numerico_usd", 0) or monto_data.get("valor_numerico_cop", 0)

        tasa_info = f.get("tasa_de_interes_ordinaria", {})
        if isinstance(tasa_info, dict):
            componentes = tasa_info.get("componentes", tasa_info)
            tasa_ref = componentes.get("tasa_de_referencia", tasa_info.get("tasa_base", "N/A"))
            margen = componentes.get("margen", tasa_info.get("margen_numerico", "N/A"))
            tasa_str = f"{tasa_ref} + {margen}" if margen != "N/A" else str(tasa_ref)
        else:
            tasa_str = str(tasa_info)

        banks.append({
            "name": name,
            "full_name": p.get("prestamista", {}).get("nombre", ""),
            "estado": "Activa",
            "monto": monto_val,
            "moneda": monto_data.get("moneda_de_desembolso", monto_data.get("moneda_base", "USD")),
            "patrimonio": p.get("prestatario", {}).get("nombre", "N/A"),
            "tasa": tasa_str,
            "plazo": f"{pl.get('plazo_anos', 'N/A')} años",
            "total": total_obs,
            "pending": pending,
            "completed": completed,
            "upcoming": upcoming,
            "proyecto": proj,
            "contract": c,
            "bidx": bidx,
        })
    return banks

banks = build_banks()

total_pending  = sum(b["pending"] for b in banks)
total_upcoming = sum(b["upcoming"] for b in banks)
active_debts   = len(banks)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    if LOGO_SIDEBAR:
        st.markdown(f"""
        <div style="text-align:center; padding:1.2rem 0.8rem 0.3rem;">
            <img src="data:image/png;base64,{LOGO_SIDEBAR}" style="width:60%; max-width:170px; display:block; margin:0 auto;" alt="Unergy">
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="text-align:center; font-size:0.6rem; color:rgba(253,250,247,0.4); font-weight:500; padding-bottom:0.4rem; letter-spacing:0.05em;">DEBT TRACKER</div>', unsafe_allow_html=True)
    st.divider()

    page = st.radio("Nav", ["Vista General", "Obligaciones", "Financiero"], label_visibility="collapsed")
    st.divider()

    total_obs_all = sum(b["total"] for b in banks)
    st.markdown(f"""
    <div style="background:rgba(145,91,216,0.12); border:1px solid rgba(145,91,216,0.2); border-radius:12px; padding:0.85rem 1rem;">
        <div style="font-size:0.68rem; font-weight:700; color:rgba(253,250,247,0.9); margin-bottom:0.4rem;">Resumen Global</div>
        <div style="font-size:0.7rem; color:rgba(253,250,247,0.75); line-height:1.9;">
            {len(banks)} banco(s) activo(s)<br>{total_obs_all} obligaciones<br>{total_pending} pendientes<br>{total_obs_all - total_pending} gestionadas
        </div>
    </div>
    """, unsafe_allow_html=True)


    st.markdown('<div style="text-align:center; padding:1rem 0 0.3rem; font-size:0.55rem; color:rgba(253,250,247,0.3);">Solo informativo · No asesoría legal</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Vista General
# ══════════════════════════════════════════════════════════════════════════════
if page == "Vista General":

    # ── 1. Header bar (clean — no pills) ─────────────────────────────────
    logo_src = f'<img src="data:image/png;base64,{LOGO_PURPLE}" style="height:28px;">' if LOGO_PURPLE else '<span style="font-weight:800; color:var(--u-purple); font-size:1.3rem;">Unergy</span>'

    st.markdown(f"""
    <div class="vg-header">
        <div class="vg-logo-title">
            {logo_src}
            <span class="tracker-label">Debt Tracker</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 2. KPI cards ──────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_pending}</div>
            <div class="kpi-label">Total obligaciones pendientes</div>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{total_upcoming}</div>
            <div class="kpi-label">Vencimientos a 30 días</div>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{active_debts}</div>
            <div class="kpi-label">Deudas activas</div>
        </div>""", unsafe_allow_html=True)

    # ── 3. Bank tabs — todo el contenido filtrado por banco ───────────────
    bank_names_vg = [b["name"] for b in banks]
    vg_tabs = st.tabs(bank_names_vg)

    for bidx_vg, tab in enumerate(vg_tabs):
        with tab:
            ab = banks[bidx_vg]

            # ── 3a. Tarjeta de deuda ──────────────────────────────────────
            st.markdown(f"""
            <div class="bank-card">
                <div class="bank-name">{ab['name']}</div>
                <div class="bank-grid">
                    <div class="bank-row">
                        <span class="bank-row-label">Estado Deuda</span>
                        <span class="bank-row-value">{ab['estado']}</span>
                    </div>
                    <div class="bank-row">
                        <span class="bank-row-label">Monto deuda</span>
                        <span class="bank-row-value highlight">{fmt_money(ab['monto'])}</span>
                    </div>
                    <div class="bank-row">
                        <span class="bank-row-label">Obligaciones Pendientes</span>
                        <span class="bank-row-value">{ab['pending']}</span>
                    </div>
                    <div class="bank-row">
                        <span class="bank-row-label">Patrimonio Autónomo</span>
                        <span class="bank-row-value">{ab['patrimonio']}</span>
                    </div>
                    <div class="bank-row">
                        <span class="bank-row-label">Vencimientos en 30 días</span>
                        <span class="bank-row-value">{ab['upcoming']}</span>
                    </div>
                    <div class="bank-row">
                        <span class="bank-row-label">Tasa interés</span>
                        <span class="bank-row-value">{ab['tasa']}</span>
                    </div>
                    <div style="grid-column: 1 / -1;">
                        <div class="bank-row">
                            <span class="bank-row-label">Plazo vencimiento</span>
                            <span class="bank-row-value">{ab['plazo']}</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── 3b. Monitoreo de Generación — solo proyectos de este banco ─
            st.markdown('<div class="section-title">Generación Solar</div>', unsafe_allow_html=True)

            bank_projects_vg = SOLARVIEW_PROJECTS.get(ab["name"], [])

            if not bank_projects_vg:
                st.info(f"No hay proyectos de monitoreo configurados para **{ab['name']}**.")
            else:
                # Scale toggle — key único por banco
                vg_scale = st.radio(
                    "Escala", ["Mensual", "Diario"],
                    horizontal=True,
                    key=f"vg_scale_{bidx_vg}",
                )
                vg_scale_val = "month" if vg_scale == "Mensual" else "day"

                token_vg = st.session_state.solarview_token
                bank_proj_data = {}

                if token_vg:
                    for proj in bank_projects_vg:
                        raw = fetch_solarview_data(proj["id"], vg_scale_val, token_vg)
                        if raw:
                            bank_proj_data[proj["name"]] = raw

                if not bank_proj_data:
                    bank_proj_data = generate_solarview_mock(bank_projects_vg, vg_scale_val)
                    if not token_vg:
                        st.caption("Datos simulados — Token Solarview no configurado.")

                # KPIs del banco
                bank_gen_total = sum(
                    sum(v.get("energy_kwh", [])) for v in bank_proj_data.values()
                    if isinstance(v, dict)
                )
                bank_cap = sum(p["cap_kw"] for p in bank_projects_vg)
                num_p = len(bank_projects_vg)

                mk1, mk2, mk3 = st.columns(3)
                with mk1:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{bank_gen_total/1000:,.0f}</div><div class="kpi-label">MWh Generados ({vg_scale})</div></div>', unsafe_allow_html=True)
                with mk2:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{num_p}</div><div class="kpi-label">Plantas monitoreadas</div></div>', unsafe_allow_html=True)
                with mk3:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{bank_cap/1000:.1f} MW</div><div class="kpi-label">Capacidad instalada</div></div>', unsafe_allow_html=True)

                # Gráfica de áreas apiladas — proyectos del banco
                if HAS_PLOTLY and bank_proj_data:
                    # Paleta amarillo-olivo (de más claro a más oscuro)
                    colors_vg = [
                        "#F5F2B2",  # 1 amarillo muy claro
                        "#ECEB88",  # 2 amarillo claro
                        "#E0DE60",  # 3 amarillo medio-claro
                        "#D2D038",  # 4 amarillo vivo
                        "#C0BE20",  # 5 amarillo-olivo
                        "#A8A60C",  # 6 olivo medio
                        "#929000",  # 7 olivo oscuro
                        "#787600",  # 8 olivo muy oscuro
                        "#DADA4A",  # 9 (extra variante)
                        "#B4B215",  # 10 (extra variante)
                    ]
                    AXIS_COLOR = "#787600"   # olivo oscuro para ejes
                    GRID_COLOR = "rgba(168,166,12,0.15)"
                    fig_vg = go.Figure()
                    for pi, (pname, pdata) in enumerate(bank_proj_data.items()):
                        if isinstance(pdata, dict) and "energy_kwh" in pdata:
                            c = colors_vg[pi % len(colors_vg)]
                            fig_vg.add_trace(go.Scatter(
                                x=pdata.get("labels", []),
                                y=[v / 1000 for v in pdata["energy_kwh"]],
                                name=pname, mode="lines",
                                line=dict(width=1, color=c),
                                fill="tonexty" if pi > 0 else "tozeroy",
                                fillcolor=c,
                                stackgroup="gen",
                                hovertemplate=f"<b>{pname}</b><br>%{{x}}: %{{y:.1f}} MWh<extra></extra>",
                            ))
                    period_lbl = "Mes" if vg_scale_val == "month" else "Día"
                    fig_vg.update_layout(
                        title=dict(text=f"Generación {ab['name']} — {vg_scale}",
                                   font=dict(family="Poppins,sans-serif", size=14, color=AXIS_COLOR),
                                   x=0, xanchor="left", y=0.98, yanchor="top"),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Lato,sans-serif", size=10, color=AXIS_COLOR),
                        margin=dict(l=50, r=145, t=40, b=30), height=350,
                        legend=dict(
                            orientation="v",
                            yanchor="top", y=1,
                            xanchor="left", x=1.03,
                            font=dict(size=9, color=AXIS_COLOR),
                            bgcolor="rgba(0,0,0,0)",
                            borderwidth=0,
                            tracegroupgap=2,
                        ),
                        yaxis=dict(gridcolor=GRID_COLOR, zeroline=False,
                                   title=dict(text="MWh", font=dict(color=AXIS_COLOR, size=10)),
                                   tickfont=dict(color=AXIS_COLOR, size=9)),
                        xaxis=dict(showgrid=False,
                                   title=dict(text=period_lbl, font=dict(color=AXIS_COLOR, size=10)),
                                   tickfont=dict(color=AXIS_COLOR, size=9)),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_vg, width="stretch", config={"displayModeBar": False})

                # Filas detalle por planta
                for proj in bank_projects_vg:
                    pdata = bank_proj_data.get(proj["name"], {})
                    p_gen = sum(pdata.get("energy_kwh", [])) / 1000 if isinstance(pdata, dict) else 0
                    p_cf = (p_gen * 1000 / (proj["cap_kw"] * 24 * (30 if vg_scale_val == "month" else 1))) * 100 if proj["cap_kw"] else 0
                    st.markdown(f"""
                    <div style="display:flex; align-items:center; justify-content:space-between;
                                background:#fff; border:1px solid var(--u-purple-15); border-radius:12px;
                                padding:0.6rem 1.1rem; margin-bottom:0.35rem;">
                        <div>
                            <div style="font-family:'Poppins',sans-serif; font-size:0.83rem;
                                        font-weight:700; color:var(--u-deep);">{proj["name"]}</div>
                            <div style="font-size:0.67rem; color:#6b7280; font-weight:600;">{proj["cap_kw"]} kWp</div>
                        </div>
                        <div style="display:flex; gap:1.8rem; align-items:center;">
                            <div style="text-align:center;">
                                <div style="font-family:'Poppins',sans-serif; font-size:1rem;
                                            font-weight:800; color:var(--u-purple);">{p_gen:,.1f}</div>
                                <div style="font-size:0.58rem; color:#6b7280; text-transform:uppercase; font-weight:700;">MWh</div>
                            </div>
                            <div style="text-align:center;">
                                <div style="font-family:'Poppins',sans-serif; font-size:1rem;
                                            font-weight:800; color:var(--u-deep);">{p_cf:.1f}%</div>
                                <div style="font-size:0.58rem; color:#6b7280; text-transform:uppercase; font-weight:700;">Factor Planta</div>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

            # ── 3c. Resumen de Estado de Obligaciones — solo este banco ────
            st.markdown('<div class="section-title">Resumen de Estado de Obligaciones</div>', unsafe_allow_html=True)

            bank_status_totals = {}
            for st_name in STATUS_OPTIONS:
                bank_status_totals[st_name] = sum(
                    1 for k, v in st.session_state.obligation_statuses.items()
                    if k.startswith(f"{bidx_vg}_") and v == st_name
                )

            scols = st.columns(4)
            for i, st_name in enumerate(STATUS_OPTIONS):
                sm = STATUS_META[st_name]
                cnt = bank_status_totals[st_name]
                with scols[i]:
                    st.markdown(f"""
                    <div style="background:{sm['bg']}; border:1.5px solid {sm['color']}30;
                                border-radius:14px; padding:1rem; text-align:center;">
                        <div style="font-size:1.6rem;">{sm['icon']}</div>
                        <div style="font-family:'Poppins',sans-serif; font-size:1.5rem;
                                    font-weight:800; color:{sm['color']};">{cnt}</div>
                        <div style="font-size:0.72rem; font-weight:700; color:{sm['text']};">{st_name}</div>
                    </div>
                    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Obligaciones (area-based layout)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Obligaciones":

    st.markdown("""
    <div class="page-heading">Obligaciones y Responsabilidades</div>
    <div class="page-subheading">Gestiona el estado de cumplimiento de cada obligación contractual por banco y área.</div>
    """, unsafe_allow_html=True)

    bank_names = [b["name"] for b in banks]
    tabs = st.tabs(bank_names)

    for bank_idx, tab in enumerate(tabs):
        with tab:
            contract = contracts[bank_idx]
            resp = contract.get("responsabilidades", {})
            if not resp:
                st.info(f"No hay obligaciones para **{bank_names[bank_idx]}**.")
                continue

            # ── Build flat item list with area assignment ──────────────────
            all_items_with_area = []
            for cat_key, items in resp.items():
                for oi, item in enumerate(items):
                    area = assign_area(cat_key, item)
                    all_items_with_area.append((cat_key, oi, item, area))

            # ── Two-column layout: left = area filter, right = content ─────
            left_col, right_col = st.columns([2, 8])

            # ── LEFT: Area filter (single-column pill-style radio) ─────────
            with left_col:
                st.markdown('<div class="area-filter-header">Área</div>', unsafe_allow_html=True)
                area_radio_options = ["Todas"] + [lbl for _, lbl in AREA_CATEGORIES]
                area_sel = st.radio(
                    "Área",
                    area_radio_options,
                    index=0,
                    key=f"area_radio_{bank_idx}",
                    label_visibility="collapsed",
                )
                active_area_label = area_sel if area_sel else "Todas"
                _area_label_to_key = {lbl: key for key, lbl in AREA_CATEGORIES}
                active_area_key = _area_label_to_key.get(active_area_label, None)  # None = Todas

            # ── RIGHT: Stats + Status filter + Cards ───────────────────────
            with right_col:

                # Filter by area
                if active_area_key is None:
                    filtered = all_items_with_area
                else:
                    filtered = [
                        (ck, oi, it, ar)
                        for ck, oi, it, ar in all_items_with_area
                        if ar == active_area_key
                    ]

                # ── Compute stats ──────────────────────────────────────────
                total_count = len(filtered)
                pending_count = sum(
                    1 for ck, oi, it, ar in filtered
                    if st.session_state.obligation_statuses.get(
                        f"{bank_idx}_{ck}_{oi}", "Pendiente") == "Pendiente"
                )
                completed_count = sum(
                    1 for ck, oi, it, ar in filtered
                    if st.session_state.obligation_statuses.get(
                        f"{bank_idx}_{ck}_{oi}", "Pendiente") == "Completo"
                )
                in_gestion_count = sum(
                    1 for ck, oi, it, ar in filtered
                    if st.session_state.obligation_statuses.get(
                        f"{bank_idx}_{ck}_{oi}", "Pendiente") == "En Gestión"
                )
                upcoming_count = compute_upcoming_30d(contract, filtered)

                # ── Stat cards = clickable status filters ──────────────────
                if f"sf_{bank_idx}" not in st.session_state:
                    st.session_state[f"sf_{bank_idx}"] = "Todos"
                active_sf = st.session_state[f"sf_{bank_idx}"]

                uid = f"sfc{bank_idx}"
                st.markdown(f"""<style>
#{uid} + [data-testid="stHorizontalBlock"] button {{
    height: 5rem !important; border-radius: 16px !important;
    white-space: pre-line !important; line-height: 1.35 !important;
    font-size: 0.8rem !important; font-weight: 700 !important;
    transition: all 0.2s ease !important;
}}
#{uid} + [data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    background: #fff !important;
    border: 1.5px solid var(--u-purple-15) !important;
    color: var(--u-deep) !important;
    box-shadow: 0 1px 4px rgba(44,32,57,0.05) !important;
}}
#{uid} + [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    border-color: var(--u-purple) !important;
    box-shadow: 0 3px 12px rgba(145,91,216,0.15) !important;
    transform: translateY(-1px) !important;
}}
#{uid} + [data-testid="stHorizontalBlock"] button[kind="primary"] {{
    font-weight: 800 !important;
}}
</style><div id="{uid}"></div>""", unsafe_allow_html=True)

                sc1, sc2, sc3, sc4 = st.columns(4)
                stat_defs = [
                    ("Todos",     total_count,    "Total\nObligaciones"),
                    ("Pendiente", pending_count,  "Pendientes"),
                    ("Próximas",  upcoming_count, "Próximas\n30 días"),
                    ("Completo",  completed_count,"Completadas"),
                ]
                for col, (fv, cnt, lbl) in zip([sc1, sc2, sc3, sc4], stat_defs):
                    with col:
                        is_act = active_sf == fv
                        if st.button(
                            f"{cnt}\n{lbl}",
                            key=f"sf_{bank_idx}_{fv}",
                            use_container_width=True,
                            type="primary" if is_act else "secondary",
                        ):
                            st.session_state[f"sf_{bank_idx}"] = fv
                            st.rerun()

                st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

                # ── Obligation cards ───────────────────────────────────────
                shown = 0
                for cat_key, oi, item, area_key in filtered:
                    sk  = f"{bank_idx}_{cat_key}_{oi}"
                    wk  = f"sel_{sk}"
                    if wk in st.session_state:
                        st.session_state.obligation_statuses[sk] = st.session_state[wk]
                    current_status = st.session_state.obligation_statuses.get(sk, "Pendiente")

                    # Filter by stat card selection
                    if active_sf == "Próximas":
                        if not is_upcoming_item(contract, item):
                            continue
                    elif active_sf != "Todos" and current_status != active_sf:
                        continue

                    sev        = item.get("severidad", "media")
                    rm         = RISK_META.get(sev, RISK_META["media"])
                    sm         = STATUS_META[current_status]
                    area_label = AREA_LABEL_MAP.get(area_key, area_key.title())

                    c_card, c_file, c_status = st.columns([5, 3, 2])

                    with c_card:
                        st.markdown(f"""
                        <div class="ob-card" style="border-left-color:{sm['color']};">
                            <div class="ob-badges">
                                <span class="ob-clause">{item.get('clausula','')}</span>
                                <span class="ob-risk" style="background:{rm['bg']}; color:{rm['text']};">{rm['label']}</span>
                                <span class="ob-area-tag">{area_label}</span>
                            </div>
                            <div class="ob-desc">{item.get('obligacion','')}</div>
                            <div class="ob-freq">📅 {compute_next_due_date(contract, item)}&nbsp;&nbsp;·&nbsp;&nbsp;Área a cargo: {area_label}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with c_file:
                        st.markdown('<div class="ob-file-label">Link de soporte</div>',
                                    unsafe_allow_html=True)
                        lk = f"link_{sk}"
                        if lk not in st.session_state:
                            st.session_state[lk] = st.session_state.obligation_links.get(sk, "")

                        def _on_link_change(_sk=sk, _lk=lk):
                            new_val = st.session_state[_lk]
                            st.session_state.obligation_links[_sk] = new_val
                            save_one_link(_sk, new_val)

                        st.text_input(
                            "Link",
                            placeholder="https://...",
                            key=lk,
                            label_visibility="collapsed",
                            on_change=_on_link_change,
                        )

                    with c_status:
                        st.markdown('<div style="padding-top:0.5rem;"></div>',
                                    unsafe_allow_html=True)
                        # Normalise any legacy status not in CARD_STATUS_OPTIONS
                        safe_status = (current_status
                                       if current_status in CARD_STATUS_OPTIONS
                                       else "Pendiente")

                        def _on_status_change(_sk=sk, _wk=wk):
                            """Persist status to Supabase the moment the user changes it."""
                            new_val = st.session_state[_wk]
                            st.session_state.obligation_statuses[_sk] = new_val
                            save_one_status(_sk, new_val)

                        st.selectbox(
                            "Estado", CARD_STATUS_OPTIONS,
                            index=CARD_STATUS_OPTIONS.index(safe_status),
                            key=wk, label_visibility="collapsed",
                            on_change=_on_status_change,
                        )

                    shown += 1

                if shown == 0:
                    st.markdown(
                        '<div style="text-align:center;color:#94a3b8;padding:2.5rem 0;'
                        'font-size:0.85rem;font-weight:600;">'
                        'No hay obligaciones que coincidan con los filtros seleccionados.</div>',
                        unsafe_allow_html=True,
                    )

            # ── Delivery Calendar (full width) ─────────────────────────────
            st.markdown('<div class="section-title">Calendario de Entregas</div>',
                        unsafe_allow_html=True)

            month_keys, months_data = build_calendar_data(contract, bank_idx)

            SEV_LABEL = {"critica": "Crítica", "alta": "Alta", "media": "Media", "baja": "Baja"}
            # Badge colours — all within the Unergy brand palette
            SEV_BG    = {"critica": "#EAE6ED", "alta": "#EDE4F9", "media": "#F4EFF9", "baja": "#FAFFD0"}
            SEV_TEXT  = {"critica": "#2C2039", "alta": "#6B3FAE", "media": "#915BD8", "baja": "#2C2039"}

            timeline_html = ""
            for mk in month_keys:
                events = months_data.get(mk, [])
                if not events:
                    continue
                year, mon = mk.split("-")
                month_label = f"{MONTH_SHORT[int(mon)]} {year}"
                total = len(events)
                # Header bar: brand colours by highest severity in month
                sevs = [e.get("sev","media") for e in events]
                hdr_color = (
                    "#2C2039" if "critica" in sevs else   # Púrpura Profundo
                    "#915BD8" if "alta"    in sevs else   # Púrpura Enérgico
                    "#B48DD9"                              # Tint suave
                )

                rows_html = ""
                for ev in events:
                    day_num  = ev["date"].day
                    sev_key  = ev.get("sev", "media")
                    badge_bg = SEV_BG.get(sev_key, "#ede9fe")
                    badge_tx = SEV_TEXT.get(sev_key, "#5b21b6")
                    sev_lbl  = SEV_LABEL.get(sev_key, sev_key.title())
                    c = ev['color']
                    lbl = ev['label']
                    rows_html += (
                        f'<div style="display:flex;align-items:center;gap:0.75rem;padding:0.45rem 0;border-bottom:1px solid #e5e7eb;">'
                        f'<div style="min-width:2.2rem;height:2.2rem;border-radius:50%;background:{c}20;border:2px solid {c};'
                        f'display:flex;align-items:center;justify-content:center;font-family:Poppins,sans-serif;'
                        f'font-size:0.78rem;font-weight:800;color:{c};flex-shrink:0;">{day_num}</div>'
                        f'<div style="flex:1;font-size:0.72rem;color:#374151;line-height:1.35;">{lbl}</div>'
                        f'<div style="padding:0.18rem 0.55rem;border-radius:12px;font-size:0.62rem;'
                        f'font-weight:700;background:{badge_bg};color:{badge_tx};white-space:nowrap;flex-shrink:0;">{sev_lbl}</div>'
                        f'</div>'
                    )

                s_label = f'{total} entrega{"s" if total != 1 else ""}'
                timeline_html += (
                    f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:16px;'
                    f'overflow:hidden;box-shadow:0 2px 8px rgba(44,32,57,0.05);margin-bottom:1rem;">'
                    f'<div style="background:{hdr_color};padding:0.55rem 1rem;display:flex;align-items:center;justify-content:space-between;">'
                    f'<span style="font-family:Poppins,sans-serif;font-size:0.88rem;font-weight:800;color:#fff;letter-spacing:0.02em;">{month_label}</span>'
                    f'<span style="background:rgba(255,255,255,0.25);color:#fff;font-size:0.68rem;font-weight:700;padding:0.15rem 0.6rem;border-radius:20px;">{s_label}</span>'
                    f'</div>'
                    f'<div style="padding:0.25rem 1rem 0.5rem;">{rows_html}</div>'
                    f'</div>'
                )

            if not timeline_html:
                timeline_html = '<div style="color:#94a3b8;font-size:0.8rem;padding:1rem;">Sin entregas programadas en los próximos 12 meses.</div>'

            legend = (
                '<div style="display:flex;gap:0.75rem;margin-top:0.75rem;flex-wrap:wrap;">'
                '<span style="background:#2C2039;color:#FDFAF7;font-size:0.65rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:20px;">● Crítica</span>'
                '<span style="background:#915BD8;color:#FDFAF7;font-size:0.65rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:20px;">● Alta</span>'
                '<span style="background:#B48DD9;color:#FDFAF7;font-size:0.65rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:20px;">● Media</span>'
                '<span style="background:#D9CCF0;color:#2C2039;font-size:0.65rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:20px;">● Baja</span>'
                '</div>'
            )
            grid_html = (
                '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));'
                f'gap:0.75rem;margin-top:0.5rem;">{timeline_html}</div>{legend}'
            )
            st.markdown(grid_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Financiero
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Financiero":

    st.markdown("""
    <div class="page-heading">Análisis Financiero</div>
    <div class="page-subheading">Portafolio, rendimiento, covenants y condiciones de distribución por banco.</div>
    """, unsafe_allow_html=True)

    # Pre-compute consolidated mock data once (shared across tabs)
    # mock = generate_portfolio_mock() # REMOVED: Now fetching individually per tab
    # total_mw = sum(b.get("proyecto", {}).get("capacidad_agregada_mw", 6) for b in banks)
    # mo_labels, ingresos, opex, ds, fcl = generate_cashflow_mock(total_mw)

    # ── Bank tabs at the TOP ──────────────────────────────────────────────
    bank_names = [b["name"] for b in banks]
    fin_tabs = st.tabs(bank_names)

    for bank_idx, tab in enumerate(fin_tabs):
        with tab:
            c = contracts[bank_idx]
            bank_name = bank_names[bank_idx]
            fin = c.get("condiciones_financieras", {})
            criticas_data = c.get("clausulas_criticas", {})
            
            # Fetch dynamic data from google sheets
            with st.spinner(f"Cargando datos financieros para {bank_name} desde Google Sheets..."):
                real_data = fetch_financial_data_from_sheets(bank_name)
            c = contracts[bank_idx]
            fin = c.get("condiciones_financieras", {})
            criticas_data = c.get("clausulas_criticas", {})

            # ── 1. Portafolio de Inversión ────────────────────────────────
            st.markdown('<div class="section-title">Portafolio de Inversión</div>', unsafe_allow_html=True)
            pk1, pk2, pk3, pk4 = st.columns(4)
            with pk1:
                val = real_data["valor_portafolio"]
                # Formateo a Billones/Millones
                val_str = f"COP {val/1e9:.1f}B" if val >= 1e9 else f"COP {val:,.0f}"
                st.markdown(f'<div class="metric-card"><div class="label">Valor Portafolio</div><div class="value">{val_str}</div><div class="sub">Total bajo gestión</div></div>', unsafe_allow_html=True)
            with pk2:
                st.markdown(f'<div class="metric-card"><div class="label">ROI Proyectado</div><div class="value">{real_data["roi_proyectado"]:.1f}%</div><div class="sub">Retorno esperado</div></div>', unsafe_allow_html=True)
            with pk3:
                st.markdown(f'<div class="metric-card"><div class="label">Generación Anual</div><div class="value">{real_data["generacion_anual_mwh"]:,.0f}</div><div class="sub">MWh / año</div></div>', unsafe_allow_html=True)
            with pk4:
                st.markdown(f'<div class="metric-card"><div class="label">CO₂ Evitado</div><div class="value">{real_data["co2_evitado_ton"]:,.0f}</div><div class="sub">Toneladas / año</div></div>', unsafe_allow_html=True)

            # ── 2. Rendimiento Financiero ─────────────────────────────────
            st.markdown('<div class="section-title">Rendimiento Financiero</div>', unsafe_allow_html=True)
            pf1, pf2, pf3, pf4 = st.columns(4)
            with pf1:
                st.markdown(f'<div class="metric-card"><div class="label">TIR Real</div><div class="value">{real_data["tir_real"]:.1f}%</div><div class="sub">Tasa interna retorno</div></div>', unsafe_allow_html=True)
            with pf2:
                st.markdown(f'<div class="metric-card"><div class="label">Payback</div><div class="value">{real_data["payback_anos"]:.1f}</div><div class="sub">Años recuperación</div></div>', unsafe_allow_html=True)
            with pf3:
                st.markdown(f'<div class="metric-card"><div class="label">Factor Planta</div><div class="value">{real_data["factor_planta"]:.1f}%</div><div class="sub">Promedio portafolio</div></div>', unsafe_allow_html=True)
            with pf4:
                st.markdown(f'<div class="metric-card"><div class="label">Margen EBITDA</div><div class="value">{real_data["margen_ebitda"]:.1f}%</div><div class="sub">Eficiencia operativa</div></div>', unsafe_allow_html=True)

            # ── 3. Flujo de Caja Consolidado ──────────────────────────────
            st.markdown('<div class="section-title">Flujo de Caja Consolidado</div>', unsafe_allow_html=True)
            if HAS_PLOTLY:
                cf_data = real_data["cashflow"]
                cf_labels = cf_data["labels"]
                fig_cf = go.Figure()
                fig_cf.add_trace(go.Bar(x=cf_labels, y=[v/1e6 for v in cf_data["ingresos"]], name="Ingresos PPA", marker_color=PURPLE))
                fig_cf.add_trace(go.Bar(x=cf_labels, y=[-v/1e6 for v in cf_data["opex"]], name="OPEX", marker_color="#ef4444"))
                fig_cf.add_trace(go.Bar(x=cf_labels, y=[-v/1e6 for v in cf_data["ds"]], name="Servicio Deuda", marker_color="#f59e0b"))
                fig_cf.add_trace(go.Scatter(x=cf_labels, y=[v/1e6 for v in cf_data["fcl"]], name="FCL", line=dict(color=SOLAR_YELLOW, width=3), mode="lines+markers"))
                fig_cf.update_layout(
                    barmode="relative", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Lato, sans-serif", size=11, color=DEEP_PURPLE),
                    margin=dict(l=50, r=20, t=20, b=40), height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
                    yaxis=dict(gridcolor="rgba(145,91,216,0.07)", zeroline=True, zerolinecolor="rgba(44,32,57,0.2)", title="COP Millones"),
                    xaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_cf, use_container_width=True, config={"displayModeBar": False},
                                key=f"cf_{bank_idx}")

            st.markdown('<hr style="border:none;border-top:1px solid var(--u-purple-15);margin:1.5rem 0;">', unsafe_allow_html=True)

            # ── 4. Covenants Financieros ──────────────────────────────────
            st.markdown('<div class="section-title">Covenants Financieros</div>', unsafe_allow_html=True)
            cov = fin.get("covenants_financieros", {})
            if cov:
                dscr_hist = cov.get("DSCR_historico_minimo", cov.get("DSCR_minimo", "N/A"))
                dscr_proj = cov.get("DSCR_proyectado_minimo", dscr_hist)
                dscr_dist = cov.get("DSCR_para_distribucion", dscr_hist)
                cv1, cv2, cv3 = st.columns(3)
                with cv1:
                    st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:14px;padding:1.2rem;text-align:center;"><div style="font-size:0.65rem;color:#374151;text-transform:uppercase;font-weight:700;">DSCR Mínimo</div><div style="font-family:Poppins,sans-serif;font-size:2.2rem;font-weight:800;color:#16a34a;margin:0.2rem 0;">{dscr_hist}x</div></div>', unsafe_allow_html=True)
                with cv2:
                    st.markdown(f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:14px;padding:1.2rem;text-align:center;"><div style="font-size:0.65rem;color:#374151;text-transform:uppercase;font-weight:700;">DSCR Proyectado</div><div style="font-family:Poppins,sans-serif;font-size:2.2rem;font-weight:800;color:#16a34a;margin:0.2rem 0;">{dscr_proj}x</div></div>', unsafe_allow_html=True)
                with cv3:
                    st.markdown(f'<div style="background:var(--u-purple-10);border:1px solid var(--u-purple-25);border-radius:14px;padding:1.2rem;text-align:center;"><div style="font-size:0.65rem;color:#374151;text-transform:uppercase;font-weight:700;">DSCR Distribución</div><div style="font-family:Poppins,sans-serif;font-size:2.2rem;font-weight:800;color:var(--u-purple);margin:0.2rem 0;">{dscr_dist}x</div></div>', unsafe_allow_html=True)
                base = cov.get("base_calculo", "NIIF/IFRS")
                anio = cov.get("año_fiscal_prestatario", "Dic 31")
                st.markdown(f'<div style="background:var(--u-cream);border:1px solid var(--u-purple-10);border-radius:10px;padding:0.65rem 1rem;margin-top:0.7rem;font-size:0.72rem;color:#374151;"><strong>Base:</strong> {base}. <strong>Año fiscal:</strong> {anio}.</div>', unsafe_allow_html=True)
            else:
                st.info("No se encontraron covenants financieros en este contrato.")

            # ── 5. Histórico DSCR ─────────────────────────────────────────
            st.markdown('<div class="section-title">Histórico DSCR</div>', unsafe_allow_html=True)
            if HAS_PLOTLY:
                dscr_real = real_data["historico_dscr"]
                dscr_labels = cf_data["labels"][:len(dscr_real)] # Ajustar labels al tamaño de dscr
                
                fig_dscr = go.Figure()
                fig_dscr.add_trace(go.Scatter(
                    x=dscr_labels, y=dscr_real, name="DSCR Real",
                    line=dict(color=PURPLE, width=3), mode="lines+markers",
                    marker=dict(size=8, color=PURPLE, line=dict(width=2, color="#fff")),
                    fill="tozeroy", fillcolor="rgba(145,91,216,0.08)",
                ))
                fig_dscr.add_hline(y=1.2, line_dash="dash", line_color="#ef4444",
                                   annotation_text="Mínimo: 1.20x", annotation_position="top left")
                fig_dscr.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Lato, sans-serif", size=12, color=DEEP_PURPLE),
                    margin=dict(l=50, r=20, t=20, b=40), height=300,
                    yaxis=dict(gridcolor="rgba(145,91,216,0.07)", zeroline=False, range=[0.9, 1.7]),
                    xaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_dscr, use_container_width=True, config={"displayModeBar": False},
                                key=f"dscr_{bank_idx}")

            # ── 6. Distribución y Prepagos ────────────────────────────────
            st.markdown('<div class="section-title">Distribución y Prepagos</div>', unsafe_allow_html=True)
            cd_col, cp_col = st.columns(2)
            with cd_col:
                dist = criticas_data.get("distribucion_permitida", {})
                conditions = dist.get("condiciones", [])
                if conditions:
                    ch = "".join(f'<div style="display:flex;align-items:flex-start;gap:0.4rem;margin-bottom:0.35rem;"><span style="color:var(--u-purple);font-size:0.8rem;flex-shrink:0;">✓</span><span style="font-size:0.73rem;color:#374151;line-height:1.45;">{cond}</span></div>' for cond in conditions)
                    st.markdown(f'<div style="background:#fff;border:1px solid var(--u-purple-15);border-radius:14px;padding:1.2rem;box-shadow:0 1px 3px rgba(44,32,57,0.04);"><div style="font-family:Poppins,sans-serif;font-size:0.82rem;font-weight:700;color:var(--u-deep);margin-bottom:0.7rem;">Condiciones para Distribución</div>{ch}</div>', unsafe_allow_html=True)
                else:
                    st.info("Condiciones de distribución no disponibles.")
            with cp_col:
                prepago = criticas_data.get("prepago", {})
                if prepago:
                    p1 = prepago.get("penalidad_antes_4_anos", prepago.get("comision_prepago", "N/A"))
                    p2 = prepago.get("penalidad_4_a_8_anos", "N/A")
                    p3 = prepago.get("penalidad_despues_8_anos", "Sin penalidad")
                    st.markdown(f"""<div style="background:#fff;border:1px solid var(--u-purple-15);border-radius:14px;padding:1.2rem;box-shadow:0 1px 3px rgba(44,32,57,0.04);">
                    <div style="font-family:Poppins,sans-serif;font-size:0.82rem;font-weight:700;color:var(--u-deep);margin-bottom:0.7rem;">Penalización por Pago Anticipado</div>
                    <table class="prepay-table"><tr><th>Período</th><th>Penalización</th></tr>
                    <tr><td>Período 1</td><td class="highlight">{p1}</td></tr>
                    <tr><td>Período 2</td><td style="color:#f59e0b;font-weight:700;">{p2}</td></tr>
                    <tr><td>Período 3</td><td class="ok">{p3}</td></tr></table></div>""", unsafe_allow_html=True)
                else:
                    st.info("Información de prepago no disponible.")


# ══════════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="footer">
    Unergy · Debt Tracker · {len(banks)} contrato(s) bajo gestión<br>
    Solo para fines informativos internos. No constituye asesoría legal.
</div>
""", unsafe_allow_html=True)
