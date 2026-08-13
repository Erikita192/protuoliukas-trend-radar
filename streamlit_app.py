
import streamlit as st
import pandas as pd
import math
from datetime import date, timedelta

st.set_page_config(page_title="Protuoliukas Trend Radar V6", page_icon="📡", layout="wide")
MONTH_NUM={"sausis":1,"vasaris":2,"kovas":3,"balandis":4,"gegužė":5,"birželis":6,"liepa":7,"rugpjūtis":8,"rugsėjis":9,"spalis":10,"lapkritis":11,"gruodis":12}

@st.cache_data
def load():
    return pd.read_csv("microtopics.csv")

def peak_days(r,today):
    vals=[]
    for x in str(r.piko_menesiai).split(","):
        pm=MONTH_NUM[x.strip()]
        y=today.year if pm>=today.month else today.year+1
        vals.append((date(y,pm,15)-today).days)
    return min(vals)

def score(r,today,h):
    d=peak_days(r,today)
    publish=max(0,d-int(r.isankstinio_paskelbimo_dienos))
    sigma=max(12,h*.55)
    time_score=100*math.exp(-((publish-h*.35)**2)/(2*sigma*sigma))
    ever=float(r.evergreen)*20
    sales={"žemas":30,"vidutinis":55,"aukštas":78,"labai aukštas":95}.get(str(r.pardavimo_potencialas).lower(),60)
    comp={"žema":90,"vidutinė":72,"aukšta":52}.get(str(r.konkurencija).lower(),65)
    return round(.50*time_score+.20*ever+.20*sales+.10*comp)

def action(r,today):
    d=peak_days(r,today)
    publish=d-int(r.isankstinio_paskelbimo_dienos)
    if publish < -7: return "📣 REKLAMUOTI / PRALEISTI", publish
    if publish <= int(r.gamybos_sanaudos_d)+3: return "🔥 KURTI DABAR", publish
    if publish <= 30: return "🟠 PLANUOTI", publish
    if publish <= 90: return "🔭 RUOŠTIS", publish
    return "⚪ VĖLIAU", publish

def stars(n):
    return "🌲"*int(n)+"○"*(5-int(n))

df=load()
st.title("📡 Protuoliukas Trend Radar — V6")
st.caption("Konkrečios mikrotemos • 3–14 m. • 5–8 klasės • Evergreen • artėjantys TOPai • išsamūs produktų planai")

with st.sidebar:
    today=st.date_input("Šiandien", date.today())
    age=st.multiselect("Amžius", sorted(df.amzius.unique()))
    area=st.multiselect("Sritis", sorted(df.sritis.unique()))
    st.divider()
    st.markdown("**V6 vertina:** laiką + evergreen + pardavimo potencialą + konkurenciją + gamybos sąnaudas.")

for h in [7,30,90]:
    df[f"{h}d"]=df.apply(lambda r:score(r,today,h),axis=1)
tmp=df.apply(lambda r:action(r,today),axis=1)
df["veiksmas"]=[x[0] for x in tmp]
df["paskelbti_po"]=[x[1] for x in tmp]
df["prioritetas"]=df[["7d","30d","90d"]].max(axis=1)

if age:
    df=df[df.amzius.isin(age)]
if area:
    df=df[df.sritis.isin(area)]

c1,c2,c3,c4=st.columns(4)
c1.metric("🔥 Kurti dabar", int((df.veiksmas=="🔥 KURTI DABAR").sum()))
c2.metric("🟠 Planuoti", int((df.veiksmas=="🟠 PLANUOTI").sum()))
c3.metric("🌲 Evergreen 5/5", int((df.evergreen==5).sum()))
c4.metric("Temų / mikrotemų", len(df))

tabs=st.tabs(["🏠 ŠIANDIEN","🚀 ARTĖJANTYS TOPAI","🌲 EVERGREEN","📘 DARŽELIS–4 KL.","🎓 5–8 KLASĖS","💡 PRODUKTŲ PLANAI","📊 7/30/90"])

