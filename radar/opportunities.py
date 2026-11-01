"""V22: practical actions with transparent evidence, no invented demand metrics.

Priority is a planning aid. Demand is only *observed* when imported sales/analytics
exist; seasonality and editorial potential never masquerade as measured demand.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .priorities import priority_group, ordered
from .timing import fmt, fmt_range, effort_label
from .topics import norm


@dataclass(frozen=True)
class Action:
    kind: str   # kurti | reklamuoti | pagerinti
    title: str
    detail: str
    reason: str
    evidence: str
    label: str
    deadline: str = ""
    url: str = ""
    effort: str = ""
    effort_code: str = ""
    topic_id: str = ""
    urgency: int = 9
    evidence_rank: int = 0
    due_in_days: int = 9999
    area: str = ""


def _product_signal(product: dict, signals: dict) -> dict:
    if not signals:
        return {}
    return (signals.get((product.get("code") or "").upper().replace(" ", ""))
            or signals.get((product.get("url") or "").rstrip("/")) or {})


def _num(x) -> Optional[float]:
    try:
        return float(str(x).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _find_signal(p: dict, signals: dict):
    r = _product_signal(p, signals)
    sales = _num(r.get("sales_30d"))
    clicks = _num(r.get("organic_clicks_7d"))
    prev = _num(r.get("organic_clicks_prev_7d"))
    views = _num(r.get("views_7d"))
    prev_views = _num(r.get("views_prev_7d"))
    facts = []
    if sales is not None:
        facts.append(f"{int(sales)} pard. per 30 d.")
    if clicks is not None and prev is not None and prev >= 5:
        facts.append(f"GSC paspaudimai per 7 d.: {clicks:g} vs {prev:g}")
    if views is not None and prev_views is not None and prev_views >= 5:
        facts.append(f"Puslapio peržiūros per 7 d.: {views:g} vs {prev_views:g}")
    return r, facts, sales, clicks, prev


def create_actions(today: date, topics: list, limit: int = 12, occupied_topics=None) -> list[Action]:
    occupied = set(occupied_topics or ())
    results = []
    for r in ordered(topics, today):
        if not r.ideas or r.feas == "LATE":
            continue
        group = priority_group(r, today)
        if group in ("MISSED", "AFTER", "LATER"):
            continue
        if group == "EVERGREEN":
            urgency, label = 8, "Lanksti idėja – be piko"
        elif group == "LAST":
            urgency, label = 1, "Skubus publikavimo terminas"
        elif group == "NOW":
            urgency, label = 2, "Ruošti ir publikuoti dabar"
        elif group == "SOON":
            urgency, label = 4, "Pasiruošti artėjančiam laikui"
        else:
            continue
        eligible_ideas = [i for i in r.ideas if i.code == "OK"] or [i for i in r.ideas if i.code == "TIGHT"]
        if not eligible_ideas:
            continue
        # Favor a manageable, complete first product, not the longest idea.
        idea = min(eligible_ideas, key=lambda i: ({"G": 1, "V": 2, "D": 3}.get(i.idea.effort, 2), i.idea.title))
        t = r.timing
        date_str = fmt_range(t.pub_start, t.pub_end, today) if t.pub_start else "Be konkrečios datos"
        if group == "LAST" and idea.code == "TIGHT":
            # DO NOT recommend a longer task when only a short publication window remains.
            continue
        overlap = r.topic.id in occupied
        reason = (f"Planuojamas publikavimo langas: {date_str}. "
                  f"{r.topic.pain} "
                  + ("Kataloge jau yra susijusių produktų – pirmiau palygink, ar verta kurti naują."
                     if overlap else ""))
        results.append(Action(
            "kurti", idea.idea.title, idea.idea.desc, reason.strip(),
            "Kalendorius / redakcinė idėja, ne patvirtinta paklausa", label,
            date_str, effort=effort_label(idea.idea.effort), effort_code=idea.idea.effort, topic_id=r.topic.id,
            urgency=urgency + (1 if overlap else 0), evidence_rank=0,
            due_in_days=((t.pub_end if group in ("LAST", "NOW") else t.pub_start) - today).days if t.pub_start and t.pub_end else 9999,
            area=r.topic.area,
        ))
    # Variety: don't fill a dashboard with the same theme or one domain.
    results.sort(key=lambda a: (a.urgency, a.due_in_days, a.title))
    # Diverse top recommendations: show different educational fields before
    # accumulating multiple maths / language ideas.
    chosen, remainder, per_area = [], [], {}
    for a in results:
        if per_area.get(a.area, 0) < 2:
            chosen.append(a)
            per_area[a.area] = per_area.get(a.area, 0) + 1
        else:
            remainder.append(a)
    return (chosen + remainder)[:limit]


def promote_actions(today: date, analysed: list, signals: dict, limit: int = 8) -> list[Action]:
    entries = []
    for p, pr in analysed:
        if pr.get("hint") not in ("LAST", "NOW", "RISE", "PREP"):
            continue
        signal, facts, sales, clicks, prev = _find_signal(p, signals)
        real = bool(facts)
        if sales is not None and sales >= 1:
            ev_rank = 3
        elif clicks is not None and prev is not None and prev >= 5 and clicks > prev:
            ev_rank = 2
        elif facts:
            ev_rank = 1
        else:
            ev_rank = 0
        when = pr.get("window") or ""
        signal_note = "; ".join(facts) if facts else "Tik kalendorinis / teminis sutapimas; pardavimų duomenų nėra"
        if pr.get("hint") == "PREP":
            label, urgency = "Paruošti reklamą", 5
        elif pr.get("hint") == "LAST":
            label, urgency = "Paskutinė reklamos galimybė", 1
        else:
            label, urgency = "Galima reklamuoti dabar", 2
        entries.append(Action(
            "reklamuoti", p.get("title", "Produktas"), pr.get("angle", "Parodyti konkretų produkto naudojimą."),
            (pr.get("why") or "Teminis sutapimas") + ". " + signal_note,
            "Importuoti rezultatai" if real else "Kalendorinė rekomendacija – ne pardavimo prognozė",
            label, when, p.get("url", ""), urgency=urgency, evidence_rank=ev_rank,
        ))
    entries.sort(key=lambda a: (a.urgency, -a.evidence_rank, a.title))
    return entries[:limit]


def improve_actions(today: date, analysed: list, signals: dict, limit: int = 8) -> list[Action]:
    """Only evidence-based diagnostics; never assert a product is weak without metrics."""
    if not signals:
        return []
    entries = []
    for p, pr in analysed:
        r = _product_signal(p, signals)
        if not r:
            continue
        impr = _num(r.get("impressions_28d"))
        clicks28 = _num(r.get("clicks_28d"))
        sales = _num(r.get("sales_30d"))
        views30 = _num(r.get("views_30d"))
        title = p.get("title", "Produktas")
        url = p.get("url", "")
        if impr is not None and clicks28 is not None and impr >= 100:
            ctr = clicks28 / impr
            if ctr < .025:
                entries.append(Action(
                    "pagerinti", title,
                    "Peržiūrėti produkto pavadinimą, paieškos fragmentą, pagrindinę nuotrauką ir užklausų atitikimą. Pakeitimus tikrinti pagal kitų 28 dienų rezultatus.",
                    f"Importuoti GSC rodikliai: {int(impr)} parodymų, {int(clicks28)} paspaudimų, CTR {ctr:.1%}.",
                    "Išmatuota: GSC CSV", "Patikrinti paieškos rezultatą", url=url, urgency=3, evidence_rank=3,
                ))
        if views30 is not None and views30 >= 60 and sales is not None and sales == 0:
            entries.append(Action(
                "pagerinti", title,
                "Patikrinti produkto demonstravimo vaizdus, turinio pavyzdžius, kainą ir pirkimo kelią. Peržiūros dar neįrodo, kad problema būtent aprašyme.",
                f"Importuoti duomenys: {int(views30)} peržiūrų ir {int(sales)} pardavimų per 30 d.",
                "Išmatuota: produktų CSV", "Peržiūrėti pasiūlymo pateikimą", url=url, urgency=3, evidence_rank=3,
            ))
    entries.sort(key=lambda a: (a.urgency, -a.evidence_rank, a.title))
    return entries[:limit]


def action_counts(actions: list[Action]) -> dict:
    return {k: sum(a.kind == k for a in actions) for k in ("kurti", "reklamuoti", "pagerinti")}


def filter_by_time(actions: list[Action], available_hours: int, category: str = "visi") -> list[Action]:
    # Estimates are coarse; a longer task can be planned for later, but mustn't
    # be presented as something achievable in a 2h slot.
    limits = {"G": 2, "V": 5, "D": 16}
    eligible = []
    for a in actions:
        if category != "visi" and a.kind != category:
            continue
        if a.kind == "kurti" and a.effort:
            effort = limits.get(a.effort_code, 16)
            if effort > available_hours:
                continue
        eligible.append(a)
    return eligible
