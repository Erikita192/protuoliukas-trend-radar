
import streamlit as st
import pandas as pd
import numpy as np
import re, math
from collections import defaultdict
from datetime import date, timedelta

st.set_page_config(page_title="Protuoliukas Trend Radar V4",page_icon="📡",layout="wide")
MONTHS={1:"sausis",2:"vasaris",3:"kovas",4:"balandis",5:"gegužė",6:"birželis",7:"liepa",8:"rugpjūtis",9:"rugsėjis",10:"spalis",11:"lapkritis",12:"gruodis"}
MONTH_NUM={v:k for k,v in MONTHS.items()}
STOP=set("""ir su į iš nuo apie vaikams vaikai vaiko vaikų uzduotys užduotys korteles kortelės priemone priemonė
mokymosi mokymo kaip kas kur yra bei arba pdf ppt lietuviu lietuvių nemokamai darzelis darželis klasei klasė
priesmokyklinis priešmokyklinis pradinis pradinių""".split())

@st.cache_data
def load_topics(): return pd.read_csv("topics.csv")
def read_any(u):
    if u is None:return pd.DataFrame()
    try:return pd.read_csv(u)
    except:
        try:u.seek(0);return pd.read_excel(u)
        except:return pd.DataFrame()
def find_col(df,names):
    for c in df.columns:
        if str(c).lower().strip() in names:return c
def toks(s):
    s=re.sub(r"[^a-ząčęėįšųūž0-9\s-]"," ",str(s).lower())
    return [x for x in s.split() if len(x)>=3 and x not in STOP]
def known_match(q,topics):
    q=str(q).lower()
    for _,r in topics.iterrows():
        if any(p.strip() and p.strip() in q for p in str(r.paieskos_frazes).lower().split("|")):return r.tema
def peak_days(r,today):
    vals=[]
    for x in str(r.piko_menesiai).split(","):
        pm=MONTH_NUM[x.strip()]; y=today.year if pm>=today.month else today.year+1
        vals.append((date(y,pm,15)-today).days)
    return min(vals)
def cal_score(r,today,h):
    d=peak_days(r,today); target=max(0,d-int(r.isankstinio_paskelbimo_dienos))
    sig=max(12,h*.55); prox=100*math.exp(-((target-h*.35)**2)/(2*sig*sig))
    return .62*prox+.38*float(r.bazinis_paklausos_balas)*10
def norm(s):
    s=pd.to_numeric(s,errors="coerce").fillna(0)
    if len(s)==0 or s.max()==s.min():return pd.Series([50]*len(s),index=s.index)
    return 100*(s-s.min())/(s.max()-s.min())

def gsc_agg(x,topics):
    if x.empty:return pd.DataFrame()
    q=find_col(x,{"query","queries","užklausa","uzklausa","paieškos užklausa"})
    imp=find_col(x,{"impressions","parodymai"}); clk=find_col(x,{"clicks","paspaudimai"})
    if q is None:return pd.DataFrame()
    if imp is None:x["_i"]=1;imp="_i"
    if clk is None:x["_c"]=0;clk="_c"
    out=[]
    for _,t in topics.iterrows():
        m=x[q].astype(str).str.lower().apply(lambda z:any(p.strip() in z for p in str(t.paieskos_frazes).lower().split("|") if p.strip()))
        out.append({"tema":t.tema,"gsc_impressions":pd.to_numeric(x.loc[m,imp],errors="coerce").fillna(0).sum(),
                    "gsc_clicks":pd.to_numeric(x.loc[m,clk],errors="coerce").fillna(0).sum()})
    return pd.DataFrame(out)

