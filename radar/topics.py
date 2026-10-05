"""Naujų priemonių idėjų radaras: temų įkėlimas, vertinimas pagal datą, įgyvendinamumas."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .timing import (Timing, bucket, compute_timing, feasibility, timing_score,
                     fmt_range, EVENTS)

ROOT = Path(__file__).resolve().parent.parent
IDEAS_PATH = ROOT / "data" / "ideas.json"

_LT = str.maketrans("ąčęėįšųūžĄČĘĖĮŠŲŪŽ", "aceeisuuzaceeisuuz")


def norm(s: str) -> str:
    return (s or "").translate(_LT).lower()


def kw_regex(kw: str):
    toks = [re.escape(t) for t in norm(kw).split()]
    return re.compile(r"\b" + r"\w*\W+".join(toks) + r"\w*")


AGE_GROUPS = ["Ikimokyklinis", "Priešmokyklinis", "1–4 kl.", "5–8 kl."]


def parse_age_groups(text: str) -> list:
    """Iš tekstų kaip '5–10 m.', '2–5 kl.', 'Darželis–4 kl.' išveda amžiaus grupes. Nerasta -> []."""
    t = norm(text)
    g = set()
    if not t:
        return []
    if "darzel" in t:
        g |= {"Ikimokyklinis", "Priešmokyklinis"}
    if "priesmokyklin" in t:
        g.add("Priešmokyklinis")
    if re.search(r"\bikimokyklin", t):
        g.add("Ikimokyklinis")
    rng = re.search(r"(\d{1,2})\s*[–\-]\s*(\d{1,2})\s*(m\.|metu|metai|kl\.|klas)", t)
    single = re.search(r"(?:nuo\s*)?(\d{1,2})\s*(m\.|metu|kl\.|klas)", t)
    lo = hi = None
    unit = None
    if rng:
        lo, hi, unit = int(rng.group(1)), int(rng.group(2)), rng.group(3)
    elif single:
        lo = hi = int(single.group(1)); unit = single.group(2)
    if lo is not None:
        if unit.startswith("kl"):
            lo, hi = lo + 6, hi + 6
        if lo <= 5: g.add("Ikimokyklinis")
        if lo <= 6 <= hi or (lo <= 6 and hi >= 6): g.add("Priešmokyklinis")
        if lo <= 10 and hi >= 7: g.add("1–4 kl.")
        if hi >= 11: g.add("5–8 kl.")
        if lo <= 5 and hi >= 7: g.add("Priešmokyklinis")
    m = re.search(r"[–\-]\s*(\d)\s*kl", t)
    if m and "darzel" in t or (m and "priesmokyklin" in t):
        hi = int(m.group(1)) + 6
        if hi >= 7: g.add("1–4 kl.")
        if hi >= 11: g.add("5–8 kl.")
    return [x for x in AGE_GROUPS if x in g]


@dataclass
class Idea:
    title: str
    desc: str
    skill: str
    effort: str


@dataclass
class Topic:
    id: str
    name: str
    area: str
    ages: str
    potential: int
    kw: list
    timing: dict
    formats: list
    pain: str
    ideas: list
    age_groups: list = field(default_factory=list)
    kw_re: list = field(default_factory=list)

    @property
    def seasonality(self) -> str:
        return {"event": "Šventė / proga", "windows": "Sezono / ugdymo langas"}.get(self.timing.get("type"), "Tęstinė")


@lru_cache(maxsize=1)
def load_topics(path: str = str(IDEAS_PATH)) -> list:
    raw = json.loads(Path(path).read_text(encoding="utf8"))
    out = []
    for t in raw["topics"]:
        tp = Topic(id=t["id"], name=t["name"], area=t["area"], ages=t["ages"], potential=t["potential"],
                   kw=t["kw"], timing=t["timing"], formats=t["formats"], pain=t["pain"],
                   ideas=[Idea(**i) for i in t["ideas"]])
        tp.age_groups = parse_age_groups(tp.ages)
        tp.kw_re = [kw_regex(k) for k in tp.kw]
        out.append(tp)
    return out


@dataclass
class EvalIdea:
    idea: Idea
    code: str
    msg: str


@dataclass
class EvalTopic:
    topic: Topic
    timing: Timing
    ideas: list
    score: int
    bucket: str
    feas: str            # geriausias kodas tarp idėjų
    feas_msg: str
    quick_ok: bool

    @property
    def window_text(self) -> str:
        t = self.timing
        return fmt_range(t.start, t.end, t.today)


MULT = {"OK": 1.0, "TIGHT": 0.92, "LATE": 0.65}


def evaluate_topic(tp: Topic, today: date) -> EvalTopic:
    t = compute_timing(tp.timing, today, for_new=True)
    ev = []
    for i in tp.ideas:
        c, m = feasibility(t, i.effort)
        ev.append(EvalIdea(i, c, m))
    rank = {"OK": 0, "TIGHT": 1, "LATE": 2}
    best = min(ev, key=lambda e: rank[e.code])
    score = round((0.6 * tp.potential + 0.4 * timing_score(t)) * MULT[best.code])
    return EvalTopic(tp, t, ev, max(0, min(100, score)), bucket(t), best.code, best.msg,
                     any(e.code == "OK" and e.idea.effort == "G" for e in ev))


def evaluate_all(today: date) -> list:
    res = [evaluate_topic(tp, today) for tp in load_topics()]
    res.sort(key=lambda r: r.score, reverse=True)
    return res
