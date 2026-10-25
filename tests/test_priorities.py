from datetime import date, timedelta
from types import SimpleNamespace
from radar.priorities import ordered, priority_group

def item(name, today, start, end, score):
    return SimpleNamespace(topic=SimpleNamespace(name=name), timing=SimpleNamespace(kind='window', pub_start=today+timedelta(days=start), pub_end=today+timedelta(days=end), end=today+timedelta(days=end+10)), score=score)

def test_deadline_beats_score():
    d=date(2026,10,25)
    urgent=item('Skubu',d,-5,1,40)
    later=item('Daugyba',d,10,20,100)
    assert ordered([later,urgent],d)[0] is urgent
    assert priority_group(urgent,d)=='LAST'

def test_missed_is_visible_and_after_active():
    d=date(2026,10,25)
    missed=item('Praejo',d,-30,-12,95)
    active=item('Dabar',d,-3,5,30)
    assert ordered([missed,active],d)==[active,missed]
    assert priority_group(missed,d)=='MISSED'
