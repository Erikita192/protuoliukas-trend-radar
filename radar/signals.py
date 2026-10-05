"""Ateities duomenų jungtys. ŠIUO METU realių GA4 / GSC / pardavimų duomenų NĖRA – kol nėra CSV, visi signalai tušti
ir radaras jų neapsimeta turįs.

CSV (data/signals.csv) stulpeliai (visi nebūtini, išskyrus code arba url):
  code | url
  organic_clicks_7d, organic_clicks_prev_7d      (GSC)
  views_7d, views_prev_7d                         (GA4)
  sales_30d, revenue_30d                          (pardavimai)
  last_promoted (YYYY-MM-DD), promoted_channel    (Facebook / kt. istorija)
"""
from __future__ import annotations

import csv
import io
import os
from datetime import date
from pathlib import Path
from typing import Optional

DATA_DIR = Path(os.environ.get("PROTUOLIUKAS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
SIGNALS_PATH = DATA_DIR / "signals.csv"


def _f(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def parse_signals(text: str) -> dict:
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        key = (r.get("code") or "").upper().replace(" ", "") or r.get("url", "").rstrip("/")
        if key:
            rows[key] = r
    return rows


def load_signals(path: Path = None) -> dict:
    p = Path(path or SIGNALS_PATH)
    if not p.exists():
        return {}
    try:
        return parse_signals(p.read_text(encoding="utf8"))
    except Exception:
        return {}


def save_signals_text(text: str, path: Path = None) -> int:
    rows = parse_signals(text)
    p = Path(path or SIGNALS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf8")
    return len(rows)


def signal_stamp(sig: dict) -> str:
    return str(len(sig))


def adjustments(product: dict, sig: dict, today: date):
    """Grąžina (delta_balo, [priežastys], flags). Nieko neišgalvoja – jei duomenų nėra, grąžina (0, [], {})."""
    if not sig:
        return 0, [], {}
    r = sig.get((product.get("code") or "").upper()) or sig.get(product.get("url", "").rstrip("/"))
    if not r:
        return 0, [], {}
    delta, why, flags = 0, [], {}
    for a, b, label, cap in (("organic_clicks_7d", "organic_clicks_prev_7d", "organinis srautas (GSC)", 14),
                             ("views_7d", "views_prev_7d", "produkto peržiūros (GA4)", 12)):
        x, y = _f(r.get(a)), _f(r.get(b))
        if x is not None and y is not None and y >= 5:
            pct = (x - y) / y * 100
            flags[a] = round(pct)
            if pct >= 30:
                delta += cap; why.append(f"{label} per 7 d. {pct:+.0f} %")
            elif pct >= 15:
                delta += cap // 2; why.append(f"{label} per 7 d. {pct:+.0f} %")
    s = _f(r.get("sales_30d"))
    if s is not None and s >= 3:
        delta += 5; why.append(f"pardavimai per 30 d.: {int(s)}")
    lp = r.get("last_promoted")
    if lp:
        try:
            days = (today - date.fromisoformat(lp)).days
            flags["last_promoted_days"] = days
            if days < 7:
                delta -= 25; why.append(f"neseniai reklamuota (prieš {days} d.) – pauzė")
            elif days < 14:
                delta -= 10; why.append(f"reklamuota prieš {days} d.")
        except ValueError:
            pass
    return delta, why, flags
