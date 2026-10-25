"""Deadline-first ordering for creation decisions; score only breaks date ties."""
from datetime import date


def priority_group(r, today: date) -> str:
    t = r.timing
    if t.kind == 'evergreen' or not t.pub_start or not t.pub_end:
        return 'EVERGREEN'
    if t.end and t.end < today:
        return 'MISSED'
    if t.pub_end < today:
        return 'MISSED' if (not t.end or t.end < today) else 'AFTER'
    remaining = (t.pub_end - today).days
    if t.pub_start <= today <= t.pub_end:
        return 'LAST' if remaining <= 3 else 'NOW'
    if t.pub_start > today:
        return 'SOON' if (t.pub_start - today).days <= 14 else 'LATER'
    return 'AFTER'


ORDER = {'LAST': 0, 'NOW': 1, 'SOON': 2, 'AFTER': 3, 'LATER': 4, 'MISSED': 5, 'EVERGREEN': 6}


def priority_key(r, today: date):
    group = priority_group(r, today)
    t = r.timing
    if group in ('LAST', 'NOW'):
        deadline = t.pub_end
    elif group in ('SOON', 'LATER'):
        deadline = t.pub_start
    elif group in ('AFTER', 'MISSED'):
        deadline = t.end or t.pub_end
    else:
        deadline = date.max
    return (ORDER[group], deadline, -r.score, r.topic.name)


def ordered(rows, today: date):
    return sorted(rows, key=lambda r: priority_key(r, today))
