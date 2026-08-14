
import streamlit as st
import pandas as pd
import math, re, requests, xml.etree.ElementTree as ET
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

st.set_page_config(page_title="Protuoliukas Trend Radar V7.3", page_icon="📡", layout="wide")
MONTH_NUM={"sausis":1,"vasaris":2,"kovas":3,"balandis":4,"gegužė":5,"birželis":6,"liepa":7,"rugpjūtis":8,"rugsėjis":9,"spalis":10,"lapkritis":11,"gruodis":12}
SHOP="https://mokymopriemones.eu/"

@st.cache_data
def load_topics():
    return pd.read_csv("microtopics.csv")

def fp(r):
    return f"{str(r.tema).strip().lower()}::{str(r.mikrotema).strip().lower()}"

@st.cache_resource
def supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def db_ok():
    try:
        # Verify that Secrets exist and client can be created.
        _ = st.secrets["SUPABASE_URL"]
        _ = st.secrets["SUPABASE_KEY"]
        supabase_client()
        return True,""
    except Exception as e:
        return False,str(e)

def save_idea(r, score):
    # Persistence must never crash the Radar UI.
    try:
        sb=supabase_client(); f=fp(r); today=str(date.today())
        old=sb.table("ideas").select("fingerprint,last_seen,top_count,status").eq("fingerprint",f).execute().data
        if old:
            x=old[0]; cnt=int(x.get("top_count") or 1)
            try: gap=(date.today()-date.fromisoformat(x.get("last_seen"))).days
            except: gap=0
            if gap>=7: cnt+=1
            sb.table("ideas").update({"last_seen":today,"top_count":cnt,"last_score":float(score),"updated_at":datetime.utcnow().isoformat()}).eq("fingerprint",f).execute()
        else:
            sb.table("ideas").insert({
                "fingerprint":f,"tema":str(r.tema),"mikrotema":str(r.mikrotema),"amzius":str(r.amzius),"sritis":str(r.sritis),
                "produkto_ideja":str(r.produkto_ideja),"formatas":str(r.formatas),"examples":str(r.uzduociu_pavyzdziai),
                "evergreen":int(r.evergreen),"competition":str(r.konkurencija),"sales":str(r.pardavimo_potencialas),
                "first_seen":today,"last_seen":today,"top_count":1,"last_score":float(score),"status":"IDEJA","product_code":""
            }).execute()
        try:
            sb.table("score_history").upsert({"day":today,"fingerprint":f,"score":float(score)},on_conflict="day,fingerprint").execute()
        except Exception:
            pass
        return True
    except Exception:
        return False

def idea_status(fingerprint):
    try:
        d=supabase_client().table("ideas").select("status,product_code").eq("fingerprint",fingerprint).limit(1).execute().data
        return d[0] if d else {"status":"IDEJA","product_code":""}
    except: return {"status":"IDEJA","product_code":""}

def set_idea_status(fingerprint,status,code=""):
    supabase_client().table("ideas").update({
        "status":status,"product_code":code.strip(),"updated_at":datetime.utcnow().isoformat()
    }).eq("fingerprint",fingerprint).execute()

def idea_bank():
    try:
        d=supabase_client().table("ideas").select("*").order("last_score",desc=True).order("last_seen",desc=True).execute().data
        return pd.DataFrame(d)
    except: return pd.DataFrame()

def republish_done(code, theme, micro, fb):
    supabase_client().table("republish_history").insert({
        "product_code":code or "BE_KODO","recommendation_date":str(date.today()),
        "theme":theme,"microtheme":micro,"fb_angle":fb
    }).execute()

def recent_republish(code, days=21):
    if not code:return False
    try:
        d=supabase_client().table("republish_history").select("recommendation_date").eq("product_code",code).order("recommendation_date",desc=True).limit(1).execute().data
        if not d:return False
        dt=date.fromisoformat(d[0]["recommendation_date"])
        return (date.today()-dt).days < days
    except:return False

