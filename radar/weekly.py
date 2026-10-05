"""„Šią savaitę“ veiksmų centras: praktinis darbo sąrašas iš abiejų radaro dalių."""
from __future__ import annotations
from datetime import date, timedelta
from .timing import EVENTS, compute_timing, fmt, fmt_range
from . import school


def _diverse(items, key, limit, per_topic=2):
    out, cnt = [], {}
    for it in items:
        k = key(it)
        if cnt.get(k, 0) >= per_topic:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        out.append(it)
        if len(out) >= limit:
            break
    return out


def weekly(today: date, topics_eval: list, analysed: list) -> dict:
    tk = lambda z: (z[1]["topic"].id if z[1]["topic"] else z[0]["key"])
    fb = [z for z in analysed if z[1]["hint"] in ("LAST", "NOW", "RISE") and z[1]["score"] >= 72]
    fb = _diverse(fb, tk, 6)
    home = _diverse([z for z in analysed if z[1]["home"].startswith("TAIP")], tk, 5)
    stories = _diverse([z for z in analysed if z[1]["stories"].startswith("TAIP")], tk, 6)
    last = [z for z in analysed if z[1]["hint"] == "LAST"]
    ending = sorted([z for z in analysed if z[1]["stop"] and z[1]["hint"] in ("NOW", "LAST") and (z[1]["stop"] - today).days <= 10],
                    key=lambda z: z[1]["stop"])
    create = [r for r in topics_eval if r.bucket in ("NOW", "SOON") and r.feas != "LATE"]
    quick = [r for r in create if r.quick_ok]
    avoid = [r for r in topics_eval if r.feas == "LATE" and r.timing.kind != "evergreen" and r.timing.phase in ("LAST", "EVENT_DAY", "ACTIVE")]
    too_far = [r for r in topics_eval if r.bucket == "LATER" and r.timing.days_to_pub_start and r.timing.days_to_pub_start > 90][:6]
    stop_now = [z for z in analysed if z[1]["hint"] == "OFF" and z[1]["timing"] and z[1]["timing"].kind != "evergreen"
                and z[1]["timing"].phase in ("EVENT_DAY", "FAR") and z[1]["timing"].days_to_end is not None
                and z[1]["timing"].kind == "event" and z[1]["days_left"] is not None and z[1]["days_left"] < 0][:8]
    return {"facebook": fb, "home": home, "stories": stories, "last": last, "ending": ending,
            "create": create, "quick": quick, "avoid_new": avoid, "too_far": too_far, "stop_now": stop_now}


def upcoming_events(today: date, horizon: int = 60) -> list:
    out = []
    for ev in EVENTS.values():
        t = compute_timing({"type": "event", "event": ev.key}, today)
        s = t.start
        d = (s - today).days
        if d <= horizon:
            out.append({"ev": ev, "t": t, "days": d})
    out.sort(key=lambda x: x["days"])
    return out
