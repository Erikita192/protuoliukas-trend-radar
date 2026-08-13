
import streamlit as st
import pandas as pd
import math, re, requests, xml.etree.ElementTree as ET
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

st.set_page_config(page_title="Protuoliukas Trend Radar V7", page_icon="📡", layout="wide")
MONTH_NUM={"sausis":1,"vasaris":2,"kovas":3,"balandis":4,"gegužė":5,"birželis":6,"liepa":7,"rugpjūtis":8,"rugsėjis":9,"spalis":10,"lapkritis":11,"gruodis":12}
SHOP="https://mokymopriemones.eu/"

@st.cache_data
def load_topics():
    return pd.read_csv("microtopics.csv")

@st.cache_resource
def supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def save_idea(r, score):
    sb = supabase_client()
    f = fp(r)
    today = str(date.today())

    existing = sb.table("ideas").select("fingerprint,last_seen,top_count").eq("fingerprint", f).execute().data
    if existing:
        row = existing[0]
        cnt = int(row.get("top_count") or 1)
        try:
            days = (date.today() - date.fromisoformat(row.get("last_seen"))).days
        except Exception:
            days = 0
        if days >= 7:
            cnt += 1
        sb.table("ideas").update({
            "last_seen": today,
            "top_count": cnt,
            "last_score": float(score),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("fingerprint", f).execute()
    else:
        sb.table("ideas").insert({
            "fingerprint": f,
            "tema": str(r.tema),
            "mikrotema": str(r.mikrotema),
            "amzius": str(r.amzius),
            "sritis": str(r.sritis),
            "produkto_ideja": str(r.produkto_ideja),
            "formatas": str(r.formatas),
            "examples": str(r.uzduociu_pavyzdziai),
            "evergreen": int(r.evergreen),
            "competition": str(r.konkurencija),
            "sales": str(r.pardavimo_potencialas),
            "first_seen": today,
            "last_seen": today,
            "top_count": 1,
            "last_score": float(score),
            "status": "IDEJA",
            "product_code": ""
        }).execute()

    sb.table("score_history").upsert({
        "day": today,
        "fingerprint": f,
        "score": float(score)
    }, on_conflict="day,fingerprint").execute()

def mark_created(fingerprint, code):
    supabase_client().table("ideas").update({
        "status": "SUKURTA",
        "product_code": code.strip(),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("fingerprint", fingerprint).execute()

def delete_idea(fingerprint):
    sb = supabase_client()
    sb.table("score_history").delete().eq("fingerprint", fingerprint).execute()
    sb.table("ideas").delete().eq("fingerprint", fingerprint).execute()

def idea_bank():
    data = supabase_client().table("ideas").select("*").order("last_score", desc=True).order("last_seen", desc=True).execute().data
    return pd.DataFrame(data)

def prior_score(fingerprint, days=1):
    target = str(date.today() - timedelta(days=days))
    data = supabase_client().table("score_history").select("score").eq("day", target).eq("fingerprint", fingerprint).limit(1).execute().data
    return float(data[0]["score"]) if data else None

def trend_label(r):
    p=prior_score(fp(r),1)
    if p is None:return "🆕 NAUJA / BE ISTORIJOS"
    d=float(r.prioritetas)-p
    if d>=6:return f"🔥 ↑ KYLA (+{d:.0f})"
    if d<=-6:return f"↓ LEIDŽIASI ({d:.0f})"
    return "→ STABILU"

def peak_days(r,today):
    vals=[]
    for x in str(r.piko_menesiai).split(","):
        pm=MONTH_NUM[x.strip()]
        y=today.year if pm>=today.month else today.year+1
        vals.append((date(y,pm,15)-today).days)
    return min(vals)

def sales_score(v):
    return {"žemas":30,"vidutinis":55,"aukštas":78,"labai aukštas":95}.get(str(v).lower(),60)
def comp_score(v):
    return {"žema":90,"vidutinė":72,"aukšta":52}.get(str(v).lower(),65)

def score(r,today,h):
    d=peak_days(r,today)
    publish=max(0,d-int(r.isankstinio_paskelbimo_dienos))
    sigma=max(12,h*.55)
    time_score=100*math.exp(-((publish-h*.35)**2)/(2*sigma*sigma))
    return round(.48*time_score+.20*(float(r.evergreen)*20)+.22*sales_score(r.pardavimo_potencialas)+.10*comp_score(r.konkurencija))

def action(r,today):
    d=peak_days(r,today)
    publish=d-int(r.isankstinio_paskelbimo_dienos)
    if publish < -7:return "📣 PERPUBLIKUOTI / PRALEISTI",publish
    if publish <= int(r.gamybos_sanaudos_d)+3:return "🔥 KURTI NAUJĄ",publish
    if publish <= 30:return "🟠 PLANUOTI",publish
    if publish <= 90:return "🔭 RUOŠTIS",publish
    return "⚪ VĖLIAU",publish

def stars(n): return "🌲"*int(n)+"○"*(5-int(n))

@st.cache_data(ttl=21600, show_spinner=False)
def scan_catalog(base_url):
    """Best-effort catalog scanner: sitemap first, then homepage links. Returns title/code/url."""
    headers={"User-Agent":"Mozilla/5.0 TrendRadar/1.0"}
    urls=[]
    # likely sitemap locations
    for sm in [urljoin(base_url,"sitemap.xml"),urljoin(base_url,"sitemap_index.xml")]:
        try:
            r=requests.get(sm,headers=headers,timeout=10)
            if r.ok and "<loc>" in r.text:
                root=ET.fromstring(r.text)
                locs=[e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
                # if sitemap index, inspect child sitemaps
                for loc in locs[:20]:
                    if loc.endswith(".xml"):
                        try:
                            rr=requests.get(loc,headers=headers,timeout=10)
                            rt=ET.fromstring(rr.text)
                            urls += [e.text.strip() for e in rt.iter() if e.tag.endswith("loc") and e.text]
                        except: pass
                    else: urls.append(loc)
                if urls: break
        except: pass
    if not urls:
        try:
            r=requests.get(base_url,headers=headers,timeout=10)
            soup=BeautifulSoup(r.text,"html.parser")
            urls=[urljoin(base_url,a.get("href")) for a in soup.find_all("a",href=True)]
        except: urls=[]
    host=urlparse(base_url).netloc
    urls=[u for u in dict.fromkeys(urls) if urlparse(u).netloc==host][:450]
    out=[]
    code_re=re.compile(r"(?:Nr\.?\s*)?((?:P)?\d{1,5})\b",re.I)
    for u in urls:
        low=u.lower()
        if any(x in low for x in ["/category","/blog","/kontakt","/apie","/login","/cart"]): continue
        title=""
        try:
            # derive title from URL cheaply first
            slug=urlparse(u).path.strip("/").split("/")[-1].replace("-"," ")
            title=slug.strip()
            m=code_re.search(title)
            code=m.group(1).upper() if m else ""
            # only fetch promising product-ish urls
            if code or "nr-" in low or "p" in slug[-8:]:
                rr=requests.get(u,headers=headers,timeout=6)
                if rr.ok:
                    s=BeautifulSoup(rr.text,"html.parser")
                    if s.title and s.title.text.strip(): title=s.title.text.strip()
                    m=code_re.search(title+" "+u)
                    code=m.group(1).upper() if m else code
            if title:
                out.append({"pavadinimas":title,"kodas":code,"nuoroda":u})
        except: pass
    return pd.DataFrame(out).drop_duplicates("nuoroda") if out else pd.DataFrame(columns=["pavadinimas","kodas","nuoroda"])

def catalog_matches(catalog, r):
    if catalog.empty:return catalog
    words=[w.lower() for w in re.findall(r"[A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž]{4,}",str(r.tema)+" "+str(r.mikrotema))]
    if not words:return catalog.head(0)
    s=(catalog["pavadinimas"].fillna("")+" "+catalog["nuoroda"].fillna("")).str.lower()
    mask=s.apply(lambda x:sum(w in x for w in words)>=1)
    return catalog[mask].head(6)

def fb_angle(r):
    micro=str(r.mikrotema).lower()
    if "palygin" in micro:return "Rodyti konkretų gebėjimą palyginti, o ne bendrą temos pavadinimą: vieną užduoties pavyzdį „kuris didesnis / mažesnis ir kodėl?“."
    if "sandara" in micro:return "Akcentuoti, kad vaikas ne tik skaičiuoja, bet supranta, iš kokių dalių sudarytas skaičius."
    if "teksto" in micro:return "Parodyti 1 trumpą teksto pavyzdį ir klausimą, kad pedagogas iš karto pamatytų priemonės sudėtingumą."
    if "dekor" in str(r.sritis).lower():return "Rodyti 3–4 gražiausias rinkinio dalis viename koliaže ir paminėti, kam tinka konkretus grupės pavadinimas."
    return f"Komunikacijos kampas: ne „priemonė apie {r.tema}“, o konkretus gebėjimas – {r.mikrotema.lower()} – su vienu realiu užduoties pavyzdžiu."

def why_not(r, catalog):
    matches=catalog_matches(catalog,r)
    if len(matches)>=4:
        return f"⛔ NEKURTI bendros priemonės: kataloge jau rasta bent {len(matches)} susijusių produktų. Ieškoti tik naujo gebėjimo / mechanikos kampo."
    if str(r.konkurencija).lower()=="aukšta" and str(r.pardavimo_potencialas).lower() not in ["labai aukštas"]:
        return "⛔ NEKURTI dabar: konkurencija aukšta, o pardavimo potencialas nepakankamai išskirtinis."
    return ""

df=load_topics()
today=st.sidebar.date_input("Šiandien",date.today())
st.title("📡 Protuoliukas Trend Radar — V7.1")
st.caption("KURTI • PERPUBLIKUOTI • IŠPLĖSTI • Artėjantys TOPai • Idėjų bankas • savaitinė suvestinė")

with st.sidebar:
    st.divider()
    st.subheader("Katalogas")
    do_scan=st.checkbox("Tikrinti mokymopriemones.eu katalogą",value=True)
    if st.button("🔄 Atnaujinti katalogą"):
        scan_catalog.clear()
    st.caption("Katalogas tikrinamas periodiškai. Jei produkto nepavyksta patikimai rasti, Radar nerodo išgalvoto kodo.")
    try:
        supabase_client().table("ideas").select("id").limit(1).execute()
        st.success("🟢 Supabase prijungta")
    except Exception as e:
        st.error("🔴 Supabase neprijungta. Patikrink Streamlit Secrets.")
    st.divider()
    st.subheader("Filtrai")
    ages=st.multiselect("Amžius",sorted(df.amzius.unique()))
    areas=st.multiselect("Sritis",sorted(df.sritis.unique()))

for h in [7,30,90]:
    df[f"{h}d"]=df.apply(lambda r:score(r,today,h),axis=1)
tmp=df.apply(lambda r:action(r,today),axis=1)
df["veiksmas"]=[x[0] for x in tmp]
df["paskelbti_po"]=[x[1] for x in tmp]
df["prioritetas"]=df[["7d","30d","90d"]].max(axis=1)

if ages: df=df[df.amzius.isin(ages)]
if areas: df=df[df.sritis.isin(areas)]

catalog=scan_catalog(SHOP) if do_scan else pd.DataFrame(columns=["pavadinimas","kodas","nuoroda"])

# Auto-save high-value current recommendations to idea bank
autos=df[(df.prioritetas>=65) & (df.veiksmas.isin(["🔥 KURTI NAUJĄ","🟠 PLANUOTI","🔭 RUOŠTIS"]))].copy()
for _,r in autos.iterrows():
    save_idea(r,r.prioritetas)

tabs=st.tabs(["🏠 ŠIANDIEN","💡 PRODUKTŲ PLANAI","🚀 ARTĖJANTYS TOPAI","📣 PERPUBLIKUOTI","🔄 IŠPLĖSTI ESAMĄ","🧠 IDĖJŲ BANKAS","📅 SAVAITĖ","⛔ NEKURTI"])

with tabs[0]:
    st.subheader("🔥 KURTI NAUJĄ")
    for _,r in df[df.veiksmas=="🔥 KURTI NAUJĄ"].sort_values("prioritetas",ascending=False).head(8).iterrows():
        deadline=today+timedelta(days=max(0,int(r.paskelbti_po)))
        st.markdown(f"### {trend_label(r)} · {r.tema} → {r.mikrotema}")
        st.write(f"**Ką kurti:** {r.produkto_ideja}")
        st.write(f"**Kam:** {r.amzius} • {r.sritis} • **Formatas:** {r.formatas}")
        st.write(f"**Publikuoti:** {'dabar' if r.paskelbti_po<=0 else deadline.strftime('%Y-%m-%d')} • **Evergreen:** {stars(r.evergreen)} • **Pardavimo potencialas:** {r.pardavimo_potencialas}")
        st.caption("Detali mechanika ir užduočių pavyzdžiai – skiltyje „Produktų planai“.")
        st.divider()

    st.subheader("📣 PERPUBLIKUOTI")
    reps=[]
    if not catalog.empty:
        for _,r in df.sort_values("7d",ascending=False).iterrows():
            m=catalog_matches(catalog,r)
            if len(m):
                reps.append((r,m.iloc[0]))
            if len(reps)>=8:break
    if reps:
        for r,p in reps:
            code=p.get("kodas","") or "kodas nerastas"
            st.markdown(f"### {r.tema} → {r.mikrotema}")
            st.write(f"**Priemonė:** {p.pavadinimas} • **Kodas:** {code}")
            st.write(f"**Nuoroda:** {p.nuoroda}")
            st.write(f"**Kodėl dabar:** 7 d. aktualumo balas {int(r['7d'])}/100.")
            st.write(f"**FB kampas:** {fb_angle(r)}")
            st.divider()
    else:
        st.info("Kataloge nepavyko patikimai susieti produktų su šiandienos temomis. Radar geriau nieko neišgalvoja.")

    st.subheader("🔄 IŠPLĖSTI ESAMĄ")
    shown=0
    for _,r in df.sort_values("30d",ascending=False).iterrows():
        m=catalog_matches(catalog,r)
        if len(m)>=1:
            st.markdown(f"### {r.tema} → naujas kampas: **{r.mikrotema}**")
            st.write(f"Kataloge rasta susijusių priemonių: **{len(m)}**. Vietoje bendros temos kurk kitą gebėjimą / mechaniką.")
            st.write(f"**Siūloma kryptis:** {r.produkto_ideja}")
            st.write("**Pavyzdžiai:** "+", ".join(str(r.uzduociu_pavyzdziai).split(" | ")[:4]))
            st.divider(); shown+=1
            if shown>=8:break
    if shown==0:st.info("Išplėtimo rekomendacijos atsiras, kai katalogo skaitytuvas patikimai ras susijusių produktų.")

with tabs[1]:
    st.subheader("💡 Išsamūs produktų planai")
    for _,r in df.sort_values("30d",ascending=False).head(20).iterrows():
        with st.expander(f"{r.tema} → {r.mikrotema} · {int(r['30d'])}/100 · {trend_label(r)}"):
            st.write(f"**Produkto idėja:** {r.produkto_ideja}")
            st.write(f"**Formatas:** {r.formatas} • **Gamyba:** ~{int(r.gamybos_sanaudos_d)} d.")
            st.write(f"**Kam:** {r.amzius} • {r.sritis}")
            st.write(f"**Evergreen:** {stars(r.evergreen)} • **Konkurencija:** {r.konkurencija} • **Pardavimo potencialas:** {r.pardavimo_potencialas}")
            st.markdown("**Konkrečių užduočių pavyzdžiai:**")
            for ex in str(r.uzduociu_pavyzdziai).split(" | "): st.write("• "+ex)
            st.markdown("**Mechanikos progresija:** atpažinimas → taikymas → klaidos paieška / paaiškinimas.")
            st.write(f"**FB kampas ateičiai:** {fb_angle(r)}")

with tabs[2]:
    st.subheader("🚀 Artėjantys TOPai")
    tops=df[df.sritis.str.contains("Dekoras|Pasaulio|etnokult|Gyvenimo|STEAM|Karjeros|Ikimokykl",case=False,regex=True)].sort_values("30d",ascending=False)
    for _,r in tops.head(15).iterrows():
        label="🔥 KYLA" if r["30d"]>=75 else "👀 STEBĖTI"
        st.markdown(f"### {label} · {r.tema} → {r.mikrotema}")
        st.write(f"**Kam:** {r.amzius} • {r.sritis}")
        st.write(f"**Produkto kryptis:** {r.produkto_ideja}")
        st.write(f"**30 d.:** {int(r['30d'])}/100 • **Evergreen:** {stars(r.evergreen)} • **Pardavimo potencialas:** {r.pardavimo_potencialas}")
        st.divider()

with tabs[3]:
    st.subheader("📣 Ką perpublikuoti / priminti")
    if reps:
        for r,p in reps:
            st.markdown(f"### {p.pavadinimas}")
            st.write(f"**Kodas:** {p.get('kodas','') or 'nerastas'}")
            st.write(f"**Tema / gebėjimas:** {r.tema} → {r.mikrotema}")
            st.write(f"**Nuoroda:** {p.nuoroda}")
            st.write(f"**FB komunikacijos kampas:** {fb_angle(r)}")
            st.write("**Kaip pateikti kita forma:** parodyti vieną konkrečią užduotį, prieš/po rezultatą, trumpą naudojimo situaciją arba kitą gebėjimo kampą – nebūtina kartoti seno įrašo.")
            st.divider()
    else: st.info("Šiuo metu nėra patikimai susietų katalogo priemonių.")

with tabs[4]:
    st.subheader("🔄 Išplėsti esamą kitu kampu")
    st.write("Radar ieško ne tik temos, bet ir **veiksmo / gebėjimo**. Termometro principas taikomas visam katalogui.")
    shown=0
    for _,r in df.sort_values("prioritetas",ascending=False).iterrows():
        m=catalog_matches(catalog,r)
        if len(m):
            with st.expander(f"{r.tema} → {r.mikrotema}"):
                st.write(f"**Susijusių katalogo produktų rasta:** {len(m)}")
                st.dataframe(m[["pavadinimas","kodas","nuoroda"]],use_container_width=True,hide_index=True)
                st.write(f"**Naujas kampas:** {r.produkto_ideja}")
                st.write("**Užduočių idėjos:** "+", ".join(str(r.uzduociu_pavyzdziai).split(" | ")))
            shown+=1
            if shown>=12:break

with tabs[5]:
    st.subheader("🧠 Idėjų bankas")
    bank=idea_bank()
    if bank.empty:
        st.info("Bankas dar tuščias. Vertingos KURTI / PLANUOTI / RUOŠTIS rekomendacijos čia išsisaugo automatiškai.")
    else:
        # filters
        c1,c2,c3,c4=st.columns(4)
        status=c1.multiselect("Būsena",sorted(bank.status.unique()),default=["IDEJA"] if "IDEJA" in bank.status.unique() else [])
        stage=c2.multiselect("Pakopa / amžius",sorted(bank.amzius.unique()))
        area=c3.multiselect("Sritis",sorted(bank.sritis.unique()))
        only_rising=c4.checkbox("Tik dažnai grįžtančios",False)
        b=bank.copy()
        if status:b=b[b.status.isin(status)]
        if stage:b=b[b.amzius.isin(stage)]
        if area:b=b[b.sritis.isin(area)]
        if only_rising:b=b[b.top_count>=2]

        # group hierarchy
        for (amz,sritis),g1 in b.groupby(["amzius","sritis"],sort=True):
            with st.expander(f"📂 {amz} → {sritis} · {len(g1)} id."):
                for tema,g2 in g1.groupby("tema",sort=True):
                    st.markdown(f"#### {tema} · {len(g2)}")
                    for _,it in g2.iterrows():
                        st.markdown(f"**{it.mikrotema}**  ·  {stars(it.evergreen)}  ·  TOP grįžo **{int(it.top_count)}** k.")
                        st.caption(f"Pirmą kartą: {it.first_seen} • paskutinį: {it.last_seen} • potencialas: {it.sales} • būsena: {it.status}")
                        st.write(it.produkto_ideja)
                        if it.status!="SUKURTA":
                            code=st.text_input("Produkto kodas",key=f"code_{it.id}",placeholder="pvz. P129 arba 301")
                            a,bcol=st.columns([1,1])
                            if a.button("✅ Pažymėti SUKURTA",key=f"created_{it.id}"):
                                if code.strip():
                                    mark_created(it.fingerprint,code)
                                    st.rerun()
                                else: st.warning("Įvesk produkto kodą.")
                            if bcol.button("🗑️ Ištrinti idėją",key=f"del_{it.id}"):
                                delete_idea(it.fingerprint); st.rerun()
                        else:
                            st.success(f"✅ SUKURTA • produkto kodas: {it.product_code}")
                            if st.button("🗑️ Ištrinti iš banko",key=f"dels_{it.id}"):
                                delete_idea(it.fingerprint); st.rerun()
                        st.divider()
        st.download_button("⬇️ Atsisiųsti Idėjų banko atsarginę kopiją",bank.to_csv(index=False).encode("utf-8-sig"),"ideju_bankas_v7.csv","text/csv")
        st.success("✅ Idėjų bankas saugomas nuolatinėje Supabase duomenų bazėje. Streamlit perkrovimai ar naujos programėlės versijos jo neištrins.")

with tabs[6]:
    st.subheader("📅 Savaitinė suvestinė")
    rising=[]
    for _,r in df.sort_values("prioritetas",ascending=False).iterrows():
        lab=trend_label(r)
        if "KYLA" in lab or "NAUJA" in lab:rising.append(r)
    st.markdown("### 🔥 Kas naujai kyla / stiprėja")
    for r in rising[:7]: st.write(f"• **{r.tema} → {r.mikrotema}** · {int(r.prioritetas)}/100")
    st.markdown("### 💡 3 stipriausios naujos kūrimo kryptys")
    for _,r in df.sort_values("30d",ascending=False).head(3).iterrows():
        st.write(f"• **{r.produkto_ideja}** — {r.amzius}, {r.sritis}")
    st.markdown("### 📣 Ką priminti")
    if reps:
        for r,p in reps[:5]: st.write(f"• **{p.pavadinimas}** ({p.get('kodas','') or 'kodas nerastas'}) — {fb_angle(r)}")
    else: st.write("• Patikimų katalogo atitikmenų šią savaitę nerasta.")
    st.markdown("### 🔁 Kas grįžta iš Idėjų banko")
    bank=idea_bank()
    ret=bank[(bank.status=="IDEJA") & (bank.top_count>=2)].sort_values(["top_count","last_score"],ascending=False).head(5)
    if len(ret):
        for _,i in ret.iterrows():st.write(f"• **{i.tema} → {i.mikrotema}** · į TOP grįžo {int(i.top_count)} k.")
    else:st.write("• Dar nėra pakankamai istorijos.")

with tabs[7]:
    st.subheader("⛔ Kodėl kai ko dabar NEKURTI")
    count=0
    for _,r in df.sort_values("prioritetas",ascending=False).iterrows():
        msg=why_not(r,catalog)
        if msg:
            st.markdown(f"### {r.tema} → {r.mikrotema}")
            st.write(msg)
            st.write("**Alternatyva:** perpublikuoti turimą priemonę arba ieškoti kito konkretaus gebėjimo kampo.")
            st.divider(); count+=1
            if count>=10:break
    if count==0: st.info("Šiandien ryškių „NEKURTI“ signalų nėra arba katalogo skenavimas nerado pakankamai duomenų.")

st.caption("V7.1: rekomendacijos automatiškai keliauja į Idėjų banką. Katalogo kodai ir nuorodos rodomi tik kai pavyksta juos patikimai aptikti.")
