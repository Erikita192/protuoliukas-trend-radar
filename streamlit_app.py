"""PROTUOLIUKO GALIMYBIŲ CENTRAS V22 · Practical creator dashboard.

All 68 original topics / 200 detailed ideas / original events are retained.
No sales, GSC, GA4 or competitor demand metrics are fabricated.
"""
from __future__ import annotations

import csv
import io
import os
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

from radar import catalog as cat, school, signals as sg
from radar.crawler import CrawlConfig
from radar.opportunities import create_actions, promote_actions, improve_actions, filter_by_time
from radar.products import analyse_all
from radar.timing import EVENTS, fmt, fmt_range, today_vilnius, now_vilnius
from radar.topics import AGE_GROUPS, evaluate_all, load_topics
from radar.ui import esc, header, inject_css, product_card, render
from radar.weekly import upcoming_events

st.set_page_config(page_title="Protuoliuko galimybių centras · V22", page_icon="🎯", layout="wide")
inject_css(st)
st.markdown("""<style>
/* V22: papildomas lengvas, aiškus veiksmų dizainas */
.pf .act{border:1px solid #E6DFD3;border-radius:17px;padding:17px 19px;background:#fff;margin:10px 0;box-shadow:0 1px 2px rgba(20,50,40,.03)}
.pf .act-kind{font-size:.77rem;font-weight:800;letter-spacing:.06em;color:#2A6A59!important;text-transform:uppercase}
.pf .act h4{font-size:1.08rem;margin:7px 0 7px;font-weight:750;color:#203A31!important}
.pf .act .act-desc{font-size:.92rem;line-height:1.5;color:#273A32!important}
.pf .act .act-why{font-size:.85rem;margin-top:10px;color:#52665C!important;border-left:3px solid #A3C2AB;padding-left:10px}
.pf .act .act-foot{font-size:.78rem;color:#48675D!important;margin-top:10px}
.pf .act a{font-size:.88rem;color:#176A56!important}
.pf .soft{background:#F0F6EF;border-radius:16px;padding:14px 18px;margin:11px 0;color:#203A31!important}
.pf .library-item{border:1px solid #E6DFD3;background:#fff;border-radius:15px;padding:13px 17px;margin:9px 0}
.pf .library-item summary{font-size:1rem;font-weight:750;color:#1E4F42!important;cursor:pointer}
.pf .library-item .li-meta{color:#637168!important;font-size:.82rem;margin:6px 0}
.pf .idea-line{border-top:1px solid #EBE7DF;padding:11px 0;font-size:.88rem}
.pf .event-line{background:#fff;border:1px solid #E6DFD3;border-radius:14px;padding:12px 16px;margin:9px 0}
.pf .event-line b{font-size:1rem;color:#244C3F!important}
.pf .event-line p{font-size:.84rem;color:#51665D!important;margin:4px 0}
</style>""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parent
MARKET_FILE = Path(os.environ.get("PROTUOLIUKAS_DATA_DIR", str(ROOT / "data"))) / "market_signals.csv"

with st.sidebar.expander("🗓️ Planavimo data", expanded=False):
    simulate = st.checkbox("Peržiūrėti kitai datai", value=False, key="v22_sim_on")
    picked = st.date_input("Data", value=today_vilnius(), disabled=not simulate, key="v22_sim_date")
TODAY = picked if simulate else today_vilnius()


def _background_refresh():
    """Retain V21 safe resumable crawler; no direct Streamlit calls in thread."""
    try:
        for _ in range(6):
            old = cat.load_catalog()
            new, _, _ = cat.update_catalog(
                resume=bool(old.get("frontier")),
                cfg=CrawlConfig(time_budget_s=70, max_pages=900, workers=8),
            )
            if new.get("meta", {}).get("complete") or not new.get("frontier"):
                break
    except Exception:
        pass


def start_refresh_once():
    if os.environ.get("PROTUOLIUKAS_DISABLE_BG") == "1":
        return
    if not st.session_state.get("v22_catalog_running_started"):
        st.session_state["v22_catalog_running_started"] = True
        st.session_state["v22_refresh_started"] = now_vilnius().isoformat(timespec="minutes")
        threading.Thread(target=_background_refresh, daemon=True, name="protuoliukas-v22-catalog").start()


start_refresh_once()

catalog = cat.load_catalog()
signals = sg.load_signals()
TOPICS = evaluate_all(TODAY)
ALL_TOPICS = load_topics()


@st.cache_resource(show_spinner=False)
def _products(catalog_marker: str, today_str: str, signal_marker: str):
    return analyse_all(cat.active_products(cat.load_catalog()), date.fromisoformat(today_str), sg.load_signals())


# Hash only the small import CSV; don't mistakenly reuse analysis when signal values
# change but the number of rows stays the same.
import hashlib
sig_hash = hashlib.sha256(repr(sorted((k, tuple(sorted(v.items()))) for k,v in signals.items())).encode("utf-8")).hexdigest()[:16]
ANALYSED = _products(cat.catalog_stamp(catalog), TODAY.isoformat(), sig_hash)
n_products = len(cat.active_products(catalog))

if callable(getattr(st, "fragment", None)):
    @st.fragment(run_every="20s")
    def watch_catalog():
        fresh = cat.load_catalog()
        stamp = cat.catalog_stamp(fresh)
        previous = st.session_state.setdefault("v22_catalog_stamp", cat.catalog_stamp(catalog))
        if stamp != previous:
            st.session_state["v22_catalog_stamp"] = stamp
            st.cache_resource.clear()
            st.rerun()
    watch_catalog()


def do_refresh(resume: bool = False):
    with st.spinner("Tikrinamas asortimentas…"):
        fresh, message, level = cat.update_catalog(
            resume=resume, cfg=CrawlConfig(time_budget_s=80, max_pages=1200, workers=8))
    st.session_state["v22_status"] = (level, message)
    st.cache_resource.clear()
    st.rerun()


def action_html(a) -> str:
    ico = {"kurti": "✳", "reklamuoti": "↗", "pagerinti": "↻"}.get(a.kind, "•")
    link = f'<div class="act-foot"><a href="{esc(a.url)}" target="_blank" rel="noopener noreferrer">Atidaryti produktą ↗</a></div>' if a.url.startswith(("https://", "http://")) else ""
    due = f" · {esc(a.deadline)}" if a.deadline else ""
    effort = f" · {esc(a.effort)}" if a.effort else ""
    return (f'<div class="act"><div class="act-kind">{ico} {esc(a.kind)} · {esc(a.label)}</div>'
            f'<h4>{esc(a.title)}</h4><div class="act-desc">{esc(a.detail)}</div>'
            f'<div class="act-why"><strong>Kodėl:</strong> {esc(a.reason)}</div>'
            f'<div class="act-foot">{esc(a.evidence)}{due}{effort}</div>{link}</div>')


def show_actions(actions: list, empty_msg: str, max_items: int = 4):
    if not actions:
        st.info(empty_msg)
        return
    for a in actions[:max_items]:
        render(st, action_html(a))


def _market_rows():
    if not MARKET_FILE.exists():
        return []
    try:
        with MARKET_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)][:300]
    except (UnicodeError, OSError, csv.Error):
        return []


def signal_count():
    return len(signals)


render(st, header("GALIMYBIŲ CENTRAS · V22 · ką kurti, reklamuoti ir patobulinti"))
st.markdown("### Ką verta daryti dabar?")
st.caption("Sprendimų ekranas: kelios konkrečios galimybės. Visa V21 temų ir progų bazė išsaugota atskiruose skirtukuose.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Idėjų bibliotekoje", f"{len(ALL_TOPICS)} temos · {sum(len(t.ideas) for t in ALL_TOPICS)} idėjų")
m2.metric("Metinių progų", len(EVENTS))
m3.metric("Parduotuvės produktų", n_products if n_products else "Tikrinama…")
m4.metric("Importuotų signalo įrašų", signal_count())

if not signals:
    st.info("**Kol kas neturime pardavimų ir paieškos statistikos.** Rekomendacijos šiuo metu paremtos kalendoriumi, konkrečiomis idėjomis ir, jei nuskaityta, parduotuvės katalogu. Jos nėra išmatuotos paklausos prognozė. Duomenų CSV galima įkelti skirtuke „Duomenys“.")

# If a catalog product matches a topic, warn rather than silently promoting
# near-duplicates; create-side business decisions need a crosscheck.
occupied = {tp.id for p,pr in ANALYSED for tp, strength, via in p.get("matches", []) if strength >= 3}
CREATIONS = create_actions(TODAY, TOPICS, limit=35, occupied_topics=occupied)
PROMOTIONS = promote_actions(TODAY, ANALYSED, signals, limit=16)
IMPROVEMENTS = improve_actions(TODAY, ANALYSED, signals, limit=16)

TABS = st.tabs(["🎯 GALIMYBĖS", "💡 IDĖJŲ BIBLIOTEKA", "📆 PROGŲ KALENDORIUS",
                "🛍️ MANO PRODUKTAI", "🔎 RINKOS RADINIAI", "⚙️ DUOMENYS"])

with TABS[0]:
    st.markdown("#### Šios savaitės sprendimai")
    ch1, ch2 = st.columns([1,1])
    slot = ch1.selectbox("Kiek laiko turi kūrimui?", ["Visos galimybės", "Iki 2 val.", "Iki 5 val.", "1–2 darbo dienos"], key="v22_time_filter")
    focus = ch2.selectbox("Kokio veiksmo ieškai?", ["Visi veiksmai", "Kurti naują", "Reklamuoti turimą", "Patobulinti"], key="v22_action_filter")
    hour_limit = {"Visos galimybės": 100, "Iki 2 val.": 2, "Iki 5 val.": 5, "1–2 darbo dienos": 16}[slot]
    create_filtered = filter_by_time(CREATIONS, hour_limit)

    def section(title: str, kind: str, rows: list, empty: str, cap: int):
        if focus != "Visi veiksmai" and {"kurti":"Kurti naują","reklamuoti":"Reklamuoti turimą","pagerinti":"Patobulinti"}[kind] != focus:
            return
        st.markdown(f"##### {title}")
        show_actions(rows, empty, cap)

    section("✳ Ką sukurti", "kurti", create_filtered,
            "Šiam pasirinktam laikui tinkamų idėjų kol kas nerasta. Bibliotekoje gali pasirinkti kitą temą.", 4)
    section("↗ Ką reklamuoti", "reklamuoti", PROMOTIONS,
            "Kol nėra tinkamų nuskaitytų produktų, negaliu parinkti konkretaus produkto reklamai. Katalogas tikrinamas automatiškai; prireikus gali paleisti rankiniu būdu skirtuke „Mano produktai“.", 3)
    section("↻ Ką verta patobulinti", "pagerinti", IMPROVEMENTS,
            "Kol nėra konkrečių rodiklių (pvz., dideli parodymai, mažai paspaudimų), produkto silpnos vietos neišgalvoju. Importuok GSC / pardavimo rezultatus, tada atsiras pagrįsti tobulinimo pasiūlymai.", 3)

    with st.expander("📆 Artimiausios progos – kad nepraleisčiau laiko"):
        nearest = upcoming_events(TODAY, 40)[:10]
        if nearest:
            for r in nearest:
                t, ev = r["t"], r["ev"]
                render(st, f'<div class="event-line"><b>{esc(ev.name)}</b><p>Proga: {esc(fmt_range(t.start,t.end,TODAY))} · liko {r["days"]} d. · rekomenduojamas publikavimas: {esc(fmt_range(t.pub_start,t.pub_end,TODAY))}</p></div>')
        else:
            st.write("Artimiausių datų nerasta.")
    st.caption("Jokių privalomų darbų sąrašų ar rankinio statusų žymėjimo. Jei realių signalų nėra, sistema taip ir sako.")

with TABS[1]:
    st.markdown("### Idėjų biblioteka")
    st.caption("Visos istorinės idėjos išsaugotos. Praėjusi data jų neištrina – čia gali ieškoti įkvėpimo bet kuriuo metu.")
    u1, u2 = st.columns(2)
    search = u1.text_input("Paieška pagal temą, veiklą ar užduotį", key="v22_library_query")
    areas = sorted({t.area for t in ALL_TOPICS})
    area = u2.selectbox("Ugdymo sritis", ["Visos sritys"] + areas, key="v22_library_area")
    v1, v2, v3 = st.columns(3)
    age = v1.selectbox("Amžiaus grupė", ["Visos amžiaus grupės"] + AGE_GROUPS, key="v22_library_age")
    fmt_sel = v2.selectbox("Formatas", ["Visi formatai"] + sorted({f for t in ALL_TOPICS for f in t.formats}), key="v22_library_format")
    season = v3.selectbox("Laikotarpis", ["Visi laikotarpiai", "Šventė / proga", "Sezono / ugdymo langas", "Tęstinė"], key="v22_library_season")
    picked_topics = []
    for t in ALL_TOPICS:
        if area != "Visos sritys" and t.area != area: continue
        if age != "Visos amžiaus grupės" and age not in t.age_groups: continue
        if fmt_sel != "Visi formatai" and fmt_sel not in t.formats: continue
        if season != "Visi laikotarpiai" and t.seasonality != season: continue
        if search and search.casefold() not in (t.name + " " + t.pain + " " + " ".join(i.title + " " + i.desc for i in t.ideas)).casefold():
            continue
        picked_topics.append(t)
    picked_topics.sort(key=lambda t: (t.area, t.name))
    n_ideas = sum(len(t.ideas) for t in picked_topics)
    st.markdown(f"**Rasta {len(picked_topics)} temų ir {n_ideas} konkrečių idėjų.**")
    limit = st.session_state.get("v22_library_limit", 24)
    for tp in picked_topics[:limit]:
        ti = next((r for r in TOPICS if r.topic.id == tp.id), None)
        timing_text = (
            "Tęstinė tema – jokios dirbtinės piko datos" if tp.timing.get("type") == "evergreen" else
            f"Kitas numatomas laikotarpis: {fmt_range(ti.timing.start, ti.timing.end, TODAY) if ti else '—'}. Tai orientyras, ne visuotinė mokymo programa."
        )
        ideas_html = "".join(
            f'<div class="idea-line"><strong>{esc(i.title)}</strong><div>{esc(i.desc)}</div>'
            f'<div class="li-meta">{esc(i.skill)} · {esc(i.effort)}</div></div>' for i in tp.ideas)
        render(st, f'<details class="library-item"><summary>{esc(tp.name)} · {len(tp.ideas)} id.</summary>'
               f'<div class="li-meta">{esc(tp.area)} · {esc(tp.ages)} · {esc(", ".join(tp.formats))}</div>'
               f'<div class="li-meta">{esc(timing_text)}</div>{ideas_html}</details>')
    if len(picked_topics) > limit and st.button(f"Rodyti dar {min(24,len(picked_topics)-limit)} temų", key="v22_library_more"):
        st.session_state["v22_library_limit"] = limit + 24
        st.rerun()

with TABS[2]:
    st.markdown("### Progų ir mokyklos kalendorius")
    st.caption("Visos datos išlaikytos; galima peržiūrėti ir praėjusius, ir būsimus mėnesius. Apytikslės datos pažymėtos.")
    MONTHS = ["Sausis", "Vasaris", "Kovas", "Balandis", "Gegužė", "Birželis", "Liepa", "Rugpjūtis", "Rugsėjis", "Spalis", "Lapkritis", "Gruodis"]
    c_y, c_m = st.columns(2)
    year = c_y.selectbox("Metai", list(range(TODAY.year-1, TODAY.year+4)), index=1, key="v22_cal_year")
    month = c_m.selectbox("Mėnuo", ["Visi mėnesiai"] + MONTHS, index=TODAY.month, key="v22_cal_month")
    eq = st.text_input("Ieškoti progos", key="v22_event_search")
    dates = []
    for ev in EVENTS.values():
        try:
            s,e = ev.rule(year)
        except (ValueError, TypeError):
            continue
        if month != "Visi mėnesiai" and s.month != MONTHS.index(month) + 1:
            continue
        if eq and eq.casefold() not in ev.name.casefold():
            continue
        use = school.classroom_date(s)
        pub_start = use - timedelta(days=ev.lead)
        pub_end = use - timedelta(days=ev.gap)
        dates.append((s,e,ev,use,pub_start,pub_end))
    dates.sort(key=lambda x: (x[0],x[2].name))
    st.markdown(f"**Rodoma {len(dates)} progų iš {len(EVENTS)} kalendoriuje.**")
    for s,e,ev,use,pub_s,pub_e in dates:
        ap = " · data apytikslė, prieš kampaniją patikrinti" if ev.approx else ""
        notes = f"<p>{esc(ev.note)}</p>" if ev.note else ""
        render(st, f'<div class="event-line"><b>{esc(ev.name)}</b>'
               f'<p>🗓️ {esc(fmt_range(s,e,TODAY))}{esc(ap)}</p>'
               f'<p>🚀 Siūlomas pasiruošimas ir publikavimas: {esc(fmt_range(pub_s,pub_e,TODAY))}</p>'
               f'{notes}</div>')
    with st.expander("🏫 Mokyklos kalendorius ir ugdymo ritmas"):
        st.caption("Mokslo metų pradžia, pertraukos, paskutinės mokymosi dienos ir kiti planavimo taškai, ne vien atostogos.")
        for x in school.timeline(TODAY):
            render(st, f'<div class="event-line"><b>{esc(x["name"])}</b><p>{esc(fmt(x["date"],TODAY))} · {esc(x["detail"])}</p></div>')
        for source in school.summary(TODAY).get("sources", []):
            if str(source.get("url", "")).startswith("https://"):
                st.markdown(f"[{source['name']}]({source['url']})")

with TABS[3]:
    st.markdown("### Mano produktai")
    st.caption("Automatiškai tikrinamas realus parduotuvės katalogas. Rekomendacijų prioritetai pagal datas yra orientyras; be pardavimo statistikos tai nėra patvirtinta paklausa.")
    meta = catalog.get("meta", {})
    st.write(f"**Aktyvių produktų:** {n_products}. **Paskutinis patikrinimas:** {meta.get('last_checked') or 'Dar neatliktas'}. **Užbaigtas nuskaitymas:** {'taip' if meta.get('complete') else 'ne / dar vyksta'}.")
    stat = st.session_state.pop("v22_status", None)
    if stat:
        getattr(st, {"ok":"success", "warn":"warning", "error":"error"}.get(stat[0], "info"))(stat[1])
    c1,c2=st.columns(2)
    if c1.button("🔄 Patikrinti katalogą dabar", key="v22_shop_refresh"):
        do_refresh()
    if catalog.get("frontier") and c2.button("▶ Tęsti dalinį nuskaitymą", key="v22_shop_resume"):
        do_refresh(resume=True)
    if not n_products:
        st.info("Dar neturime katalogo. Tikrinimas vyksta fone – tai gali užtrukti, ypač pirmą kartą. Katalogas atnaujinamas neperrašant ankstesnių gerų duomenų.")
    elif not meta.get("complete"):
        st.warning("Nuskaitymas dalinis; iki jo pabaigos produktų skaičius ir rekomendacijos gali būti nepilni.")
    c1,c2,c3=st.columns(3)
    query_p=c1.text_input("Ieškoti produkto ar kodo", key="v22_shop_search")
    status_p=c2.selectbox("Reklamos periodas", ["Visi", "Dabar", "Ruošti", "Vėliau"], key="v22_shop_status")
    region_p=c3.selectbox("Rodyti", ["20 produktų", "50 produktų", "100 produktų"], key="v22_shop_limit")
    num = int(region_p.split()[0])
    shown=[]
    for p,pr in ANALYSED:
        if query_p and query_p.casefold() not in (str(p.get("title") or "")+" "+str(p.get("code") or "")).casefold(): continue
        if status_p == "Dabar" and pr.get("hint") not in ("LAST", "NOW", "RISE"): continue
        if status_p == "Ruošti" and pr.get("hint") != "PREP": continue
        if status_p == "Vėliau" and pr.get("hint") != "OFF": continue
        shown.append((p,pr))
    st.caption(f"Pagal filtrą: {len(shown)} produktų. Balai – redakciniai, ne realūs pardavimai.")
    for p,pr in shown[:num]:
        render(st, product_card(p,pr,TODAY))

with TABS[4]:
    st.markdown("### Rinkos radiniai")
    st.caption("Vieta tikriems, patikrintiems konkurentų radiniams, o ne automatiškai išgalvotoms tendencijoms. Nuorodą ir šaltinį galima įkelti CSV formatu skirtuke „Duomenys“.")
    market = _market_rows()
    if not market:
        st.info("Rinkos radinių dar neimportuota. Šis skirtukas pats netvirtina, kad konkurentų prekės populiarios – tam reikia šaltinio ir datos.")
    else:
        st.caption(f"Įkelta {len(market)} radinių (nepriklausoma nuo idėjų banko).")
        for r in sorted(market,key=lambda x:x.get("observed_at", ""),reverse=True):
            url = (r.get("url") or "").strip()
            link = f'<p><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Atidaryti šaltinį ↗</a></p>' if url.startswith(("https://","http://")) else ""
            render(st, f'<div class="event-line"><b>{esc(r.get("title") or "Radinys")}</b>'
                   f'<p>Šaltinis: {esc(r.get("source") or "nenurodytas")} · data: {esc(r.get("observed_at") or "nenurodyta")}</p>'
                   f'<p>{esc(r.get("note") or "")}</p>{link}</div>')

with TABS[5]:
    st.markdown("### Duomenys ir importas")
    st.caption("Duomenys nėra automatiškai prijungti prie GSC, GA4, pardavimų ar konkurentų. Čia gali importuoti savo skaičius; be jų programa nenaudoja tariamų paklausos rodiklių.")
    st.markdown("#### Pardavimų, Google Search Console ir peržiūrų CSV")
    st.caption("Privalomas stulpelis: `code` (pvz., P213) arba `url`. Visi kiti neprivalomi. Skirtingų šaltinių eilutes iš anksto sujunk pagal produkto kodą / URL.")
    template = "code,url,organic_clicks_7d,organic_clicks_prev_7d,views_7d,views_prev_7d,sales_30d,revenue_30d,impressions_28d,clicks_28d,views_30d,last_promoted,promoted_channel\n"
    st.download_button("⬇️ CSV šablonas", data=template.encode("utf-8-sig"), file_name="protuoliukas_signalu_sablonas.csv", mime="text/csv", key="v22_template")
    upload = st.file_uploader("Įkelti CSV su realiais produkto rodikliais", type=["csv"], key="v22_signal_upload")
    if upload is not None:
        try:
            text = upload.getvalue().decode("utf-8-sig")
            parsed = sg.parse_signals(text)
            if not parsed:
                st.error("CSV nėra tinkamų eilučių su `code` arba `url`.")
            else:
                st.info(f"Atpažinta {len(parsed)} produktų eilučių. Patvirtink importą žemiau.")
                if st.button("Importuoti rodiklius",key="v22_import_signals"):
                    sg.save_signals_text(text)
                    st.cache_resource.clear()
                    st.rerun()
        except (UnicodeError, csv.Error, OSError, AttributeError) as ex:
            st.error(f"Nepavyko perskaityti CSV: {ex}")
    st.write(f"Šiuo metu importuoti duomenys apie **{len(signals)} produktų**.")
    if sg.SIGNALS_PATH.exists():
        st.download_button("⬇️ Išsaugoto CSV kopija", data=sg.SIGNALS_PATH.read_bytes(), file_name="protuoliukas_signalai.csv", mime="text/csv", key="v22_signal_backup")

    st.markdown("#### Konkurentų / rinkos radinių CSV")
    st.caption("Stulpeliai: `title,source,url,observed_at,note`. Tai stebėjimų registras, ne automatiškai patvirtintas pardavimų populiarumas.")
    mt = "title,source,url,observed_at,note\n"
    st.download_button("⬇️ Rinkos radinių šablonas", mt.encode("utf-8-sig"), file_name="rinkos_radiniu_sablonas.csv", mime="text/csv", key="v22_market_template")
    market_upload = st.file_uploader("Įkelti rinkos radinių CSV", type=["csv"], key="v22_market_upload")
    if market_upload is not None:
        try:
            raw = market_upload.getvalue()
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            if not rows or not {"title", "source", "url", "observed_at", "note"}.issubset(rows[0].keys()):
                st.error("CSV privalo turėti `title,source,url,observed_at,note` stulpelius.")
            else:
                st.caption(f"Atpažinta {len(rows)} rinkos įrašų.")
                if st.button("Importuoti rinkos radinius", key="v22_import_market"):
                    MARKET_FILE.parent.mkdir(parents=True, exist_ok=True)
                    MARKET_FILE.write_bytes(raw)
                    st.rerun()
        except (UnicodeError, csv.Error, OSError, AttributeError) as ex:
            st.error(f"Nepavyko importuoti: {ex}")

    st.markdown("#### Duomenų patikimumas")
    st.info("Streamlit Cloud vietiniai failai po programos perkrovimo ar perkėlimo gali išnykti. Atsisiųsk importuotų CSV kopijas ir, jei nori, įkelk jas į GitHub repozitorijos `data/` aplanką (privačiai, jei rodikliai konfidencialūs). Viešoje GitHub repozitorijoje nepaskelbk jautrių pardavimo duomenų.")
    st.caption("Automatiškai tikrinamas tik viešas parduotuvės katalogas. GSC, GA4, pardavimų ir konkurentų signalai savaime neatsinaujina: juos reikia importuoti arba ateityje prijungti per autorizuotą API.")
