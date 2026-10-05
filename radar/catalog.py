"""Katalogo saugykla: patvarus JSON cache, saugus sujungimas, užraktas, atnaujinimo paleidimas.

Taisyklės:
- tuščias / nepavykęs nuskaitymas NIEKADA neperrašo paskutinės geros kopijos;
- produktas laikomas pašalintu tik jei jo nebuvo dviejuose PILNUOSE nuskaitymuose iš eilės;
- dalinis nuskaitymas (laiko limitas) tik papildo, bet nieko neišjungia;
- vienas produktas = vienas įrašas, kategorijos kaupiamos kaip žymos.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .crawler import CrawlConfig, CrawlResult, crawl, diagnose

DATA_DIR = Path(os.environ.get("PROTUOLIUKAS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
CATALOG_PATH = DATA_DIR / "catalog.json"
LOCK_PATH = DATA_DIR / ".crawl.lock"
STALE_HOURS = float(os.environ.get("CATALOG_STALE_HOURS", "24"))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def empty_catalog() -> dict:
    return {"meta": {"last_checked": None, "last_success": None, "baseline_scan_at": None, "scans": 0, "last_diag": {}},
            "products": {}, "frontier": [], "visited": []}


def load_catalog(path: Path = None) -> dict:
    path = path or CATALOG_PATH
    try:
        c = json.loads(Path(path).read_text(encoding="utf8"))
        if "products" in c:
            c.setdefault("meta", empty_catalog()["meta"]); c.setdefault("frontier", []); c.setdefault("visited", [])
            return c
    except Exception:
        pass
    return empty_catalog()


def save_catalog(c: dict, path: Path = None) -> None:
    path = Path(path or CATALOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf8")
    os.replace(tmp, path)


def catalog_stamp(c: dict) -> str:
    return str(c["meta"].get("last_checked")) + ":" + str(len(c["products"]))


def active_products(c: dict) -> list:
    out = []
    for k, p in c["products"].items():
        if p.get("active", True):
            q = dict(p); q["key"] = k
            out.append(q)
    return out


def is_stale(c: dict, hours: float = STALE_HOURS) -> bool:
    lc = c["meta"].get("last_checked")
    if not lc:
        return True
    try:
        return (datetime.now() - datetime.fromisoformat(lc)).total_seconds() > hours * 3600
    except Exception:
        return True


def _hash(p: dict) -> str:
    return hashlib.md5(f"{p.get('title','')}|{p.get('price','')}|{p.get('description','')[:800]}".encode("utf8")).hexdigest()[:12]


def merge(old: dict, res: CrawlResult, resumed: bool = False) -> dict:
    new = {"meta": dict(old["meta"]), "products": {k: dict(v) for k, v in old["products"].items()},
           "frontier": [], "visited": []}
    now = _now()
    first = old["meta"].get("baseline_scan_at") is None
    clean = res.complete and (res.pages_failed <= max(3, 0.1 * max(1, res.pages_fetched)))
    for key, p in res.products.items():
        prev = new["products"].get(key)
        rec = dict(p)
        rec["content_hash"] = _hash(p)
        if prev:
            rec["first_seen"] = prev.get("first_seen", now)
            rec["baseline"] = prev.get("baseline", False)
            rec["changed_at"] = now if prev.get("content_hash") not in (None, rec["content_hash"]) else prev.get("changed_at")
        else:
            rec["first_seen"] = now; rec["baseline"] = first; rec["changed_at"] = None
        rec["last_seen"] = now; rec["miss_count"] = 0; rec["active"] = bool(p.get("available", True))
        # kategorijų žymos kaupiamos
        tags = set(p.get("categories", [])) | set(p.get("listing_tags", []))
        if prev:
            tags |= set(prev.get("categories", [])) | set(prev.get("listing_tags", []))
        rec["all_categories"] = sorted(tags)
        new["products"][key] = rec
    if clean:
        for key, p in new["products"].items():
            if key not in res.products:
                p["miss_count"] = p.get("miss_count", 0) + 1
                if p["miss_count"] >= 2:
                    p["active"] = False
    m = new["meta"]
    m["last_checked"] = now
    m["scans"] = m.get("scans", 0) + 1
    m["complete"] = res.complete
    m["stop_reason"] = res.stop_reason
    if res.ok and res.products:
        m["last_success"] = now
        if first:
            m["baseline_scan_at"] = now
    m["last_diag"] = diagnose(res)
    if not res.complete:
        new["frontier"] = res.frontier[:5000]
        new["visited"] = sorted(res.visited)[:20000]
    return new


def acquire_lock(max_age_s: int = 900) -> bool:
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_PATH.exists() and time.time() - LOCK_PATH.stat().st_mtime < max_age_s:
            return False
        LOCK_PATH.write_text(_now())
        return True
    except Exception:
        return True


def release_lock():
    try:
        LOCK_PATH.unlink()
    except Exception:
        pass


def update_catalog(progress: Optional[Callable] = None, resume: bool = False, cfg: CrawlConfig = None,
                   path: Path = None):
    """Grąžina (catalog, message, level). level: ok | warn | error."""
    old = load_catalog(path)
    if not acquire_lock():
        return old, "Atnaujinimas jau vyksta (kitas naršyklės langas ar planuota užduotis). Pabandyk po kelių minučių.", "warn"
    try:
        res = crawl(cfg or CrawlConfig(), resume=({"visited": old["visited"], "frontier": old["frontier"]} if resume and old["frontier"] else None),
                    progress=progress)
        if not res.ok or not res.products:
            old["meta"]["last_checked"] = _now()
            old["meta"]["last_diag"] = diagnose(res)
            save_catalog(old, path)
            return old, ("Nepavyko nuskaityti parduotuvės (svetainė nepasiekiama arba pasikeitė struktūra). "
                         "Paliktas paskutinis geras katalogas – jo duomenys nepaveikti."), "error"
        prev_n = len([1 for p in old["products"].values() if p.get("active", True)])
        new = merge(old, res, resumed=resume)
        save_catalog(new, path)
        d = new["meta"]["last_diag"]
        n = len(active_products(new))
        if not res.complete:
            return new, f"Nuskaitymas dalinis ({res.stop_reason}): rasta {n} aktyvių produktų. Paspausk „Tęsti nuskaitymą“, kad užbaigtum.", "warn"
        if prev_n and n < prev_n * 0.6:
            return new, f"Dėmesio: aktyvių produktų sumažėjo nuo {prev_n} iki {n}. Patikrink skirtuką „Duomenys“ – gali būti pasikeitusi svetainės struktūra.", "warn"
        if d.get("category_mismatch"):
            return new, f"Rasta {n} produktų, bet {len(d['category_mismatch'])} kategorijų rodo daugiau produktų, nei surinkta (žr. „Duomenys“).", "warn"
        return new, f"Katalogas atnaujintas: {n} aktyvių produktų.", "ok"
    finally:
        release_lock()