def trends_agg(x,topics):
    if x.empty:return pd.DataFrame()
    q=find_col(x,{"query","tema","term","keyword","užklausa","uzklausa"})
    cur=find_col(x,{"current","dabartinis","current_value","interest","value","reikšmė","reiksme"})
    prev=find_col(x,{"previous","ankstesnis","previous_value"})
    if q is None:return pd.DataFrame()
    out=[]
    for _,t in topics.iterrows():
        m=x[q].astype(str).str.lower().apply(lambda z:any(p.strip() in z for p in str(t.paieskos_frazes).lower().split("|") if p.strip()))
        z=x[m]; C=pd.to_numeric(z[cur],errors="coerce").fillna(0).sum() if cur else 0
        P=pd.to_numeric(z[prev],errors="coerce").fillna(0).sum() if prev else 0
        growth=(C-P)/max(P,1)*100 if prev else 0
        out.append({"tema":t.tema,"trends_interest":C,"trends_growth":growth})
    return pd.DataFrame(out)

def discover(frames,topics):
    rows=[]
    for x in frames:
        q=find_col(x,{"query","queries","užklausa","uzklausa","paieškos užklausa","term","keyword","tema"})
        val=find_col(x,{"impressions","parodymai","current","dabartinis","interest","value","reikšmė","reiksme"})
        prev=find_col(x,{"previous","ankstesnis","previous_value"})
        if q is None:continue
        for _,r in x.iterrows():
            query=str(r[q]).strip()
            if not query or query=="nan" or known_match(query,topics):continue
            V=float(pd.to_numeric(pd.Series([r[val] if val else 1]),errors="coerce").fillna(0).iloc[0])
            P=float(pd.to_numeric(pd.Series([r[prev] if prev else 0]),errors="coerce").fillna(0).iloc[0])
            growth=(V-P)/max(P,1)*100 if prev else 0
            rows.append((query,V,growth,toks(query)))
    buckets=defaultdict(list)
    for q,v,g,ts in rows:
        if not ts:continue
        candidates=([" ".join(ts[i:i+2]) for i in range(len(ts)-1)]+ts)
        key=candidates[0] if candidates else "kita"
        buckets[key].append((q,v,g))
    out=[]
    for k,its in buckets.items():
        sig=sum(x[1] for x in its); growth=np.mean([x[2] for x in its]) if its else 0
        opp=min(100,round(20*np.log1p(sig)+min(35,max(0,growth)*.35)+min(25,len(its)*5)))
        out.append({"tema":k.title(),"score":opp,"signalas":sig,"augimas":growth,
                    "pavyzdžiai":" | ".join(x[0] for x in its[:5])})
    return pd.DataFrame(out).sort_values("score",ascending=False) if out else pd.DataFrame()

def product_blueprint(topic,area,age,urgency):
    t=topic.lower()
    if area=="Matematika":
        fmt="Interaktyvi PPT + spausdinamas PDF"
        idea=f"„{topic}: mokausi per užduotis“"
        scope="30–40 trumpų užduočių, 3 sunkumo lygiai, aiškus atsakymo patikrinimas"
    elif "Lietuvi" in area or "Kalbin" in area:
        fmt="PDF kortelės / užduočių rinkinys"
        idea=f"„{topic}: atpažink, susiek ir pasakyk“"
        scope="24–36 kortelės, nuo atpažinimo iki savarankiško pritaikymo"
    elif "Social" in area or "Gyvenimo" in area:
        fmt="Situacijų kortelės PDF"
        idea=f"„{topic}: kaip pasielgtum tu?“"
        scope="20–30 gyvenimiškų situacijų su pasirinkimais ir aptarimo klausimais"
    else:
        fmt="Vaizdinis PDF rinkinys"
        idea=f"„{topic}: tyrinėju ir atrandu“"
        scope="24–32 kortelės / užduotys: atpažinimas, rūšiavimas, poravimas, paaiškinimas"
    if urgency=="greita":
        scope="12–20 kortelių / užduočių MVP, kad būtų galima paskelbti per 1–2 dienas"
    return idea,fmt,scope

