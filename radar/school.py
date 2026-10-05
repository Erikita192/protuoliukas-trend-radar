"""Lietuvos mokyklų kalendorius: atostogos, paskutinė mokymosi diena prieš pertrauką.
Duomenys – data/school_calendar.json (ŠMSM). Kai tam laikotarpiui oficialių datų nėra, grąžinama tik
savaitgalio korekcija ir pažymima, kad kalendoriaus trūksta."""
from __future__ import annotations
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "school_calendar.json"


@lru_cache(maxsize=1)
def load() -> dict:
    try:
        raw = json.loads(PATH.read_text(encoding="utf8"))
    except Exception:
        return {"years": {}}
    return raw


def _d(s):
    return date.fromisoformat(s) if s else None


def breaks() -> list:
    out = []
    for yk, y in load().get("years", {}).items():
        for b in y.get("breaks", []):
            out.append((b["name"], _d(b["start"]), _d(b["end"]), yk))
    return sorted(out, key=lambda x: x[1])


def year_for(d: date):
    for yk, y in load().get("years", {}).items():
        s = _d(y["start"]); e = _d(y.get("year_end_grades_5_8_approx") or y["start"])
        if s <= d <= e + timedelta(days=0):
            return yk, y
    return None, None


def has_calendar(d: date) -> bool:
    yrs = load().get("years", {})
    for y in yrs.values():
        s = _d(y["start"]); e = _d(y.get("year_end_grades_5_8_approx") or y["start"])
        if s - timedelta(days=100) <= d <= e + timedelta(days=100):
            return True
    return False


def in_break(d: date):
    for name, s, e, _ in breaks():
        if s <= d <= e:
            return name
    return None


def is_school_day(d: date) -> bool:
    if d.weekday() >= 5 or in_break(d):
        return False
    yk, y = year_for(d)
    if y:
        end = _d(y.get("year_end_grades_1_4_approx"))
        if end and d > end:
            return False
        if d < _d(y["start"]):
            return False
    return True


def classroom_date(d: date) -> date:
    """Paskutinė mokymosi diena iki d imtinai (į kurią realiai klasėje galima naudoti šventės medžiagą).
    Jei oficialaus kalendoriaus nėra – tik savaitgalio korekcija."""
    x = d
    for _ in range(40):
        if has_calendar(x):
            if is_school_day(x):
                return x
        elif x.weekday() < 5:
            return x
        x -= timedelta(days=1)
    return d


def next_break(today: date):
    for name, s, e, _ in breaks():
        if e >= today:
            return name, s, e
    return None


def summary(today: date) -> dict:
    nb = next_break(today)
    out = {"calendar": has_calendar(today), "next_break": nb}
    if nb:
        out["last_school_day"] = classroom_date(nb[1] - timedelta(days=1))
        out["days_to_break"] = (nb[1] - today).days
    yk, y = year_for(today)
    out["year"] = yk
    out["verified"] = y.get("verified") if y else None
    out["sources"] = y.get("sources", []) if y else []
    return out


def timeline(today: date) -> list:
    """Artimiausi mokyklinio ritmo taškai, naudingi planuojant produktų kūrimą ir reklamą."""
    yk, y = year_for(today)
    if not y:
        return []
    items = []
    start = _d(y.get("start"))
    if start:
        items.append({"date": start, "name": "Mokslo metų pradžia", "detail": f"{yk} m. m. · planavimo sezono pradžia"})
    for b in y.get("breaks", []):
        s, e = _d(b["start"]), _d(b["end"])
        last = classroom_date(s - timedelta(days=1))
        items.append({"date": last, "name": f"Paskutinė mokymosi diena prieš: {b['name']}", "detail": f"Atostogos {s.strftime('%m-%d')}–{e.strftime('%m-%d')}"})
        items.append({"date": s, "name": b["name"], "detail": f"{s.strftime('%m-%d')}–{e.strftime('%m-%d')} · mokinių pertrauka"})
    sem = _d(y.get("semester1_end_approx"))
    if sem:
        items.append({"date": sem, "name": "I pusmečio pabaiga (apytikslė)", "detail": "Refleksijos, įsivertinimo ir kartojimo priemonėms aktualus laikotarpis; tikslią datą nustato mokykla."})
    e14 = _d(y.get("year_end_grades_1_4_approx"))
    if e14:
        items.append({"date": e14, "name": "Mokslo metų pabaiga 1–4 kl. (apytikslė)", "detail": "Metų refleksijai, atsisveikinimo ir vasaros priemonėms."})
    e58 = _d(y.get("year_end_grades_5_8_approx"))
    if e58:
        items.append({"date": e58, "name": "Mokslo metų pabaiga 5–8 kl. (apytikslė)", "detail": "Kartojimo, įsivertinimo ir vasaros planavimo laikotarpis."})
    return [x for x in sorted(items, key=lambda z: z["date"]) if x["date"] >= today - timedelta(days=30)]
