"""PROTUOLIUKO PAKLAUSOS RADARAS · V17"""
from datetime import date, datetime, timedelta
import json
import threading

import streamlit as st

from radar import catalog as cat
from radar import school, signals as sg
from radar.crawler import CrawlConfig, parse_page, make_session
from radar.products import analyse_all
from radar.timing import fmt, fmt_range, now_vilnius, today_vilnius, EVENTS
from radar.topics import AGE_GROUPS, evaluate_all, load_topics
from radar.ui import (esc, header, inject_css, mini_row, product_card, render, topic_card, left_text, PHASE_CLASS)
from radar.weekly import upcoming_events, weekly

st.set_page_config(page_title="Protuoliuko paklausos radaras", page_icon="📡", layout="wide")
inject_css(st)

# ------------------------------------------------------------------ data
catalog = cat.load_catalog()
sig = sg.load_signals()

with st.expander("🗓️ Planavimo data (neprivaloma)"):
    use_sim = st.checkbox("Peržiūrėti radarą kitai datai", value=False)
    sim = st.date_input("Data", value=today_vilnius(), disabled=not use_sim)
TODAY = sim if use_sim else today_vilnius()


@st.cache_resource(show_spinner=False)
def _analysed(stamp: str, today_iso: str, sig_stamp: str):
    return analyse_all(cat.active_products(cat.load_catalog()), date.fromisoformat(today_iso), sg.load_signals())


TOPICS = evaluate_all(TODAY)
ANALYSED = _analysed(cat.catalog_stamp(catalog), TODAY.isoformat(), sg.signal_stamp(sig))
SC = school.summary(TODAY)