def prior_score(fingerprint,days=1):
    try:
        target=str(date.today()-timedelta(days=days))
        d=supabase_client().table("score_history").select("score").eq("day",target).eq("fingerprint",fingerprint).limit(1).execute().data
        return float(d[0]["score"]) if d else None
    except:return None

def trend_label(r):
    p=prior_score(fp(r),1)
    if p is None:return "🆕 NAUJA"
    d=float(r.prioritetas)-p
    if d>=6:return f"🔥 ↑ KYLA (+{d:.0f})"
    if d<=-6:return f"↓ LEIDŽIASI ({d:.0f})"
    return "→ STABILU"

def peak_days(r,today):
    vals=[]
    for x in str(r.piko_menesiai).split(","):
        pm=MONTH_NUM.get(x.strip())
        if not pm:continue
        y=today.year if pm>=today.month else today.year+1
        vals.append((date(y,pm,15)-today).days)
    return min(vals) if vals else 180

def sales_score(v): return {"žemas":30,"vidutinis":55,"aukštas":78,"labai aukštas":95}.get(str(v).lower(),60)
def comp_score(v): return {"žema":90,"vidutinė":72,"aukšta":52}.get(str(v).lower(),65)
def stars(n): return "🌲"*int(n)+"○"*(5-int(n))

def horizon_score(r,today,h):
    d=peak_days(r,today)
    publish=max(0,d-int(r.isankstinio_paskelbimo_dienos))
    sigma=max(8,h*.65)
    timing=100*math.exp(-((publish-h*.40)**2)/(2*sigma*sigma))
    return round(.48*timing+.20*(float(r.evergreen)*20)+.22*sales_score(r.pardavimo_potencialas)+.10*comp_score(r.konkurencija))

