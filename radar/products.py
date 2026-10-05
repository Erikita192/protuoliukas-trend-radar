"""Esamų produktų praturtinimas (tema, amžius, formatas) ir REKLAMAVIMO prioriteto variklis.
Reklamos balas (0–100) – planavimo heuristika, NE išmatuota paklausa, ir niekada nesumaišomas su naujų idėjų balu."""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta
from typing import Optional

from .timing import compute_timing, fmt, fmt_range
from .topics import load_topics, norm, parse_age_groups
from .signals import adjustments

FORMAT_RULES = [
    ("PDF", r"\bpdf\b"), ("PowerPoint", r"powerpoint|pptx|\bppt\b|skaidr"), ("Kortelės", r"kortel"),
    ("Bee-Bot", r"bee[\s\-]?bot"), ("Žaidimas", r"zaidim"), ("Darbo lapai", r"darbo lap|uzduociu lap"),
    ("Plakatas", r"plakat"), ("Dekoras", r"dekor|vardu|uzrasai"), ("Testas", r"\btest"), ("Interaktyvu", r"interaktyv"),
]
CONF_ADJ = {"high": 0, "medium": -2, "low": -8, "": -8}
STATUS = {"LAST": "⚡ PASKUTINĖ PROGA", "NOW": "🔥 REKLAMUOTI DABAR", "RISE": "↑ KYLA",
          "PREP": "📅 RUOŠTI REKLAMĄ", "OFF": "💤 DABAR NEAKTUALU"}


def detect_formats(text_norm: str) -> list:
    return [n for n, rx in FORMAT_RULES if re.search(rx, text_norm)]


def enrich(p: dict) -> dict:
    topics = load_topics()
    title = norm(p.get("title", ""))
    cats = norm(" | ".join(p.get("all_categories") or (p.get("categories", []) + p.get("listing_tags", [])) + [p.get("topic_text", "")]))
    desc = norm(p.get("description", "")[:3500])
    matches = []
    for tp in topics:
        strength, via = 0.0, ""
        if any(r.search(title) for r in tp.kw_re):
            strength, via = 3.0, "pavadinimas"
        elif any(r.search(cats) for r in tp.kw_re):
            strength, via = 3.0, "kategorija"
        else:
            hits = {i for i, r in enumerate(tp.kw_re) if r.search(desc)}
            if len(hits) >= 2:
                strength, via = 1.5, "aprašymas"
        if strength:
            matches.append((tp, strength, via))
    matches.sort(key=lambda m: -m[1])
    age_text = p.get("age_text") or ""
    groups = parse_age_groups(age_text) if age_text else []
    age_src = "puslapis" if groups else ""
    if not groups:
        m = re.search(r"(?:amžius|amzius|nuo|skirta)[^.]{0,30}?(\d{1,2}\s*[–\-]\s*\d{1,2}\s*(?:m\.|metų|kl\.)|\d{1,2}\s*(?:m\.|metų|kl\.))", p.get("description", "")[:2500], re.I)
        if m:
            groups = parse_age_groups(m.group(1)); age_src = "aprašymas"
    fmts = detect_formats(norm(p.get("title", "") + " " + p.get("format_text", "") + " " + " ".join(p.get("all_categories", [])) + " " + p.get("description", "")[:1500]))
    return {**p, "matches": matches, "age_groups": groups, "age_src": age_src, "formats": fmts,
            "topic_names": [m[0].name for m in matches if m[1] >= 3] or [m[0].name for m in matches[:2]],
            "area": next((m[0].area for m in matches), "")}


def _rotation(key: str, today: date) -> int:
    wk = today.isocalendar()
    h = hashlib.md5(f"{key}{wk[0]}{wk[1]}".encode()).hexdigest()
    return int(h[:4], 16) % 9