meta = catalog["meta"]
last_checked = meta.get("last_checked")
n_active = len(cat.active_products(catalog))
render(st, header("Paklausos radaras · V18 · ką kurti, ką reklamuoti ir ką publikuoti"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Naujų idėjų temų", len(TOPICS))
c2.metric("Aktyvių produktų", n_active if n_active else "—")
c3.metric("Reklamuoti dabar", sum(1 for _, p in ANALYSED if p["hint"] in ("NOW", "LAST")))
c4.metric("Artimiausia pertrauka", (f"po {SC['days_to_break']} d." if SC.get("next_break") else "—"))
if SC.get("next_break"):
    nb = SC["next_break"]
    st.caption(f"{nb[0]}: {fmt_range(nb[1], nb[2], TODAY)} · paskutinė mokymosi diena prieš ją: {fmt(SC.get('last_school_day'), TODAY)} "
               f"(ŠMSM kalendorius, patikrinta {SC.get('verified')}). Šventinė medžiaga klasėje realiai naudojama iki šios dienos.")
if not SC.get("calendar"):
    st.warning("Šiems mokslo metams oficialaus kalendoriaus faile nėra – progų datos koreguojamos tik pagal savaitgalius. Papildyk data/school_calendar.json.")

tabs = st.tabs(["📋 ŠIĄ SAVAITĘ", "🆕 NAUJOS IDĖJOS", "📆 PROGOS", "🛍️ ESAMI PRODUKTAI", "📣 14 D. FB PLANAS", "⚙️ DUOMENYS"])


# ------------------------------------------------------------------ helpers
def run_update(resume=False):
    bar = st.progress(0.0, text="Pradedama…")
    box = st.empty()

    def cb(s):
        total = max(1, s["fetched"] + s["queued"])
        bar.progress(min(0.99, s["fetched"] / total), text=f"Perskaityta {s['fetched']} puslapių · rasta produktų {s['products']} · eilėje {s['queued']}")
    new, msg, lvl = cat.update_catalog(progress=cb, resume=resume)
    bar.empty()
    st.session_state["update_msg"] = (msg, lvl)
    st.session_state["_scanned"] = True
    st.cache_resource.clear()
    st.rerun()


def _background_catalog_update():
    # Kiekviena nauja vartotojo sesija inicijuoja realaus katalogo patikrą.
    # Sena gera kopija lieka rodoma, kol atnaujinimas vyksta fone.
    try:
        cat.update_catalog()
    except Exception:
        pass


def ensure_background_refresh():
    if not st.session_state.get("_catalog_refresh_started"):
        st.session_state["_catalog_refresh_started"] = True
        st.session_state["_catalog_refresh_started_at"] = now_vilnius().isoformat(timespec="minutes")
        threading.Thread(target=_background_catalog_update, daemon=True, name="protuoliukas-catalog-refresh").start()


ensure_background_refresh()


def product_mini(z):
    p, pr = z
    code = f"{p['code']} · " if p.get("code") else ""
    return mini_row(pr["score"], code + p["title"], f"{pr['status']} · {pr['why'][:110]}", p["url"])


# ------------------------------------------------------------------ ŠIĄ SAVAITĘ
with tabs[0]:
    W = weekly(TODAY, TOPICS, ANALYSED)
    ev7 = upcoming_events(TODAY, 7)
    create_rows = sorted(W["create"], key=lambda r: (not r.quick_ok, -r.score))[:15]
    product_actions = len({(z[0].get("key") or z[0].get("url")) for z in (W["facebook"] + W["home"] + W["stories"] + W["last"])})
    total_actions = len(create_rows) + len(ev7) + product_actions
    st.markdown("### Šią savaitę")
    st.caption("Bendras veiksmų centras: ką kurti + kokios progos artėja + ką iš esamų produktų reklamuoti. Esamų produktų katalogas kiekvienoje naujoje sesijoje atsinaujina fone.")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("🆕 Kurti / ruošti", len(create_rows))
    c2.metric("📆 Progos per 7 d.", len(ev7))
    c3.metric("🛍️ Esamų produktų veiksmai", product_actions if ANALYSED else "atnaujinama…")
    c4.metric("🎯 Veiksmų iš viso", total_actions if ANALYSED else len(create_rows)+len(ev7))

    with st.expander(f"🆕 Naujos priemonės, kurias verta kurti · {len(create_rows)}", expanded=True):
        st.caption("Temos, kurias pagal laiką dar realu spėti. Pirmiausia rodomos greitos ir aukšto prioriteto idėjos.")
        render(st, "".join(mini_row(r.score, r.topic.name, f"{r.ideas[0].idea.title if r.ideas else ''} · publikuoti {fmt_range(r.timing.pub_start, r.timing.pub_end, TODAY)} · {r.feas_msg}") for r in create_rows) or "Nėra.")

    with st.expander(f"📆 Artėjančios progos per 7 d. · {len(ev7)}", expanded=bool(ev7)):
        if ev7:
            render(st, "".join(mini_row(max(1,100-min(70,x['days']*5)), x['ev'].name, f"{fmt_range(x['t'].start,x['t'].end,TODAY)} · po {x['days']} d. · publikuoti {fmt_range(x['t'].pub_start,x['t'].pub_end,TODAY)}") for x in ev7))
        else: st.write("Per artimiausias 7 dienas kalendoriuje nėra įtrauktų progų.")

    if not ANALYSED:
        st.info("🛍️ Esamų produktų katalogas šiuo metu atnaujinamas fone. Naujų idėjų ir progų rekomendacijos nuo jo nepriklauso.")
    else:
        blocks = [
            ("📘 Facebook", W["facebook"], "Esami produktai, kuriuos verta rodyti Facebook šią savaitę."),
            ("🏠 Pagrindinis puslapis", W["home"], "Esami produktai, kuriuos verta iškelti pagrindiniame puslapyje."),
            ("📱 Stories", W["stories"], "Esami produktai su aiškiu Stories kampu."),
            ("⚡ Paskutinė proga", W["last"], "Produktai, kurių reklamos langas baigiasi."),
        ]
        for lbl,items,hint in blocks:
            with st.expander(f"{lbl} · {len(items)}"):
                st.caption(hint)
                render(st, "".join(product_mini(z) for z in items) or "Šiuo metu nėra.")

    with st.expander(f"🚫 Ko dabar geriau NEDARYTI · {len(W['avoid_new']) + len(W['stop_now'])}"):
        render(st, "".join(mini_row(r.score, "Nekurti naujos: " + r.topic.name, r.feas_msg) for r in W["avoid_new"]) +
               "".join(mini_row(z[1]["score"], "Nebereklamuoti: " + z[0]["title"], z[1]["why"], z[0]["url"]) for z in W["stop_now"]) or "Nieko.")

# ------------------------------------------------------------------ NAUJOS IDĖJOS
with tabs[1]:
    topics_all = load_topics()
    with st.expander("Filtrai"):
        a, b = st.columns(2)
        areas = a.multiselect("Kategorija", sorted({t.area for t in topics_all}))
        ages = b.multiselect("Amžiaus grupė", AGE_GROUPS)
        a, b = st.columns(2)
        fmts = a.multiselect("Formatas", sorted({f for t in topics_all for f in t.formats}))
        seas = b.multiselect("Sezoniškumas", ["Šventė / proga", "Sezono / ugdymo langas", "Tęstinė"])
        a, b, c = st.columns(3)
        only_ok = a.checkbox("Tik realu spėti", value=False)
        mins = b.slider("Min. galimybių balas", 0, 100, 0)
        q = c.text_input("Paieška (tema, idėja)")
    st.caption("Galimybių balas = planavimo heuristika (potencialas × laikas × ar spėsi). Tai NĖRA išmatuota Google paklausa.")
    view = st.radio("Laikotarpis", ["🔥 DABAR", "📅 NETRUKUS", "🔭 ARTĖJA", "🗓️ 30 DIENŲ", "💡 VISAS BANKAS"], horizontal=True, label_visibility="collapsed")

    def pass_f(r):
        t = r.topic
        if areas and t.area not in areas: return False
        if ages and not set(ages) & set(t.age_groups): return False
        if fmts and not set(fmts) & set(t.formats): return False
        if seas and t.seasonality not in seas: return False
        if only_ok and r.feas == "LATE": return False
        if r.score < mins: return False
        if q:
            blob = (t.name + " " + " ".join(i.title + " " + i.desc for i in t.ideas)).lower()
            if q.lower() not in blob: return False
        return True

    F = [r for r in TOPICS if pass_f(r)]
    by = lambda bk: [r for r in F if r.bucket == bk]
    if view.startswith("🔥"):
        now_ = by("NOW")
        st.markdown(f"### Kurti ir publikuoti dabar · {len(now_)}")
        for r in now_: render(st, topic_card(r, TODAY, True))
        eg = by("EVERGREEN")[:12]
        st.markdown(f"### 📚 Tęstinės temos (be konkretaus piko) · rodoma {len(eg)} iš {len(by('EVERGREEN'))}")
        st.caption("Jų aktualumą lemia klasė ir ugdymo eiga, todėl konkrečios datos nerodomos.")
        for r in eg: render(st, topic_card(r, TODAY))
    elif view.startswith("📅"):
        rows = sorted(by("SOON"), key=lambda r: r.timing.pub_start)
        st.markdown(f"### Publikavimo langas prasideda per ≤14 d. · {len(rows)}")
        for r in rows: render(st, topic_card(r, TODAY))
    elif view.startswith("🔭"):
        rows = sorted(by("UPCOMING"), key=lambda r: r.timing.pub_start)
        st.markdown(f"### Publikavimo langas prasideda po 15–60 d. · {len(rows)}")
        for r in rows: render(st, topic_card(r, TODAY))
    elif view.startswith("🗓️"):
        st.markdown("### Kas publikuotina per artimiausias 4 savaites")
        st.caption("Pagal realius idealaus publikavimo langus, ne pagal reitingo eilę.")
        dated = [r for r in F if r.timing.pub_start]
        for w in range(5):
            a0 = TODAY + timedelta(days=7 * w); a1 = a0 + timedelta(days=6)
            rows = [r for r in dated if r.timing.pub_start <= a1 and (r.timing.pub_end or r.timing.end) >= a0 and r.feas != "LATE"]
            rows.sort(key=lambda r: -r.score)
            render(st, f'<div class="week">{a0.strftime("%m-%d")} – {a1.strftime("%m-%d")} · {len(rows)} temų</div>' +
                   ("".join(mini_row(r.score, r.topic.name, f"publikuoti {fmt_range(r.timing.pub_start, r.timing.pub_end, TODAY)} · {r.feas_msg}") for r in rows[:14]) or "<div class='meta'>Nėra datomis pagrįstų temų.</div>"))
    else:
        st.markdown(f"### Visas bankas · {len(F)} temų · {sum(len(r.ideas) for r in F)} konkrečių priemonių")
        for r in F: render(st, topic_card(r, TODAY))

# ------------------------------------------------------------------ PROGOS
with tabs[2]:
    hz = st.radio("Horizontas", [7, 14, 30, 60, 120], index=3, horizontal=True, format_func=lambda x: f"per {x} d.")
    ups = [u for u in upcoming_events(TODAY, 400) if u["days"] <= hz]
    st.markdown(f"### Artėjančios progos · {len(ups)}")
    st.caption("Atskirta PROGOS DATA, NAUDOJIMO KLASĖJE DATA (pagal mokyklų atostogas) ir REKOMENDUOJAMAS PUBLIKAVIMAS.")
    for u in ups:
        t, ev = u["t"], u["ev"]
        pill = f'<span class="pill {PHASE_CLASS.get(t.phase,"")}">{esc(t.phase.replace("_"," "))}</span>'
        facts = [("🗓️ Proga", fmt_range(t.start, t.end, TODAY) + (" (apytiksliai)" if ev.approx else "")), ("⏳ Liko", f"{u['days']} d."),
                 ("🏫 Naudojama klasėje iki", fmt(t.use_by, TODAY)), ("🚀 Publikuoti", fmt_range(t.pub_start, t.pub_end, TODAY))]
        render(st, f'<div class="card"><div class="title">{esc(ev.name)}</div><div class="pills">{pill}</div>'
                   f'<div class="facts">{"".join(f"<div><em>{esc(k)}</em>{esc(v)}</div>" for k, v in facts)}</div>'
                   f'<div class="note">{esc(t.note)}</div></div>')
    st.markdown("### Mokyklos kalendorius")
    for name, s, e, yk in school.breaks():
        if e >= TODAY - timedelta(days=30):
            render(st, f'<div class="mini"><span class="n">{s.strftime("%m-%d")}</span><div>{esc(name)} · {fmt_range(s, e, TODAY)}<div class="meta">{esc(yk)} m. m. · ŠMSM</div></div></div>')
    for s_ in SC.get("sources", []):
        st.markdown(f"[{s_['name']}]({s_['url']})")

# ------------------------------------------------------------------ ESAMI PRODUKTAI
with tabs[3]:
    st.markdown("### Esami produktai")
    st.caption("Tik realiai parduotuvėje rasti produktai. Čia nekuriamos naujos idėjos – tik sprendimas, ką reklamuoti.")
    if not catalog["products"]:
        st.info("Katalogo dar nėra. Automatinis pirmas nuskaitymas jau paleistas fone; po kelių minučių perkrauk puslapį. Rankinį mygtuką gali naudoti, jei nori palaukti atnaujinimo šiame lange.")
    else:
        st.caption(f"🔄 Automatinis asortimento patikrinimas fone paleistas šios sesijos pradžioje: {st.session_state.get('_catalog_refresh_started_at','—')}. Kol jis vyksta, rodomas paskutinis geras katalogas.")
    a, b, c = st.columns([1.2, 1.2, 2])
    if a.button("🔄 ATNAUJINTI ASORTIMENTĄ", use_container_width=True):
        run_update()
    if catalog.get("frontier") and b.button("▶ Tęsti nuskaitymą", use_container_width=True):
        run_update(resume=True)
    m = st.session_state.pop("update_msg", None)
    if m:
        {"ok": st.success, "warn": st.warning, "error": st.error}[m[1]](m[0])
    if last_checked:
        lc = datetime.fromisoformat(last_checked).strftime("%Y-%m-%d %H:%M")
        c.markdown(f"**Paskutinį kartą asortimentas patikrintas:** {lc}  \n**Rasta aktyvių produktų:** {n_active}")
        if cat.is_stale(catalog):
            st.warning(f"Asortimentas senesnis nei {int(cat.STALE_HOURS)} val. – verta atnaujinti.")
        if not meta.get("complete", True):
            st.warning("Paskutinis nuskaitymas buvo nepilnas – sąrašas gali būti neišsamus.")
    if ANALYSED:
        with st.expander("Filtrai", expanded=True):
            all_cats = sorted({c_ for p, _ in ANALYSED for c_ in (p.get("all_categories") or [])})
            r1 = st.columns(3)
            f_cat = r1[0].multiselect("Kategorija", all_cats)
            f_age = r1[1].multiselect("Amžius", AGE_GROUPS)
            f_topic = r1[2].multiselect("Tema", sorted({n for p, _ in ANALYSED for n in p["topic_names"]}))
            r2 = st.columns(3)
            f_fmt = r2[0].multiselect("Formatas", sorted({f for p, _ in ANALYSED for f in p["formats"]}))
            f_seas = r2[1].multiselect("Sezoniškumas", ["Šventė / proga", "Sezono / ugdymo langas", "Tęstinė"])
            f_stat = r2[2].multiselect("Reklamos būsena", ["⚡ PASKUTINĖ PROGA", "🔥 REKLAMUOTI DABAR", "↑ KYLA", "📅 RUOŠTI REKLAMĄ", "💤 DABAR NEAKTUALU"],
                                       default=["⚡ PASKUTINĖ PROGA", "🔥 REKLAMUOTI DABAR", "↑ KYLA", "📅 RUOŠTI REKLAMĄ"])
            r3 = st.columns(3)
            f_min = r3[0].slider("Min. reklamos balas", 0, 100, 0)
            f_q = r3[1].text_input("Paieška (pavadinimas / numeris)")
            f_end = r3[2].checkbox("Pikas baigiasi ≤10 d.")
        shown = []
        for p, pr in ANALYSED:
            if f_cat and not set(f_cat) & set(p.get("all_categories") or []): continue
            if f_age and not set(f_age) & set(p["age_groups"]): continue
            if f_topic and not set(f_topic) & set(p["topic_names"]): continue
            if f_fmt and not set(f_fmt) & set(p["formats"]): continue
            if f_seas and pr["seasonality"] not in f_seas: continue
            if f_stat and pr["status"] not in f_stat: continue
            if pr["score"] < f_min: continue
            if f_q and f_q.lower() not in (p["title"] + " " + p.get("code", "")).lower(): continue
            if f_end and not (pr["stop"] and pr["days_left"] is not None and 0 <= pr["days_left"] <= 10): continue
            shown.append((p, pr))
        st.markdown(f"#### Rodoma: {len(shown)} iš {len(ANALYSED)}")
        st.caption("Reklamos prioriteto balas – planavimo heuristika (data, tema, naujumas, signalai); jis nėra išmatuota paklausa ir nesimaišo su naujų idėjų balu.")
        lim = st.session_state.get("lim", 20)
        for p, pr in shown[:lim]:
            render(st, product_card(p, pr, TODAY))
        if len(shown) > lim and st.button(f"Rodyti daugiau ({len(shown) - lim})"):
            st.session_state["lim"] = lim + 30
            st.rerun()

# ------------------------------------------------------------------ 14 D. FB PLANAS
with tabs[4]:
    st.markdown("### 14 dienų Facebook planas")
    st.caption("Automatinis planas iš REALIŲ parduotuvės produktų. Tekstai – juodraščiai/redakciniai kampai, ne automatinis publikavimas.")
    if not ANALYSED:
        st.info("Pirmiausia nuskaityk parduotuvės asortimentą skirtuke „ESAMI PRODUKTAI“.")
    else:
        cand=[z for z in ANALYSED if z[1]["hint"] in ("LAST","NOW","RISE","PREP") and z[1]["score"]>=65]
        cand=sorted(cand,key=lambda z:-z[1]["score"])
        used=set(); plan=[]
        for day in range(14):
            # 5 įrašai per 7 d.; savaitgaliais paliekame laisviau
            d=TODAY+timedelta(days=day)
            if d.weekday() in (5,) or not cand: continue
            chosen=None
            for z in cand:
                key=z[0].get("key") or z[0].get("url")
                if key not in used:
                    chosen=z; used.add(key); break
            if not chosen: break
            p_,pr=chosen
            plan.append((d,p_,pr))
        for d,p_,pr in plan:
            code=(p_.get("code")+" · ") if p_.get("code") else ""
            with st.expander(f"{d.strftime('%m-%d')} · {code}{p_['title']} · {pr['score']}/100"):
                st.markdown(f"**Kodėl ši diena:** {pr['why']}")
                st.markdown(f"**Kampas:** {pr['angle']}")
                draft=(f"{pr['angle']}\n\nŠi priemonė gali padėti pedagogui temą paversti konkrečia vaikų veikla. "
                       f"Įraše parodyk ne vien viršelį – 2–3 vidinius pavyzdžius ir aiškiai pasakyk, ką vaikas atliks. "
                       f"Nuorodą į produktą dėk komentare.")
                st.text_area("FB juodraščio karkasas", draft, height=145, key="fb_"+str(d)+str(p_.get('key','')))
                st.caption("Prieš publikuojant tekstą verta suasmeninti pagal konkretaus produkto turinį.")

# ------------------------------------------------------------------ DUOMENYS
with tabs[5]:
    st.markdown("### Duomenų būklė ir aprėptis")
    d = meta.get("last_diag") or {}
    if d:
        k = st.columns(4)
        k[0].metric("Perskaityta puslapių", d.get("pages_fetched", 0))
        k[1].metric("Nepavykę", d.get("pages_failed", 0))
        k[2].metric("Sitemap nuorodų", d.get("sitemap_urls", 0))
        k[3].metric("Kategorijų / sąrašų", d.get("listings", 0))
        st.caption(f"Pilnas nuskaitymas: {'taip' if d.get('complete') else 'ne (' + str(d.get('stop_reason')) + ')'} · sitemap nuorodų nepasiektų: {d.get('sitemap_unfetched', 0)}")
        if d.get("category_mismatch"):
            st.warning("Kategorijos, kuriose svetainė deklaruoja daugiau produktų, nei surinkta:")
            st.dataframe(d["category_mismatch"], use_container_width=True)
        if d.get("uncertain"):
            with st.expander(f"Abejotini puslapiai ({len(d['uncertain'])}) – gali būti produktai, kurių parseris nepatvirtino"):
                st.dataframe(d["uncertain"], use_container_width=True)
        if d.get("errors"):
            with st.expander(f"Klaidos ({len(d['errors'])})"):
                st.dataframe(d["errors"], use_container_width=True)
    else:
        st.info("Diagnostikos dar nėra – paleisk nuskaitymą.")

    st.markdown("#### 🔎 Testuoti vieną produkto nuorodą")
    st.caption("Įklijuok produkto URL – pamatysi, ką parseris iš jo išskaito. Jei kažko trūksta, tai parodo, ką reikia pataisyti.")
    u = st.text_input("Produkto URL", placeholder="https://mokymopriemones.eu/...")
    if u and st.button("Tikrinti nuorodą"):
        try:
            r = make_session(CrawlConfig()).get(u, timeout=(8, 20))
            pr_ = parse_page(r.url, r.text, {"mokymopriemones.eu"}, datetime.now().isoformat(timespec="seconds"))
            st.write(f"Puslapis klasifikuotas kaip: **{pr_.kind}**" + (" (abejotina)" if pr_.uncertain else ""))
            st.json(pr_.product or {"pastaba": "produktu nepripažintas"})
        except Exception as e:
            st.error(f"Nepavyko: {type(e).__name__}: {e}")

    st.markdown("#### 📥 Ateities duomenys (GA4 / GSC / pardavimai / Facebook istorija)")
    st.caption("Šiuo metu: " + (f"įkelta signalų {len(sig)} produktams." if sig else "NĖRA prijungtų duomenų – radaras jų neapsimeta turįs."))
    up = st.file_uploader("CSV (code arba url, organic_clicks_7d, organic_clicks_prev_7d, views_7d, views_prev_7d, sales_30d, last_promoted)", type=["csv"])
    if up is not None and st.button("Išsaugoti signalus"):
        n = sg.save_signals_text(up.getvalue().decode("utf8-sig"))
        st.cache_resource.clear(); st.success(f"Išsaugota {n} eilučių."); st.rerun()
    st.download_button("Atsisiųsti signalų CSV šabloną", "code,organic_clicks_7d,organic_clicks_prev_7d,views_7d,views_prev_7d,sales_30d,last_promoted\nP171,42,30,120,100,3,2026-09-20\n", "signals_example.csv")

    st.markdown("#### 💾 Katalogo kopija")
    st.download_button("Atsisiųsti catalog.json", json.dumps(catalog, ensure_ascii=False), "catalog.json")
    up2 = st.file_uploader("Įkelti catalog.json", type=["json"], key="catup")
    if up2 is not None and st.button("Atkurti katalogą iš failo"):
        try:
            c_ = json.loads(up2.getvalue().decode("utf8"))
            assert "products" in c_
            cat.save_catalog(c_); st.cache_resource.clear(); st.success("Katalogas atkurtas."); st.rerun()
        except Exception as e:
            st.error(f"Netinkamas failas: {e}")

    with st.expander("📐 Kaip skaičiuojami balai ir datos"):
        st.markdown("""
**Datų pagrindas.** Švenčių datos skaičiuojamos kiekvienais metais (Velykos, Užgavėnės, Advento pradžia, Motinos / Tėvo diena). **Naudojimo klasėje data** nustatoma pagal ŠMSM mokinių atostogas: jei proga patenka į atostogas ar savaitgalį, medžiaga klasėje naudojama iki paskutinės mokymosi dienos (pvz., Vėlinės 11-02 → iki 10-30).

**Ugdymo programos.** Bendrosios programos (2022 m.) nenurodo mėnesių, jos skirstomos pagal 2 metų koncentrus. Mėnesius lemia vadovėliai ir mokytojų ilgalaikiai planai, kurie skiriasi. Todėl kiekvienas aktualumo langas pažymėtas **pagrindu** (ŠMSM kalendorius / vadovėlių seka / gamtos sezonas / prielaida) ir **patikimumu**. Savo leidyklos seką gali įrašyti į `data/ideas.json` (laukas `timing.windows`).

**Idėjų galimybių balas** = 0,6 × potencialas + 0,4 × laiko faktorius, sumažintas, jei idėjos nespėsi pagaminti. **Reklamos balas** = stipriausias laiko varomasis (proga / langas / tęstinė tema) + naujumas + neseniai atnaujintas puslapis + savaitės rotacija (tik tęstiniams) ± signalai (GA4 / GSC / pardavimai / paskutinė reklama), jei jie įkelti. Abu balai yra planavimo heuristikos, ne išmatuota Google paklausa.

**Temos atpažinimas.** Produktas siejamas su tema pagal pavadinimą ar kategoriją (stipru) arba bent 2 skirtingus raktažodžius aprašyme (silpna). Pavienis žodis aprašyme nieko nelemia.
""")