with tabs[0]:
    st.subheader("Ką verta kurti dabar")
    top=df.sort_values("prioritetas",ascending=False).head(12)
    for _,r in top.iterrows():
        deadline=today+timedelta(days=max(0,int(r.paskelbti_po)))
        st.markdown(f"### {r.veiksmas} · {r.tema} → {r.mikrotema}")
        st.write(f"**{r.amzius} • {r.sritis}**")
        st.write(f"7 d. **{int(r['7d'])}** · 30 d. **{int(r['30d'])}** · 90 d. **{int(r['90d'])}**")
        st.write(f"**Publikuoti:** {'dabar' if r.paskelbti_po<=0 else deadline.strftime('%Y-%m-%d')}")
        st.write(f"**Evergreen:** {stars(r.evergreen)} · **Konkurencija:** {r.konkurencija} · **Pardavimo potencialas:** {r.pardavimo_potencialas}")
        st.divider()

with tabs[1]:
    st.subheader("🚀 Artėjantys TOPai – ne tik matematika ir lietuvių")
    cross=df[df.sritis.str.contains("Pasaulio|etnokult|Gyvenimo|STEAM|Karjeros|informatika|Gamtos",case=False,regex=True)]
    for _,r in cross.sort_values("30d",ascending=False).head(12).iterrows():
        st.markdown(f"### {r.tema} → {r.mikrotema}")
        st.write(f"**Kam:** {r.amzius} • {r.sritis}")
        st.write(f"**30 d. balas:** {int(r['30d'])}/100 · **Evergreen:** {stars(r.evergreen)} · **Pardavimo potencialas:** {r.pardavimo_potencialas}")
        st.write(f"**Produkto kryptis:** {r.produkto_ideja}")
        st.divider()

with tabs[2]:
    st.subheader("🌲 Evergreen")
    ev=df.sort_values(["evergreen","30d"],ascending=[False,False]).head(20)
    st.dataframe(ev[["tema","mikrotema","amzius","sritis","evergreen","pardavimo_potencialas","konkurencija","formatas"]],
                 use_container_width=True,hide_index=True)

with tabs[3]:
    st.subheader("Darželis, priešmokyklinis ir 1–4 klasės")
    part=df[df.amzius.isin(["4–6 m.","5–7 m.","6–8 m.","5–8 m.","8–10 m.","8–11 m.","9–11 m."])]
    st.dataframe(part.sort_values("30d",ascending=False)[["tema","mikrotema","amzius","sritis","30d","veiksmas"]],
                 use_container_width=True,hide_index=True)

with tabs[4]:
    st.subheader("🎓 5–8 klasės")
    part=df[df.amzius.isin(["10–12 m.","10–13 m.","11–14 m.","10–14 m.","7–14 m.","8–14 m."])]
    st.dataframe(part.sort_values("30d",ascending=False)[["tema","mikrotema","amzius","sritis","30d","veiksmas","evergreen","pardavimo_potencialas"]],
                 use_container_width=True,hide_index=True)

with tabs[5]:
    st.subheader("💡 Išsamūs produktų planai")
    for _,r in df.sort_values("30d",ascending=False).head(18).iterrows():
        with st.expander(f"{r.tema} → {r.mikrotema} · {int(r['30d'])}/100"):
            st.write(f"**Produkto idėja:** {r.produkto_ideja}")
            st.write(f"**Kam:** {r.amzius} • {r.sritis}")
            st.write(f"**Formatas:** {r.formatas}")
            st.write(f"**Apytikslė gamyba:** {int(r.gamybos_sanaudos_d)} d.")
            st.write(f"**Evergreen:** {stars(r.evergreen)} ({int(r.evergreen)}/5)")
            st.write(f"**Konkurencija:** {r.konkurencija}")
            st.write(f"**Pardavimo potencialas:** {r.pardavimo_potencialas}")
            st.markdown("**Konkrečių užduočių pavyzdžiai:**")
            for ex in str(r.uzduociu_pavyzdziai).split(" | "):
                st.write("• "+ex)
            st.markdown("**Kaip plėsti:**")
            st.write("Atpažinimas → taikymas → klaidos paieška / paaiškinimas. Jei Evergreen 4–5/5, verta kurti pilnesnę ilgaamžę versiją.")

with tabs[6]:
    st.dataframe(df.sort_values("prioritetas",ascending=False)[["veiksmas","tema","mikrotema","amzius","sritis","7d","30d","90d","evergreen","konkurencija","pardavimo_potencialas"]],
                 use_container_width=True,hide_index=True)
    st.download_button("Atsisiųsti V6 planą CSV",df.to_csv(index=False).encode("utf-8-sig"),"trend_radar_v6.csv","text/csv")

st.caption("V6 – sprendimų paramos radaras. Balai yra prioritetai, ne garantuoti būsimi pardavimai.")