def timing(r,today):
    peak=today+timedelta(days=max(0,peak_days(r,today)))
    publish=peak-timedelta(days=int(r.isankstinio_paskelbimo_dienos))
    start=publish-timedelta(days=int(r.gamybos_sanaudos_d))
    last=peak-timedelta(days=max(2,int(r.isankstinio_paskelbimo_dienos)//3))
    return start,publish,peak,last

def examples(r,n=8):
    return [x.strip() for x in str(r.uzduociu_pavyzdziai).split(" | ") if x.strip()][:n]

def angles(r):
    return [x.strip() for x in str(getattr(r,"kampai","")).split(" | ") if x.strip()]

@st.cache_data(ttl=21600,show_spinner=False)
def scan_catalog(base_url):
    headers={"User-Agent":"Mozilla/5.0 TrendRadar/1.0"}
    urls=[]
    for sm in [urljoin(base_url,"sitemap.xml"),urljoin(base_url,"sitemap_index.xml")]:
        try:
            rr=requests.get(sm,headers=headers,timeout=10)
            if rr.ok and "<loc>" in rr.text:
                root=ET.fromstring(rr.text)
                locs=[e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
                for loc in locs[:30]:
                    if loc.endswith(".xml"):
                        try:
                            x=requests.get(loc,headers=headers,timeout=8)
                            rt=ET.fromstring(x.text)
                            urls += [e.text.strip() for e in rt.iter() if e.tag.endswith("loc") and e.text]
                        except:pass
                    else: urls.append(loc)
                if urls:break
        except:pass
    if not urls:
        try:
            rr=requests.get(base_url,headers=headers,timeout=10)
            s=BeautifulSoup(rr.text,"html.parser")
            urls=[urljoin(base_url,a.get("href")) for a in s.find_all("a",href=True)]
        except:urls=[]
    host=urlparse(base_url).netloc
    urls=[u for u in dict.fromkeys(urls) if urlparse(u).netloc==host][:500]
    code_re=re.compile(r"(?:Nr\.?\s*)?((?:P)?\d{1,5})\b",re.I)
    out=[]
    for u in urls:
        low=u.lower()
        if any(x in low for x in ["/category","/blog","/kontakt","/apie","/login","/cart"]):continue
        slug=urlparse(u).path.strip("/").split("/")[-1].replace("-"," ")
        title=slug; m=code_re.search(title+" "+u); code=m.group(1).upper() if m else ""
        if code or "nr-" in low:
            try:
                x=requests.get(u,headers=headers,timeout=5)
                if x.ok:
                    s=BeautifulSoup(x.text,"html.parser")
                    if s.title and s.title.text.strip():title=s.title.text.strip()
                    m=code_re.search(title+" "+u); code=m.group(1).upper() if m else code
            except:pass
        if title:out.append({"pavadinimas":title,"kodas":code,"nuoroda":u})
    return pd.DataFrame(out).drop_duplicates("nuoroda") if out else pd.DataFrame(columns=["pavadinimas","kodas","nuoroda"])

def catalog_matches(catalog,r):
    if catalog.empty:return catalog
    stop={"ugdymas","užduotys","priemonė","kortelės","vaikams","tema","grupės","rinkinys"}
    words=[w.lower() for w in re.findall(r"[A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž]{4,}",str(r.tema)+" "+str(r.mikrotema)) if w.lower() not in stop]
    if not words:return catalog.head(0)
    s=(catalog.pavadinimas.fillna("")+" "+catalog.nuoroda.fillna("")).str.lower()
    scored=s.apply(lambda x:sum(w in x for w in words))
    z=catalog.assign(_score=scored)
    return z[z._score>=1].sort_values("_score",ascending=False).head(8)

def exact_catalog_match(catalog,r):
    m=catalog_matches(catalog,r)
    if m.empty:return m
    micro_words=[w.lower() for w in re.findall(r"[A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž]{5,}",str(r.mikrotema))]
    s=(m.pavadinimas.fillna("")+" "+m.nuoroda.fillna("")).str.lower()
    mask=s.apply(lambda x:sum(w in x for w in micro_words)>=max(1,min(2,len(micro_words))))
    return m[mask].head(4)

def fb_angle(r):
    a=angles(r)
    hook=a[0] if a else str(r.mikrotema)
    return f"Rodyti ne bendrą temą, o konkretų veiksmą „{hook}“. Įkelti vieną realią užduotį / ekraną ir parodyti, ką vaikas turi padaryti."

def decision(r,catalog,today):
    stt=idea_status(fp(r))
    if stt.get("status") in ["SUKURTA","PRAPLESTA"]:
        return "ATLIKTA",None
    exact=exact_catalog_match(catalog,r)
    related=catalog_matches(catalog,r)
    start,pub,peak,last=timing(r,today)
    if len(exact):
        p=exact.iloc[0]
        if not recent_republish(str(p.kodas),21) and today >= pub-timedelta(days=4) and today <= last:
            return "PERPUBLIKUOTI",p
        return "PALAUkti",p
    if len(related):
        return "ISPLESTI",related.iloc[0]
    if today >= start and today <= last:
        return "KURTI",None
    return "PALAUKTI",None

def source_badge(r):
    lvl=str(getattr(r,"teorijos_lygis","bendras"))
    if lvl=="būtina tikrinti":return "🟠 BŪTINA PATIKRINTI TEORIJĄ"
    if lvl=="reikia šaltinių":return "🔵 REMTIS ŠALTINIAIS"
    return "🟢 BENDRO IŠMANYMO / PROGRAMOS LYGMUO"

def full_card(r,action_label=None,product=None,key_prefix="card",show_buttons=True):
    start,pub,peak,last=timing(r,today)
    action_label=action_label or "IDĖJA"
    st.markdown(f"### {trend_label(r)} · {r.tema} → {r.mikrotema}")
    if action_label=="PERPUBLIKUOTI" and product is not None:
        st.write(f"**📣 Priemonė:** {product.pavadinimas}  •  **Kodas:** {product.kodas or 'nerastas'}")
        st.write(f"**Optimalu perpublikuoti:** {pub.strftime('%Y-%m-%d')}–{min(last,peak).strftime('%Y-%m-%d')}  •  **Paklausos pikas:** apie {peak.strftime('%Y-%m-%d')}")
        st.write(f"**FB kampas:** {fb_angle(r)}")
        if product.nuoroda:st.write(f"**Nuoroda:** {product.nuoroda}")
        if show_buttons and st.button("✅ PASIDALINAU",key=f"{key_prefix}_share_{fp(r)}"):
            republish_done(str(product.kodas),str(r.tema),str(r.mikrotema),fb_angle(r)); st.rerun()
        return
    if action_label=="ISPLESTI" and product is not None:
        st.write(f"**🔄 Esamas produktas:** {product.pavadinimas} • **Kodas:** {product.kodas or 'nerastas'}")
        st.write(f"**Naujas kampas:** {r.produkto_ideja}")
    else:
        st.write(f"**💡 Siūloma priemonė:** {r.produkto_ideja}")
    st.write(f"**Kam:** {r.amzius} • {r.sritis} • **Formatas:** {r.formatas}")
    st.write(f"**Apimtis:** {getattr(r,'produkto_apimtis','24–36 užduotys')} • **Evergreen:** {stars(r.evergreen)} • **Pardavimo potencialas:** {r.pardavimo_potencialas} • **Konkurencija:** {r.konkurencija}")
    st.markdown("**🎯 Rekomenduojamas užduoties kampas**")
    aa=angles(r)
    for i,a in enumerate(aa[:3],1):st.write(f"{['🥇','🥈','🥉'][i-1]} **{a}**")
    st.markdown("**🧩 Konkretūs užduočių pavyzdžiai**")
    for x in examples(r,8):st.write("• "+x)
    st.markdown("**📅 Laikas**")
    st.write(f"**Pradėti kurti:** {'dabar' if today>=start else start.strftime('%Y-%m-%d')}  •  **Optimalu publikuoti:** {pub.strftime('%Y-%m-%d')}  •  **Paskutinė verta diena:** {last.strftime('%Y-%m-%d')}  •  **Tikėtinas pikas:** {peak.strftime('%Y-%m-%d')}")
    st.markdown(f"**📚 Turinys:** {source_badge(r)}")
    st.write(str(getattr(r,"saltiniu_kryptis","Aktualios ugdymo programos ir patikimi dalyko šaltiniai.")))
    if show_buttons:
        code=st.text_input("Produkto kodas, kai atliksi",key=f"{key_prefix}_code_{fp(r)}",placeholder="pvz. P129 arba 301")
        c1,c2=st.columns(2)
        if action_label=="ISPLESTI":
            if c1.button("✅ PRAPLĖČIAU",key=f"{key_prefix}_expanded_{fp(r)}"):
                if code.strip():set_idea_status(fp(r),"PRAPLESTA",code);st.rerun()
                else:st.warning("Įvesk naujai sukurtos priemonės kodą.")
        else:
            if c1.button("✅ SUKŪRIAU",key=f"{key_prefix}_created_{fp(r)}"):
                if code.strip():set_idea_status(fp(r),"SUKURTA",code);st.rerun()
                else:st.warning("Įvesk produkto kodą.")

df=load_topics()
today=st.sidebar.date_input("Šiandien",date.today())
for h in [7,14,30]:df[f"{h}d"]=df.apply(lambda r:horizon_score(r,today,h),axis=1)
df["prioritetas"]=df[["7d","14d","30d"]].max(axis=1)

st.title("📡 Protuoliukas Trend Radar — V7.3.4")
st.caption("7 / 14 / 30 dienų radaras • konkretus užduoties kampas • KURTI / PERPUBLIKUOTI / IŠPLĖSTI be prieštaravimų")

with st.sidebar:
    st.divider()
    st.subheader("Katalogas")
    do_scan=st.checkbox("Tikrinti mokymopriemones.eu",True)
    if st.button("🔄 Atnaujinti katalogą"):scan_catalog.clear()
    ok,err=db_ok()
    if ok:
        st.success("🟢 Supabase prijungta")
    else:
        st.error("🔴 Supabase neprijungta")
        safe_err=str(err)
        try:
            secret=str(st.secrets.get("SUPABASE_KEY",""))
            if secret:
                safe_err=safe_err.replace(secret,"[SECRET HIDDEN]")
        except Exception:
            pass
        if len(safe_err)>600:
            safe_err=safe_err[:600]+"…"
        st.caption("Diagnostika:")
        st.code(safe_err)
    st.divider()
    ages=st.multiselect("Amžius",sorted(df.amzius.astype(str).unique()))
    areas=st.multiselect("Sritis",sorted(df.sritis.astype(str).unique()))
    st.caption("Visos amžiaus grupės svarbios. 5–8 kl. Radar ypač stebi lietuvių ir matematiką, bet gali iškelti ir stiprias kitų dalykų nišas.")

if ages:df=df[df.amzius.isin(ages)]
if areas:df=df[df.sritis.isin(areas)]
catalog=scan_catalog(SHOP) if do_scan else pd.DataFrame(columns=["pavadinimas","kodas","nuoroda"])

# One decision per idea: no self-contradictions
decisions=[]
for _,r in df.iterrows():
    act,prod=decision(r,catalog,today)
    decisions.append((fp(r),act,prod))
dmap={a:(b,c) for a,b,c in decisions}

# Auto-save valuable create/expand ideas
for _,r in df[df.prioritetas>=65].iterrows():
    act,_=dmap[fp(r)]
    if act in ["KURTI","ISPLESTI","PALAUKTI"]:
        save_idea(r,r.prioritetas)

tabs=st.tabs(["🏠 ŠIANDIEN","📅 SAVAITĖ","🚀 ARTĖJANTYS TOPAI","💡 PRODUKTŲ PLANAI","📣 PERPUBLIKUOTI","🔄 IŠPLĖSTI ESAMĄ","🧠 IDĖJŲ BANKAS"])

def demand_window(r, today):
    """
    Exclusive demand horizon.
    0–7 d.   = ŠIANDIEN
    8–14 d.  = SAVAITĖ
    15–30 d. = ARTĖJANTYS TOPAI

    The anchor is the optimal publication / demand-entry date rather than
    simply the middle of the peak month. If publication is already due,
    the item belongs to ŠIANDIEN while its useful sales window remains open.
    """
    start,pub,peak,last=timing(r,today)
    days=(pub-today).days
    if days <= 7 and last >= today:
        return "TODAY"
    if 8 <= days <= 14:
        return "WEEK"
    if 15 <= days <= 30:
        return "COMING"
    return "OUT"

def window_score(r, window):
    if window=="TODAY": return float(r["7d"])
    if window=="WEEK": return float(r["14d"])
    if window=="COMING": return float(r["30d"])
    return 0.0

def eligible_rows(frame, window, limit=8):
    rows=[]
    for _,r in frame.iterrows():
        if demand_window(r,today)!=window:
            continue
        act,prod=dmap[fp(r)]
        if act=="ATLIKTA":
            continue
        rows.append((r,act,prod,window_score(r,window)))
    rows.sort(key=lambda x:x[3], reverse=True)
    return rows[:limit]

with tabs[0]:
    st.subheader("🏠 ŠIANDIEN · TOP dabar ir per artimiausias 0–7 dienas")
    st.caption("Tik tai, kam paklausos / publikavimo langas jau atsidarė arba atsidarys per 7 dienas. Čia verta veikti dabar.")
    active=eligible_rows(df,"TODAY",8)
    if not active:
        st.info("Šiuo metu 0–7 dienų lange nėra pakankamai stiprių aktyvių TOPų.")
    for i,(r,act,prod,sc) in enumerate(active,1):
        label={"KURTI":"🔥 KURTI NAUJĄ","PERPUBLIKUOTI":"📣 PERPUBLIKUOTI","ISPLESTI":"🔄 IŠPLĖSTI ESAMĄ","PALAUKTI":"🔥 TOP DABAR"}.get(act,"🔥 TOP DABAR")
        st.markdown(f"## {i}. {label} · {int(sc)}/100")
        full_card(r,act if act in ["KURTI","PERPUBLIKUOTI","ISPLESTI"] else "IDĖJA",prod,key_prefix=f"today{i}",show_buttons=act in ["KURTI","PERPUBLIKUOTI","ISPLESTI"])
        st.divider()

with tabs[1]:
    st.subheader("📅 SAVAITĖ · TOP, kurie taps aktualūs po savaitės")
    st.caption("8–14 dienų langas. Dar nereikia pulti kurti vien todėl, kad matai idėją – tai tavo išankstinis signalas, ką pradėti rimtai svarstyti po savaitės.")
    weekly=eligible_rows(df,"WEEK",8)
    if not weekly:
        st.info("Šiuo metu 8–14 dienų lange nėra pakankamai stiprių TOPų.")
    for i,(r,act,prod,sc) in enumerate(weekly,1):
        start,pub,peak,last=timing(r,today)
        st.markdown(f"## {i}. 👀 TOP PO SAVAITĖS · {int(sc)}/100")
        st.write(f"**Kada pereis į aktyvų langą:** apie {(pub-timedelta(days=7)).strftime('%Y-%m-%d')} • **optimalu publikuoti:** {pub.strftime('%Y-%m-%d')}")
        full_card(r,act if act in ["ISPLESTI","PERPUBLIKUOTI"] else "IDĖJA",prod,key_prefix=f"week{i}",show_buttons=False)
        st.divider()

with tabs[2]:
    st.subheader("🚀 ARTĖJANTYS TOPAI · ankstyvas 15–30 dienų radaras")
    st.caption("Tai dar ne šios ir ne kitos savaitės darbai. Čia matai, kas gali tapti stipria paklausos banga po 2–4 savaičių, kad didesnėms priemonėms spėtum pasiruošti.")
    coming=eligible_rows(df,"COMING",10)
    if not coming:
        st.info("Šiuo metu 15–30 dienų lange nėra pakankamai stiprių artėjančių TOPų.")
    for i,(r,act,prod,sc) in enumerate(coming,1):
        start,pub,peak,last=timing(r,today)
        st.markdown(f"## {i}. 🔭 ARTĖJANTIS TOP · {int(sc)}/100")
        st.write(f"**Iki optimalaus publikavimo:** {(pub-today).days} d. • **optimalu publikuoti:** {pub.strftime('%Y-%m-%d')} • **tikėtinas pikas:** {peak.strftime('%Y-%m-%d')}")
        full_card(r,act if act in ["ISPLESTI","PERPUBLIKUOTI"] else "IDĖJA",prod,key_prefix=f"coming{i}",show_buttons=False)
        st.divider()

with tabs[3]:
    st.subheader("💡 Produktų planai – platesnė perspektyvių produktų bazė")
    st.caption("Čia gali naršyti daugiau variantų pagal pasirinktą horizontą. Tai nėra TOP langų kopija – skirta sąmoningai paieškai ir planavimui.")
    horizon=st.radio("Horizontas",[7,14,30],horizontal=True)
    view=df.sort_values(f"{horizon}d",ascending=False)
    for i,(_,r) in enumerate(view.head(30).iterrows(),1):
        act,prod=dmap[fp(r)]
        w=demand_window(r,today)
        wtxt={"TODAY":"0–7 d. / ŠIANDIEN","WEEK":"8–14 d. / SAVAITĖ","COMING":"15–30 d. / ARTĖJA","OUT":"už aktyvaus 30 d. lango"}[w]
        with st.expander(f"{r.tema} → {r.mikrotema} · {int(r[f'{horizon}d'])}/100 · {wtxt}"):
            full_card(r,act if act in ["KURTI","ISPLESTI","PERPUBLIKUOTI"] else "IDĖJA",prod,key_prefix=f"plan{i}",show_buttons=False)

with tabs[4]:
    st.subheader("📣 Perpublikuoti – su terminais ir atlikimo istorija")
    count=0
    for _,r in df.sort_values("7d",ascending=False).iterrows():
        act,prod=dmap[fp(r)]
        if act=="PERPUBLIKUOTI":
            count+=1; full_card(r,act,prod,key_prefix=f"rep{count}"); st.divider()
        if count>=12:break
    if count==0:st.info("Šiuo metu nėra produktų, kuriems Radar matytų pagrįstą perpublikavimo langą.")

with tabs[5]:
    st.subheader("🔄 Išplėsti esamą – visas katalogas, ne tik dekorai")
    count=0
    for _,r in df.sort_values("30d",ascending=False).iterrows():
        act,prod=dmap[fp(r)]
        if act=="ISPLESTI":
            count+=1
            full_card(r,act,prod,key_prefix=f"exp{count}")
            st.divider()
        if count>=15:break
    if count==0:st.info("Katalogo skaitytuvas šiuo metu nerado patikimų plėtros atitikmenų.")

with tabs[6]:
    st.subheader("🧠 Idėjų bankas – tik tai, ko dar nesukūrei")
    st.caption("Geros neįgyvendintos idėjos čia lieka neribotai. Paspaudus SUKŪRIAU ar PRAPLĖČIAU jos iš aktyvaus banko dingsta, bet Supabase istorijoje išlieka.")
    bank=idea_bank()
    if bank.empty:
        st.info("Bankas dar tuščias.")
    else:
        # Aktyvus bankas rodo tik neįgyvendintas idėjas.
        active_bank=bank[~bank.status.isin(["SUKURTA","PRAPLESTA"])].copy()
        done_bank=bank[bank.status.isin(["SUKURTA","PRAPLESTA"])].copy()

        st.markdown("### 💡 Aktyvios idėjos")
        if active_bank.empty:
            st.success("Šiuo metu aktyviame banke nėra neįgyvendintų idėjų.")
        else:
            for (amz,sritis),g in active_bank.groupby(["amzius","sritis"],dropna=False):
                with st.expander(f"📂 {amz} → {sritis} · {len(g)} id."):
                    for tema,g2 in g.groupby("tema"):
                        st.markdown(f"### {tema}")
                        for _,it in g2.iterrows():
                            st.markdown(f"**{it.mikrotema}** · {stars(it.evergreen)} · TOP grįžo {int(it.top_count)} k.")
                            st.write(f"**💡 {it.produkto_ideja}**")
                            st.markdown("**🧩 Užduočių pavyzdžiai**")
                            for x in [q.strip() for q in str(it.examples).split(" | ") if q.strip()][:8]:
                                st.write("• "+x)
                            st.caption(f"Potencialas: {it.sales} • konkurencija: {it.competition} • pirmą kartą {it.first_seen} • paskutinį {it.last_seen}")
                            code=st.text_input("Produkto kodas",key=f"bank_code_{it.id}",placeholder="pvz. P129 arba 301")
                            c1,c2=st.columns(2)
                            if c1.button("✅ SUKŪRIAU",key=f"bank_created_{it.id}"):
                                if code.strip():
                                    set_idea_status(it.fingerprint,"SUKURTA",code)
                                    st.rerun()
                                else:
                                    st.warning("Įvesk sukurto produkto kodą.")
                            if c2.button("🗑️ IŠTRINTI",key=f"bank_delete_{it.id}"):
                                supabase_client().table("ideas").delete().eq("fingerprint",it.fingerprint).execute()
                                st.rerun()
                            st.divider()

        # Įgyvendintos idėjos nėra aktyvaus banko dalis, bet prireikus galima
        # pasižiūrėti istoriją. Tai leidžia Radar prisiminti produkto kodą.
        with st.expander(f"✅ ĮGYVENDINTŲ ISTORIJA · {len(done_bank)}"):
            if done_bank.empty:
                st.caption("Dar nėra įgyvendintų Radar idėjų.")
            else:
                for _,it in done_bank.sort_values("updated_at",ascending=False,na_position="last").iterrows():
                    label="SUKURTA" if it.status=="SUKURTA" else "PRAPLĖSTA"
                    st.write(f"**{label}** · {it.product_code or 'be kodo'} · {it.tema} → {it.mikrotema}")

st.caption("V7.3.4: 0–7 d. = ŠIANDIEN • 8–14 d. = SAVAITĖ • 15–30 d. = ARTĖJANTYS TOPAI. Idėjų banke rodomos tik dar neįgyvendintos idėjos.")
