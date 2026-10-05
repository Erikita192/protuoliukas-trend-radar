"""Vaizdo sluoksnis: premium paletė, kontrasto valdymas, kortelės, laiko juostos. Visas scrape'intas tekstas escape'inamas."""
from __future__ import annotations

import base64
import html
import re
from datetime import date
from pathlib import Path

from .timing import PHASE_TEXT, effort_label, fmt, fmt_range

ROOT = Path(__file__).resolve().parent.parent
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');
:root{color-scheme:light;--ink:#1B2B28;--muted:#56665F;--paper:#FBF8F3;--card:#FFFFFF;--line:#E6DFD3;--brand:#1F4D45;--brand2:#2E7D6B;--accent:#B7791F}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:var(--paper)!important;color:var(--ink)!important;font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.block-container{max-width:1180px;padding-top:1.1rem;padding-bottom:4rem}
.stApp p,.stApp li,.stApp label,.stApp span,.stApp div[data-testid="stMarkdownContainer"],.stApp [data-testid="stCaptionContainer"],.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--ink)!important}
.stApp [data-testid="stCaptionContainer"],.stApp small{color:var(--muted)!important}
.stApp h2,.stApp h3{font-family:'Fraunces',Georgia,serif;font-weight:700;letter-spacing:-.01em}
[data-baseweb="input"] input,[data-baseweb="textarea"] textarea,[data-baseweb="select"] div,[data-baseweb="select"] input,.stTextInput input,.stNumberInput input{background:#fff!important;color:var(--ink)!important;-webkit-text-fill-color:var(--ink)!important}
[data-baseweb="input"],[data-baseweb="select"]>div{background:#fff!important;border-color:var(--line)!important;border-radius:12px!important}
[data-baseweb="popover"] *,[role="listbox"] *{background:#fff!important;color:var(--ink)!important}
[data-baseweb="tag"]{background:#E3F1EA!important}[data-baseweb="tag"] *{color:#1F4D45!important}
.stButton>button,.stDownloadButton>button{background:var(--brand)!important;color:#fff!important;border:0!important;border-radius:12px!important;font-weight:600;padding:.55rem 1rem}
.stButton>button p,.stDownloadButton>button p{color:#fff!important}
.stButton>button:hover{background:var(--brand2)!important}
button[data-baseweb="tab"]{background:transparent!important;color:var(--muted)!important;font-weight:600;border-radius:10px 10px 0 0}
button[data-baseweb="tab"] p{color:inherit!important}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--brand)!important}
div[data-baseweb="tab-list"]{overflow-x:auto;gap:.2rem;border-bottom:1px solid var(--line)}
div[data-baseweb="tab-highlight"]{background:var(--brand)!important}
div[role="radiogroup"] label{background:#fff;border:1px solid var(--line);border-radius:999px;padding:.25rem .8rem;margin-right:.3rem}
div[role="radiogroup"] label:has(input:checked){background:#E3F1EA;border-color:var(--brand2)}
.streamlit-expanderHeader,[data-testid="stExpander"] summary{background:#fff!important;color:var(--ink)!important;border-radius:12px}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:14px!important;background:#fff!important}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:14px;padding:.6rem .9rem}
[data-testid="stMetricValue"],[data-testid="stMetricLabel"]{color:var(--ink)!important}
.pf .hero{display:flex;align-items:center;gap:16px;border:1px solid var(--line);border-radius:22px;padding:18px 22px;background:linear-gradient(135deg,#FFFFFF,#F4EFE6);margin-bottom:14px}
.pf .mark{width:54px;height:54px;border-radius:16px;background:var(--brand);color:#F7F1E3!important;display:flex;align-items:center;justify-content:center;font:700 30px 'Fraunces',Georgia,serif}
.pf .logoimg{height:54px;max-width:220px;object-fit:contain}
.pf .brand{font:700 1.45rem 'Fraunces',Georgia,serif;letter-spacing:.14em;color:var(--brand)!important;line-height:1}
.pf .tag{color:var(--muted)!important;font-size:.88rem;margin-top:5px}
.pf .card{border:1px solid var(--line);border-radius:18px;padding:16px 18px;margin:10px 0;background:var(--card);box-shadow:0 1px 2px rgba(31,77,69,.04)}
.pf .row{display:flex;gap:14px;align-items:flex-start}
.pf .ring{--p:50;flex:0 0 56px;width:56px;height:56px;border-radius:50%;background:conic-gradient(var(--c,#1F4D45) calc(var(--p)*1%),#ECE6DA 0);display:flex;align-items:center;justify-content:center;position:relative}
.pf .ring:before{content:"";position:absolute;inset:6px;background:#fff;border-radius:50%}
.pf .ring b{position:relative;font:700 1.05rem 'Fraunces',Georgia,serif;color:var(--ink)!important}
.pf .title{font:700 1.08rem 'Inter',sans-serif;color:var(--ink)!important;line-height:1.25}
.pf .meta{font-size:.84rem;color:var(--muted)!important;margin-top:3px}
.pf .pills{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 4px}
.pf .pill{font-size:.72rem;font-weight:700;letter-spacing:.03em;padding:3px 10px;border-radius:999px;background:#EEEBE5;color:#4C5A55!important;white-space:nowrap}
.pf .pill.now{background:#DDF0E5;color:#175B3E!important}.pf .pill.last{background:#FCE6C4;color:#7C4306!important}
.pf .pill.rise{background:#DEE9F6;color:#1F4570!important}.pf .pill.prep{background:#ECE4F6;color:#46306F!important}
.pf .pill.late{background:#F6DCDC;color:#8B2323!important}.pf .pill.ok{background:#DDF0E5;color:#175B3E!important}
.pf .pill.tight{background:#FCE6C4;color:#7C4306!important}
.pf .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:6px 18px;margin:10px 0 2px;font-size:.88rem}
.pf .facts div{color:var(--ink)!important}.pf .facts em{font-style:normal;color:var(--muted)!important;font-size:.78rem;display:block}
.pf .tl{position:relative;height:30px;margin:12px 2px 4px}
.pf .tl .bar{position:absolute;top:11px;height:8px;border-radius:6px}
.pf .tl .base{left:0;right:0;background:#EFE9DD}.pf .tl .ideal{background:#2E7D6B}.pf .tl .late{background:#E0A03B}
.pf .tl .now{position:absolute;top:3px;width:2px;height:24px;background:#1B2B28}
.pf .tl .lbl{position:absolute;top:19px;font-size:.66rem;color:var(--muted)!important;white-space:nowrap}
.pf details{margin-top:8px}.pf summary{cursor:pointer;font-weight:700;color:var(--brand)!important;padding:5px 0;font-size:.92rem}
.pf .idea{background:#F7F4EE;border-radius:13px;padding:10px 13px;margin:7px 0;font-size:.9rem;line-height:1.45}
.pf .idea b{color:var(--ink)!important}.pf .idea .sk{display:block;margin-top:4px;color:var(--muted)!important;font-size:.82rem}
.pf .idea .sk i{font-style:normal;font-weight:700;color:var(--brand)!important}
.pf .why{background:#F7F4EE;border-left:3px solid var(--brand2);border-radius:10px;padding:9px 12px;margin:9px 0;font-size:.9rem}
.pf .grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;font-size:.88rem;margin-top:6px}
.pf .grid2 div{color:var(--ink)!important}.pf .grid2 em{font-style:normal;font-size:.72rem;font-weight:700;letter-spacing:.05em;color:var(--muted)!important;display:block}
.pf .note{font-size:.8rem;color:var(--muted)!important;margin-top:8px}
.pf a{color:var(--brand2)!important;font-weight:600}
.pf .mini{display:flex;gap:10px;align-items:center;border-bottom:1px solid var(--line);padding:8px 0;font-size:.9rem}
.pf .mini .n{flex:0 0 38px;font-weight:700;color:var(--brand)!important;font-family:'Fraunces',Georgia,serif}
.pf .week{font:700 1rem 'Fraunces',Georgia,serif;margin:16px 0 4px;color:var(--brand)!important}
@media(max-width:700px){.block-container{padding-left:12px;padding-right:12px}.pf .hero{padding:14px}.pf .brand{font-size:1.15rem}.pf .grid2{grid-template-columns:1fr}.pf .facts{grid-template-columns:1fr 1fr}}
"""


def inject_css(st):
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def render(st, htm: str):
    htm = re.sub(r"\n\s*", "", htm)
    st.markdown(f'<div class="pf">{htm}</div>', unsafe_allow_html=True)


def logo_html() -> str:
    for name in ("logo.png", "logo.webp", "logo.jpg", "logo.jpeg", "logo.svg"):
        for base in (ROOT / "assets", ROOT):
            f = base / name
            if f.exists():
                mime = {"png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}[f.suffix[1:]]
                b64 = base64.b64encode(f.read_bytes()).decode()
                return f'<img class="logoimg" alt="Protuoliukas" src="data:{mime};base64,{b64}">'
    return '<div class="mark">P</div>'      # tekstinis fallback – ne tikras logotipas


def header(sub: str, with_text: bool = True) -> str:
    lg = logo_html()
    brand = '<div><div class="brand">PROTUOLIUKAS</div><div class="tag">{}</div></div>'.format(esc(sub))
    if lg.startswith("<img"):
        brand = '<div><div class="tag" style="margin:0">{}</div></div>'.format(esc(sub))
    return f'<div class="hero">{lg}{brand}</div>'


def ring(score: int, color: str = "#1F4D45") -> str:
    return f'<div class="ring" style="--p:{int(score)};--c:{color}"><b>{int(score)}</b></div>'


def timeline(t, today: date) -> str:
    """Mini laiko juosta: idealus publikavimo langas (žalia), paskutinė proga (gintaro), šiandien (juoda linija)."""
    if not t or not t.start:
        return ""
    a = min(today, t.pub_start or today)
    b = max(t.end or t.start, today)
    span = max(1, (b - a).days)
    pos = lambda d: max(0, min(100, (d - a).days / span * 100))
    parts = [f'<div class="bar base"></div>']
    if t.pub_start and t.pub_end:
        parts.append(f'<div class="bar ideal" style="left:{pos(t.pub_start):.1f}%;width:{max(1.5, pos(t.pub_end) - pos(t.pub_start)):.1f}%"></div>')
        end_late = t.use_by or t.end or t.start
        parts.append(f'<div class="bar late" style="left:{pos(t.pub_end):.1f}%;width:{max(1.5, pos(end_late) - pos(t.pub_end)):.1f}%"></div>')
    parts.append(f'<div class="now" style="left:{pos(today):.1f}%"></div>')
    lbl = f'<span class="lbl" style="left:{pos(today):.1f}%;transform:translateX(-50%)">šiandien</span>'
    return f'<div class="tl">{"".join(parts)}{lbl}</div>'


PHASE_CLASS = {"PUBLISH_NOW": "now", "ACTIVE": "now", "LAST": "last", "EVENT_DAY": "late", "PREP": "prep",
               "UPCOMING": "rise", "FAR": "", "EVERGREEN": ""}
FEAS_PILL = {"OK": ("ok", "SPĖSI"), "TIGHT": ("tight", "ĮTEMPTA"), "LATE": ("late", "PER VĖLU")}
CONF_TEXT = {"high": "oficialiai patvirtinta data", "medium": "tipinė seka / apytikslė", "low": "prielaida – patikrink", "": ""}
BASIS_TEXT = {"calendar": "ŠMSM kalendorius", "textbook": "vadovėlių seka", "nature": "gamtos sezonas", "assumption": "prielaida"}


def left_text(t) -> str:
    if t.kind == "evergreen":
        return "tęstinė tema – termino nėra"
    d = t.days_to_use if t.days_to_use is not None else t.days_to_start
    if t.kind == "window":
        if t.today < t.start:
            return f"langas prasidės po {t.days_to_start} d."
        return f"lango pabaigai {t.days_to_end} d."
    if d is None:
        return "—"
    if d < 0:
        return "klasės laikas baigėsi"
    if d == 0:
        return "šiandien paskutinė diena"
    return f"{d} d. iki naudojimo klasėje" if t.use_by and t.use_by != t.start else f"{d} d. iki progos"


def topic_card(r, today: date, open_ideas: bool = False) -> str:
    tp, t = r.topic, r.timing
    ph = PHASE_TEXT.get(t.phase, "")
    kind_lbl = "Proga" if t.kind == "event" else ("Aktualumo langas" if t.kind == "window" else "Aktualumas")
    pills = [f'<span class="pill {PHASE_CLASS.get(t.phase,"")}">{esc(ph)}</span>']
    fc, ft = FEAS_PILL[r.feas]
    pills.append(f'<span class="pill {fc}">{ft}</span>')
    pills.append(f'<span class="pill">{esc(tp.seasonality)}</span>')
    if t.confidence:
        pills.append(f'<span class="pill">{esc(BASIS_TEXT.get(t.basis,""))} · {esc(CONF_TEXT.get(t.confidence,""))}</span>')
    facts = [("🗓️ " + kind_lbl, (fmt_range(t.start, t.end, today) if t.start else "tęstinė tema – be konkrečios datos")),
             ("⏳ Liko", left_text(t))]
    if t.pub_start:
        facts.append(("🚀 Rekomenduojamas publikavimas", fmt_range(t.pub_start, t.pub_end, today)))
    facts.append(("📅 Būsena", ph))
    f_html = "".join(f"<div><em>{esc(k)}</em>{esc(v)}</div>" for k, v in facts)
    ideas = ""
    for e in r.ideas:
        fc2, ft2 = FEAS_PILL[e.code]
        ideas += (f'<div class="idea"><b>{esc(e.idea.title)}</b><br>{esc(e.idea.desc)}'
                  f'<span class="sk"><i>Lavina:</i> {esc(e.idea.skill)}</span>'
                  f'<span class="sk"><i>Gamyba:</i> {esc(effort_label(e.idea.effort))} · {esc(e.msg)}</span></div>')
    # Pirmas konkretus pavyzdys visada matomas: tema negali likti vien abstraktus pavadinimas.
    first = r.ideas[0] if r.ideas else None
    preview = (f'<div class="why"><b>💡 KONKRETUS PAVYZDYS: {esc(first.idea.title)}</b><br>{esc(first.idea.desc)}'
               f'<div class="note"><b>Lavina:</b> {esc(first.idea.skill)} · <b>Gamyba:</b> {esc(effort_label(first.idea.effort))}</div></div>') if first else ""
    note = f'<div class="note">{esc(t.note)}</div>' if t.note else ""
    pain = f'<div class="why"><b>Kodėl pedagogui aktualu:</b> {esc(tp.pain)}</div>'
    return (f'<div class="card"><div class="row">{ring(r.score)}<div><div class="title">{esc(tp.name)}</div>'
            f'<div class="meta">{esc(tp.area)} · {esc(tp.ages)} · potencialas {tp.potential}</div></div></div>'
            f'<div class="pills">{"".join(pills)}</div>{timeline(t, today)}<div class="facts">{f_html}</div>{note}{pain}{preview}'
            f'<details {"open" if open_ideas else ""}><summary>Visos {len(r.ideas)} konkrečios priemonės – rodyti</summary>{ideas}</details></div>')


def product_card(p: dict, pr: dict, today: date) -> str:
    cls = {"LAST": "last", "NOW": "now", "RISE": "rise", "PREP": "prep", "OFF": ""}[pr["hint"]]
    color = {"LAST": "#B7791F", "NOW": "#1F4D45", "RISE": "#2E5C8A", "PREP": "#5B3F8C", "OFF": "#8A948F"}[pr["hint"]]
    rel = {"LAST": "PASKUTINĖ PROGA", "NOW": "DABAR", "RISE": "KYLA", "PREP": "ARTĖJA", "OFF": "NEAKTUALU"}[pr["hint"]]
    code = f'{esc(p["code"])} · ' if p.get("code") else ""
    price = f' · {esc(p["price"])} €' if p.get("price") else ""
    pills = [f'<span class="pill {cls}">{esc(pr["status"])}</span>', f'<span class="pill">{esc(pr["seasonality"])}</span>']
    if pr["confidence"] and pr["kind"] != "evergreen":
        pills.append(f'<span class="pill">{esc(CONF_TEXT.get(pr["confidence"], ""))}</span>')
    pills += [f'<span class="pill">{esc(f)}</span>' for f in p.get("formats", [])[:3]]
    if p.get("age_groups"):
        pills.append(f'<span class="pill">{esc(", ".join(p["age_groups"]))}</span>')
    topics = ", ".join(p.get("topic_names", [])[:3]) or "tema neatpažinta"
    stop = fmt(pr["stop"], today) if pr["stop"] else "— (nėra datos; vertink pagal rotaciją)"
    remind = fmt(pr["remind"], today) if pr["remind"] else "—"
    cats = ", ".join((p.get("all_categories") or [])[:5]) or "kategorijos nerastos"
    t = pr["timing"]
    tl = timeline(t, today) if t and t.kind != "evergreen" else ""
    sig = f'<div class="note">Signalai: {esc("; ".join(pr["signal_notes"]))}</div>' if pr["signal_notes"] else ""
    return (f'<div class="card"><div class="row">{ring(pr["score"], color)}<div><div class="title">{code}{esc(p["title"])}</div>'
            f'<div class="meta">Reklamos prioritetas{price} · {esc(topics)}</div></div></div>'
            f'<div class="pills">{"".join(pills)}</div>{tl}'
            f'<div class="grid2"><div><em>📈 TEMOS AKTUALUMAS</em>{rel}</div><div><em>🗓️ AKTUALUMO / REKLAMOS LANGAS</em>{esc(pr["window"])}</div></div>'
            f'<div class="why"><b>KODĖL DABAR:</b> {esc(pr["why"])}</div>'
            f'<div class="grid2"><div><em>FACEBOOK</em>{esc(pr["fb"])}</div><div><em>PAGRINDINIS PUSLAPIS</em>{esc(pr["home"])}</div>'
            f'<div><em>STORIES</em>{esc(pr["stories"])}</div><div><em>PAKARTOTINIS PRIMINIMAS</em>{esc(remind)}</div>'
            f'<div style="grid-column:1/-1"><em>REKLAMOS KAMPAS</em>{esc(pr["angle"])}</div>'
            f'<div><em>NUSTOTI AKTYVIAI REKLAMUOTI</em>{esc(stop)}</div><div><em>KATEGORIJOS</em>{esc(cats)}</div></div>{sig}'
            f'<div class="note"><a href="{esc(p["url"])}" target="_blank" rel="noopener">Atidaryti parduotuvėje ↗</a></div></div>')


def mini_row(score, title, sub="", url="") -> str:
    t = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(title)}</a>' if url else esc(title)
    return f'<div class="mini"><span class="n">{int(score)}</span><div>{t}<div class="meta">{esc(sub)}</div></div></div>'