topics=load_topics()
st.title("📡 Protuoliukas Trend Radar — V4")
st.caption("Vienas ekranas: žinomos temos + naujos nišos + konkretus produkto planas + paskelbimo data.")

with st.sidebar:
    today=st.date_input("Šiandien",date.today())
    gfile=st.file_uploader("Search Console CSV/XLSX",type=["csv","xlsx"],key="g")
    tfile=st.file_uploader("Google Trends CSV/XLSX",type=["csv","xlsx"],key="t")
    other=st.file_uploader("Kitas raktažodžių failas",type=["csv","xlsx"],key="o")
    st.divider()
    pdf_days=st.number_input("Mažas PDF – dienų",1,14,2)
    medium_days=st.number_input("Vidutinis PDF – dienų",1,30,4)
    ppt_days=st.number_input("PPT – dienų",1,30,5)
    st.caption("Šie terminai naudojami rekomenduojant, ar dar spėsi sukurti pilną priemonę.")

g=read_any(gfile); tr=read_any(tfile); oth=read_any(other)
frames=[x for x in [g,tr,oth] if not x.empty]

# Known topic radar
df=topics.copy()
ga=gsc_agg(g,df)
ta=trends_agg(tr,df)
if len(ga):df=df.merge(ga,on="tema",how="left")
else:df["gsc_impressions"]=0;df["gsc_clicks"]=0
if len(ta):df=df.merge(ta,on="tema",how="left")
else:df["trends_interest"]=0;df["trends_growth"]=0
for c in ["gsc_impressions","gsc_clicks","trends_interest","trends_growth"]:df[c]=df[c].fillna(0)
df["search_signal"]=norm(np.log1p(df.gsc_impressions))
df["trend_signal"]=np.clip(50+df.trends_growth,0,100) if len(ta) else 50
for h in [7,30,90]:
    df[f"calendar_{h}"]=df.apply(lambda r:cal_score(r,today,h),axis=1)
    if len(ga) or len(ta):
        df[f"{h}d"]=(.60*df[f"calendar_{h}"]+.22*df.trend_signal+.18*df.search_signal).round().clip(0,100)
    else:df[f"{h}d"]=df[f"calendar_{h}"].round().clip(0,100)
df["paskelbti_po"]=df.apply(lambda r:peak_days(r,today)-int(r.isankstinio_paskelbimo_dienos),axis=1)
df["priority"]=df[["7d","30d","90d"]].max(axis=1)
def action(r):
    p=r.paskelbti_po; prod=int(r.gamybos_dienos); score=max(r["7d"],r["30d"])
    if p < -5:return "📣 REKLAMUOTI / PRALEISTI"
    if p <= prod+3 and score>=60:return "🔥 KURTI DABAR"
    if p<=30 and score>=55:return "🟠 PLANUOTI"
    if p<=90:return "🔭 RUOŠTIS"
    return "⚪ VĖLIAU"
df["veiksmas"]=df.apply(action,axis=1)

new=discover(frames,topics)
c1,c2,c3,c4=st.columns(4)
c1.metric("🔥 Kurti dabar",(df.veiksmas=="🔥 KURTI DABAR").sum())
c2.metric("🟠 Planuoti",(df.veiksmas=="🟠 PLANUOTI").sum())
c3.metric("🚨 Naujos nišos",len(new) if len(new) else 0)
c4.metric("Stebimų temų",len(df))

if not frames:
    st.warning("Gyvi paieškų failai dar neįkelti. Žinomų temų prognozė veikia pagal ugdymo/sezoninį ciklą; naujų nišų skiltis aktyvuosis įkėlus paieškų duomenis.")

tabs=st.tabs(["🏠 ŠIANDIEN","🔥 Produktų planai","🚨 Naujos nišos","📈 7/30/90","🔬 Kodėl?"])