def _driver(tp, strength, today):
    """Grąžina dict(score, hint, label, timing) vienai temai."""
    t = compute_timing(tp.timing, today)
    ph = t.phase
    adj = CONF_ADJ.get(t.confidence, -8) if t.kind == "window" else 0
    disc = 0 if strength >= 3 else -12
    sc, hint, lab = 40, "OFF", ""
    if t.kind == "event":
        dl = t.days_to_use
        if ph == "EVENT_DAY":
            if dl is not None and dl >= 0:
                sc, hint, lab = 94, "LAST", "proga šiandien"
            else:
                sc, hint, lab = 35, "OFF", "klasės laikas šiai progai baigėsi"
        elif ph == "LAST":
            sc, hint, lab = (96 if dl <= 4 else 90), ("LAST" if dl <= 4 else "NOW"), f"klasėje naudoti liko {dl} d."
        elif ph == "PUBLISH_NOW":
            sc, hint, lab = 95, "NOW", "vyksta optimalus reklamos langas"
        elif ph == "PREP":
            sc, hint, lab = 82, "PREP", f"artėja – reklamą pradėk {fmt(t.pub_start, today)}"
        elif ph == "UPCOMING":
            sc, hint, lab = 55, "OFF", f"dar toli ({(t.pub_start - today).days} d. iki reklamos pradžios)"
        else:
            sc, hint, lab = 25, "OFF", f"kitas pikas {fmt(t.start, today)}"
    elif t.kind == "window":
        if ph == "LAST":
            sc, hint, lab = 90, "LAST", f"aktualumo langas baigiasi po {t.days_to_end} d."
        elif ph == "PUBLISH_NOW":
            sc, hint, lab = 88, "NOW", "prasidėjo ar prasideda aktualumo langas"
        elif ph == "ACTIVE":
            sc, hint, lab = 80, "NOW", "aktualumo langas vyksta"
        elif ph == "PREP":
            sc, hint, lab = 78, ("RISE" if (t.start - today).days <= 14 else "PREP"), f"langas prasideda {fmt(t.start, today)}"
        elif ph == "UPCOMING":
            sc, hint, lab = 55, "OFF", f"langas prasidės {fmt(t.start, today)}"
        else:
            sc, hint, lab = 25, "OFF", f"kitas langas {fmt(t.start, today)}"
    else:
        sc, hint, lab = 48, "OFF", "tęstinė tema be piko"
    if hint in ("LAST",) and strength < 3:
        hint = "NOW"
    return {"score": sc + adj + disc, "hint": hint, "label": lab, "timing": t, "topic": tp, "strength": strength}


