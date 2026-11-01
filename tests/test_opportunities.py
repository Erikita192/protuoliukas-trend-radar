from datetime import date
from pathlib import Path
from radar.opportunities import create_actions, promote_actions, improve_actions, filter_by_time
from radar.topics import evaluate_all, load_topics
from radar.timing import EVENTS

TODAY = date(2026, 10, 30)


def test_preserves_all_original_ideas_and_dates():
    topics = load_topics()
    assert len(topics) == 68
    assert sum(len(t.ideas) for t in topics) == 200
    assert len(EVENTS) >= 115
    assert any(t.id == "asmenines-ribos" for t in topics)


def test_creation_actions_are_concrete_and_transparently_labeled():
    actions = create_actions(TODAY, evaluate_all(TODAY))
    assert actions
    assert all(a.kind == "kurti" and a.detail and a.reason for a in actions)
    assert all("ne patvirtinta paklausa" in a.evidence for a in actions)
    assert all(a.urgency <= 8 for a in actions)


def test_time_filter_never_claims_big_task_fits_two_hours():
    actions = create_actions(TODAY, evaluate_all(TODAY), limit=35)
    selected = filter_by_time(actions, 2)
    assert selected
    assert all(a.effort_code == "G" for a in selected)


def test_product_promotions_separate_heuristic_and_measured_data():
    p = {"key": "p213", "code": "P213", "title": "Kortelės", "url": "https://example.org/p213"}
    pr = {"hint": "NOW", "window": "10-20 – 11-10", "angle": "Parodyti dvi korteles", "why": "Tinka sezonui"}
    without = promote_actions(TODAY, [(p, pr)], {})
    assert len(without) == 1
    assert "Kalendorinė" in without[0].evidence
    with_data = promote_actions(TODAY, [(p, pr)], {"P213": {"sales_30d": "4"}})
    assert with_data[0].evidence == "Importuoti rezultatai"
    assert with_data[0].evidence_rank > without[0].evidence_rank


def test_improvements_require_real_numbers():
    p = {"key": "p213", "code": "P213", "title": "Priemonė", "url": "https://example.org/p213"}
    assert improve_actions(TODAY, [(p, {})], {}) == []
    assert improve_actions(TODAY, [(p, {})], {"P213": {"impressions_28d": "8", "clicks_28d": "0"}}) == []
    found = improve_actions(TODAY, [(p, {})], {"P213": {"impressions_28d": "700", "clicks_28d": "5"}})
    assert len(found) == 1
    assert "700" in found[0].reason and "GSC" in found[0].evidence
