import sys, os
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from radar.timing import compute_timing, EVENTS, easter, advent_start, feasibility
from radar.topics import evaluate_all, parse_age_groups
from radar import school
from radar.products import enrich, promotion, analyse_all
from radar.catalog import merge, empty_catalog
from radar.crawler import CrawlResult
from radar.ui import product_card, topic_card
from radar.weekly import weekly


def test_dates():
    assert advent_start(2026) == date(2026, 11, 29)
    assert easter(2027) == date(2027, 3, 28)
    assert EVENTS["uzgavenes"].rule(2027)[0] == date(2027, 2, 9)
    assert EVENTS["motinos_diena"].rule(2027)[0] == date(2027, 5, 2)


def test_school_calendar_shifts_velines():
    t = compute_timing({"type": "event", "event": "velines"}, date(2026, 10, 4))
    assert t.use_by == date(2026, 10, 30) and t.phase == "PREP"


def test_teachers_day_tomorrow_blocks_big_items():
    t = compute_timing({"type": "event", "event": "mokytoju_diena"}, date(2026, 10, 4))
    assert feasibility(t, "D")[0] == "LATE" and feasibility(t, "G")[0] == "TIGHT"


def test_year_rollover():
    t = compute_timing({"type": "event", "event": "kaledos"}, date(2027, 1, 10))
    assert t.start.year == 2027 and t.start.month == 12


def test_topics_buckets_depend_on_date():
    a = {r.topic.id: r.bucket for r in evaluate_all(date(2026, 10, 4))}
    b = {r.topic.id: r.bucket for r in evaluate_all(date(2026, 12, 1))}
    assert a["helovinas"] == "SOON" and b["helovinas"] == "LATER"
    assert b["kaledos"] in ("NOW", "SOON")


def test_age_groups():
    assert parse_age_groups("Darželis–4 kl.") == ["Ikimokyklinis", "Priešmokyklinis", "1–4 kl."]


def test_promotion_not_seasonal_keyword_only():
    p = {"key": "x", "title": "Taisyklingas rašymas", "description": "Pristatymo sąlygos, taisyklės, nuolaidos, rudens pasiūlymas, kapinės",
         "all_categories": [], "url": "u", "code": "P1"}
    pr = promotion(enrich(p), date(2026, 10, 4))
    assert pr["hint"] == "OFF"


def test_html_escaped_and_cards_render():
    p = {"key": "x", "title": "<script>alert(1)</script> Helovino kortelės", "description": "x", "all_categories": ["Helovinas"], "url": "http://a/b?x=1&y=2", "code": "P9"}
    e = enrich(p); pr = promotion(e, date(2026, 10, 4))
    html = product_card(e, pr, date(2026, 10, 4))
    assert "<script>" not in html and pr["topic"].id == "helovinas"
    for r in evaluate_all(date(2026, 10, 4))[:5]:
        assert topic_card(r, date(2026, 10, 4))


def test_merge_keeps_old_on_failure_and_dedupes():
    old = empty_catalog()
    res = CrawlResult(ok=True, complete=True, pages_fetched=10)
    res.products = {"k1": {"url": "u1", "title": "A", "description": "d", "categories": ["M"], "listing_tags": ["N"], "available": True}}
    c1 = merge(old, res)
    assert c1["products"]["k1"]["baseline"] is True and set(c1["products"]["k1"]["all_categories"]) == {"M", "N"}
    empty = CrawlResult(ok=True, complete=True, pages_fetched=10)
    c2 = merge(c1, empty); assert c2["products"]["k1"]["active"] is True and c2["products"]["k1"]["miss_count"] == 1
    c3 = merge(c2, empty); assert c3["products"]["k1"]["active"] is False
    partial = CrawlResult(ok=True, complete=False, pages_fetched=10)
    c4 = merge(c1, partial); assert c4["products"]["k1"]["miss_count"] == 0


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