def promotion(p: dict, today: date, sig: Optional[dict] = None) -> dict:
    drivers = [_driver(tp, st, today) for tp, st, _ in p["matches"]]
    drivers.sort(key=lambda d: -d["score"])
    best = drivers[0] if drivers else None
    reasons, score, hint = [], 40, "OFF"
    if best:
        score, hint = best["score"], best["hint"]
        reasons.append(f"{best['topic'].name}: {best['label']}")
        extra = [d for d in drivers[1:] if d["score"] >= 70]
        score += min(8, 3 * len(extra))
        for d in extra[:2]:
            reasons.append(f"{d['topic'].name}: {d['label']}")
    # ne sezoniniai varomieji
    tags = " ".join(norm(t) for t in p.get("all_categories", []))
    if "naujaus" in tags:
        score += 14; reasons.append("pažymėta kaip „Naujausios priemonės“ parduotuvėje")
        if hint == "OFF":
            hint = "RISE"
    ch = p.get("changed_at")
    if ch:
        try:
            if (datetime.now() - datetime.fromisoformat(ch)).days <= 14:
                score += 6; reasons.append("produkto puslapis neseniai atnaujintas")
        except Exception:
            pass
    if not best or best["hint"] == "OFF":
        rot = _rotation(p["key"], today)
        score += rot
        if not best:
            reasons.append("tęstinis produktas – siūlomas savaitės rotacijoje")
    delta, why, flags = adjustments(p, sig or {}, today)
    score += delta; reasons += why
    if delta > 0 and hint == "OFF":
        hint = "RISE"
    score = max(0, min(100, round(score)))
    if hint == "PREP":
        score = min(score, 88)      # artėjantis, bet dar nevykstantis langas neturi aplenkti aktyvių
    if hint == "OFF" and score >= 70:
        hint = "RISE"
    status = STATUS[hint]
    t = best["timing"] if best else None
    kind = t.kind if t else "evergreen"
    # datos
    stop = remind = None; window = "—"; peak = "Tęstinė tema – nėra konkretaus piko"
    if t and t.kind == "event":
        stop = t.use_by or t.start
        window = fmt_range(t.pub_start, stop, today)
        peak = f"{t.label}: proga {fmt_range(t.start, t.end, today)}" + (f" · klasėje iki {fmt(t.use_by, today)}" if t.use_by and t.use_by != t.start else "")
    elif t and t.kind == "window":
        stop = t.end
        window = fmt_range(t.start, t.end, today)
        peak = f"Aktualumo langas {window}"
    if stop and hint in ("NOW", "LAST", "RISE", "PREP"):
        cand = today + timedelta(days=7 if score >= 85 else 10)
        remind = cand if cand < stop else None
    topic = best["topic"] if best else None
    # veiksmai
    dl = (stop - today).days if stop else None
    fb = {"LAST": "TAIP – šiandien / per 1 d.", "NOW": "TAIP – per 1–2 d.", "RISE": "TAIP – šią savaitę",
          "PREP": f"RUOŠTI – pradėk {fmt(t.pub_start, today)}" if t else "RUOŠTI", "OFF": "NE dabar"}[hint]
    home_yes = hint in ("LAST", "NOW") and score >= 85
    home = (f"TAIP – laikyti iki {fmt(stop, today)}" + (f" ({dl} d.)" if dl is not None else "")) if home_yes and stop else (
        "TAIP – sezoniniame bloke" if home_yes else ("SVARSTYTI, jei yra vietos" if hint in ("NOW", "LAST", "RISE") and score >= 72 else "NE"))
    fm = p.get("formats", [])
    st_what = ("ekrano įrašas 8–10 s su 2 užduotimis" if "PowerPoint" in fm else
               "vaizdo klipas su maršrutu" if "Bee-Bot" in fm else
               "3 kortelės ir 1 užduotis kadre" if "Kortelės" in fm else
               "spausdinimo rezultatas: užpildytas lapas ant stalo" if ("PDF" in fm or "Darbo lapai" in fm) else
               "priemonė realioje grupės / klasės aplinkoje" if ("Dekoras" in fm or "Plakatas" in fm) else "2–3 realūs vidiniai puslapiai")
    stories = f"TAIP – {st_what}" if score >= 70 and hint != "OFF" else "NE dabar"
    # kampas
    if topic and t and t.kind == "event" and hint in ("LAST", "NOW", "PREP"):
        angle = (f"Pradėti nuo termino: „{t.label} – klasėje liko {t.days_to_use} d.“ " if t.days_to_use is not None else "") + \
                "Parodyti, kad priemonė jau paruošta ir ją galima atsisiųsti bei atspausdinti šiandien."
    elif topic and hint != "OFF":
        angle = f"Pradėti nuo pedagogo problemos: {topic.pain} Parodyti, kaip tai sprendžia ši priemonė."
    elif "Bee-Bot" in fm:
        angle = "Parodyti konkrečią Bee-Bot užduotį ir maršrutą, ne vien viršelį."
    elif "Kortelės" in fm:
        angle = "Parodyti 3 skirtingas korteles ir vieną veiklą, kurią pedagogas gali atlikti iškart."
    else:
        angle = "Akcentuoti vieną konkrečią problemą, kurią priemonė išsprendžia, ir parodyti realų vidinį puslapį."
    conf = (t.confidence if t else "") or ("high" if kind == "event" else "")
    return {"score": score, "status": status, "hint": hint, "why": "; ".join(reasons[:4]) or "nėra aiškaus piko – rotacija",
            "peak": peak, "window": window, "stop": stop, "remind": remind, "fb": fb, "home": home, "stories": stories,
            "angle": angle, "kind": kind, "confidence": conf, "basis": (t.basis if t else ""), "timing": t,
            "topic": topic, "days_left": dl, "flags": flags, "signal_notes": why,
            "seasonality": "Šventė / proga" if kind == "event" else ("Sezono / ugdymo langas" if kind == "window" else "Tęstinė")}


def analyse_all(catalog_products: list, today: date, sig: Optional[dict] = None) -> list:
    out = []
    for p in catalog_products:
        try:
            e = enrich(p)
            out.append((e, promotion(e, today, sig)))
        except Exception:      # vieno produkto klaida negali sugadinti viso radaro
            continue
    out.sort(key=lambda z: -z[1]["score"])
    return out
