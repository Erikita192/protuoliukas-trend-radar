import streamlit as st
from datetime import date, timedelta
import math

st.set_page_config(
    page_title="Protuoliuko paklausos radaras",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# V11 – mobile-first premium UI
# -----------------------------
st.markdown("""
<style>
:root {
  --ink:#173b34;
  --muted:#667b76;
  --line:#dfe8e5;
  --soft:#f6f9f8;
  --mint:#e7f7ee;
  --mint-2:#d4f2df;
  --accent:#386e61;
  --warm:#fff4df;
  --blue:#eef4ff;
  --rose:#fff0f0;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  background:#ffffff !important;
  color:var(--ink) !important;
}
[data-testid="stHeader"] { background:rgba(255,255,255,.92) !important; }
[data-testid="stMainBlockContainer"] {
  max-width:1180px;
  padding-top:1.2rem;
  padding-bottom:4rem;
}
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li, label, .stCaption {
  color:var(--ink) !important;
}
h1,h2,h3,h4 { color:var(--ink) !important; letter-spacing:-.02em; }
.smallcaps {font-size:.82rem;font-weight:800;letter-spacing:.16em;color:#71827e !important;margin:1.5rem 0 .65rem;}
.hero {
  border:1px solid var(--line); border-radius:26px; padding:24px 26px;
  background:linear-gradient(145deg,#ffffff 0%,#f7fbf9 100%);
  box-shadow:0 10px 30px rgba(28,62,54,.05); margin-bottom:16px;
}
.hero h1 {font-size:clamp(1.8rem,5vw,3.2rem);margin:0 0 .35rem;}
.hero p {color:var(--muted)!important;margin:.25rem 0 0;font-size:1rem;}
.kpis {display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px;}
.kpi {background:white;border:1px solid var(--line);border-radius:16px;padding:13px;}
.kpi b {display:block;font-size:1.25rem;color:var(--ink)!important;}
.kpi span {font-size:.78rem;color:var(--muted)!important;}
.timeline {display:flex;gap:8px;overflow-x:auto;padding:3px 1px 10px;scrollbar-width:thin;}
.day {min-width:118px;border:1px solid var(--line);border-radius:16px;padding:11px;background:#fff;}
.day.now {background:var(--mint);border-color:#b7dfc6;}
.day .d {font-weight:800;font-size:.82rem;color:var(--ink)!important;}
.day .t {font-size:.78rem;color:var(--muted)!important;margin-top:4px;}
.card {
  border:1px solid var(--line); border-radius:20px; padding:18px 20px;
  background:#fff; margin:0 0 12px; box-shadow:0 5px 18px rgba(28,62,54,.035);
}
.card.hot {background:var(--mint);}
.card.soon {background:var(--warm);}
.card.later {background:var(--blue);}
.card.plan {background:#f8f4ff;}
.card h3 {margin:0 0 6px;font-size:1.08rem;}
.card p {margin:5px 0;color:var(--ink)!important;}
.meta {font-size:.82rem;color:var(--muted)!important;}
.score {font-weight:800;white-space:nowrap;}
.idea {
  border-left:3px solid #8bbbab; padding:8px 11px; margin:8px 0;
  background:rgba(255,255,255,.72); border-radius:0 10px 10px 0;
}
.winner {
  background:var(--mint-2);border:1px solid #b7dfc6;border-radius:18px;
  padding:18px 20px;margin:10px 0 14px;
}
.winner strong,.winner div {color:#245c4e!important;}
[data-baseweb="tab-list"] {gap:5px;overflow-x:auto!important;}
button[data-baseweb="tab"] {
  color:var(--ink)!important;background:#f5f7f6!important;border-radius:12px 12px 0 0!important;
  white-space:nowrap!important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  background:var(--accent)!important;
}
button[data-baseweb="tab"][aria-selected="true"] p,
button[data-baseweb="tab"][aria-selected="true"] div,
button[data-baseweb="tab"][aria-selected="true"] span {
  color:white!important;
}
div[data-testid="stExpander"] {border-color:var(--line)!important;border-radius:14px!important;}
.stButton>button, .stDownloadButton>button {
  border-radius:12px!important;border:1px solid var(--line)!important;color:var(--ink)!important;
  background:white!important;
}
@media (max-width:700px) {
  [data-testid="stMainBlockContainer"] {padding-left:1rem;padding-right:1rem;padding-top:.7rem;}
  .hero {padding:19px 17px;border-radius:20px;}
  .kpis {grid-template-columns:repeat(2,1fr);}
  .card {padding:15px 15px;}
  .winner {padding:15px;}
  button[data-baseweb="tab"] {padding-left:10px!important;padding-right:10px!important;}
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------
# Concrete product-demand topic knowledge
# Fixed peak dates: they DO NOT move with today.
# Edit/extend this bank as needed.
# ---------------------------------------
TOPICS = [
    dict(topic="Rudens požymiai", area="Pasaulio pažinimas", peak="2026-09-21", score=96,
         ideas=["„Rudens požymiai“ – atpažinimo kortelės",
                "„Kas pasikeitė rudenį?“ – interaktyvus PPT",
                "Bee-Bot: nuvažiuok iki rudens požymio",
                "Rūšiavimas: ruduo / ne ruduo"]),
    dict(topic="Medžių lapai", area="Gamta", peak="2026-09-28", score=99,
         ideas=["„Kuris lapas nuo kurio medžio?“ – poravimo kortelės",
                "„Atpažink medžio lapą“ – interaktyvus PPT",
                "Bee-Bot: lapas → medis",
                "Lapų rūšiavimas pagal formą ir kraštą"]),
    dict(topic="Miško gyvūnai", area="Gamta", peak="2026-10-02", score=95,
         ideas=["Gyvūnas → buveinė – poravimo kortelės",
                "„Kas gyvena miške?“ – atrankos kortelės",
                "Bee-Bot: nuvažiuok iki tinkamo gyvūno",
                "Interaktyvus PPT „Atpažink miško gyvūną“"]),
    dict(topic="Grybai: valgomi ir nevalgomi", area="Gamta", peak="2026-10-05", score=92,
         ideas=["Valgomas / nevalgomas – rūšiavimo kortelės",
                "„Atpažink grybą“ – pažintinis PPT",
                "Grybas → pavadinimas – poravimo kortelės",
                "Miško radiniai – kas tinka / kas netinka"]),
    dict(topic="Žmogaus kūno dalys", area="Pasaulio pažinimas", peak="2026-10-08", score=94,
         ideas=["Kūno dalis → pavadinimas – kortelės",
                "„Kur yra...?“ – interaktyvus PPT",
                "Bee-Bot: nuvažiuok iki kūno dalies",
                "Kūno dalis → funkcija – poravimo kortelės"]),
    dict(topic="Sveika mityba", area="Gyvenimo įgūdžiai", peak="2026-10-12", score=91,
         ideas=["Sveika / rečiau – maisto rūšiavimo kortelės",
                "„Sukurk sveiką lėkštę“ – PDF užduotys",
                "Maisto grupės – poravimo kortelės",
                "Interaktyvus PPT „Ką rinktis?“"]),
    dict(topic="Skaičių tiesė", area="Matematika", peak="2026-10-15", score=97,
         ideas=["„Kuris skaičius arčiau?“ – kortelės",
                "„Tarp kurių skaičių?“ – kortelės",
                "„Koks veiksmas pavaizduotas?“ – skaičių tiesė",
                "Sudėtis ir atimtis skaičių tiesėje"]),
    dict(topic="Daugyba kaip vienodos grupės", area="Matematika", peak="2026-10-19", score=94,
         ideas=["Daugyba su vienodomis objektų grupėmis",
                "Daugyba skaičių tiesėje – šuoliai",
                "Veiksmas → vaizdas – poravimo kortelės",
                "„Kiek grupių po kiek?“ – užduočių kortelės"]),
    dict(topic="Sakinio dalys", area="Lietuvių kalba", peak="2026-10-22", score=90,
         ideas=["Kas? Ką veikia? Ką? – sakinio kortelės",
                "Sudėk sakinį iš 3 dalių",
                "Sakinys → trūkstama dalis – interaktyvus PPT",
                "Paveikslas → sudaryk sakinį"]),
    dict(topic="Helovinas", area="Sezoninės temos", peak="2026-10-27", score=89,
         ideas=["Helovino žodyno skaitymo kortelės",
                "„Kas netinka?“ – Helovino pastabumo kortelės",
                "Skaičiavimas su moliūgais iki 10 / 20",
                "Helovino Bee-Bot paieškos žaidimas"]),
    dict(topic="Vėlinės", area="Pažintinė veikla", peak="2026-10-30", score=93,
         ideas=["Vėlinių simbolių pažinimo kortelės",
                "„Kas tinka Vėlinėms?“ – rūšiavimo užduotys",
                "Trumpas pažintinis PPT apie Vėlines",
                "Skaitymo ir teksto suvokimo užduotys 1–2 klasei"]),
    dict(topic="Žodžio sandara", area="Lietuvių kalba", peak="2026-11-05", score=88,
         ideas=["Šaknis / priešdėlis / priesaga – atpažinimo kortelės",
                "Sudėk žodį iš jo dalių",
                "Rask giminiškus žodžius",
                "Interaktyvus PPT „Kuri dalis pažymėta?“"]),
    dict(topic="Ilgio matavimas", area="Matematika", peak="2026-11-09", score=87,
         ideas=["Pamatuok liniuote – realaus mastelio kortelės",
                "Kuris daiktas ilgesnis / trumpesnis?",
                "cm → pasirink tinkamą ilgį",
                "Matavimo klaidų detektyvas"]),
    dict(topic="Laikrodis: valandos ir minutės", area="Matematika", peak="2026-11-12", score=91,
         ideas=["Nuskaityk laiką: pilnos ir pusinės valandos",
                "Laikas su 5 / 10 / 15 min. intervalais",
                "Nupiešk rodykles pagal laiką",
                "Kasdienės situacijos → parink laiką"]),
]

def d(s): return date.fromisoformat(s)
today = date.today()

def phase(t):
    delta = (d(t["peak"]) - today).days
    if delta <= 7:
        return "DABAR"
    if delta <= 17:
        return "NETRUKUS"
    if delta <= 30:
        return "ARTĖJA"
    return "PLANAI"

def adjusted_score(t):
    delta = (d(t["peak"]) - today).days
    timing = 8 if 0 <= delta <= 7 else 5 if 8 <= delta <= 17 else 2 if 18 <= delta <= 30 else 0
    return min(100, t["score"] + timing)

def card(t, cls=""):
    ideas = "".join(f'<div class="idea">• {x}</div>' for x in t["ideas"])
    return f"""
    <div class="card {cls}">
      <h3>{t["topic"]} <span class="score">· {adjusted_score(t)}/100</span></h3>
      <div class="meta">{t["area"]} · piko data {d(t["peak"]).strftime("%Y-%m-%d")}</div>
      <p><b>Ką konkrečiai galima kurti:</b></p>
      {ideas}
    </div>"""

active30 = [t for t in TOPICS if -10 <= (d(t["peak"])-today).days <= 45]
active30.sort(key=lambda x: abs((d(x["peak"])-today).days))

st.markdown("""
<div class="hero">
  <div class="smallcaps" style="margin:0 0 .35rem">PROTUOLIUKAS</div>
  <h1>Paklausos radaras</h1>
  <p>Ne abstrakčios kryptys, o konkrečios temos ir konkretūs produktai, kuriuos verta kurti.</p>
  <div class="kpis">
    <div class="kpi"><b>30 d.</b><span>kūrimo horizontas</span></div>
    <div class="kpi"><b>DABAR</b><span>0–7 d. sprendimai</span></div>
    <div class="kpi"><b>4+</b><span>idėjos kiekvienai temai</span></div>
    <div class="kpi"><b>Fiksuotos</b><span>piko datos</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="smallcaps">30 DIENŲ RADARAS</div>', unsafe_allow_html=True)
timeline_items = []
for t in sorted([x for x in TOPICS if -3 <= (d(x["peak"])-today).days <= 30], key=lambda x:d(x["peak"])):
    nowcls = " now" if phase(t)=="DABAR" else ""
    timeline_items.append(
        f'<div class="day{nowcls}"><div class="d">{d(t["peak"]).strftime("%d.%m")}</div>'
        f'<div class="t"><b>{t["topic"]}</b><br>{t["area"]}</div></div>'
    )
st.markdown('<div class="timeline">' + "".join(timeline_items) + '</div>', unsafe_allow_html=True)

st.markdown('<div class="smallcaps">DARBO ERDVĖ</div>', unsafe_allow_html=True)
tabs = st.tabs(["🔥 DABAR","📅 NETRUKUS","🔭 ARTĖJA","💡 PLANAI","🔎 VISOS TEMOS"])

mapping = [
    ("DABAR", "hot", "Ką verta užbaigti ar pradėti artimiausiomis dienomis"),
    ("NETRUKUS", "soon", "Ką verta ruošti iš anksto"),
    ("ARTĖJA", "later", "Temos, kurių paklausa artėja"),
    ("PLANAI", "plan", "Tolimesnio horizonto temos"),
]

for tab, (label, cls, intro) in zip(tabs[:4], mapping):
    with tab:
        subset = [t for t in TOPICS if phase(t)==label]
        subset.sort(key=lambda x:(-adjusted_score(x), d(x["peak"])))
        st.markdown(f"### {intro}")
        if subset:
            top = subset[0]
            st.markdown(
                f'<div class="winner"><strong>🏆 JEI {label} KURTUMĖTE TIK VIENĄ:</strong>'
                f'<div style="margin-top:6px;font-size:1.05rem">{top["topic"]} · {adjusted_score(top)}/100</div>'
                f'<div class="meta">Pirmas konkretus variantas: {top["ideas"][0]}</div></div>',
                unsafe_allow_html=True
            )
            for t in subset:
                st.markdown(card(t, cls), unsafe_allow_html=True)
        else:
            st.info("Šiame lange šiuo metu nėra temos iš bazės.")

with tabs[4]:
    areas = ["Visos"] + sorted(set(t["area"] for t in TOPICS))
    area = st.selectbox("Sritis", areas)
    q = st.text_input("Ieškoti temos ar produkto", placeholder="pvz. skaičių tiesė, Bee-Bot, lapai")
    rows = TOPICS
    if area != "Visos":
        rows = [t for t in rows if t["area"] == area]
    if q.strip():
        qq=q.lower().strip()
        rows=[t for t in rows if qq in (t["topic"]+" "+t["area"]+" "+" ".join(t["ideas"])).lower()]
    for t in sorted(rows, key=lambda x:d(x["peak"])):
        st.markdown(card(t), unsafe_allow_html=True)

st.markdown('<div class="smallcaps">GREITAS KŪRIMO PLANAS</div>', unsafe_allow_html=True)
ranked = sorted(TOPICS, key=lambda x:(-adjusted_score(x), abs((d(x["peak"])-today).days)))[:5]
for i,t in enumerate(ranked,1):
    st.markdown(f"**{i}. {t['topic']}** — {t['ideas'][0]}  \n{t['area']} · {adjusted_score(t)}/100 · pikas {t['peak']}")

with st.expander("Kaip veikia prioritetas"):
    st.write(
        "Radaras pirmiausia vertina temos bazinį potencialą ir laiką iki fiksuotos piko datos. "
        "Piko data nėra perskaičiuojama slenkant kalendoriui. 0–7 dienų langas gauna didžiausią "
        "laiko prioritetą. Temos sąmoningai formuluojamos konkrečiai, o prie kiekvienos pateikiami "
        "realūs PDF, PPT, kortelių ar Bee-Bot produktų pavyzdžiai."
    )

st.caption("Protuoliuko paklausos radaras · V11 · nemokamas, be mokamų API")