with tabs[0]:
    st.subheader("Ką verta daryti dabar")
    top=df.sort_values(["priority"],ascending=False).head(12)
    for _,r in top.iterrows():
        deadline=today+timedelta(days=max(0,int(r.paskelbti_po)))
        st.markdown(f"### {r.veiksmas} · {r.tema}")
        st.write(f"**{r.amzius} • {r.sritis}**  |  7 d. **{int(r['7d'])}** · 30 d. **{int(r['30d'])}** · 90 d. **{int(r['90d'])}**")
        st.write(f"Rekomenduojama paskelbti: **{'dabar' if r.paskelbti_po<=0 else deadline.strftime('%Y-%m-%d')}**")
        st.divider()

with tabs[1]:
    st.subheader("Konkrečios naujų priemonių specifikacijos")
    for _,r in df.sort_values("30d",ascending=False).head(15).iterrows():
        urgency="greita" if r.paskelbti_po<=max(pdf_days,2)+3 else "normali"
        idea,fmt,scope=product_blueprint(r.tema,r.sritis,r.amzius,urgency)
        deadline=today+timedelta(days=max(0,int(r.paskelbti_po)))
        with st.expander(f"{r.tema} — {int(r['30d'])}/100 • {r.veiksmas}"):
            st.write(f"**Produkto idėja:** {idea}")
            st.write(f"**Kam:** {r.amzius} • {r.sritis}")
            st.write(f"**Formatas:** {fmt}")
            st.write(f"**Apimtis:** {scope}")
            st.write(f"**Paskelbti:** {'kuo greičiau' if r.paskelbti_po<=0 else 'iki '+deadline.strftime('%Y-%m-%d')}")
            st.write(f"**Paieškos kryptys:** {str(r.paieskos_frazes).replace('|', ', ')}")
            st.caption(f"Pagrindimas: kalendorinis 30 d. balas {int(r.calendar_30)}/100; Trends augimas {r.trends_growth:.1f}%; GSC parodymai {int(r.gsc_impressions)}.")

with tabs[2]:
    if new.empty:
        st.info("Įkelk paieškų failą – čia V4 parodys užklausų klasterius, kurių 130 temų bazėje dar nėra.")
    else:
        st.dataframe(new,use_container_width=True,hide_index=True)
        for _,r in new.head(10).iterrows():
            with st.expander(f"🚨 {r.tema} — galimybė {int(r.score)}/100"):
                st.write(f"**Aptiktos užklausos:** {r.pavyzdžiai}")
                st.write("**Pirmas veiksmas:** jei tema pedagogiškai prasminga, sukurti mažą bandomąją priemonę arba įtraukti temą į stebėjimą 1–2 savaitėms.")
                st.write("**Svarbu:** naujai aptiktai temai V4 dar nepriskiria išgalvotos būsimos piko datos – tam reikia sukaupti jos laiko eilutę.")

with tabs[3]:
    st.dataframe(df.sort_values("priority",ascending=False)[["veiksmas","tema","amzius","sritis","7d","30d","90d","paskelbti_po"]],
                 use_container_width=True,hide_index=True)
    st.download_button("Atsisiųsti planą CSV",df.to_csv(index=False).encode("utf-8-sig"),"protuoliukas_v4_planas.csv","text/csv")

with tabs[4]:
    st.markdown("""
### Kaip V4 priima sprendimą
**Žinomoms temoms** derinamas Lietuvos ugdymo/sezoninis ciklas ir, jei įkelti, faktiniai Search Console bei Google Trends signalai.
**Naujoms temoms** sistema pirmiausia ieško pasikartojančių, žodyne dar neegzistuojančių užklausų. Ji sąmoningai nepriskiria joms fiktyvios piko datos.
""")
    st.dataframe(df.sort_values("priority",ascending=False)[["tema","calendar_30","trends_growth","gsc_impressions","search_signal","trend_signal","30d"]],
                 use_container_width=True,hide_index=True)

st.caption("V4 – sprendimų paramos prototipas. Balai yra prioritetai, ne garantuoti būsimi pardavimai.")
