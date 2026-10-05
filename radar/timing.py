"""Kalendorius ir laiko variklis: progų datos (perskaičiuojamos kiekvienais metais),
aktualumo langai, publikavimo langai, fazės ir įgyvendinamumas."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from . import school


def today_vilnius() -> date:
    o = os.environ.get("RADAR_TODAY")
    if o:
        try:
            return date.fromisoformat(o)
        except ValueError:
            pass
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Vilnius")).date()
    except Exception:
        return (datetime.utcnow() + timedelta(hours=3)).date()


def now_vilnius() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Vilnius")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow() + timedelta(hours=3)


def easter(y: int) -> date:
    a = y % 19; b = y // 100; c = y % 100
    d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    da = (h + l - 7 * m + 114) % 31 + 1
    return date(y, mo, da)


def first_sunday(y: int, m: int) -> date:
    d = date(y, m, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7)

def nth_weekday(y: int, m: int, weekday: int, n: int = 1) -> date:
    """weekday: pirmadienis=0 ... sekmadienis=6."""
    d = date(y, m, 1)
    first = d + timedelta(days=(weekday - d.weekday()) % 7)
    return first + timedelta(days=7 * (n - 1))

def last_weekday(y: int, m: int, weekday: int) -> date:
    if m == 12:
        d = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(y, m + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def advent_start(y: int) -> date:
    d = date(y, 12, 24)
    fourth = d - timedelta(days=(d.weekday() + 1) % 7)
    return fourth - timedelta(days=21)


@dataclass(frozen=True)
class EventDef:
    key: str
    name: str
    rule: Callable[[int], tuple]
    lead: int          # kiek dienų iki progos prasideda rekomenduojamas publikavimas
    gap: int           # kiek dienų iki progos baigiasi rekomenduojamas publikavimo langas
    approx: bool = False
    note: str = ""


def _d(m, d, m2=None, d2=None):
    if m2 is None:
        return lambda y: (date(y, m, d), date(y, m, d))
    return lambda y: (date(y, m, d), date(y + (1 if (m2, d2) < (m, d) else 0), m2, d2))


EVENTS = {e.key: e for e in [
    EventDef("veliavos_diena", "Lietuvos vėliavos diena", _d(1, 1), 14, 5),
    EventDef("brailio_diena", "Pasaulinė Brailio diena", _d(1, 4), 14, 5),
    EventDef("aciu_diena", "Tarptautinė „Ačiū“ diena", _d(1, 11), 12, 4, approx=True, note="Populiari edukacinė minėtina diena – prieš kampaniją verta patikrinti metų šaltinį"),
    EventDef("laisves_gyneju_diena", "Laisvės gynėjų diena", _d(1, 13), 21, 7),
    EventDef("rasysenos_diena", "Rašysenos diena", _d(1, 23), 14, 5, approx=True),
    EventDef("mokslo_metu_pradzia", "Mokslo metų pradžia", _d(9, 1), 21, 7),
    EventDef("mokytoju_diena", "Mokytojų diena", _d(10, 5), 18, 6),
    EventDef("sypsenos_diena", "Pasaulinė šypsenos diena", lambda y: (nth_weekday(y, 10, 4, 1),) * 2, 14, 5,
             note="Pirmasis spalio penktadienis – data kasmet perskaičiuojama"),
    EventDef("gyvunijos_diena", "Pasaulinė gyvūnijos diena", _d(10, 4), 14, 5),
    EventDef("helovinas", "Helovinas", _d(10, 31), 21, 8),
    EventDef("velines", "Visų Šventųjų diena ir Vėlinės", _d(11, 1, 11, 2), 14, 6,
             note="Visų Šventųjų diena – 11-01, Vėlinės – 11-02"),
    EventDef("tolerancijos_diena", "Tolerancijos diena", _d(11, 16), 24, 8),
    EventDef("vaiko_teisiu_diena", "Pasaulinė vaiko teisių diena", _d(11, 20), 18, 6),
    EventDef("sveikinimosi_diena", "Pasaulinė sveikinimosi diena", _d(11, 21), 14, 5),
    EventDef("adventas", "Advento pradžia", lambda y: (advent_start(y),) * 2, 28, 10,
             note="Pirmasis Advento sekmadienis (skaičiuojamas pagal metus)"),
    EventDef("kaledos", "Kūčios ir Kalėdos", _d(12, 24, 12, 25), 35, 12),
    EventDef("naujieji_metai", "Metų pabaiga ir Naujieji metai", _d(12, 31, 1, 1), 21, 7),
    EventDef("draugystes_diena", "Draugystės diena (vasario 14)", _d(2, 14), 18, 6),
    EventDef("saugaus_interneto_diena", "Saugesnio interneto diena", lambda y: (nth_weekday(y, 2, 1, 2),) * 2, 21, 7, approx=True,
             note="Planuojama pagal antrą vasario antradienį; prieš naudojant verta patikrinti konkrečių metų kampanijos datą"),
    EventDef("gimtosios_kalbos_diena", "Tarptautinė gimtosios kalbos diena", _d(2, 21), 18, 6),
    EventDef("radio_diena", "Pasaulinė radijo diena", _d(2, 13), 12, 4),
    EventDef("vasario16", "Vasario 16-oji", _d(2, 16), 21, 7),
    EventDef("uzgavenes", "Užgavėnės", lambda y: (easter(y) - timedelta(days=47),) * 2, 28, 9,
             note="47 d. iki Velykų (skaičiuojama pagal metus)"),
    EventDef("kovo11", "Kovo 11-oji", _d(3, 11), 21, 7),
    EventDef("miego_diena", "Pasaulinė miego diena", lambda y: (nth_weekday(y, 3, 4, 2),) * 2, 14, 5, approx=True, note="Kintanti kampanijos data; rodoma planavimo orientyrui"),
    EventDef("zemes_diena_lt", "Žemės diena (Lietuvoje)", _d(3, 20), 18, 6, note="Lietuvoje minima kovo 20 d."),
    EventDef("vandens_diena", "Pasaulinė vandens diena", _d(3, 22), 18, 6),
    EventDef("teatro_diena", "Tarptautinė teatro diena", _d(3, 27), 14, 5),
    EventDef("velykos", "Velykos", lambda y: (easter(y),) * 2, 30, 10, note="Skaičiuojama pagal metus"),
    EventDef("juoku_diena", "Balandžio 1-oji – juokų diena", _d(4, 1), 12, 4),
    EventDef("vaiku_knygos_diena", "Tarptautinė vaikų knygos diena", _d(4, 2), 18, 6),
    EventDef("saugaus_eismo_diena", "Saugaus eismo diena", _d(4, 6), 18, 6),
    EventDef("sveikatos_diena", "Pasaulinė sveikatos diena", _d(4, 7), 16, 5),
    EventDef("knygos_diena", "Pasaulinė knygos diena", _d(4, 23), 18, 6),
    EventDef("sokio_diena", "Tarptautinė šokio diena", _d(4, 29), 14, 5),
    EventDef("zemes_diena", "Tarptautinė Motinos Žemės diena", _d(4, 22), 18, 6),
    EventDef("motinos_diena", "Motinos diena", lambda y: (first_sunday(y, 5),) * 2, 21, 7,
             note="Pirmasis gegužės sekmadienis"),
    EventDef("seimos_diena", "Tarptautinė šeimos diena", _d(5, 15), 18, 6),
    EventDef("muzieju_diena", "Tarptautinė muziejų diena", _d(5, 18), 14, 5),
    EventDef("biciu_diena", "Pasaulinė bičių diena", _d(5, 20), 18, 6),
    EventDef("tevo_diena", "Tėvo diena", lambda y: (first_sunday(y, 6),) * 2, 21, 7,
             note="Pirmasis birželio sekmadienis"),
    EventDef("vaiku_diena", "Vaikų diena", _d(6, 1), 18, 6),
    EventDef("dviracio_diena", "Pasaulinė dviračio diena", _d(6, 3), 14, 5),
    EventDef("jogos_diena", "Tarptautinė jogos diena", _d(6, 21), 12, 4),
    EventDef("saulėgriza_vasara", "Vasaros saulėgrįža", _d(6, 21), 14, 5, approx=True, note="Astronominė data gali svyruoti apie birželio 20–21 d."),
    EventDef("draugystes_tarptautine", "Tarptautinė draugystės diena", _d(7, 30), 14, 5),
    EventDef("drambliu_diena", "Pasaulinė dramblių diena", _d(8, 12), 12, 4),
    EventDef("kairiarankiu_diena", "Tarptautinė kairiarankių diena", _d(8, 13), 12, 4),
    EventDef("fotografijos_diena", "Pasaulinė fotografijos diena", _d(8, 19), 12, 4),
    EventDef("baltijos_kelias", "Baltijos kelio diena", _d(8, 23), 18, 6),
    EventDef("demokratijos_diena", "Tarptautinė demokratijos diena", _d(9, 15), 14, 5),
    EventDef("taikos_diena", "Tarptautinė taikos diena", _d(9, 21), 16, 5),
    EventDef("muzikos_diena", "Tarptautinė muzikos diena", _d(10, 1), 16, 5),
    EventDef("maisto_diena", "Pasaulinė maisto diena", _d(10, 16), 16, 5),
    EventDef("gerumo_diena", "Pasaulinė gerumo diena", _d(11, 13), 16, 5),
    EventDef("mokslo_metu_pabaiga", "Mokslo metų pabaiga (1–4 kl.)", _d(6, 3), 28, 10, approx=True,
             note="Apytikslė data (2026–27 m. m. – apie 06-03, 5–8 kl. apie 06-10); tikslią nustato mokykla"),
]}


def occurrence(rule: Callable[[int], tuple], today: date):
    for y in (today.year - 1, today.year, today.year + 1, today.year + 2):
        s, e = rule(y)
        if e >= today:
            return s, e
    return rule(today.year + 1)


def window_rule(a: str, b: str):
    m1, d1 = map(int, a.split("-")); m2, d2 = map(int, b.split("-"))
    return lambda y: (date(y, m1, d1), date(y + (1 if (m2, d2) < (m1, d1) else 0), m2, d2))


def fmt(d: Optional[date], today: Optional[date] = None, with_year_if_other=True) -> str:
    if not d:
        return "—"
    s = d.strftime("%m-%d")
    if today and with_year_if_other and d.year != today.year:
        s += f" ({d.year})"
    return s


def fmt_range(a, b, today=None) -> str:
    if not a:
        return "—"
    if b is None or a == b:
        return fmt(a, today)
    return f"{fmt(a, today)}–{fmt(b, today)}"


# ------------------------------------------------------------------ Timing
@dataclass
class Timing:
    kind: str                  # event | window | evergreen
    label: str
    start: Optional[date] = None
    end: Optional[date] = None
    pub_start: Optional[date] = None
    pub_end: Optional[date] = None
    phase: str = "EVERGREEN"   # PUBLISH_NOW ACTIVE LAST EVENT_DAY PREP UPCOMING FAR EVERGREEN
    approx: bool = False
    note: str = ""
    today: Optional[date] = None
    use_by: Optional[date] = None      # paskutinė mokymosi diena prieš proga (pagal ŠMSM kalendorių)
    basis: str = ""                    # calendar | textbook | nature | assumption
    confidence: str = ""               # high | medium | low
    school_cal: bool = False

    @property
    def days_to_use(self):
        return (self.use_by - self.today).days if self.use_by else None

    @property
    def days_to_start(self):
        return (self.start - self.today).days if self.start else None

    @property
    def days_to_end(self):
        return (self.end - self.today).days if self.end else None

    @property
    def days_to_pub_start(self):
        return (self.pub_start - self.today).days if self.pub_start else None

    @property
    def days_to_pub_end(self):
        return (self.pub_end - self.today).days if self.pub_end else None


def _phase_before(today, pub_start):
    d = (pub_start - today).days
    return "PREP" if d <= 14 else ("UPCOMING" if d <= 60 else "FAR")


def compute_timing(spec: dict, today: date, for_new: bool = False) -> Timing:
    """spec: {'type':'event','event':key} | {'type':'windows','windows':[[a,b],..]} | {'type':'evergreen'}.
    for_new=True: jei proga vyksta šiandien, naujai priemonei planuojamas kitas pikas."""
    typ = spec.get("type", "evergreen")
    if typ == "event":
        ev = EVENTS[spec["event"]]
        s, e = occurrence(ev.rule, today)
        use = school.classroom_date(s)
        phase_override = None
        if today > use and today <= e or (s <= today <= e):
            if for_new:
                s, e = occurrence(ev.rule, e + timedelta(days=1))
                use = school.classroom_date(s)
                phase_override = "FAR"
            else:
                phase_override = "EVENT_DAY"
        pub_s = use - timedelta(days=ev.lead); pub_e = use - timedelta(days=ev.gap)
        if phase_override:
            ph = phase_override
        elif today > pub_e:
            ph = "LAST"
        elif today >= pub_s:
            ph = "PUBLISH_NOW"
        else:
            ph = _phase_before(today, pub_s)
        note = ev.note
        if use != s:
            note = (note + " · " if note else "") + f"klasėje naudojama iki {use.strftime('%m-%d')} (pagal mokyklų kalendorių)"
        return Timing("event", ev.name, s, e, pub_s, pub_e, ph, ev.approx, note, today, use_by=use,
                      basis="calendar", confidence="high" if not ev.approx else "medium",
                      school_cal=school.has_calendar(s))
    if typ == "windows":
        best = None
        for a, b in spec["windows"]:
            s, e = occurrence(window_rule(a, b), today)
            key = (0 if s <= today <= e else 1, s)
            if best is None or key < best[0]:
                best = (key, s, e)
        _, s, e = best
        pub_s = s - timedelta(days=14)
        pub_e = min(s + timedelta(days=14), max(s, e - timedelta(days=10)))
        if today > e:
            ph = "FAR"
        elif today >= pub_s and today <= pub_e:
            ph = "PUBLISH_NOW"
        elif today > pub_e:
            ph = "LAST" if (e - today).days <= 10 else "ACTIVE"
        else:
            ph = _phase_before(today, pub_s)
        return Timing("window", "Aktualumo langas", s, e, pub_s, pub_e, ph, False, spec.get("note", ""), today,
                      basis=spec.get("basis", "assumption"), confidence=spec.get("confidence", "low"))
    return Timing("evergreen", "Tęstinė tema", phase="EVERGREEN", today=today)


# --------------------------------------------------------------- Gamyba
EFFORT = {
    "G": ("🟢", "GREITA", "~1–2 val.", 1),
    "V": ("🟡", "VIDUTINĖ", "~3–5 val.", 2),
    "D": ("🔴", "DIDESNĖ", "~1–2 darbo dienos", 4),
}


def effort_label(code: str) -> str:
    ic, name, hrs, _ = EFFORT.get(code, EFFORT["V"])
    return f"{ic} {name} {hrs}"


def feasibility(t: Timing, effort: str):
    """Grąžina (kodas, žinutė). Kodai: OK / TIGHT / LATE. Tai planavimo orientyras, ne tikslus skaičiavimas."""
    need = EFFORT.get(effort, EFFORT["V"])[3]
    if t.kind == "evergreen":
        return "OK", "Nėra termino – kurk, kada patogu."
    nxt = fmt(t.pub_start, t.today)
    if t.kind == "event":
        avail = ((t.use_by or t.start) - t.today).days
        if t.phase == "EVENT_DAY":
            return "LATE", "Klasės / grupės laikas šiai progai baigėsi – naujai priemonei per vėlu."
        if t.phase in ("PUBLISH_NOW", "PREP", "UPCOMING", "FAR"):
            ideal = (t.pub_end - t.today).days
            if ideal >= need:
                return "OK", f"Dar realu pagaminti: iki rekomenduojamo publikavimo lango pabaigos liko {ideal} d."
            if avail >= need:
                return "TIGHT", "Spėsi tik pasibaigus idealiam langui – publikuok kaip „paskutinę progą“."
            return "LATE", f"Iki naudojimo klasėje liko {avail} d. – per vėlu; kitas pikas: {fmt(t.start, t.today)}."
        # LAST
        if avail >= need:
            if need == 1:
                return "TIGHT", f"Iki naudojimo klasėje liko {avail} d. – tik GREITA idėja: pagamink šiandien ir publikuok kaip „paskutinę progą“."
            return "TIGHT", f"Iki naudojimo klasėje liko {avail} d. – dar galima, bet tik kaip skubus leidimas."
        if need >= 4:
            return "LATE", f"Iki naudojimo klasėje liko {avail} d. – naujai didelei priemonei jau per vėlu."
        return "LATE", f"Iki naudojimo klasėje liko {avail} d. – naujai priemonei jau per vėlu."
    # window
    avail = (t.end - t.today).days if t.today >= t.start else (t.end - t.today).days
    if t.phase == "FAR" and t.today > t.end:
        return "LATE", "Langas praėjo."
    if t.phase in ("PUBLISH_NOW", "PREP", "UPCOMING", "FAR"):
        ideal = (t.pub_end - t.today).days
        if ideal >= need:
            return "OK", f"Dar realu pagaminti: ideali publikavimo pradžia – {fmt(t.pub_start, t.today)}, langas iki {fmt(t.end, t.today)}."
        return ("TIGHT", f"Langas dar trunka {avail} d. – publikuok kuo greičiau.") if avail >= need else ("LATE", "Langas beveik baigėsi.")
    if avail >= need + 2:
        return "TIGHT", f"Langas dar trunka {avail} d. – pavėluota, bet dar tinka."
    return "LATE", f"Lango pabaigai liko {avail} d. – per vėlu naujai priemonei."


def timing_score(t: Timing) -> int:
    p = t.phase
    if p == "PUBLISH_NOW": return 100
    if p == "ACTIVE": return 78
    if p == "LAST": return 70
    if p == "EVENT_DAY": return 20
    if p == "PREP":
        d = t.days_to_pub_start
        return 90 if d <= 3 else (82 if d <= 7 else 74)
    if p == "UPCOMING":
        return 60 if t.days_to_pub_start <= 30 else 48
    if p == "FAR": return 25
    return 52


def bucket(t: Timing) -> str:
    return {"PUBLISH_NOW": "NOW", "ACTIVE": "NOW", "LAST": "NOW", "PREP": "SOON",
            "UPCOMING": "UPCOMING", "FAR": "LATER", "EVENT_DAY": "LATER"}.get(t.phase, "EVERGREEN")


PHASE_TEXT = {
    "PUBLISH_NOW": "PUBLIKUOTI DABAR",
    "ACTIVE": "AKTYVUS LANGAS",
    "LAST": "PASKUTINĖ PROGA",
    "EVENT_DAY": "PROGA VYKSTA",
    "PREP": "RUOŠTI NETRUKUS",
    "UPCOMING": "ARTĖJA",
    "FAR": "VĖLIAU",
    "EVERGREEN": "TĘSTINĖ TEMA",
}
