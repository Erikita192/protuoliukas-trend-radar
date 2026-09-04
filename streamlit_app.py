
import streamlit as st
import pandas as pd
import math, re, requests, xml.etree.ElementTree as ET, io, json, hashlib, zipfile, os
from pathlib import Path
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse
from urllib.parse import quote_plus

st.set_page_config(page_title="Protuoliukas Trend Radar V11.5", page_icon="📡", layout="wide")

# --- V11.5 universal visual system: same readable palette in light/dark mode ---
st.markdown("""
<style>
:root {
  --radar-accent: #5f766a;
  --radar-accent-strong: #465c52;
  --radar-accent-soft: #dfe9e4;
  --radar-border: #c9d7d0;
  --radar-panel: #edf3f0;
  --radar-panel-2: #f6f8f7;
  --radar-ink: #24312b;
  --radar-muted: #52645b;
}
.block-container {max-width:1480px;padding-top:1.15rem;padding-bottom:2.2rem;}
h1 {letter-spacing:-.02em;margin-bottom:.15rem!important;} h2,h3{letter-spacing:-.01em;}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--radar-border);overflow-x:auto;}
.stTabs [data-baseweb="tab"]{height:2.75rem;padding:0 .8rem;border-radius:.55rem .55rem 0 0;white-space:nowrap;}
.stTabs [aria-selected="true"]{background:var(--radar-accent-soft)!important;color:var(--radar-ink)!important;font-weight:650;}
/* Universal cards: deliberately independent of Streamlit light/dark theme. */
div[data-testid="stExpander"], div[data-testid="stMetric"]{border:1px solid var(--radar-border)!important;border-radius:.8rem!important;background:var(--radar-panel)!important;color:var(--radar-ink)!important;overflow:hidden;}
div[data-testid="stExpander"] summary{background:var(--radar-panel)!important;color:var(--radar-ink)!important;}
div[data-testid="stExpander"] summary:hover{background:var(--radar-accent-soft)!important;}
div[data-testid="stExpander"] summary *, div[data-testid="stExpander"] [data-testid="stExpanderDetails"] *, div[data-testid="stMetric"] *{color:var(--radar-ink)!important;}
div[data-testid="stExpander"] [data-testid="stExpanderDetails"]{background:var(--radar-panel-2)!important;padding-top:.75rem;}
div[data-testid="stExpander"] pre, div[data-testid="stExpander"] code{background:#e3ebe7!important;color:var(--radar-ink)!important;}
div[data-testid="stMetric"]{padding:.7rem .85rem;}
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:.65rem;border-color:var(--radar-border);}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:var(--radar-accent);border-color:var(--radar-accent);color:white!important;}
div[data-baseweb="select"]>div,div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stDateInput"] input,div[data-testid="stFileUploader"] section{border-radius:.65rem!important;}
section[data-testid="stSidebar"]{border-right:1px solid var(--radar-border);}
section[data-testid="stSidebar"]>div{background:var(--radar-panel-2)!important;color:var(--radar-ink)!important;}
section[data-testid="stSidebar"] *{color:var(--radar-ink);}
div[data-testid="stAlert"]{border-radius:.75rem;}
@media (max-width: 700px){
  .block-container{padding-left:.75rem;padding-right:.75rem;padding-top:.75rem;}
  h1{font-size:1.65rem!important;} h2{font-size:1.35rem!important;} h3{font-size:1.08rem!important;}
  .stTabs [data-baseweb="tab"]{padding:0 .58rem;height:2.55rem;font-size:.88rem;}
  div[data-testid="stExpander"] [data-testid="stExpanderDetails"]{padding-left:.7rem!important;padding-right:.7rem!important;}
  hr{margin:.7rem 0!important;}
}
</style>
""", unsafe_allow_html=True)
MONTH_NUM={"sausis":1,"vasaris":2,"kovas":3,"balandis":4,"gegužė":5,"birželis":6,"liepa":7,"rugpjūtis":8,"rugsėjis":9,"spalis":10,"lapkritis":11,"gruodis":12}
SHOP="https://mokymopriemones.eu/"

@st.cache_data
def load_topics():
    return pd.read_csv("microtopics.csv")

@st.cache_data
def load_school_calendar():
    x=pd.read_csv("school_calendar_2026_2027.csv")
    x["start"]=pd.to_datetime(x["start"]).dt.date
    x["end"]=pd.to_datetime(x["end"]).dt.date
    return x

@st.cache_data
def load_occasions():
    x=pd.read_csv("occasions_2026_2027.csv")
    x["date"]=pd.to_datetime(x["date"]).dt.date
    return x

@st.cache_data
def load_verified_program_timing():
    return pd.read_csv("verified_program_timing_v9.csv")

@st.cache_data
def load_program_membership():
    return pd.read_csv("program_membership_v9.csv")

@st.cache_data
def load_parent_demand_calendar():
    x=pd.read_csv("parent_demand_calendar_v10.csv")
    x["start"]=pd.to_datetime(x["start"]).dt.date
    x["end"]=pd.to_datetime(x["end"]).dt.date
    return x

@st.cache_data
def load_occasion_product_ideas():
    return pd.read_csv("occasion_product_ideas_v10.csv")

SCHOOL_CAL=load_school_calendar()
OCCASIONS=load_occasions()
VERIFIED_TIMING=load_verified_program_timing()
PROGRAM_MEMBERSHIP=load_program_membership()
PARENT_DEMAND=load_parent_demand_calendar()
OCCASION_IDEAS=load_occasion_product_ideas()

def is_school_holiday(day):
    for _,x in SCHOOL_CAL[SCHOOL_CAL["type"]=="atostogos"].iterrows():
        if x["start"]<=day<=x["end"]:
            return True
    return False

# Precompute the effective school calendar ONCE.
# V8.1 recalculated it thousands of times while scoring cards, which could leave
# the main Streamlit area blank for a long time after the date field appeared.
_EFFECTIVE_SCHOOL_DAYS=[]
_d=date(2026,9,1)
while _d<date(2027,7,1):
    if _d.weekday()<5 and not is_school_holiday(_d):
        _EFFECTIVE_SCHOOL_DAYS.append(_d)
    _d+=timedelta(days=1)

_SCHOOL_WEEK_START={}
for _i,_day in enumerate(_EFFECTIVE_SCHOOL_DAYS):
    _week=(_i//5)+1
    if _week not in _SCHOOL_WEEK_START:
        _SCHOOL_WEEK_START[_week]=_day

def instruction_days_between(start_day,end_day):
    """Fast count of effective school days from the precomputed calendar."""
    if end_day<start_day:
        return 0
    return sum(1 for d in _EFFECTIVE_SCHOOL_DAYS if start_day<=d<=end_day)

def school_week_for_date(day):
    """1-based effective school week from 2026-09-01, excluding school holidays."""
    if day<date(2026,9,1):
        return None
    # Only ~200 effective school days; still much cheaper than rebuilding the calendar.
    count=0
    for d in _EFFECTIVE_SCHOOL_DAYS:
        if d<=day:
            count+=1
        else:
            break
    return max(1,math.ceil(count/5)) if count else 1

def school_date_for_week(week_no):
    """O(1) lookup of the first effective school day in a school-week number."""
    return _SCHOOL_WEEK_START.get(int(week_no))

def shift_before_holiday(target):
    """
    If a demand/publish point falls immediately after a holiday,
    move preparation signal to the last school week before it.
    """
    for _,x in SCHOOL_CAL[SCHOOL_CAL["type"]=="atostogos"].iterrows():
        if x["end"] < target <= x["end"]+timedelta(days=7):
            return x["start"]-timedelta(days=3)
    return target


def _norm(s):
    s=str(s).lower().replace("–","-").replace("—","-")
    s=re.sub(r"[^a-ząčęėįšųūž0-9%]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def _tokens(s, min_len=4):
    stop={"tema","ugdymas","užduotys","užduotis","priemonė","priemonės","vaikams",
          "mokymas","mokytis","kortelės","rinkinys","pagal","atlikti","veiksmą",
          "taikymas","situacijoje","atpažinti","klaidos","paieška"}
    return {w for w in _norm(s).split() if len(w)>=min_len and w not in stop}

def keyword_overlap(a,b):
    return len(_tokens(a) & _tokens(b))

def _age_bounds(age_text):
    nums=[int(x) for x in re.findall(r"\d+",str(age_text))]
    if not nums:
        return (3,99)
    if len(nums)==1:
        return (nums[0],nums[0])
    return (min(nums[0],nums[1]),max(nums[0],nums[1]))

GRADE_AGES={
    1:(6,8),2:(7,9),3:(8,10),4:(9,11),
    5:(10,12),6:(11,13),7:(12,14),8:(13,15)
}

def _grade_relevant(r, grade):
    try:g=int(grade)
    except:return True
    lo,hi=_age_bounds(getattr(r,"amzius",""))
    glo,ghi=GRADE_AGES.get(g,(3,99))
    return max(lo,glo) <= min(hi,ghi)

def _subject_relevant(r, subject):
    area=_norm(getattr(r,"sritis",""))
    subject=_norm(subject)
    if "matemat" in subject:
        return "matemat" in area
    if "lietuvi" in subject:
        return ("lietuvi" in area) or ("kalbin" in area)
    return keyword_overlap(area,subject)>0

def _topic_match_score(r, official_topic, aliases):
    query=_norm(f"{getattr(r,'tema','')} {getattr(r,'mikrotema','')}")
    target=_norm(f"{official_topic} {aliases}")
    qtok=_tokens(query)
    ttok=_tokens(target)
    overlap=len(qtok & ttok)
    score=overlap*4
    theme=_norm(getattr(r,"tema",""))
    micro=_norm(getattr(r,"mikrotema",""))
    official=_norm(official_topic)

    if theme and theme in target:
        score+=7
    if official and official in query:
        score+=10

    for phrase in [
        "vienodais vardikliais","skirtingais vardikliais","trupmenų palyginimas",
        "trupmenų sudėtis","trupmenų atimtis","sveikieji skaičiai",
        "tiesioginis proporcingumas","atvirkštinis proporcingumas",
        "lygčių sistemos","raidiniai reiškiniai","kvadratinė šaknis",
        "kubinė šaknis","finansiniai skaičiavimai","duomenų interpretavimas",
        "tikimybės","plokščios figūros","erdvės figūros"
    ]:
        if phrase in micro and phrase in target:
            score+=12
    return score

def occasion_signal(r,today):
    text=f"{r.tema} {r.mikrotema} {r.sritis}"
    best=None
    weights={"vidutinis":6,"aukštas":12,"labai aukštas":18}
    for _,o in OCCASIONS.iterrows():
        delta=(o["date"]-today).days
        if -3<=delta<=35:
            ov=keyword_overlap(text,o["keywords"])
            if ov>0:
                score=weights.get(str(o["commercial_weight"]),6)+min(8,ov*2)
                if best is None or score>best["score"]:
                    best={"score":score,"occasion":o["occasion"],"date":o["date"],
                          "delta":delta,"confidence":95}
    return best

def verified_program_windows(r,today):
    """
    Only class-specific, narrow windows may create a program peak.
    Hard safety rule: >3 school weeks is rejected.
    """
    matches=[]
    for _,pw in VERIFIED_TIMING.iterrows():
        try:
            w1,w2=int(pw["week_start"]),int(pw["week_end"])
        except Exception:
            continue
        if w2 < w1 or (w2-w1+1)>3:
            continue
        if not _subject_relevant(r,pw["subject"]):
            continue
        if not _grade_relevant(r,pw["grade"]):
            continue

        mscore=_topic_match_score(r,pw["official_topic"],pw["aliases"])
        if mscore < 9:
            continue

        startd=school_date_for_week(w1)
        end_start=school_date_for_week(w2)
        if startd is None or end_start is None:
            continue
        endd=end_start+timedelta(days=4)

        matches.append({
            "grade":int(pw["grade"]),
            "subject":str(pw["subject"]),
            "official_topic":str(pw["official_topic"]),
            "start":startd,
            "end":endd,
            "week_start":w1,
            "week_end":w2,
            "week_window":f"{w1}–{w2}",
            "confidence":int(pw["confidence"]),
            "source_count":int(pw["source_count"]),
            "source_type":str(pw["source_type"]),
            "source":str(pw["source_url"]),
            "source_note":str(pw["source_note"]),
            "match_score":mscore
        })

    # A broad related chapter must not beat the concrete microtopic merely because
    # it occurs earlier. Keep the strongest semantic match PER CLASS first.
    best_by_grade={}
    for x in matches:
        g=x["grade"]
        if g not in best_by_grade or x["match_score"]>best_by_grade[g]["match_score"]:
            best_by_grade[g]=x
    matches=list(best_by_grade.values())

    matches.sort(key=lambda x: (
        0 if x["end"] >= today-timedelta(days=3) else 1,
        max(0,(x["start"]-today).days) if x["end"] >= today-timedelta(days=3) else 999,
        -x["match_score"],
        x["grade"]
    ))
    return matches

def program_memberships(r):
    """Confirms class/program membership, never the date."""
    out=[]
    for _,pm in PROGRAM_MEMBERSHIP.iterrows():
        if not _subject_relevant(r,pm["subject"]):
            continue
        if not _grade_relevant(r,pm["grade"]):
            continue
        mscore=_topic_match_score(r,pm["program_topic"],pm["aliases"])
        if mscore < 9:
            continue
        out.append({
            "grade":int(pm["grade"]),
            "subject":str(pm["subject"]),
            "program_topic":str(pm["program_topic"]),
            "source":str(pm["source_url"]),
            "source_note":str(pm["source_note"]),
            "match_score":mscore
        })
    out.sort(key=lambda x:(-x["match_score"],x["grade"]))
    return out

def program_signal(r,today):
    windows=verified_program_windows(r,today)
    memberships=program_memberships(r)
    if windows:
        primary=windows[0]
        primary["all_windows"]=windows
        primary["memberships"]=memberships
        return primary
    if memberships:
        return {
            "timing_verified":False,
            "memberships":memberships,
            "all_windows":[],
            "confidence":25
        }
    return None

def parent_signal(r):
    t=_norm(f"{r.tema} {r.mikrotema}")
    return any(k in t for k in [
        "raid","abėc","skaič","rašym","rašyt","skaity","emoc","kūnas","spalv","forma",
        "sudėt","atimt","daugyb","dalyb","dėmes","pastab","mokykl"
    ])

def parent_window_topics(x):
    raw=[k.strip() for k in str(x.get("keywords","")).split(";") if k.strip()]
    out=[]
    for k in raw:
        if _norm(k) not in [_norm(y) for y in out]:
            out.append(k)
    return out[:7]

def parent_window_stage(x,today):
    if x["start"] <= today <= x["end"]:
        return "Didžiausias potencialas" if int(x["strength"])>=92 else ("Paklausa aukšta" if int(x["strength"])>=85 else "Aktualu dabar")
    if x["start"] > today:
        return "Paklausa kyla" if (x["start"]-today).days<=14 else "Artėja"
    return "Baigiasi"

def parent_demand_signal(r,today):
    """A real parent-demand time window, not merely a +6 score bonus."""
    text=f"{r.tema} {r.mikrotema} {r.sritis}"
    best=None
    for _,x in PARENT_DEMAND.iterrows():
        # Include current/near-future windows so SAVAITĖ can be populated before they start.
        if x["end"] < today-timedelta(days=3) or x["start"] > today+timedelta(days=35):
            continue
        ov=keyword_overlap(text,x["keywords"])
        if ov<=0:
            continue
        # Suggested buying peak is early in the strongest part of the window.
        window_len=max(1,(x["end"]-x["start"]).days)
        peak=x["start"]+timedelta(days=min(5,max(2,window_len//3)))
        score=int(x["strength"])+min(10,ov*2)
        cand={
            "score":min(100,score),
            "label":str(x["label"]),
            "start":x["start"],
            "end":x["end"],
            "peak":peak,
            "note":str(x["note"]),
            "confidence":82 if int(x["strength"])>=85 else 72,
            "topics":parent_window_topics(x),
            "audience":"TĖVAI"
        }
        if best is None or cand["score"]>best["score"]:
            best=cand
    return best

def signal_stack(r,today):
    ps=program_signal(r,today)
    osig=occasion_signal(r,today)
    pds=parent_demand_signal(r,today)
    signals=[]
    extra=0

    if ps and ps.get("all_windows"):
        signals.append("📚 patikrintas klasės planavimo langas")
        extra+=14
    elif ps and ps.get("memberships"):
        signals.append("📘 tema patvirtinta programoje, data dar nepatvirtinta")
        extra+=4

    if osig:
        signals.append(f"📅 PROGA · {osig['occasion']}")
        extra+=min(18,osig["score"])

    if int(r.evergreen)>=4:
        signals.append("🌿 evergreen")
        extra+=6

    if pds:
        signals.append(f"👨‍👩‍👧 TĖVAI · {pds['start'].strftime('%m-%d')}–{pds['end'].strftime('%m-%d')}")
        extra+=min(28,max(10,(pds["score"]-50)//2))
    elif parent_signal(r):
        signals.append("👨‍👩‍👧 TĖVAI · evergreen paklausa")
        extra+=4

    return ps,osig,pds,signals,extra

def seasonal_peak(r,today):
    vals=[]
    for x in str(getattr(r,"piko_menesiai","")).split(","):
        pm=MONTH_NUM.get(x.strip())
        if not pm:
            continue
        y=today.year if pm>=today.month else today.year+1
        vals.append(date(y,pm,15))
    if not vals:
        return today+timedelta(days=180)
    future=[d for d in vals if d>=today-timedelta(days=5)]
    return min(future or vals,key=lambda d:abs((d-today).days))

def pedagogical_peak(r,today):
    """
    V9 hierarchy:
    1) verified 2–3 week class timing;
    2) fixed education occasion;
    3) low-confidence seasonality.
    Program membership without timing never creates a peak.
    """
    ps,osig,pds,signals,extra=signal_stack(r,today)
    candidates=[]

    if ps and ps.get("all_windows"):
        w=ps["all_windows"][0]
        teaching_start=w["start"]
        purchase_peak=shift_before_holiday(teaching_start-timedelta(days=5))
        candidates.append({
            "peak":purchase_peak,
            "kind":"programa",
            "use_date":teaching_start,
            "detail":w,
            "confidence":int(w["confidence"])
        })

    if osig:
        lead=5 if osig["score"]>=16 else 3
        purchase_peak=shift_before_holiday(osig["date"]-timedelta(days=lead))
        candidates.append({
            "peak":purchase_peak,
            "kind":"proga",
            "use_date":osig["date"],
            "detail":osig,
            "confidence":95
        })

    if pds:
        parent_target=pds["peak"]
        candidates.append({
            "peak":parent_target,
            "kind":"tevai",
            "use_date":pds["end"],
            "detail":pds,
            "confidence":int(pds["confidence"])
        })

    eligible=[c for c in candidates if c["peak"]>=today-timedelta(days=5)]
    if eligible:
        chosen=min(eligible,key=lambda c:(c["peak"]-today).days)
        return (chosen["peak"],chosen["kind"],chosen["use_date"],chosen["detail"],
                signals,extra,chosen["confidence"])

    seasonal=seasonal_peak(r,today)
    confidence=55 if (parent_signal(r) or "ikimokykl" in _norm(r.sritis) or "dekor" in _norm(r.sritis)) else 48
    return seasonal,"sezonika",seasonal,None,signals,extra,confidence

def date_confidence(r,today):
    return int(pedagogical_peak(r,today)[6])

def date_confidence_label(conf):
    if conf>=88:return "🟢 AUKŠTA"
    if conf>=65:return "🟡 ORIENTACINĖ"
    return "⚪ ŽEMA"

def fp(r):
    return f"{str(r.tema).strip().lower()}::{str(r.mikrotema).strip().lower()}"

@st.cache_resource
def supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_creation_lead():
    return int(st.session_state.get("creation_lead_days",3))

def effort_level(r):
    text=(" ".join([str(getattr(r,"produkto_ideja","")),str(getattr(r,"uzduociu_pavyzdziai","")),str(getattr(r,"formatas",""))])).lower()
    score=1
    for x in ["40 ","50 ","60 ","72 ","100 ","situacij","individual","skirtingų iliustr","interaktyv","animacij","trigger","daug iliustr"]:
        if x in text: score+=2
    for x in ["20 ","30 ","kortel","skaidr","iliustr","powerpoint","ppt"]:
        if x in text: score+=1
    return "🔴 DIDELĖ" if score>=6 else ("🟡 VIDUTINĖ" if score>=3 else "🟢 MAŽA")

def effort_bonus(r):
    return {"🟢 MAŽA":8,"🟡 VIDUTINĖ":3,"🔴 DIDELĖ":-4}[effort_level(r)]

def estimated_creation_days(r):
    """Realistiškas rezervas pagal vartotojo tempą + konkrečios idėjos apimtį."""
    base=get_creation_lead()
    lvl=effort_level(r)
    if lvl=="🟢 MAŽA": return max(1,base-1)
    if lvl=="🔴 DIDELĖ": return base+2
    return base

def execution_fit(r,today):
    """Kiek ši idėja praktiškai įgyvendinama dabar, o ne vien teoriškai stipri."""
    start,pub,peak,last=timing(r,today)
    need=estimated_creation_days(r)
    until_pub=(pub-today).days
    until_peak=(peak-today).days
    if today>last: return -24
    if until_peak<0: return -14
    if until_pub>=need: return 14
    if until_peak>=need: return 7
    if effort_level(r)=="🟢 MAŽA" and until_peak>=1: return 2
    return -10

def execution_action(r,today,act,prod=None):
    """Veiksmas pagal tai, ar realiai dar spėjama, neperrašant tikros piko datos."""
    start,pub,peak,last=timing(r,today)
    need=estimated_creation_days(r)
    until_pub=(pub-today).days
    until_peak=(peak-today).days
    if today>last:
        return "🗓️ RUOŠTI KITAM LANGUI", "Šio paklausos lango aktyvioji dalis jau baigėsi."
    if until_peak<0:
        if prod is not None: return "📣 DAR PALAIKYTI MATOMUMĄ", f"Pikas buvo prieš {abs(until_peak)} d.; naujos didelės priemonės šiam pikui nebeskubink."
        return "🗓️ RUOŠTI KITAM LANGUI", f"Pikas buvo prieš {abs(until_peak)} d.; idėja gera, bet naujai priemonei šis langas jau per vėlus."
    if act=="PERPUBLIKUOTI" and prod is not None:
        return "📣 PERPUBLIKUOTI DABAR", "Priemonė jau yra, todėl paklausą galima išnaudoti be naujo kūrimo."
    if act=="ISPLESTI" and prod is not None and until_peak < need:
        return "📣 PIRMA RODYTI TURIMĄ", f"Iki piko {until_peak} d., o plėtrai skaičiuojamas ~{need} d. rezervas; naują kampą ruošk kitam langui."
    if until_pub>=need:
        return "🔥 PRADĖTI KURTI DABAR", f"Iki publikavimo lango {until_pub} d.; šiai idėjai skaičiuojamas ~{need} d. kūrimo rezervas."
    if until_peak>=need:
        return "⚡ KURTI, JEI GALI UŽBAIGTI", f"Optimalus publikavimo startas jau arti, bet iki piko dar {until_peak} d.; kūrimui reikia ~{need} d."
    if effort_level(r)=="🟢 MAŽA" and until_peak>=1:
        return "⚡ TIK GREITAS VARIANTAS", f"Iki piko tik {until_peak} d.; verta tik jei tikrai užbaigsi greitai."
    if prod is not None:
        return "📣 IŠNAUDOTI TURIMĄ PRIEMONĘ", f"Iki piko {until_peak} d., o naujam kūrimui skaičiuojamas ~{need} d. rezervas."
    return "🗓️ GERĄ IDĖJĄ RUOŠTI KITAM LANGUI", f"Iki piko {until_peak} d., o kūrimui skaičiuojamas ~{need} d. rezervas – šiam pikui nebeskubėk."

def execution_priority(r,score,today):
    return float(score)+effort_bonus(r)+execution_fit(r,today)

def idea_signature(r):
    words=set(re.findall(r"[a-ząčęėįšųūž0-9]+", _norm(f"{r.tema} {r.mikrotema} {r.produkto_ideja}")))
    stop={"ir","su","bei","pagal","užduotys","užduotis","priemonė","rinkinys","kortelės","pdf","ppt"}
    return words-stop

def too_similar(r, selected, threshold=.72):
    a=idea_signature(r)
    if not a:return False
    for old in selected:
        b=idea_signature(old)
        if b and len(a&b)/max(1,len(a|b))>=threshold:return True
    return False

def roi_label(r,score):
    x=float(score)+effort_bonus(r)
    return "🔥 LABAI AUKŠTA" if x>=88 else ("🟢 AUKŠTA" if x>=76 else ("🟡 VIDUTINĖ" if x>=62 else "⚪ ŽEMESNĖ"))

def db_ok():
    try:
        # Verify that Secrets exist and client can be created.
        _ = st.secrets["SUPABASE_URL"]
        _ = st.secrets["SUPABASE_KEY"]
        supabase_client()
        return True,""
    except Exception as e:
        return False,str(e)

@st.cache_data(ttl=60,show_spinner=False)
def load_idea_status_map():
    try:
        rows=supabase_client().table("ideas").select("fingerprint,status,product_code,updated_at").execute().data
        return {
            str(x.get("fingerprint")):{
                "status":str(x.get("status") or "IDEJA"),
                "product_code":str(x.get("product_code") or ""),
                "updated_at":str(x.get("updated_at") or "")
            } for x in rows
        }
    except Exception:
        return {}

@st.cache_data(ttl=60,show_spinner=False)
def load_recent_republish_map():
    try:
        rows=supabase_client().table("republish_history").select("product_code,recommendation_date").execute().data
        out={}
        for x in rows:
            code=str(x.get("product_code") or "")
            ds=str(x.get("recommendation_date") or "")
            if not code or not ds:
                continue
            try:d=date.fromisoformat(ds)
            except:continue
            if code not in out or d>out[code]:
                out[code]=d
        return out
    except Exception:
        return {}


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
                "produkto_ideja":str(r.produkto_ideja).replace("Pastatyk skaičių","Sudėliok skaičių"),"formatas":str(r.formatas),"examples":str(r.uzduociu_pavyzdziai),
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
    x=load_idea_status_map().get(str(fingerprint),{"status":"IDEJA","product_code":""}).copy()
    # V8.1.x briefly stored PASIDALINTA as the idea status. Treat it as an
    # already-existing product, so Radar never proposes creating it again.
    if x.get("status")=="PASIDALINTA":
        x["status"]="SUKURTA"
    return x

def set_idea_status(fingerprint,status,code=""):
    try:
        supabase_client().table("ideas").update({
            "status":status,
            "product_code":code.strip(),
            "updated_at":datetime.utcnow().isoformat()
        }).eq("fingerprint",fingerprint).execute()
        load_idea_status_map.clear()
        return True
    except Exception:
        return False

def idea_bank():
    try:
        d=supabase_client().table("ideas").select("*").order("last_score",desc=True).order("last_seen",desc=True).execute().data
        return pd.DataFrame(d)
    except: return pd.DataFrame()

def republish_done(code, theme, micro, fb):
    """
    Best-effort history log.
    A duplicate row / old schema / temporary Supabase write error must NEVER crash the app.
    The main completion state is also persisted in `ideas`, which V9 already uses reliably.
    """
    try:
        supabase_client().table("republish_history").insert({
            "product_code":code or "BE_KODO",
            "recommendation_date":str(date.today()),
            "theme":theme,
            "microtheme":micro,
            "fb_angle":fb
        }).execute()
        load_recent_republish_map.clear()
        return True
    except Exception:
        # Keep Radar usable even if this auxiliary table rejects the write.
        load_recent_republish_map.clear()
        return False

def recent_republish(code, days=21):
    if not code:
        return False
    dt=load_recent_republish_map().get(str(code))
    return bool(dt and (date.today()-dt).days < days)

def recent_idea_touch(fingerprint, days=21):
    """
    Fallback republish memory stored in the already-working `ideas` table.
    `updated_at` is refreshed when PASIDALINAU is clicked.
    """
    x=load_idea_status_map().get(str(fingerprint),{})
    raw=str(x.get("updated_at") or "")
    if not raw:
        return False
    try:
        dt=datetime.fromisoformat(raw.replace("Z","+00:00")).date()
        return (date.today()-dt).days < days
    except Exception:
        return False

def _session_completed():
    if "completed_fingerprints" not in st.session_state:
        st.session_state["completed_fingerprints"]=set()
    return st.session_state["completed_fingerprints"]

def persist_completed_idea(r,status,code=""):
    """
    Persist completion in Supabase and VERIFY it before hiding the card.
    Uses explicit SELECT -> UPDATE/INSERT instead of relying on a silent UPDATE
    that may match zero rows.
    """
    try:
        sb=supabase_client()
        f=fp(r)
        now=datetime.utcnow().isoformat()
        existing=sb.table("ideas").select("fingerprint").eq("fingerprint",f).limit(1).execute().data

        if existing:
            sb.table("ideas").update({
                "status":str(status),
                "product_code":str(code or "").strip(),
                "last_seen":str(date.today()),
                "last_score":float(getattr(r,"prioritetas",0) or 0),
                "updated_at":now
            }).eq("fingerprint",f).execute()
        else:
            sb.table("ideas").insert({
                "fingerprint":f,
                "tema":str(r.tema),
                "mikrotema":str(r.mikrotema),
                "amzius":str(r.amzius),
                "sritis":str(r.sritis),
                "produkto_ideja":str(r.produkto_ideja).replace("Pastatyk skaičių","Sudėliok skaičių"),
                "formatas":str(r.formatas),
                "examples":str(r.uzduociu_pavyzdziai),
                "evergreen":int(r.evergreen),
                "competition":str(r.konkurencija),
                "sales":str(r.pardavimo_potencialas),
                "first_seen":str(date.today()),
                "last_seen":str(date.today()),
                "top_count":1,
                "last_score":float(getattr(r,"prioritetas",0) or 0),
                "status":str(status),
                "product_code":str(code or "").strip(),
                "updated_at":now
            }).execute()

        # Read back from DB. Only success if persistence is really there.
        check=sb.table("ideas").select("status,product_code,updated_at").eq("fingerprint",f).limit(1).execute().data
        if not check:
            return False
        row=check[0]
        if str(row.get("status") or "") != str(status):
            return False

        load_idea_status_map.clear()
        return True
    except Exception:
        return False


def mark_shared(r, product):
    """
    Persist PASIDALINAU safely:
    - optional republish_history log (best effort);
    - ideas row is guaranteed to exist;
    - status remains SUKURTA so product history/code are not lost;
    - updated_at becomes the reliable last-share timestamp.
    """
    code=str(getattr(product,"kodas","") or "")
    republish_done(code,str(r.tema),str(r.mikrotema),fb_angle(r))
    ok=persist_completed_idea(r,"SUKURTA",code)
    if ok:
        _session_completed().add(fp(r))
    return ok


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
    p,*_=pedagogical_peak(r,today)
    return (p-today).days

def sales_score(v): return {"žemas":30,"vidutinis":55,"aukštas":78,"labai aukštas":95}.get(str(v).lower(),60)
def comp_score(v): return {"žema":90,"vidutinė":72,"aukšta":52}.get(str(v).lower(),65)
def stars(n): return "🌲"*int(n)+"○"*(5-int(n))

def horizon_score(r,today,h):
    peak,kind,use_date,detail,signals,extra,conf=pedagogical_peak(r,today)
    d=(peak-today).days
    sigma=max(5,h*.55)
    timing_score=100*math.exp(-((d-h*.40)**2)/(2*sigma*sigma))

    raw=(
        .42*timing_score
        +.20*sales_score(r.pardavimo_potencialas)
        +.12*comp_score(r.konkurencija)
        +.12*(float(r.evergreen)*20)
        +min(12,extra*.35)
        +.10*conf
    )

    # Safety cap: weak date confidence can never become a 99/100 TOP.
    cap=60+(0.40*conf)
    return round(max(0,min(100,raw,cap)))

def peak_kind_label(kind):
    return {
        "programa":"📚 PROGRAMINIS PIKAS",
        "proga":"📅 PROGOS PIKAS",
        "tevai":"👨‍👩‍👧 TĖVŲ PAKLAUSOS PIKAS",
        "sezonika":"🌿 SEZONINĖ PROGNOZĖ",
    }.get(kind,"📈 PAKLAUSOS PIKAS")

def peak_stage(peak,today,last=None):
    d=(peak-today).days
    if d>5: return f"🟢 Pikas po {d} d."
    if 2<=d<=5: return f"🔥 Pikas artėja · po {d} d."
    if d==1: return "🔥 Pikas rytoj"
    if d==0: return "🔥 Pikas šiandien"
    ago=abs(d)
    if ago==1: return "🟠 Pikas buvo vakar · dar aktualu"
    if ago<=3: return f"🟠 Pikas buvo prieš {ago} d. · dar verta rodyti"
    if ago<=5: return f"🟡 Pikas buvo prieš {ago} d. · paklausa slopsta"
    return f"⚪ Pikas buvo prieš {ago} d."

def recommended_stage_action(r,today):
    start,pub,peak,last=timing(r,today)
    d=(peak-today).days
    if today < start: return "💡 PLANUOTI · dar nebūtina pradėti"
    if today < pub: return "🔥 KURTI · kad spėtum iki publikavimo lango"
    if d>=0: return "📣 PUBLIKUOTI / DALINTIS · aktyvus langas"
    if (today-peak).days<=3: return "📣 DAR VERTA DALINTIS · pikas ką tik praėjo"
    if today<=last: return "🟡 PALAIKYTI MATOMUMĄ · paklausa slopsta"
    return "⚪ AKTYVUS LANGAS BAIGĖSI"

def timing(r,today):
    peak,kind,use_date,detail,signals,extra,conf=pedagogical_peak(r,today)
    publish=peak-timedelta(days=3)
    start=publish-timedelta(days=get_creation_lead())
    start=shift_before_holiday(start)
    publish=shift_before_holiday(publish)
    last=(use_date+timedelta(days=2)) if kind in ["programa","proga","tevai"] else (peak+timedelta(days=5))
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
    # Pakanka vieno stipraus mikrotemos žodžio, nes senų produktų pavadinimai
    # dažnai būna trumpesni nei nauja Radar mikrotema.
    mask=s.apply(lambda x:sum(w in x for w in micro_words)>=1)
    return m[mask].head(6)

def republish_candidates(catalog,r):
    """Republish may use a broader thematic match than 'exact' product expansion."""
    m=catalog_matches(catalog,r)
    if m.empty:return m
    # Prefer rows with a real product code and stronger textual match.
    if "kodas" in m.columns:
        m=m.assign(_hascode=m["kodas"].fillna("").astype(str).str.len()>0)
        m=m.sort_values(["_hascode","_score"],ascending=[False,False])
    return m.head(8)

def fb_angle(r):
    a=angles(r)
    hook=a[0] if a else str(r.mikrotema)
    return f"Rodyti ne bendrą temą, o konkretų veiksmą „{hook}“. Įkelti vieną realią užduotį / ekraną ir parodyti, ką vaikas turi padaryti."


def _synthetic_product(code,r):
    return pd.Series({
        "pavadinimas":str(getattr(r,"produkto_ideja",r.mikrotema)).strip("„“"),
        "kodas":str(code or ""),
        "nuoroda":""
    })

def decision(r,catalog,today):
    stt={"status":"IDEJA","product_code":""}
    status=str(stt.get("status") or "IDEJA")
    stored_code=str(stt.get("product_code") or "")

    exact=exact_catalog_match(catalog,r)
    related=catalog_matches(catalog,r)
    reps=republish_candidates(catalog,r)
    start,pub,peak,last=timing(r,today)

    if status in ["SUKURTA","PRAPLESTA"]:
        p=None
        if stored_code:
            if not catalog.empty and "kodas" in catalog.columns:
                found=catalog[catalog.kodas.fillna("").astype(str).str.upper()==stored_code.upper()]
                if len(found):
                    p=found.iloc[0]
            if p is None:
                p=_synthetic_product(stored_code,r)

        early=pub-timedelta(days=10)
        late=max(last,peak+timedelta(days=3))
        if p is not None and early<=today<=late and not recent_republish(stored_code,21) and not recent_idea_touch(fp(r),21):
            return "PERPUBLIKUOTI",p
        return "ATLIKTA",None

    if len(reps):
        p=reps.iloc[0]
        code=str(p.kodas) if "kodas" in p else ""
        early=pub-timedelta(days=10)
        late=max(last,peak+timedelta(days=3))
        if not recent_republish(code,21) and not recent_idea_touch(fp(r),21) and early<=today<=late:
            return "PERPUBLIKUOTI",p

    if len(related):
        return "ISPLESTI",related.iloc[0]

    if start<=today<=last:
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
        aud="pedagogai + tėvai" if any(x in (str(r.tema)+" "+str(r.mikrotema)).lower() for x in ["raid","abėc","skaič","rašym","rašyt","skaity","sudėt","atimt","laikrod","finans","biudž","pinig"]) else "pedagogai / pagal temą ir tėvai"
        st.write(f"**Auditorija:** {aud}")
        st.write(f"**FB kampas:** {fb_angle(r)}")
        if product.nuoroda:st.write(f"**Nuoroda:** {product.nuoroda}")
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
    render_theme_coverage(r, product if action_label=="ISPLESTI" else None)
    st.markdown("**📅 Laikas**")
    _pk,_kind,*_=pedagogical_peak(r,today)
    st.write(f"**{peak_kind_label(_kind)}:** {peak.strftime('%Y-%m-%d')} · **{peak_stage(peak,today,last)}**")
    st.write(f"**Pradėti kurti:** {'dabar' if today>=start else start.strftime('%Y-%m-%d')} • **Optimalu publikuoti:** {pub.strftime('%Y-%m-%d')} • **Aktualumo lango pabaiga:** {last.strftime('%Y-%m-%d')}")
    _ea,_ew=execution_action(r,today,action_label,product)
    st.write(f"**Veiksmas dabar:** {_ea}")
    st.caption(_ew)
    ps,osig,pds,signals,extra=signal_stack(r,today)
    st.markdown("**🧭 Kodėl ši idėja dabar?**")
    if signals:
        st.write(" + ".join(signals))
    else:
        st.write("Sezoninis / bendras paklausos signalas.")
    conf=date_confidence(r,today)
    st.write(f"**📅 Datos patikimumas:** {date_confidence_label(conf)} · {conf}/100")
    if ps and ps.get("all_windows"):
        w=ps["all_windows"][0]
        st.write(
            f"**📚 Programinis pagrindas:** {w['grade']} kl. • {w['subject']} • "
            f"**tikėtinas mokymo langas:** {w['start'].strftime('%Y-%m-%d')}–{w['end'].strftime('%Y-%m-%d')} "
            f"• ugdymo savaitės {w['week_window']}."
        )
        st.caption("🟡 Orientacinis 2–3 savaičių langas iš konkretaus planavimo šaltinio, o ne viena privaloma data visoms mokykloms.")
        st.caption(f"Šaltinis: {w['source_type']} · {w['source']}")
        others=[x for x in ps.get("all_windows",[])[1:5] if x["end"]>=today-timedelta(days=3)]
        if others:
            st.markdown("**Kiti tos pačios temos programiniai langai:**")
            for x in others:
                st.write(f"• {x['grade']} kl. · {x['start'].strftime('%Y-%m-%d')}–{x['end'].strftime('%Y-%m-%d')} · {x['official_topic']}")
    elif ps and ps.get("memberships"):
        grades=", ".join(str(x["grade"])+" kl." for x in ps["memberships"][:6])
        st.write(f"**📘 Programos atitikimas:** tema patvirtinta ({grades}), tačiau **savaitinis mokymo laikas dar nepatvirtintas**.")
        st.caption("⚪ Programos atitikimas pats savaime pirkimo piko datos nesukuria.")
    if osig:
        st.write(f"**📅 Progos signalas:** {osig['occasion']} – {osig['date'].strftime('%Y-%m-%d')}.")
    lvl=str(getattr(r,"teorijos_lygis","bendras"))
    st.markdown("**📚 Ar reikia tikrinti teoriją?**")
    if lvl=="būtina tikrinti":
        st.write("🔎 **Taip, būtina.** Prieš publikuojant patikrink faktus ir terminus oficialiuose / dalyko šaltiniuose.")
    elif lvl=="reikia šaltinių":
        st.write("📘 **Taip.** Pasitikrink programoje ir patikimoje metodinėje medžiagoje.")
    else:
        st.write("✅ **Specialios teorijos tikrinti nereikia**, bet amžiaus tinkamumą verta sutikrinti su programa.")
    st.write("**Kur tikrinti:** "+str(getattr(r,"saltiniu_kryptis","Aktualios ugdymo programos ir patikimi dalyko šaltiniai.")))
    if show_buttons:
        code=st.text_input("Produkto kodas, kai atliksi",key=f"{key_prefix}_code_{fp(r)}",placeholder="pvz. P129 arba 301")

def compact_done_controls(*args,**kwargs):
    return


def separate_product_angles(r):
    """Distinct, clearly explained directions for broader theme coverage.
    A current product is never labelled weak; it may simply cover one part of a broader theme.
    """
    text=_norm(f"{r.tema} {r.mikrotema} {r.produkto_ideja}")
    candidates=[]
    def add(title, skill, tasks, difference):
        if title not in [x["title"] for x in candidates]:
            candidates.append({"title":title,"skill":skill,"tasks":tasks,"difference":difference})

    if any(k in text for k in ["procent","trupmen","dešimtain"]):
        add("Lygiaverčių trupmenų, dešimtainių skaičių ir procentų siejimas",
            "Vaikas supranta, kad tas pats dydis gali būti užrašytas trupmena, dešimtainiu skaičiumi ir procentais, ir mokosi pereiti iš vienos išraiškos į kitą.",
            ["sujungti 1/2, 0,5 ir 50 % į vieną grupę","prie vaizdinio modelio parinkti tinkamus užrašus","rasti vieną netinkamą reikšmę tarp lygiaverčių","įrašyti trūkstamą trupmeną, dešimtainį skaičių arba procentą","rūšiuoti sumaišytas reikšmes į lygiaverčių dydžių grupes"],
            "Tai ne vien trupmenos atpažinimas: pagrindinis gebėjimas – suvokti skirtingų skaitinių užrašų lygiavertiškumą.")
        add("Trupmenų dydžio palyginimas pagal vaizdą ir skaičių",
            "Vaikas mokosi nustatyti, kuri iš dviejų ar kelių trupmenų yra didesnė, mažesnė arba lygi, pirmiausia remdamasis vaizdu, vėliau – skaitiniu užrašu.",
            ["palyginti du nuspalvintus modelius","įrašyti >, < arba =","rasti dvi vienodo dydžio trupmenas","surikiuoti 3–4 trupmenas nuo mažiausios iki didžiausios","paaiškinti pasirinkimą pagal vaizdinį modelį"],
            "Čia lavinamas dydžio suvokimas ir palyginimas, o ne tik trupmenos įvardijimas.")
        add("Trūkstamos reikšmės ir konversijos",
            "Vaikas savarankiškai apskaičiuoja arba parenka trūkstamą tos pačios reikšmės užrašą.",
            ["užpildyti 1/4 = ___ = 25 %","parinkti procentą pateiktai trupmenai","dešimtainį skaičių paversti procentais","užbaigti lygiaverčių reikšmių grandinę","ištaisyti neteisingai atliktą konversiją"],
            "Šis kampas reikalauja ne atpažinti paruoštą porą, o pačiam atlikti konversiją.")
        add("Kasdienės situacijos su trupmenomis ir procentais",
            "Vaikas pritaiko trupmenas ar procentus realistiškose pirkimo, kiekio, nuolaidos ar dalies situacijose.",
            ["apskaičiuoti nuolaidos dalį","rasti likusią visumos dalį","palyginti dvi nuolaidas","parinkti situacijai tinkamą skaitinį užrašą","spręsti trumpus tekstinius uždavinius"],
            "Tema perkeliama iš abstraktaus užrašo į praktinį taikymą ir problemų sprendimą.")
    elif any(k in text for k in ["laikrod","laiką","valand"]):
        add("Nurodyto laiko pažymėjimas laikrodyje","Vaikas ne perskaito jau parodytą laiką, o pats nustato rodykles pagal pateiktą laiką.",["nustatyti pilną valandą","pažymėti pusvalandį ar ketvirtį","nustatyti laiką pagal skaitmeninį užrašą","rasti ir pataisyti neteisingai nustatytas rodykles","parodyti tą patį laiką analoginiame ir skaitmeniniame laikrodyje"],"Keičiasi vaiko veiksmas: iš laiko atpažinimo pereinama į aktyvų laiko pavaizdavimą.")
        add("Laiko palyginimas ir rikiavimas","Vaikas suvokia laiko seką ir geba palyginti kelis laikus.",["pasirinkti ankstesnį laiką","pasirinkti vėlesnį laiką","surikiuoti 3–5 laikrodžius","susieti dienos veiklas su laiku","rasti du tą patį laiką rodančius laikrodžius"],"Tai jau ne vien laikrodžio skaitymas – lavinama laiko seka ir santykiai tarp kelių laikų.")
        add("Praėjusio laiko skaičiavimas","Vaikas nustato, kiek laiko praėjo tarp pradžios ir pabaigos.",["apskaičiuoti trukmę tarp dviejų laikrodžių","rasti veiklos pabaigos laiką","rasti pradžios laiką","palyginti dviejų veiklų trukmę","spręsti trumpas kasdienes situacijas"],"Ši kryptis pereina nuo laiko nuskaitymo prie skaičiavimo ir trukmės suvokimo.")
        add("Kasdienės situacijos ir dienotvarkė","Vaikas taiko laikrodžio žinias realiose dienos situacijose.",["susieti veiklą su tinkamu laiku","sudėlioti dienos įvykius chronologiškai","nuspręsti, ar spės į veiklą","apskaičiuoti laukimo laiką","parinkti tinkamą pradžios ar pabaigos laiką"],"Tema tampa funkcionali ir artima realiam gyvenimui, o ne izoliuota laikrodžio užduotis.")
    elif any(k in text for k in ["finans", "biudž", "pinig", "kain", "grąž", "taup"]):
        add("Biudžeto sudarymas ir sprendimai",
            "Vaikas mokosi planuoti ribotą pinigų sumą: pasirinkti pirkinius, neviršyti biudžeto ir pagrįsti savo sprendimą.",
            ["turint 20 € sudaryti 3 prekių krepšelį ir neviršyti biudžeto","iš kelių pirkinių variantų pasirinkti tuos, kuriems pakanka 15 €","apskaičiuoti, kiek pinigų liks po pasirinkto pirkinio","rasti krepšelį, kuris viršija biudžetą, ir jį pataisyti","palyginti du krepšelius ir nuspręsti, kuris geriau atitinka nurodytą biudžetą"],
            "Čia svarbiausia ne vien atlikti veiksmą su eurais, o priimti sprendimą esant ribotam biudžetui.")
        add("Poreikiai ir norai",
            "Vaikas skiria būtinus poreikius nuo norų ir mokosi argumentuoti, kam pinigus verta skirti pirmiausia.",
            ["suskirstyti pirkinius į poreikius ir norus","turint ribotą sumą pasirinkti, ką pirkti pirmiausia","paaiškinti, kodėl vienas pirkinys svarbesnis už kitą","rasti situaciją, kurioje verta dalį pinigų pasilikti","palyginti du sprendimus ir pasirinkti atsakingesnį"],
            "Šis kampas ugdo finansinių prioritetų suvokimą, o ne tik skaičiavimo įgūdį.")
        add("Kainų palyginimas, nuolaidos ir geresnis pasirinkimas",
            "Vaikas lygina kainas ir pasiūlymus bei sprendžia, kuris variantas finansiškai naudingesnis.",
            ["palyginti tos pačios prekės kainą dviejose parduotuvėse","apskaičiuoti, kiek sutaupoma pasirinkus pigesnį variantą","pasirinkti naudingesnį iš dviejų pasiūlymų","rasti, ar už turimą sumą galima nupirkti pasirinktą prekę","vyresniems – palyginti paprastą nuolaidą su pradine kaina"],
            "Tema pereina nuo kainos perskaitymo prie realaus pasirinkimo ir finansinio pagrindimo.")
        add("Pinigų skaičiavimas ir grąža kasdienėse situacijose",
            "Vaikas praktiškai taiko eurų ir centų skaičiavimą pirkimo situacijose.",
            ["sudėti kelių prekių kainas","apskaičiuoti grąžą sumokėjus 10 € ar 20 €","parinkti tinkamus monetų ir banknotų derinius nurodytai sumai","rasti klaidingai apskaičiuotą grąžą","sukurti kelis skirtingus būdus sumokėti tą pačią sumą"],
            "Tai praktinis pinigų naudojimas: ne abstraktūs skaičiai, o pirkimo, mokėjimo ir grąžos situacijos.")
    elif any(k in text for k in ["raid", "abėc", "skaity", "rašym", "rašyt", "skiemen", "žodžių"]):
        add("Raidės ar garso atpažinimas skirtinguose žodžiuose","Vaikas ieško konkrečios raidės ar garso ne pavieniui, o įvairiuose žodžiuose ir paveikslėlių pavadinimuose.",["rasti žodžius, prasidedančius nurodyta raide","atrinkti paveikslėlius pagal pirmą garsą","rasti raidę žodžio viduryje ar gale","išbraukti netinkamą paveikslėlį","sugrupuoti žodžius pagal garsą"],"Plečiama nuo paprasto raidės pažinimo į jos girdėjimą ir atpažinimą žodžiuose.")
        add("Raidės, skiemens, žodžio ir vaizdo siejimas","Vaikas jungia kelias kalbos reprezentacijas ir turi nustatyti, kas kam priklauso.",["sujungti žodį su paveikslėliu","pridėti trūkstamą pirmą raidę","parinkti skiemenį žodžiui užbaigti","sudaryti poras iš didžiosios ir mažosios raidės","rasti paveikslėlį pagal perskaitytą žodį"],"Čia svarbus ne vien simbolio atpažinimas, o ryšys tarp raidės, garso, skiemens, žodžio ir reikšmės.")
        add("Žodžių sudarymas ir konstravimas","Vaikas pats kuria žodį iš pateiktų raidžių ar skiemenų.",["sudėti žodį iš raidžių","sudėti žodį iš skiemenų","įrašyti trūkstamą raidę","sukeisti raides į teisingą tvarką","pagal paveikslėlį sudaryti jo pavadinimą"],"Vaikas nebe tik pasirenka atsakymą – pats konstruoja kalbos vienetą.")
        add("Klaidų paieška ir taisymas","Vaikas turi pastebėti neteisingą raidę, skiemenį ar žodį ir paaiškinti arba pataisyti klaidą.",["rasti neteisingai parašytą žodį","pasirinkti tinkamą raidę klaidai ištaisyti","rasti paveikslėliui netinkantį žodį","palyginti du beveik vienodus žodžius","ištaisyti sumaišytą raidžių seką"],"Ši mechanika lavina atidumą ir kalbinį tikrinimą, o ne vien atpažinimą.")
    elif any(k in text for k in ["emoc","draug","toler","social"]):
        add("Situacijos atpažinimas ir emocijos supratimas","Vaikas analizuoja konkrečią situaciją ir nustato, kaip joje gali jaustis veikėjas.",["parinkti emociją situacijai","paaiškinti, kas galėjo sukelti jausmą","rasti kelias galimas emocijas","susieti kūno ženklus su emocija","palyginti dviejų veikėjų savijautą"],"Emocija nagrinėjama kontekste, ne tik atpažįstama iš veido.")
        add("Sprendimo pasirinkimas socialinėje situacijoje","Vaikas svarsto kelis elgesio variantus ir pasirenka tinkamiausią.",["pasirinkti, kaip pasielgti konflikto metu","rasti saugų sprendimą","palyginti dvi reakcijas","numatyti galimą pasekmę","pasiūlyti kitą tinkamą veiksmą"],"Pagrindinis gebėjimas – sprendimų priėmimas ir pasekmių numatymas.")
        add("Ką pasakyti konkrečioje situacijoje","Vaikas mokosi praktiškų frazių, kurios padeda bendrauti, atsiprašyti, paprašyti pagalbos ar nustatyti ribas.",["parinkti tinkamą frazę","užbaigti dialogą","sugalvoti mandagų atsakymą","pasakyti, kaip paprašyti pagalbos","palyginti pagarbų ir nepagarbų atsakymą"],"Tai kalbinė socialinių gebėjimų praktika, o ne vien situacijos įvertinimas.")
        add("Veiksmas ir pasekmė","Vaikas sieja elgesį su tikėtina pasekme sau ir kitiems.",["sujungti veiksmą su pasekme","sudėti 3 paveikslėlių seką","numatyti, kas nutiks toliau","rasti, kuri pasekmė nelogiška","pasiūlyti kitą veiksmą, kuris pakeistų rezultatą"],"Tema išplečiama į priežasties–pasekmės ir atsakomybės suvokimą.")
    else:
        aa=angles(r); ex=examples(r,8)
        for i,a in enumerate(aa[:4]):
            task=ex[i:i+4] or ["atlikti kelias skirtingas tos pačios temos užduotis"]
            add(a, f"Atskira temos kryptis, kurioje vaikas aktyviai atlieka užduotį „{a}“, o ne tik pakartoja tą patį veiksmą kitu dizainu.", task, "Šį kampą verta vertinti kaip atskirą gebėjimą ar užduoties mechaniką ir palyginti su jau turimų priemonių turiniu.")
    return candidates[:4]

def render_theme_coverage(r, product=None):
    series=separate_product_angles(r)
    if not series: return
    st.markdown("**🧭 Temos padengimas · ką jau turime ir kokiais dar kampais ją galima išplėtoti**")

    # Temos padengimui neužtenka vieno sprendimui parinkto produkto. Surenkame visas
    # katalogo priemones, kurias skeneris su šia tema gali pagrįstai susieti.
    try:
        related_all=catalog_matches(catalog,r) if 'catalog' in globals() else pd.DataFrame()
    except Exception:
        related_all=pd.DataFrame()

    if related_all is not None and not related_all.empty:
        st.write(f"**Kataloge rasta susijusių priemonių: {len(related_all)}.** Prieš siūlydamas kitus kampus Radar pirmiausia parodo, ką pavyko susieti su šia tema:")
        for _,cp in related_all.iterrows():
            name=str(cp.get('pavadinimas','')).strip()
            code=str(cp.get('kodas','')).strip()
            url=str(cp.get('nuoroda','')).strip()
            label=f"• **{name}**" + (f" · kodas {code}" if code else "")
            st.markdown(label)
            if url:
                st.caption(url)
        st.caption("Pastaba: katalogo susiejimas atliekamas pagal produkto pavadinimą, nuorodą ir temos raktažodžius. Todėl tai yra rastos susijusios priemonės, o ne garantija, kad automatinis skeneris aptiko absoliučiai visą temos turinį.")
        st.write("**Ką tikriname toliau:** ne ar šios priemonės yra geros – jos jau yra vertingos temos dalys. Radar ieško, kokių kitų gebėjimų, sudėtingumo lygių ar užduočių mechanikų visa tema dar gali neapimti.")
    else:
        st.warning("🔎 **Kataloge nepavyko patikimai susieti šios temos su konkrečiomis turimomis priemonėmis.** Todėl žemiau pateikiami galimi temos plėtimo kampai neatsižvelgiant į esamų priemonių turinį. Tai nereiškia, kad parduotuvėje šios temos priemonių nėra.")

    st.markdown("**💡 Galimi dar nepadengti arba papildomi temos kampai**")
    for n,item in enumerate(series,1):
        st.markdown(f"**{n}. {item['title']}**")
        st.write(item['skill'])
        st.write("**Ką vaikas galėtų atlikti:** " + "; ".join(item['tasks']) + ".")
        st.caption("Kuo tai kitas kampas: " + item['difference'])
    if len(series)>=3:
        st.info("💎 **Galimas produktų šeimos / rinkinio potencialas.** Turimos ir naujais kampais sukurtos atskiros priemonės gali padengti skirtingus tos pačios temos gebėjimus ir vėliau kartu sudaryti nuoseklų teminį rinkinį. Nebūtina visko sutalpinti į vieną produktą.")


def fast_detail_card(r,action_label=None,product=None):
    """Detail content for TOP expanders with no extra DB/network calls.
    Because Streamlit expander itself opens client-side, details appear instantly."""
    start,pub,peak,last=timing(r,today)
    action_label=action_label or "IDĖJA"

    if action_label=="PERPUBLIKUOTI" and product is not None:
        st.write(f"**📣 Priemonė:** {product.pavadinimas} • **Kodas:** {product.kodas or 'nerastas'}")
        st.write(f"**Optimalu perpublikuoti:** {pub.strftime('%Y-%m-%d')}–{min(last,peak).strftime('%Y-%m-%d')} • **Paklausos pikas:** apie {peak.strftime('%Y-%m-%d')}")
        aud="pedagogai + tėvai" if any(x in (str(r.tema)+" "+str(r.mikrotema)).lower() for x in ["raid","abėc","skaič","rašym","rašyt","skaity","sudėt","atimt","laikrod","finans","biudž","pinig"]) else "pedagogai / pagal temą ir tėvai"
        st.write(f"**Auditorija:** {aud}")
        st.write(f"**FB kampas:** {fb_angle(r)}")
        if product.nuoroda:
            st.write(f"**Nuoroda:** {product.nuoroda}")
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
    for j,a in enumerate(aa[:3],1):
        st.write(f"{['🥇','🥈','🥉'][j-1]} **{a}**")

    st.markdown("**🧩 Konkretūs užduočių pavyzdžiai**")
    _ex=examples(r,8)
    for x in _ex:
        st.write("• "+x)

    st.markdown("**📈 Kaip tą pačią mechaniką galima auginti**")
    st.write("1. Pasirinkimas iš kelių atsakymų → 2. atsakymo įrašymas savarankiškai → 3. užduotis su mažiau vaizdinės pagalbos → 4. pritaikymas situacijoje ar probleminėje užduotyje.")
    st.markdown("**💶 Kodėl ši kryptis gali būti komerciškai verta**")
    st.write(f"Tema turi {str(r.pardavimo_potencialas).lower()} pardavimo potencialą; užduoties esmę galima aiškiai parodyti produkto viršelyje, o skirtingi gebėjimo lygiai leidžia temą plėtoti ne dubliuojant tą pačią priemonę, bet kuriant nuoseklią seriją.")

    render_theme_coverage(r, product if action_label=="ISPLESTI" else None)

    with st.expander("📋 Paruošta kopijuoti į ChatGPT"):
        _brief=(f"Padėk išplėtoti mokomąją priemonę.\nTema: {r.tema} → {r.mikrotema}.\nKam: {r.amzius}. Sritis: {r.sritis}. Formatas: {r.formatas}.\nPriemonės kryptis: {r.produkto_ideja}.\n"
                + "Pavyzdžiai, rodantys norimą kryptį:\n- " + "\n- ".join(_ex)
                + "\nSukurk daugiau įvairių, nesidubliuojančių užduočių ta pačia kryptimi. Jei reikia pedagoginių žinių ar amžiaus pritaikymo, paaiškink ir pritaikyk pats – nepalik to spręsti man.")
        st.code(_brief,language=None)

    st.markdown("**📅 Laikas**")
    _pk,_kind,_use,_detail,_sig,_extra,_conf=pedagogical_peak(r,today)
    st.write(f"**{peak_kind_label(_kind)}:** {peak.strftime('%Y-%m-%d')} · **{peak_stage(peak,today,last)}**")
    st.write(
        f"**Pradėti kurti:** {'dabar' if today>=start else start.strftime('%Y-%m-%d')} "
        f"• **Optimalu publikuoti:** {pub.strftime('%Y-%m-%d')} "
        f"• **Aktualumo lango pabaiga:** {last.strftime('%Y-%m-%d')}"
    )
    _ea,_ew=execution_action(r,today,action_label,product)
    st.write(f"**Veiksmas dabar:** {_ea}")
    st.caption(_ew)
    st.caption("Piko data yra fiksuota pagal signalą ir neperkeliama į šiandieną. Po piko gali likti tik trumpa aktualumo uodega.")

    ps,osig,pds,signals,extra=signal_stack(r,today)
    audiences=[]
    if any("PEDAGOGAI" in s for s in signals): audiences.append("📚 pedagogams")
    if any("TĖVAI" in s for s in signals): audiences.append("👨‍👩‍👧 tėvams")
    if any("PROGA" in s for s in signals): audiences.append("📅 progai")
    if audiences:
        st.caption("Paklausos šaltinis: " + " + ".join(audiences))
    st.markdown("**🧭 Kodėl ši idėja dabar?**")
    st.write(" + ".join(signals) if signals else "Sezoninis / bendras paklausos signalas.")

    conf=date_confidence(r,today)
    st.write(f"**📅 Datos patikimumas:** {date_confidence_label(conf)} · {conf}/100")
    if ps and ps.get("all_windows"):
        w=ps["all_windows"][0]
        st.write(
            f"**📚 Programinis pagrindas:** {w['grade']} kl. • {w['subject']} "
            f"• **tikėtinas mokymo langas:** {w['start'].strftime('%Y-%m-%d')}–{w['end'].strftime('%Y-%m-%d')} "
            f"• ugdymo savaitės {w['week_window']}."
        )
        st.caption("🟡 Orientacinis 2–3 savaičių langas iš konkretaus planavimo šaltinio; ne viena privaloma data visoms mokykloms.")
        st.caption(f"Šaltinis: {w['source_type']} · {w['source']}")
        others=[x for x in ps.get("all_windows",[])[1:5] if x["end"]>=today-timedelta(days=3)]
        if others:
            st.markdown("**Kiti tos pačios temos programiniai langai:**")
            for x in others:
                st.write(f"• {x['grade']} kl. · {x['start'].strftime('%Y-%m-%d')}–{x['end'].strftime('%Y-%m-%d')} · {x['official_topic']}")
    elif ps and ps.get("memberships"):
        grades=", ".join(str(x["grade"])+" kl." for x in ps["memberships"][:6])
        st.write(f"**📘 Programos atitikimas:** tema patvirtinta ({grades}), tačiau **savaitinis mokymo laikas dar nepatvirtintas**.")
        st.caption("⚪ Programos atitikimas be savaitinio šaltinio tikslaus pirkimo piko nesukuria.")
    if osig:
        st.write(f"**📅 Progos signalas:** {osig['occasion']} – {osig['date'].strftime('%Y-%m-%d')}.")

    lvl=str(getattr(r,"teorijos_lygis","bendras"))
    st.markdown("**📚 Ar reikia tikrinti teoriją?**")
    if lvl=="būtina tikrinti":
        st.write("🔎 **Taip, būtina.** Prieš publikuojant patikrink faktus ir terminus oficialiuose / dalyko šaltiniuose.")
    elif lvl=="reikia šaltinių":
        st.write("📘 **Taip.** Pasitikrink programoje ir patikimoje metodinėje medžiagoje.")
    else:
        st.write("✅ **Specialios teorijos tikrinti nereikia**, bet amžiaus tinkamumą verta sutikrinti su programa.")
    st.write("**Kur tikrinti:** "+str(getattr(r,"saltiniu_kryptis","Aktualios ugdymo programos ir patikimi dalyko šaltiniai.")))


def compact_recommendation(r,act,prod,sc,i,key_prefix,time_text):
    label_map={
        "KURTI":"🔥 KURTI",
        "PERPUBLIKUOTI":"📣 PERPUBLIKUOTI",
        "ISPLESTI":"🔄 IŠPLĖSTI"
    }
    label=label_map.get(act,"💡 IDĖJA")
    exec_label,exec_why=execution_action(r,today,act,prod)
    st.markdown(f"### {i}. {exec_label} · {int(sc)}/100")
    st.write(f"**{r.tema} → {r.mikrotema}**")

    if act=="PERPUBLIKUOTI" and prod is not None:
        st.caption(f"{prod.pavadinimas} • kodas {prod.kodas or 'nerastas'}")
    elif act=="ISPLESTI" and prod is not None:
        st.caption(f"Išplėsti: {prod.pavadinimas} → {r.produkto_ideja}")
    else:
        st.caption(str(r.produkto_ideja).replace("Pastatyk skaičių","Sudėliok skaičių"))

    st.write(time_text)
    st.caption(exec_why)

    # Completion action remains visible for EVERY recommendation.
    # Native expander = same interaction style as Produktų planai.
    # No button / st.rerun, so opening and closing is immediate in the browser.
    with st.expander("🔎 Išskleisti visą idėją", expanded=False):
        fast_detail_card(
            r,
            act if act in ["KURTI","PERPUBLIKUOTI","ISPLESTI"] else "IDĖJA",
            prod
        )

    st.divider()


df=load_topics()
today=st.sidebar.date_input("Šiandien",date.today())
with st.spinner("Radar skaičiuoja artimiausius paklausos signalus..."):
    for h in [7,14,30]:
        df[f"{h}d"]=df.apply(lambda r:horizon_score(r,today,h),axis=1)
df["prioritetas"]=df[["7d","14d","30d"]].max(axis=1)

st.title("📡 Protuoliukas Trend Radar — V11.4.1")
st.caption("V11.5.1 • sprendimų sistema • realus kūrimo laikas • fiksuoti pikai • konkretūs produktų briefai • SEO")

with st.sidebar:
    st.markdown("### ⚙️ Mano dabartinis kūrimo tempas")
    st.radio("Kiek dienų noriu turėti priemonei sukurti?",[1,2,3,5,7],index=2,horizontal=True,key="creation_lead_days",
             help="Bendras dabartinio užimtumo rezervas. Tai nėra PDF ar PowerPoint trukmė.")
    st.caption("Kūrybos apimtį Radar vertina pagal pačią idėją: iliustracijas, užduočių kiekį ir interaktyvumą.")
    upcoming=OCCASIONS[(OCCASIONS["date"]>=today) & (OCCASIONS["date"]<=today+timedelta(days=30))].sort_values("date").head(5)
    if len(upcoming):
        st.markdown("**📅 Artimiausios ugdymo progos**")
        for _,o in upcoming.iterrows():
            st.caption(f"{o['date'].strftime('%m-%d')} · {o['occasion']}")
    active_parent=PARENT_DEMAND[(PARENT_DEMAND["end"]>=today) & (PARENT_DEMAND["start"]<=today+timedelta(days=21))].sort_values(["start","strength"],ascending=[True,False]).head(3)
    if len(active_parent):
        st.markdown("**👨‍👩‍👧 Ką dabar / netrukus perka tėvai**")
        for _,x in active_parent.iterrows():
            st.markdown(f"**{x['start'].strftime('%m-%d')}–{x['end'].strftime('%m-%d')} · {parent_window_stage(x,today)}**")
            st.caption(" • ".join(parent_window_topics(x)))
    st.markdown("**📚 V10 programinių datų aprėptis**")
    st.caption("✅ Matematika 5–8 kl.: konkretūs 2–3 sav. langai iš oficialių pavyzdinių planų.")
    st.caption("📘 Pradinė matematika ir dalis LT temų: klasė patvirtinta, bet savaitė nerodoma, kol neturime patikimo planavimo šaltinio.")
    st.caption("🚫 Platūs 1–35 / 1–36 sav. intervalai piko skaičiavimui nebenaudojami.")
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

# Auto-save valuable create/expand ideas once per selected date/session.
_autosave_key=f"autosaved_{today.isoformat()}"
if not st.session_state.get(_autosave_key,False):
    for _,r in df[df.prioritetas>=65].iterrows():
        act,_=dmap[fp(r)]
        if act in ["KURTI","ISPLESTI","PALAUKTI"]:
            save_idea(r,r.prioritetas)
    st.session_state[_autosave_key]=True


def pinterest_search_terms(r):
    """Generate several English Pinterest discovery angles from a Radar idea."""
    text=_norm(f"{r.tema} {r.mikrotema} {r.produkto_ideja}")
    age=str(r.amzius)
    base=[]
    # Mechanic-oriented English searches; Pinterest tends to have more useful
    # inspiration in English than literal Lithuanian translations.
    rules=[
        (["abėc","raid"],["alphabet activities","letter recognition activities","letter formation activities","phonics task cards"]),
        (["rašyt","rašym"],["handwriting activities","letter tracing activities","writing center activities","fine motor writing activities"]),
        (["skaity"],["early reading activities","reading comprehension activities","literacy centers","reading task cards"]),
        (["skaič"],["number sense activities","number recognition activities","math task cards","counting activities"]),
        (["sudėt","atimt"],["addition subtraction activities","math centers","addition task cards","number bond activities"]),
        (["daugyb"],["multiplication activities","multiplication games","math task cards","multiplication centers"]),
        (["dalyb"],["division activities","division games","math task cards","division centers"]),
        (["trupmen"],["fractions activities","fraction games","fraction task cards","fraction visual models"]),
        (["geometr","figūr"],["geometry activities","shape activities","geometry task cards","hands on geometry"]),
        (["emoc"],["social emotional learning activities","feelings activities","emotion cards","SEL activities"]),
        (["kūn"],["human body activities for kids","body parts activities","human body preschool activities","human body task cards"]),
        (["spalv"],["colors activities preschool","color matching activities","color sorting activities","color task cards"]),
        (["dėmes","pastab"],["visual discrimination activities","attention activities for kids","spot the difference activities","visual perception activities"]),
        (["toler","draug"],["friendship activities","kindness activities","social skills activities","SEL task cards"]),
        (["žem","ekolog","atliek"],["earth day activities","recycling activities for kids","environment activities","earth day task cards"]),
    ]
    for keys,queries in rules:
        if any(k in text for k in keys):
            base.extend(queries)
    if not base:
        # fallback from the radar's own topic, with generic activity mechanics
        raw=f"{r.tema} {r.mikrotema}".strip()
        base=[f"{raw} activities",f"{raw} task cards",f"{raw} games",f"{raw} classroom activity"]
    # de-duplicate and cap
    out=[]
    for q in base:
        if q not in out: out.append(q)
    return out[:6]

def pinterest_mechanic_label(q):
    ql=q.lower()
    mapping=[
        ("task cards","Užduočių kortelės"),
        ("centers","Veiklos stotelės / centrai"),
        ("games","Žaidybinė mechanika"),
        ("visual models","Vaizdiniai modeliai"),
        ("matching","Poravimo / atitikimo užduotis"),
        ("sorting","Rūšiavimo užduotis"),
        ("tracing","Apvedžiojimo / rašymo mechanika"),
        ("formation","Raidės formavimo mechanika"),
        ("recognition","Atpažinimo užduotis"),
        ("comprehension","Teksto suvokimo mechanika"),
        ("fine motor","Smulkiosios motorikos mechanika"),
        ("visual discrimination","Vizualinio pastabumo mechanika"),
        ("social emotional","Socialinė-emocinė veikla"),
        ("feelings","Emocijų atpažinimo mechanika"),
    ]
    for key,label in mapping:
        if key in ql:return label
    return "Veiklos pateikimo idėjos"

def pinterest_url(query):
    return "https://www.pinterest.com/search/pins/?q="+quote_plus(query)

def radar_inspiration_rows():
    """Use only topics Radar has already selected; no manual Pinterest search box."""
    rows=[]
    seen=set()
    for horizon,data in [("DABAR",TODAY_ROWS),("NETRUKUS",WEEK_ROWS),("ARTĖJA",COMING_ROWS)]:
        for item in data:
            r=item[0]
            key=_norm(f"{r.tema}|{r.mikrotema}")
            if key in seen: continue
            seen.add(key)
            rows.append((horizon,r))
    return rows[:12]



# ========================= SEO OPTIMIZATORIUS · V10.6 · BE API =========================
def _seo_clean_col(c):
    s = _norm(str(c))
    s = s.translate(str.maketrans({"ą":"a","č":"c","ę":"e","ė":"e","į":"i","š":"s","ų":"u","ū":"u","ž":"z"}))
    return s.replace(" ", "_")


def _xlsx_frames_without_openpyxl(raw):
    """Read ordinary Search Console .xlsx exports without openpyxl."""
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.findall(".//m:t", ns)))

        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rr = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rels = {x.attrib["Id"]: x.attrib["Target"] for x in rr}
        out = {}

        for sh in wb.findall("m:sheets/m:sheet", ns):
            name = sh.attrib.get("name", "Sheet")
            rid = sh.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rels.get(rid, "")
            path = target.lstrip("/") if target.startswith("/") else "xl/" + target.replace("../", "")
            if path not in z.namelist():
                continue

            root = ET.fromstring(z.read(path))
            rows = []
            for row in root.findall(".//m:sheetData/m:row", ns):
                vals = {}
                for c in row.findall("m:c", ns):
                    mt = re.match(r"([A-Z]+)", c.attrib.get("r", ""))
                    if not mt:
                        continue
                    idx = 0
                    for ch in mt.group(1):
                        idx = idx * 26 + ord(ch) - 64
                    idx -= 1
                    typ = c.attrib.get("t")
                    v = c.find("m:v", ns)
                    val = ""
                    if typ == "inlineStr":
                        val = "".join(t.text or "" for t in c.findall(".//m:t", ns))
                    elif v is not None:
                        val = v.text or ""
                        if typ == "s":
                            try:
                                val = shared[int(val)]
                            except Exception:
                                pass
                    vals[idx] = val

                if vals:
                    a = [""] * (max(vals) + 1)
                    for i, v in vals.items():
                        a[i] = v
                    rows.append(a)

            if rows:
                width = max(map(len, rows))
                rows = [r + [""] * (width - len(r)) for r in rows]
                hdr = [str(x).strip() or f"col_{i}" for i, x in enumerate(rows[0])]
                out[name] = pd.DataFrame(rows[1:], columns=hdr)
        return out


def _standardize_gsc_frame(x, kind=None):
    x = x.copy()
    aliases = {
        "query": "query", "queries": "query", "top_queries": "query",
        "uzklausa": "query", "uzklausos": "query", "populiariausios_uzklausos": "query",
        "page": "page", "pages": "page", "puslapis": "page", "puslapiai": "page",
        "populiariausi_puslapiai": "page",
        "date": "date", "data": "date",
        "clicks": "clicks", "click": "clicks", "paspaudimai": "clicks", "spustelejimai": "clicks",
        "impressions": "impressions", "impression": "impressions", "parodymai": "impressions",
        "ctr": "ctr", "pr": "ctr",
        "position": "position", "average_position": "position", "pozicija": "position", "vidutine_pozicija": "position",
    }
    ren = {}
    for c in x.columns:
        k = _seo_clean_col(c)
        if k in aliases:
            ren[c] = aliases[k]
        elif "uzklaus" in k or "query" in k:
            ren[c] = "query"
        elif "puslap" in k or k in ("page", "pages"):
            ren[c] = "page"
        elif "spustelej" in k or "paspaud" in k or "click" in k:
            ren[c] = "clicks"
        elif "parodym" in k or "impression" in k:
            ren[c] = "impressions"
        elif k in ("pr", "ctr") or "click_through" in k:
            ren[c] = "ctr"
        elif "pozic" in k or "position" in k:
            ren[c] = "position"
        elif k in ("data", "date"):
            ren[c] = "date"
    x = x.rename(columns=ren)

    for c in ["clicks", "impressions", "position"]:
        if c in x.columns:
            x[c] = pd.to_numeric(
                x[c].astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False),
                errors="coerce",
            )
    if "ctr" in x.columns:
        raw = x["ctr"].astype(str)
        had_pct = raw.str.contains("%", regex=False).any()
        vals = raw.str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
        x["ctr"] = pd.to_numeric(vals, errors="coerce")
        if not had_pct and len(x["ctr"].dropna()) and x["ctr"].dropna().max() <= 1:
            x["ctr"] *= 100
    if "date" in x.columns:
        x["date"] = pd.to_datetime(x["date"], errors="coerce")
    return x


SEO_CACHE_DIR = Path(".radar_seo_cache")
SEO_GSC_META = SEO_CACHE_DIR / "gsc_meta.json"
SEO_SEEN_META = SEO_CACHE_DIR / "seen_products.json"

class _SavedUpload:
    def __init__(self, raw, name):
        self._raw=raw; self.name=name
    def getvalue(self): return self._raw

def _ensure_seo_cache():
    try: SEO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception: pass

def save_gsc_upload(uploaded):
    """Keep the latest GSC export so the user does not need to upload it for every product."""
    _ensure_seo_cache()
    raw=uploaded.getvalue(); name=getattr(uploaded,"name","search_console.xlsx") or "search_console.xlsx"
    ext=Path(name).suffix.lower() or ".xlsx"
    data_path=SEO_CACHE_DIR / ("latest_gsc"+ext)
    # remove an older export with another extension
    for old in SEO_CACHE_DIR.glob("latest_gsc.*"):
        try:
            if old != data_path: old.unlink()
        except Exception: pass
    data_path.write_bytes(raw)
    meta={"name":name,"saved_at":datetime.now().isoformat(timespec="seconds"),"path":str(data_path)}
    SEO_GSC_META.write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
    return meta

def load_saved_gsc():
    try:
        meta=json.loads(SEO_GSC_META.read_text(encoding="utf-8"))
        path=Path(meta.get("path",""))
        if path.exists(): return _SavedUpload(path.read_bytes(), meta.get("name",path.name)), meta
    except Exception: pass
    return None, None

def _gsc_export_date(meta):
    if not meta: return None
    name=meta.get("name","")
    m=re.search(r"(20\\d{2})[-_](\\d{2})[-_](\\d{2})",name)
    if m:
        try: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
        except Exception: pass
    try: return datetime.fromisoformat(meta.get("saved_at","")).date()
    except Exception: return None

def _gsc_freshness(meta):
    d=_gsc_export_date(meta)
    if not d: return "⚪ Data nenustatyta", None
    age=max(0,(date.today()-d).days)
    if age<=7: return f"🟢 Švieži duomenys · {age} d.", age
    if age<=30: return f"🟡 Duomenys {age} d. senumo · auditui tinka, bet galima atnaujinti", age
    return f"🔴 Duomenys {age} d. senumo · rekomenduojama įkelti naują eksportą", age

def _load_seen_products():
    try: return json.loads(SEO_SEEN_META.read_text(encoding="utf-8"))
    except Exception: return {}

def _save_seen_products(data):
    try:
        _ensure_seo_cache(); SEO_SEEN_META.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception: pass

def detect_product_change(product_url, product):
    if not product_url: return False
    key=hashlib.md5(product_url.rstrip('/').encode()).hexdigest()
    data=_load_seen_products(); now=_content_hash(product); prev=data.get(key,{}).get("hash")
    changed=bool(prev and prev!=now)
    data[key]={"url":product_url,"hash":now,"seen_at":datetime.now().isoformat(timespec="seconds")}
    _save_seen_products(data)
    return changed

def read_search_console_workbook(uploaded):
    """Return all useful Search Console sheets instead of assuming one table."""
    name = (getattr(uploaded, "name", "") or "").lower()
    raw = uploaded.getvalue()

    if name.endswith(".xlsx"):
        sheets = _xlsx_frames_without_openpyxl(raw)
    elif name.endswith(".xls"):
        raise ValueError("Senas .xls formatas nepalaikomas. Eksportuok kaip .xlsx arba CSV.")
    else:
        frame = pd.read_csv(io.BytesIO(raw), sep=None, engine="python")
        sheets = {"CSV": frame}

    result = {"queries": pd.DataFrame(), "pages": pd.DataFrame(), "trend": pd.DataFrame(), "filters": pd.DataFrame(), "raw_sheets": sheets}

    for sheet_name, frame in sheets.items():
        sn = _seo_clean_col(sheet_name)
        std = _standardize_gsc_frame(frame)
        cols = set(std.columns)

        if "query" in cols or "uzklaus" in sn:
            if result["queries"].empty:
                result["queries"] = std
        if "page" in cols or "puslap" in sn:
            if result["pages"].empty:
                result["pages"] = std
        if "date" in cols or "diagram" in sn:
            if result["trend"].empty:
                result["trend"] = std
        if "filtr" in sn:
            result["filters"] = frame.copy()

    # CSV can be a page-filtered query export with no separate sheets.
    if name.endswith(".csv"):
        std = _standardize_gsc_frame(next(iter(sheets.values())))
        if "query" in std.columns:
            result["queries"] = std
        if "page" in std.columns:
            result["pages"] = std
        if "date" in std.columns:
            result["trend"] = std

    return result


def _filter_value_map(filters_df):
    out = {}
    if filters_df is None or filters_df.empty or len(filters_df.columns) < 2:
        return out
    a, b = filters_df.columns[:2]
    for _, row in filters_df.iterrows():
        key = _norm(row.get(a, ""))
        val = str(row.get(b, "") or "").strip()
        if key:
            out[key] = val
    return out


def gsc_is_page_filtered(book, product_url=""):
    fm = _filter_value_map(book.get("filters"))
    page_val = ""
    for k, v in fm.items():
        if "puslap" in k or "page" in k:
            page_val = v
            break
    if not page_val:
        return False, ""
    if product_url:
        return page_val.rstrip("/") == product_url.rstrip("/"), page_val
    return True, page_val


def fetch_product_seo(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ProtuoliukasSEO/1.1)"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_desc = md.get("content", "").strip() if md else ""
    h1 = soup.find("h1")
    product_name = h1.get_text(" ", strip=True) if h1 else title.split("|")[0].strip()

    desc_candidates = [
        soup.find(attrs={"itemprop": "description"}),
        soup.find(attrs={"class": re.compile(r"product[-_ ]?description|description[-_ ]?product", re.I)}),
        soup.find(attrs={"id": re.compile(r"product[-_ ]?description|description", re.I)}),
    ]
    main = next((x for x in desc_candidates if x is not None), None) or soup.find("main") or soup.body
    text = main.get_text("\n", strip=True) if main else ""
    text = re.sub(r"\n{3,}", "\n\n", text)

    return {
        "url": url,
        "product_name": product_name,
        "meta_title": title,
        "meta_description": meta_desc,
        "description": text[:14000],
    }


def _weighted_avg(g, col, weight="impressions"):
    if col not in g.columns:
        return 0.0
    ww = g[weight].fillna(0) if weight in g.columns else pd.Series([1] * len(g), index=g.index)
    if ww.sum() > 0:
        return float((g[col].fillna(0) * ww).sum() / ww.sum())
    return float(g[col].fillna(0).mean()) if len(g) else 0.0


def seo_query_table(queries, product, product_specific=False):
    if queries is None or queries.empty or "query" not in queries.columns:
        return pd.DataFrame()
    x = queries.copy()
    for c in ["clicks", "impressions", "ctr", "position"]:
        if c not in x.columns:
            x[c] = 0.0
    x = x.dropna(subset=["query"]).copy()
    x["query"] = x["query"].astype(str).str.strip()
    x = x[x["query"] != ""]

    product_text = _norm(" ".join([
        product.get("product_name", ""), product.get("meta_title", ""),
        product.get("meta_description", ""), product.get("description", "")[:5000],
    ]))
    ptok = _tokens(product_text, min_len=3)

    rows = []
    for q, g in x.groupby("query", dropna=False):
        imp = float(g.impressions.fillna(0).sum())
        clk = float(g.clicks.fillna(0).sum())
        ctr = (clk / imp * 100) if imp else _weighted_avg(g, "ctr")
        pos = _weighted_avg(g, "position")
        qtok = _tokens(q, min_len=3)
        overlap = len(qtok & ptok)
        phrase_in_page = _norm(q) in product_text

        # Product-filtered export: every query is genuinely associated with this page.
        # Sitewide export: only retain plausible lexical candidates and label them as such.
        if not product_specific and overlap == 0 and not phrase_in_page:
            continue

        base = min(55, math.log10(max(imp, 1) + 1) * 18)
        pos_bonus = 24 if 3 <= pos <= 15 else 16 if pos <= 25 else 6
        ctr_gap = max(0, 21 - min(21, ctr * 4))
        relevance = 0 if product_specific else min(18, overlap * 6 + (8 if phrase_in_page else 0))
        score = min(100, round(base + pos_bonus + ctr_gap + relevance))

        rows.append({
            "Užklausa": q,
            "Paspaudimai": int(round(clk)),
            "Parodymai": int(round(imp)),
            "CTR %": round(ctr, 2),
            "Pozicija": round(pos, 1),
            "SEO galimybė": score,
            "Tipas": "produkto užklausa" if product_specific else "svetainės užklausa · galima sąsaja",
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["SEO galimybė", "Parodymai"], ascending=False).head(30)


def page_metrics_for_url(pages, product_url):
    if pages is None or pages.empty or "page" not in pages.columns or not product_url:
        return None
    x = pages.copy()
    exact = x[x["page"].astype(str).str.rstrip("/") == product_url.rstrip("/")]
    if exact.empty:
        return None
    r = exact.iloc[0]
    return {
        "clicks": float(r.get("clicks", 0) or 0),
        "impressions": float(r.get("impressions", 0) or 0),
        "ctr": float(r.get("ctr", 0) or 0),
        "position": float(r.get("position", 0) or 0),
    }


def page_opportunities(pages):
    if pages is None or pages.empty or "page" not in pages.columns:
        return pd.DataFrame()
    x = pages.copy()
    for c in ["clicks", "impressions", "ctr", "position"]:
        if c not in x.columns:
            x[c] = 0.0
    x = x.dropna(subset=["page"])
    rows = []
    for _, r in x.iterrows():
        imp = float(r.get("impressions", 0) or 0)
        clk = float(r.get("clicks", 0) or 0)
        ctr = float(r.get("ctr", 0) or 0)
        pos = float(r.get("position", 0) or 0)
        if imp < 20:
            continue
        volume = min(48, math.log10(imp + 1) * 17)
        pos_bonus = 28 if 3 <= pos <= 15 else 20 if pos <= 25 else 8 if pos <= 40 else 2
        ctr_gap = max(0, 24 - min(24, ctr * 5))
        score = min(100, round(volume + pos_bonus + ctr_gap))
        rows.append({
            "SEO galimybė": score,
            "Puslapis": str(r.get("page", "")),
            "Paspaudimai": int(round(clk)),
            "Parodymai": int(round(imp)),
            "CTR %": round(ctr, 2),
            "Pozicija": round(pos, 1),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["SEO galimybė", "Parodymai"], ascending=False).head(40)


def _content_hash(product):
    raw = "\n".join([
        product.get("product_name", "") or "", product.get("meta_title", "") or "",
        product.get("meta_description", "") or "", product.get("description", "") or "",
    ])
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def _query_coverage(product, opp):
    page_text = _norm(" ".join([
        product.get("product_name", ""), product.get("meta_title", ""),
        product.get("meta_description", ""), product.get("description", ""),
    ]))
    out=[]
    if opp is None or opp.empty:
        return out
    for _, r in opp.head(12).iterrows():
        q=str(r.get("Užklausa", "")).strip()
        if not q: continue
        exact=_norm(q) in page_text
        toks=_tokens(q, min_len=3)
        covered=len(toks & _tokens(page_text, min_len=3))
        ratio=(covered/len(toks)) if toks else 0
        out.append((q, exact, ratio, int(r.get("Parodymai",0) or 0), float(r.get("Pozicija",0) or 0)))
    return out


def audit_product_seo(product, opp, page_metrics=None, product_specific_queries=False):
    name=(product.get("product_name","") or "").strip()
    mt=(product.get("meta_title","") or "").strip()
    md=(product.get("meta_description","") or "").strip()
    desc=(product.get("description","") or "").strip()
    audits={}

    # Product name: conservative. Never change just for length.
    name_good=[]; name_missing=[]; name_change=[]
    if len(name) >= 8: name_good.append("Pavadinimas aiškus ir pakankamai informatyvus.")
    else: name_missing.append("Pavadinimas labai trumpas – neaiški produkto paskirtis.")
    audits["Produkto pavadinimas"]={"status":"🟢 PALIKTI" if not name_missing else "🟡 PATOBULINTI", "good":name_good, "missing":name_missing, "change":name_change}

    # Meta title
    good=[]; missing=[]; change=[]
    if 35 <= len(mt) <= 65: good.append(f"Ilgis tinkamas ({len(mt)} simb.).")
    elif not mt: missing.append("Meta title nepavyko rasti.")
    elif len(mt)<35: missing.append(f"Meta title trumpas ({len(mt)} simb.) – galima aiškiau įvardyti produkto paskirtį.")
    else: missing.append(f"Meta title ilgas ({len(mt)} simb.) – svarbiausia informacija gali būti nukerpama.")
    audits["Meta title"]={"status":"🟢 PALIKTI" if not missing else "🟡 PATOBULINTI", "good":good, "missing":missing, "change":change}

    # Meta description
    good=[]; missing=[]; change=[]
    if 110 <= len(md) <= 165: good.append(f"Ilgis tinkamas ({len(md)} simb.).")
    elif not md: missing.append("Meta description nerasta.")
    elif len(md)<110: missing.append(f"Meta description trumpa ({len(md)} simb.) – galima aiškiau pasakyti, ką pirkėjas gaus.")
    else: missing.append(f"Meta description ilga ({len(md)} simb.) – verta sutrumpinti iki svarbiausio pažado.")
    audits["Meta description"]={"status":"🟢 PALIKTI" if not missing else "🟡 PATOBULINTI", "good":good, "missing":missing, "change":change}

    # Description
    good=[]; missing=[]; change=[]
    words=re.findall(r"\b[\wĄČĘĖĮŠŲŪŽąčęėįšųūž-]+\b", desc, flags=re.UNICODE)
    if len(words)>=70: good.append(f"Aprašymas nėra per trumpas ({len(words)} žodž.).")
    else: missing.append(f"Aprašymas trumpas ({len(words)} žodž.) – gali trūkti paskirties, naudos ar turinio paaiškinimo.")
    if any(x in _norm(desc) for x in ["skirta", "tinka", "vaik", "mokin", "ugd", "lavin"]): good.append("Aprašyme matyti paskirties / ugdomosios naudos signalų.")
    else: missing.append("Silpnai įvardyta, kam priemonė skirta ir kokį gebėjimą ji ugdo.")

    cov=_query_coverage(product, opp)
    strong=[]
    for q, exact, ratio, imp, pos in cov:
        if imp>=20 and not exact and ratio<0.75:
            strong.append(q)
    if product_specific_queries and strong:
        missing.append("Produkto Search Console duomenyse yra svarbių frazių, kurios dabartiniame puslapyje silpnai atspindėtos: " + ", ".join(strong[:4]) + ".")
        change.append("Šias frazes naudoti tik natūraliai ir tik jei jos tiksliai atitinka produkto turinį.")
    elif not product_specific_queries and strong:
        change.append("Visos svetainės užklausų nelaikyti šio produkto raktažodžiais be produkto URL filtro.")
    if not missing:
        status="🟢 PALIKTI"
    elif len(missing)<=2:
        status="🟡 PAPILDYTI, NEPERRAŠYTI"
    else:
        status="🔴 REIKIA RIMČIAU PERŽIŪRĖTI"
    audits["Produkto aprašymas"]={"status":status,"good":good,"missing":missing,"change":change}

    # CTR signal applies primarily to snippet, not description body.
    if page_metrics and page_metrics.get("impressions",0)>=100 and page_metrics.get("position",99)<=15 and page_metrics.get("ctr",0)<1.5:
        audits["Meta title"]["missing"].append("Produktas jau matomas aukštai, bet CTR žemas – verta patikrinti, ar title tiksliai ir patraukliai atspindi produktą.")
        audits["Meta description"]["missing"].append("Žemas CTR rodo, kad paieškos rezultato aprašas gali nepakankamai paskatinti paspausti.")
        audits["Meta title"]["status"]="🟡 PATOBULINTI"
        audits["Meta description"]["status"]="🟡 PATOBULINTI"

    return audits


def audit_score(audits):
    vals=[]
    for a in audits.values():
        stt=a["status"]
        vals.append(100 if "PALIKTI" in stt else 72 if "PAPILDYTI" in stt or "PATOBULINTI" in stt else 48)
    return round(sum(vals)/len(vals)) if vals else 0


def overall_audit_verdict(audits, watching=False):
    if watching:
        return "🕒 STEBĖTI PO PAKEITIMO", "Radaro nuskaitytas produkto turinys pasikeitė. Dabar pirmiausia vertink dabartinį auditą ir neskubėk dar kartą perrašyti vien dėl senesnių Search Console duomenų."
    statuses=[a["status"] for a in audits.values()]
    if any("NEĮVERTINTA" in x for x in statuses):
        return "⚪ DALINIS AUDITAS", "Vieno ar kelių laukų nepavyko patikimai nuskaityti. Jie nemažina SEO balo – įklijuok trūkstamą tekstą į neprivalomą rankinį lauką, jei nori pilno audito."
    if any("RIMČIAU" in x for x in statuses):
        return "🔴 REIKIA PERŽIŪRĖTI", "Yra keli konkretūs trūkumai. Keisk tik tas vietas, kurias Radaras nurodo – ne visą puslapį automatiškai."
    if any("PAPILDYTI" in x or "PATOBULINTI" in x for x in statuses):
        return "🟡 YRA KĄ PATOBULINTI", "Pilno perrašymo nereikia. Žemiau parodyta, ką palikti ir ką konkrečiai papildyti."
    return "🟢 SEO TVARKOJE", "Pagal dabartinį puslapį ir turimus signalus nėra pagrindo keisti tekstus vien dėl SEO."


def make_chatgpt_audit_prompt(product, audits, opp, page_metrics=None, product_specific_queries=False):
    actions=[]
    for name,a in audits.items():
        if "PALIKTI" in a["status"] or "NEĮVERTINTA" in a["status"]:
            continue
        actions.append(f"{name}: {a['status']}")
        for x in a["missing"]:
            actions.append("- Reikia pataisyti: "+x)
        for x in a["change"]:
            actions.append("- Pastaba: "+x)
    qrows=[]
    if product_specific_queries and opp is not None and not opp.empty:
        qrows=opp.head(8)[[c for c in ["Užklausa","Parodymai","CTR %","Pozicija"] if c in opp.columns]].to_dict("records")
    if not actions:
        return "SEO Radaras nenustatė pakeitimų. Tekstų keisti nereikia."
    return (
        "Patobulink mano produkto tekstą pagal šį SEO Radaro auditą. Dabartinį tekstą įklijuosiu atskirai. "
        "Keisk tik tai, kas nurodyta žemiau, neišgalvok produkto savybių ir URL nekeisk.\n\n"
        "RADARO NUSTATYTI PAKEITIMAI:\n" + "\n".join(actions) + "\n\n"
        + ("KONKRETAUS PRODUKTO SEARCH CONSOLE SIGNALAI:\n"+json.dumps(qrows,ensure_ascii=False,indent=2)+"\n\n" if qrows else "")
        + "Išlaikyk tai, kas jau gerai, ir pateik tik pataisytą variantą to elemento, kurį reikia tobulinti."
    )

def copy_block(label, value, caption=None):
    st.markdown(f"**{label}**")
    if caption:
        st.caption(caption)
    st.code(str(value or ""), language=None)

tabs=st.tabs(["🔥 DABAR","📅 NETRUKUS","🔭 ARTĖJA","💡 PRODUKTŲ PLANAI","🔎 SEO OPTIMIZATORIUS","📌 PINTEREST ĮKVĖPIMAS","📅 PROGŲ IDĖJOS","🌿 EVERGREEN"])


def days_to_peak(r,today):
    p,kind,use_date,detail,signals,extra,conf=pedagogical_peak(r,today)
    return (p-today).days

def demand_window(r,today):
    start,pub,peak,last=timing(r,today)
    d=(peak-today).days
    # V11.4: pikas niekada neperkeliamas į šiandieną. Po jo tema lieka ŠIANDIEN
    # tik iki tikros aktualumo lango pabaigos.
    if d < 0:
        return "TODAY" if today <= last else "OUT"
    if d<=7:return "TODAY"
    if d<=14:return "WEEK"
    if d<=30:return "COMING"
    return "OUT"

def allocate_v74(frame):
    eligible=[]
    for _,r in frame.iterrows():
        act,prod=dmap[fp(r)]
        if act!="ATLIKTA": eligible.append((r,act,prod))
    used=set()
    out=[]
    for win,col,n in [("TODAY","7d",12),("WEEK","14d",12),("COMING","30d",12)]:
        exact=[x for x in eligible if demand_window(x[0],today)==win and fp(x[0]) not in used]
        exact.sort(key=lambda x:execution_priority(x[0],float(x[0][col]),today),reverse=True)
        rows=[]
        selected_topics=[]
        for item in exact:
            if too_similar(item[0],selected_topics):
                continue
            rows.append(item); selected_topics.append(item[0])
            if len(rows)>=n: break
        # V9 deliberately does not fill a time window with unrelated dates.
        # A shorter list is more truthful than a fake "today" recommendation.
        used|={fp(x[0]) for x in rows}
        out.append([(r,a,p,float(r[col])+effort_bonus(r)) for r,a,p in rows])
    return out

TODAY_ROWS,WEEK_ROWS,COMING_ROWS=allocate_v74(df)

with tabs[0]:
    st.subheader("🔥 DABAR · ką verta užbaigti ar pradėti artimiausiomis dienomis")
    st.caption("0–7 dienų sprendimų langas. DABAR nereiškia vien šios dienos: Radar vertina, ką realiai dar spėsi užbaigti, ir piko datos nestumdo.")
    if TODAY_ROWS:
        pr,pa,pp,psc=TODAY_ROWS[0]
        st.success(f"🏆 **JEI DABAR UŽBAIGTUM / KURTUM TIK VIENĄ:** {pr.tema} → {pr.mikrotema} · {int(psc)}/100")
        st.write(f"**Kryptis:** {pr.produkto_ideja}")
        _ea,_why=execution_action(pr,today,pa,pp)
        st.write(f"**Ką daryti:** {_ea}")
        st.caption(f"Kodėl prioritetas: {_why} · {effort_level(pr)} kūrybos apimtis · pardavimo potencialas {pr.pardavimo_potencialas}.")
    else:
        st.info("DABAR lange nėra temos, kurios aktyvus paklausos langas dar galiotų. Radar dirbtinai nepritraukia būsimų ar pasibaigusių pikų vien tam, kad užpildytų ekraną – žiūrėk NETRUKUS, ARTĖJA arba EVERGREEN.")
    for i,(r,act,prod,sc) in enumerate(TODAY_ROWS,1):
        start,pub,peak,last=timing(r,today)
        peak_delta=days_to_peak(r,today)
        if peak_delta < 0:
            peak_distance=f"**Pikas buvo prieš:** {abs(peak_delta)} d."
        elif peak_delta == 0:
            peak_distance="**Pirkimo pikas:** šiandien"
        else:
            peak_distance=f"**Iki prognozuojamo pirkimo piko:** {peak_delta} d."
        time_text=(
            f"{peak_distance} "
            f"• **Kūrybos apimtis:** {effort_level(r)} "
            f"• **Grąža už pastangas:** {roi_label(r,sc)}  \n"
            f"**Pradėti:** {start.strftime('%Y-%m-%d')} "
            f"• **Publikuoti:** {pub.strftime('%Y-%m-%d')}–{(peak-timedelta(days=2)).strftime('%Y-%m-%d')} "
            f"• **Pirkimo pikas:** {peak.strftime('%Y-%m-%d')}"
        )
        compact_recommendation(r,act,prod,sc,i,f"today{i}",time_text)

with tabs[1]:
    st.subheader("📅 NETRUKUS · ką verta pasiruošti iš anksto")
    st.caption("8–14 dienų iki piko. Tai pasiruošimo langas: idėjos rodomos pakankamai anksti, kad nereikėtų vytis paskutinę minutę.")
    for i,(r,act,prod,sc) in enumerate(WEEK_ROWS,1):
        start,pub,peak,last=timing(r,today)
        time_text=(
            f"**Iki prognozuojamo pirkimo piko:** {days_to_peak(r,today)} d. "
            f"• **Kūrybos apimtis:** {effort_level(r)} "
            f"• **Grąža už pastangas:** {roi_label(r,sc)}  \n"
            f"**Pagal {get_creation_lead()} d. tempą pradėti:** {start.strftime('%Y-%m-%d')} "
            f"• **Publikuoti:** {pub.strftime('%Y-%m-%d')}–{(peak-timedelta(days=2)).strftime('%Y-%m-%d')}"
        )
        compact_recommendation(r,act,prod,sc,i,f"week{i}",time_text)

with tabs[2]:
    st.subheader("🔭 ARTĖJA · 15–30 dienų iki piko")
    st.caption("Ankstyvas radaras. Trumpa santrauka matoma iškart; pilną produkto planą išskleidi tik tada, kai idėja verta dėmesio.")
    for i,(r,act,prod,sc) in enumerate(COMING_ROWS,1):
        start,pub,peak,last=timing(r,today)
        time_text=(
            f"**Iki prognozuojamo pirkimo piko:** {days_to_peak(r,today)} d. "
            f"• **Kūrybos apimtis:** {effort_level(r)} "
            f"• **Grąža už pastangas:** {roi_label(r,sc)}  \n"
            f"**Numatomas kūrimo startas:** {start.strftime('%Y-%m-%d')} "
            f"• **Publikavimo langas:** {pub.strftime('%Y-%m-%d')}–{(peak-timedelta(days=2)).strftime('%Y-%m-%d')} "
            f"• **Pirkimo pikas:** {peak.strftime('%Y-%m-%d')}"
        )
        compact_recommendation(r,act,prod,sc,i,f"coming{i}",time_text)


with tabs[3]:
    st.subheader("💡 Produktų planai – platesnė perspektyvių produktų bazė")
    st.caption("Čia gali naršyti daugiau variantų pagal pasirinktą horizontą. Tai nėra TOP langų kopija – skirta sąmoningai paieškai ir planavimui.")
    horizon=st.radio("Horizontas",[7,14,30],horizontal=True)
    view=df.sort_values(f"{horizon}d",ascending=False)
    for i,(_,r) in enumerate(view.head(30).iterrows(),1):
        act,prod=dmap[fp(r)]
        w=demand_window(r,today)
        wtxt={"TODAY":"0–7 d. / DABAR","WEEK":"8–14 d. / NETRUKUS","COMING":"15–30 d. / ARTĖJA","OUT":"už aktyvaus 30 d. lango"}[w]
        with st.expander(f"{r.tema} → {r.mikrotema} · {int(r[f'{horizon}d'])}/100 · {wtxt}"):
            full_card(r,act if act in ["KURTI","ISPLESTI","PERPUBLIKUOTI"] else "IDĖJA",prod,key_prefix=f"plan{i}",show_buttons=False)




with tabs[4]:
    st.subheader("🔎 SEO optimizatorius")
    st.caption("V11.5 · produkto SEO auditas. Search Console neprivalomas: įkėlus vieną kartą, Radaras naudoja paskutinį išsaugotą eksportą, kol įkelsi naujesnį.")

    # ---- Search Console: optional + latest saved export ----
    st.markdown("### 📊 Search Console duomenys · neprivaloma")
    saved_upload, saved_meta = load_saved_gsc()
    gsc_file = st.file_uploader("Įkelti naują Search Console eksportą", type=["xlsx", "xls", "csv"], key="seo_gsc", help="Nebūtina kelti kiekvienam produktui. Naujas failas pakeičia anksčiau išsaugotą.")
    if gsc_file is not None:
        try:
            saved_meta=save_gsc_upload(gsc_file); saved_upload,_=load_saved_gsc()
            st.success("Naujas Search Console eksportas išsaugotas ir nuo šiol bus naudojamas SEO auditams.")
        except Exception as e:
            st.warning("Failą perskaičiau, bet nepavyko jo išsaugoti ilgesniam naudojimui. Šioje sesijoje vis tiek bandysiu naudoti.")
            saved_upload=gsc_file; saved_meta={"name":getattr(gsc_file,"name",""),"saved_at":datetime.now().isoformat(timespec="seconds")}

    book=None
    if saved_upload is not None:
        try:
            book=read_search_console_workbook(saved_upload)
            qn=len(book["queries"]) if not book["queries"].empty else 0
            pn=len(book["pages"]) if not book["pages"].empty else 0
            tn=len(book["trend"]) if not book["trend"].empty else 0
            fresh,_=_gsc_freshness(saved_meta)
            st.info(f"Naudojamas: {saved_meta.get('name','Search Console eksportas')} · {fresh} · užklausų {qn} · puslapių {pn} · dienų {tn}")
            if not book["pages"].empty:
                with st.expander("🔥 Kurie svetainės puslapiai turi didžiausią SEO galimybę"):
                    st.caption("Atranka pagal parodymus, CTR ir poziciją – kad žinotum, kurį produktą verta audituoti pirmiausia.")
                    po=page_opportunities(book["pages"])
                    st.dataframe(po.head(25),use_container_width=True,hide_index=True) if not po.empty else st.info("Nepakanka duomenų reitingui.")
        except Exception as e:
            st.error("Nepavyko perskaityti išsaugoto Search Console failo."); st.caption(str(e)[:500]); book=None
    else:
        st.caption("Search Console dar neįkeltas. Auditas vis tiek veiks pagal dabartinį produkto puslapį; tiesiog nebus Google parodymų, CTR, pozicijos ir užklausų signalų.")

    st.divider()
    st.markdown("### 🔗 Audituoti produktą")
    product_url=st.text_input("Produkto nuoroda",placeholder="https://mokymopriemones.eu/...",key="seo_url").strip()
    auto={"url":product_url,"product_name":"","meta_title":"","meta_description":"","description":""}
    scrape_error=""
    if product_url:
        try:
            auto=fetch_product_seo(product_url)
            st.success(f"Puslapis nuskaitytas: {auto.get('product_name','produktas')}")
        except Exception as e:
            scrape_error=str(e); st.warning("Nepavyko patikimai nuskaityti visų produkto puslapio laukų. Žemiau gali įklijuoti trūkstamus tekstus rankiniu būdu.")

    with st.expander("✍️ Neprivalomi rankiniai laukai · naudok tik jei automatinis nuskaitymas netikslus", expanded=bool(product_url and not auto.get("description"))):
        st.caption("Rankiniu būdu įklijuotas tekstas turi prioritetą prieš automatiškai nuskaitytą. Tuščius laukus Radaras paliks iš URL.")
        manual_name=st.text_input("Produkto pavadinimas · neprivaloma",key="seo_manual_name",placeholder=auto.get("product_name","")[:180])
        manual_mt=st.text_input("Meta title · neprivaloma",key="seo_manual_mt",placeholder=auto.get("meta_title","")[:180])
        manual_md=st.text_area("Meta description · neprivaloma",height=90,key="seo_manual_md",placeholder=auto.get("meta_description","")[:300])
        manual_desc=st.text_area("Produkto aprašymas · neprivaloma",height=260,key="seo_manual_desc",placeholder="Įklijuok tik jei Radaras aprašymo nenuskaitė arba nuskaitė neteisingai.")

    product={
        "url":product_url,
        "product_name":manual_name.strip() or auto.get("product_name","") or "",
        "meta_title":manual_mt.strip() or auto.get("meta_title","") or "",
        "meta_description":manual_md.strip() or auto.get("meta_description","") or "",
        "description":manual_desc.strip() or auto.get("description","") or "",
    }
    has_product=bool(product_url and any(product.get(k) for k in ["product_name","meta_title","meta_description","description"]))

    if has_product:
        try:
            page_filtered=False; page_metrics=None; opp=pd.DataFrame()
            if book is not None:
                page_filtered,_=gsc_is_page_filtered(book,product_url)
                page_metrics=page_metrics_for_url(book["pages"],product_url) if product_url else None
                opp=seo_query_table(book["queries"],product,product_specific=page_filtered)

            audits=audit_product_seo(product,opp,page_metrics,page_filtered)
            # A scraper failure must not lower the score as if the page itself lacked content.
            unknown_sections=set()
            if not product.get("description") and not manual_desc.strip(): unknown_sections.add("Produkto aprašymas")
            if not product.get("meta_title") and not manual_mt.strip(): unknown_sections.add("Meta title")
            if not product.get("meta_description") and not manual_md.strip(): unknown_sections.add("Meta description")
            for sec in unknown_sections:
                audits[sec]={"status":"⚪ NEĮVERTINTA · NEPAVYKO NUSKAITYTI","good":[],"missing":[],"change":["Įklijuok šį tekstą į neprivalomą rankinį lauką. Tai techninis nuskaitymo trūkumas, todėl SEO balas dėl jo nemažinamas."]}

            watching=detect_product_change(product_url,product)
            verdict,why=overall_audit_verdict(audits,watching)
            vals=[]
            for a in audits.values():
                if "NEĮVERTINTA" in a["status"]: continue
                vals.append(100 if "PALIKTI" in a["status"] else 72 if "PAPILDYTI" in a["status"] or "PATOBULINTI" in a["status"] else 48)
            score=round(sum(vals)/len(vals)) if vals else 0

            st.divider(); st.markdown(f"## {verdict}"); st.write(why)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("SEO auditas",f"{score}/100" if vals else "–")
            if page_metrics:
                c2.metric("Produkto parodymai",f"{int(page_metrics['impressions']):,}".replace(","," "))
                c3.metric("CTR",f"{page_metrics['ctr']:.2f}%")
                c4.metric("Pozicija",f"{page_metrics['position']:.1f}")
            else:
                c2.metric("Produkto parodymai","–"); c3.metric("CTR","–"); c4.metric("Pozicija","–")

            if watching:
                st.info("🕒 Radaras pastebėjo, kad šio URL tekstai nuo ankstesnio audito pasikeitė. Dabartinį puslapį vertina iš naujo, bet senesni Search Console duomenys dar gali atspindėti ankstesnę versiją – todėl neskubėk vėl perrašyti.")
            if book is None:
                st.warning("🟡 Auditas be Search Console duomenų: vertinama dabartinio produkto puslapio SEO kokybė. Google paklausa, realūs parodymai, CTR, pozicija ir užklausos nevertinami.")
            elif page_metrics is None:
                st.info("Search Console įkeltas, bet šiame eksporte neradau tikslios šio URL eilutės. Puslapio auditas atliekamas, o produkto Google metrikos nerodomos.")

            st.markdown("### 🩺 SEO auditas · tik tai, ką reikia daryti")
            for section,a in audits.items():
                status=a["status"]
                if "PALIKTI" in status:
                    st.success(f"🟢 {section}: nekeisti.")
                    continue
                if "NEĮVERTINTA" in status:
                    st.warning(f"⚪ {section}: nepavyko įvertinti automatiškai. Jei nori pilno audito, įklijuok šį lauką rankiniu būdu aukščiau.")
                    continue
                st.markdown(f"**{status} · {section}**")
                if a["missing"]:
                    for x in a["missing"]:
                        st.write("• "+x)
                if a["change"]:
                    for x in a["change"]:
                        st.caption("↳ "+x)

            if book is not None:
                if page_filtered:
                    st.success("✅ Search Console eksportas filtruotas pagal šį produkto puslapį – užklausų signalus galima naudoti konkrečiam produktui.")
                else:
                    st.info("ℹ️ Bendrame Search Console eksporte užklausų negalima patikimai priskirti vienam produktui. Konkretaus URL parodymai, CTR ir pozicija imami iš „Puslapiai“, o bendros užklausos nelaikomos privalomais raktažodžiais.")
                with st.expander("Search Console užklausų signalai"):
                    if opp.empty: st.caption("Aiškių susijusių užklausų signalų nerasta arba eksportas nėra filtruotas pagal šį produktą.")
                    else: st.dataframe(opp.head(20),use_container_width=True,hide_index=True)

            prompt_text=make_chatgpt_audit_prompt(product,audits,opp,page_metrics,page_filtered)
            needs_changes=any(("PALIKTI" not in a["status"] and "NEĮVERTINTA" not in a["status"]) for a in audits.values())
            if needs_changes:
                st.markdown("### 📋 Kopijuoti į ChatGPT")
                st.caption("Čia tik Radaro diagnozė. Dabartinį aprašymą ar meta tekstą įklijuok į ChatGPT atskirai – Radaras jo nekartoja.")
                st.code(prompt_text,language=None)
        except Exception as e:
            st.error("SEO analizės nepavyko užbaigti."); st.caption(str(e)[:500])
    elif product_url:
        st.info("Automatiškai nepavyko gauti produkto tekstų. Įklijuok bent produkto aprašymą į neprivalomą rankinį lauką – Search Console nėra būtinas.")
    else:
        st.info("Įklijuok produkto nuorodą. Search Console failas nėra privalomas.")


with tabs[5]:
    st.subheader("📌 Pinterest įkvėpimas")
    st.caption("Tik toms temoms, kurias Radar jau atrinko kaip aktualias. Čia ieškome ne kopijuoti dizainą, o rasti kitokių užduoties mechanikų ir pateikimo kampų.")
    insp=radar_inspiration_rows()
    if not insp:
        st.info("Šiuo metu Radar neturi aktyvių temų, todėl Pinterest įkvėpimo sąrašas tuščias.")
    else:
        for horizon,r in insp:
            with st.expander(f"{horizon} · {r.tema} → {r.mikrotema}"):
                st.write(f"**Radaro idėja:** {r.produkto_ideja}")
                st.caption(f"{r.amzius} • {r.sritis} • {r.formatas}")
                queries=pinterest_search_terms(r)
                for q in queries:
                    label=pinterest_mechanic_label(q)
                    st.markdown(f"**📌 {label}**")
                    st.link_button(f"Peržiūrėti Pinterest · {q}",pinterest_url(q),use_container_width=True)
                st.caption("💡 Tikslas: greitai peržiūrėti skirtingus užsienyje naudojamus pateikimo principus ir pritaikyti mechaniką lietuviškam turiniui, nekopijuojant konkretaus dizaino.")

def _as_date(value):
    """Safely normalize date / datetime / pandas Timestamp values to datetime.date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None

def occasion_relevance_label(d, today):
    d0=_as_date(d)
    t0=_as_date(today)
    if d0 is None or t0 is None:
        return "data nepatikslinta"
    delta=(d0-t0).days
    if delta < 0:
        n=abs(delta)
        return f"buvo prieš {n} d. · dar aktualu" if n>1 else "buvo vakar · dar aktualu"
    if delta == 0: return "šiandien"
    if delta == 1: return "rytoj"
    return f"po {delta} d."

def curated_occasion_ideas(o):
    """V11.4: only occasion-specific, usable product directions. No generic filler."""
    occ=str(o['occasion'])
    pot=str(o.get('commercial_weight','vidutinis'))
    data={
      'Mokslo ir žinių diena':[
        ('4–6 m.','PDF','Pirmosios dienos grupėje – situacijų kortelės','Paveikslėlio situacija + saugus pasirinkimas + pokalbis',[
          'Vaikas atėjo į naują grupę ir nežino, kur pasidėti daiktus. Iš paveikslėlių pasirink, ko galėtų paklausti auklėtojos.',
          'Vienas vaikas žaidžia vienas. Pasirink, kaip galima jį pakviesti žaisti kartu.',
          'Du vaikai nori to paties žaislo. Kuris iš trijų sprendimų padėtų susitarti?',
          'Paveikslėliuose parodytos grupės veiklos. Surikiuok: atėjau → pasisveikinau → pasidėjau daiktus → prisijungiau prie veiklos.',
          'Rask paveikslėlį, kuriame vaikas prašo pagalbos tinkamu būdu.',
          'Pasirink, ką galima padaryti, jei pirmą dieną liūdna ir norisi namo.'
        ]),
        ('1–4 kl.','PDF/PPT','Klasės pradžios situacijos – kaip pasielgtum?','Kasdienė mokyklos situacija + keli sprendimai + pasekmė',[
          'Naujokas per pertrauką lieka vienas. Pasirink du būdus, kaip galima padėti jam įsitraukti.',
          'Pamiršai vieną mokyklinę priemonę. Kuris sprendimas atsakingiausias?',
          'Per grupinį darbą visi kalba vienu metu. Kokią taisyklę pasiūlytum?',
          'Draugas suklydo atsakydamas ir keli mokiniai nusijuokė. Ką galėtum pasakyti?',
          'Surūšiuok veiksmus į „padeda klasei susitarti“ ir „trukdo“.',
          'Sukurk vieną klasės susitarimą ir trumpai paaiškink, kam jis reikalingas.'
        ])],
      'Tarptautinė ozono sluoksnio apsaugos diena':[
        ('1–4 kl.','PDF/PPT','Saulė, atmosfera ir apsauga – pažintinės užduotys','Paprastas modelis + faktų atranka + priežasties ir pasekmės ryšiai',[
          'Schemoje Saulė → atmosfera → Žemė pažymėk, kur yra ozono sluoksnis.',
          'Iš trijų teiginių pasirink teisingą: ozono sluoksnis padeda sulaikyti dalį žalingos ultravioletinės spinduliuotės.',
          'Sujunk sąvokas „Saulė“, „UV spinduliai“, „ozono sluoksnis“, „Žemė“ su paprastais paaiškinimais.',
          'Rask netinkamą teiginį: „ozono sluoksnis yra debesų rūšis“ ir paaiškink, kodėl jis netinka.',
          'Pagal paveikslėlius pasirink saugaus elgesio saulėje pavyzdžius: pavėsis, kepurė, tinkami drabužiai.',
          'Užbaik priežasties–pasekmės sakinį: jei ozono sluoksnis suplonėja, Žemės paviršių gali pasiekti daugiau ...'
        ]),
        ('5–8 kl.','PPT/PDF','Ozono sluoksnis: duomenys, priežastys ir sprendimai','Mokslinis paaiškinimas + duomenų interpretavimas + aplinkosauginis sprendimas',[
          'Pagal pateiktą ozono koncentracijos grafiką nustatyk, kuriuo laikotarpiu rodiklis mažiausias.',
          'Paaiškink skirtumą tarp stratosferos ozono sluoksnio ir pažemio ozono.',
          'Iš pateikto sąrašo atrink medžiagas ar veiklas, istoriškai siejamas su ozono sluoksnio ardymu, ir pagrįsk pasirinkimą pagal pateiktą informacinį tekstą.',
          'Sudėliok grandinę: ozoną ardančios medžiagos → cheminiai procesai stratosferoje → mažiau ozono → daugiau UV spinduliuotės.',
          'Perskaityk trumpą informaciją apie Monrealio protokolą ir įvardyk, kokią problemą šalys sprendė kartu.',
          'Palygink du sprendimus ir argumentuok, kuris labiau mažina ozono sluoksniui žalingų medžiagų patekimą į aplinką.'
        ])],
      'Tarptautinė taikos diena':[
        ('5–6 m.','PDF','Taikūs sprendimai – paveikslėlių situacijos','Kasdienis konfliktas + emocija + taikus pasirinkimas',[
          'Du vaikai nori tos pačios mašinėlės. Pasirink paveikslėlį, kuriame jie randa taikų sprendimą.',
          'Draugas netyčia nugriovė tavo statinį. Kuris atsakymas padėtų nesusipykti?',
          'Vienas vaikas nepriimamas į žaidimą. Ką galėtų padaryti kitas vaikas?',
          'Sujunk piktą situaciją su veiksmu, kuris padeda nusiraminti prieš kalbantis.',
          'Surūšiuok paveikslėlius į „sprendžiame taikiai“ ir „konfliktą didiname“.',
          'Užbaik sakinį: „Kai su draugu nesutariame, galime...“ pasirinkdamas vieną iš trijų variantų.'
        ]),
        ('1–4 kl.','PDF/PPT','Ką darytum ir ką pasakytum? – konfliktų sprendimas','Reali situacija + keli atsakymai + pasekmės aptarimas',[
          'Du klasės draugai nori būti komandos kapitonais. Pasiūlyk sprendimą, kuriame abu būtų išgirsti.',
          'Draugas paėmė tavo daiktą neatsiklausęs. Kuris sakinys aiškiai pasako ribą, bet neįžeidžia?',
          'Klasės pokalbyje prasidėjo ginčas. Pasirink žinutę, kuri konfliktą ramina, o ne kursto.',
          'Vienas vaikas atsisako žaisti pagal kitų pasiūlytas taisykles. Kaip grupė galėtų susitarti?',
          'Rask, kuris iš keturių atsakymų yra kompromisas.',
          'Palygink dvi to paties konflikto baigtis ir paaiškink, kuri padėtų išsaugoti santykius.'
        ]),
        ('5–8 kl.','PPT/PDF','Socialinės dilemos: konfliktas, spaudimas ir kompromisas','Realesnė dilema + galimų veiksmų pasekmės + argumentuotas sprendimas',[
          'Du klasės draugai susipyko grupiniame pokalbyje, o vienas prašo kitų pasirinkti pusę. Įvertink tris galimus veiksmus ir jų pasekmes.',
          'Per grupinį darbą du mokiniai nori vadovauti. Pasiūlyk sprendimą be „laimėtojo“ ir „pralaimėtojo“.',
          'Draugas pasako žeidžiantį komentarą ir teisina jį „tik juoku“. Parašyk atsakymą, kuris nustato ribą, bet neeskaluoja konflikto.',
          'Klasėje pasklinda gandas. Ką gali padaryti žmogus, kuris nėra konflikto dalyvis?',
          'Palygink kompromisą, nusileidimą ir bendro sprendimo paiešką konkrečioje situacijoje.',
          'Sukurk keturių žingsnių konflikto sprendimo planą pateiktai situacijai.'
        ])],
      'Europos kalbų diena':[
        ('5–6 m.','PDF','Tas pats žodis skirtingomis kalbomis – paveikslėlių poros','Paveikslėlis + keli trumpi žodžiai + panašumų pastebėjimas',[
          'Prie obuolio paveikslėlio pateik kelių Europos kalbų žodžius ir rask, kurie skamba ar atrodo panašiai.',
          'Sujunk pasisveikinimą su šalies vėliavėle pagal pateiktą pavyzdžių lentelę.',
          'Klausydamasis ar skaitydamas trijų trumpų pasisveikinimų rask du vienodus pagal reikšmę.',
          'Surūšiuok korteles: lietuviškas žodis / kitos kalbos žodis.',
          'Rask paveikslėlį, kurio žodis pateiktas trimis skirtingomis kalbomis.',
          'Pasirink, kuris iš pateiktų žodžių reiškia „ačiū“, remdamasis mažyte žodžių lentele.'
        ]),
        ('1–4 kl.','PDF/PPT','Europos kalbų žodžių laboratorija','Žodžių palyginimas + reikšmės paieška + kalbinis smalsumas',[
          'Palygink žodį „mama“ keliomis Europos kalbomis ir pažymėk panašumus.',
          'Pagal mini žodynėlį sujunk penkis kasdienius žodžius su jų reikšmėmis.',
          'Rask žodžių poras, kurios skirtingose kalbose atrodo panašiai ir reiškia tą patį.',
          'Iš pateiktų pasisveikinimų nustatyk, kurie priklauso skirtingoms kalboms.',
          'Sukurk mini daugiakalbį žodynėlį tema „mokykla“ iš 5 pateiktų žodžių.',
          'Pagal žemėlapį ir žodžių lentelę susiek šalį, kalbą ir vieną pasisveikinimą.'
        ]),
        ('5–8 kl.','PPT/PDF','Europos kalbos: panašumai, skoliniai ir kalbų šeimos','Kalbinių duomenų palyginimas + žodžių kilmės pastebėjimas + argumentavimas',[
          'Palygink tą pačią reikšmę turinčius žodžius keliomis kalbomis ir sugrupuok panašiausias formas.',
          'Pagal pateiktą lentelę nustatyk, kurios kalbos priklauso tai pačiai kalbų šeimai.',
          'Iš kasdien vartojamų lietuviškų žodžių sąrašo atrink pateiktame šaltinyje nurodytus skolinius ir nurodyk jų kilmę.',
          'Palygink du klaidinančiai panašius skirtingų kalbų žodžius, kurių reikšmės skiriasi.',
          'Perskaityk trumpą daugiakalbystės situaciją ir argumentuok, kokių privalumų gali turėti kelių kalbų mokėjimas.',
          'Pagal Europos kalbų žemėlapį padaryk tris išvadas apie kalbų įvairovę.'
        ])],
      'Tarptautinė pagyvenusių žmonių diena':[
        ('5–8 m.','PDF','Kartų istorijos – klausyk, palygink, papasakok','Šeimos kartos + kasdienybės palyginimas + pasakojimas',[
          'Sujunk daiktų poras „anksčiau“ ir „dabar“: laidinis telefonas ir išmanusis telefonas, laiškas ir žinutė.',
          'Pasirink tris klausimus, kuriuos galėtum užduoti seneliui ar vyresniam žmogui apie vaikystę.',
          'Pagal paveikslėlius palygink, kaip galėjo skirtis žaidimai anksčiau ir dabar.',
          'Sudėliok šeimos kartas nuo jauniausios iki vyriausios.',
          'Užbaik sakinį „Iš vyresnio žmogaus galiu išmokti...“.',
          'Pagal trumpą pasakojimą rask vieną dalyką, kuris pasikeitė, ir vieną, kuris liko panašus.'
        ]),
        ('1–4 kl.','PDF/PPT','Interviu su vyresne karta – tyrinėjimo lapai','Klausimų kūrimas + atsakymų fiksavimas + praeities ir dabarties palyginimas',[
          'Pasirink 5 klausimus interviu apie mokyklą, žaidimus ir kasdienybę vaikystėje.',
          'Užrašyk vieną išgirstą prisiminimą ir išskirk svarbiausią jo mintį.',
          'Lentelėje palygink „vaikystė anksčiau / mano vaikystė dabar“.',
          'Iš interviu atsakymų sudaryk 4 įvykių ar pokyčių seką.',
          'Rask, kokį gebėjimą ar tradiciją būtų įdomu perimti iš vyresnės kartos.',
          'Parašyk trumpą padėkos sakinį žmogui, kurio istoriją išklausei.'
        ])],
      'Pasaulinė gyvūnų diena':[
        ('4–6 m.','PDF','Gyvūnų poreikiai – ko kam reikia?','Gyvūnas + buveinė + maistas + atsakingas elgesys',[
          'Sujunk gyvūną su tinkama buveine: žuvis–vanduo, paukštis–lizdas, lapė–urvas.',
          'Parink gyvūnui tinkamą maistą iš trijų paveikslėlių.',
          'Rask paveikslėlį, kuriame su augintiniu elgiamasi atsakingai.',
          'Surūšiuok gyvūnus į naminius ir laukinius.',
          'Pasirink, ko reikia šuniui kasdien: vandens, maisto, judėjimo, priežiūros.',
          'Rask netinkamą veiksmą: erzinti gyvūną, kai jis ilsisi.'
        ]),
        ('1–4 kl.','PDF/PPT','Gyvūnų detektyvai – požymiai, buveinės ir mityba','Požymių analizė + klasifikavimas + išvadų darymas',[
          'Pagal pėdsaką, maistą ir buveinę nustatyk, kuris iš trijų gyvūnų aprašomas.',
          'Suklasifikuok gyvūnus pagal mitybą: augalėdžiai, plėšrūnai, visaėdžiai.',
          'Sujunk prisitaikymo požymį su jo nauda: storas kailis, plėvėtos pėdos, snapo forma.',
          'Pagal trumpą aprašą nustatyk, kokioje buveinėje gyvūnas galėtų gyventi.',
          'Rask vieną gyvūną, kuris grupei netinka, ir pagrįsk.',
          'Sukurk trijų požymių mįslę apie pasirinktą gyvūną.'
        ])],
      'Tarptautinė mokytojų diena':[
        ('5–9 m.','PDF','Mokytojo profesija – ką jis daro per dieną?','Profesijos pažinimas + veiklų seka + padėkos kūrimas',[
          'Iš paveikslėlių atrink veiklas, kurios gali būti mokytojo darbo dalis.',
          'Sudėliok galimą mokytojo dienos seką: pasiruošia → moko → padeda → tikrina darbus.',
          'Rask tris gebėjimus, kurie padeda mokytojui dirbti su klase.',
          'Sujunk klasės situaciją su tuo, kaip mokytojas gali padėti.',
          'Užbaik sakinį „Mokytojui dėkoju už...“ konkrečiu pavyzdžiu.',
          'Sukurk trumpą padėkos kortelės tekstą, kuriame įvardytas konkretus mokytojo darbas.'
        ])],
      'Pasaulinė psichikos sveikatos diena':[
        ('1–4 kl.','PDF/PPT','Kas man padeda, kai sunku? – savireguliacijos situacijos','Emocija + kūno signalas + tinkamos pagalbos ar nusiraminimo strategijos pasirinkimas',[
          'Prieš kontrolinį labai jaudiniesi. Iš keturių veiksmų pasirink du, kurie gali padėti nusiraminti.',
          'Sujunk kūno signalą su galima emocija: greitai plaka širdis, įsitempę pečiai, norisi verkti.',
          'Draugas kelias dienas atrodo liūdnas ir atsitraukęs. Pasirink, kaip galima parodyti rūpestį.',
          'Surūšiuok veiksmus į „galiu pabandyti pats“ ir „verta kreiptis pagalbos į suaugusįjį“.',
          'Užbaik savo pagalbos planą: kai jaučiuosi..., galiu..., o jei nepadeda – kreipiuosi į... .',
          'Rask netinkamą patarimą žmogui, kuris stipriai nerimauja, ir paaiškink, kuo jį pakeistum.'
        ]),
        ('5–8 kl.','PPT/PDF','Kasdienio streso ir pagalbos situacijos','Situacijos analizė + apsauginiai įpročiai + pagalbos ieškojimo sprendimai',[
          'Mokinys kelias savaites miega per mažai dėl mokslų ir veiklų. Išskirk, ką jis gali keisti pats ir kur verta prašyti pagalbos.',
          'Palygink trumpalaikį streso mažinimą ir ilgalaikį problemos sprendimą pateiktoje situacijoje.',
          'Draugas parašo, kad „nieko nebenori“. Pasirink saugiausią reagavimo kryptį: išklausyti, nepalikti vieno su problema ir kreiptis į patikimą suaugusįjį.',
          'Iš dienos režimo pavyzdžio rask tris veiksnius, galinčius stiprinti savijautą.',
          'Atpažink mitą ir faktą apie emocinę savijautą pagal pateiktą informacinį tekstą.',
          'Sukurk asmeninį „kur kreipiuosi pagalbos“ žemėlapį iš patikimų žmonių ir institucijų kategorijų.'
        ])],
      'Pasaulinė maisto diena':[
        ('5–7 m.','PDF','Maisto kelias – nuo ūkio iki stalo','Paveikslėlių seka + maisto kilmė + atsakingas vartojimas',[
          'Sudėliok duonos kelią: grūdai → miltai → tešla → duona.',
          'Sujunk produktą su jo kilme: pienas–karvė, obuolys–obelis, kiaušinis–višta.',
          'Rask, kuriame paveikslėlyje maistas laikomas taip, kad mažiau sugestų.',
          'Surūšiuok: maisto likučius galima panaudoti / reikia išmesti, remiantis pateiktomis saugiomis situacijomis.',
          'Pasirink porciją iš kelių paveikslėlių, kuri padėtų neįsidėti daugiau, nei suvalgysi.',
          'Sudėliok paprastą seką „užauginama → atvežama → parduodama → valgoma“.'
        ]),
        ('1–4 kl.','PDF/PPT','Maistas be švaistymo – situacijos ir skaičiavimai','Kasdieniai pasirinkimai + produktų kelias + paprasti duomenys',[
          'Šeima nusipirko 8 obuolius, 3 liko nesuvalgyti. Kiek suvalgė? Ką galima padaryti su likusiais?',
          'Pagal pirkinių sąrašą pažymėk, kurių produktų jau yra namuose ir kurių nereikia pirkti dar kartą.',
          'Sudėliok produkto kelią nuo ūkio iki parduotuvės ir įvardyk, kuriuose etapuose naudojami ištekliai.',
          'Palygink dvi pietų situacijas ir rask, kur susidaro daugiau maisto atliekų.',
          'Pagal mažą lentelę apskaičiuok, kiek maisto klasė išmetė per tris dienas.',
          'Pasiūlyk du konkrečius būdus, kaip mokyklos valgykloje sumažinti maisto švaistymą.'
        ]),
        ('5–8 kl.','PPT/PDF','Maisto sistema ir švaistymas – duomenų užduotys','Duomenų interpretavimas + tiekimo grandinė + argumentuotas sprendimas',[
          'Pagal pateiktą diagramą nustatyk, kuriame maisto grandinės etape susidaro daugiausia atliekų.',
          'Palygink dviejų produktų kelią nuo gamintojo iki vartotojo ir įvardyk galimus išteklių naudojimo skirtumus.',
          'Apskaičiuok, kiek kilogramų maisto būtų sutaupyta per mėnesį, jei klasė kasdien išmestų 0,4 kg mažiau.',
          'Įvertink situaciją „pirkti daugiau, nes taikoma akcija“ – kada tai taupu, o kada skatina švaistymą?',
          'Perskaityk trumpą tekstą apie maisto ženklinimą ir atskirk „geriausias iki“ nuo „tinka vartoti iki“ pagal pateiktą šaltinį.',
          'Parenk trijų veiksmų pasiūlymą mokyklai, kaip mažinti maisto švaistymą, ir pagrįsk prioritetą.'
        ])]
    }
    rows=data.get(occ,[])
    return [dict(age=a,format=f,product_idea=pi,mechanic=m,examples=ex,sales_potential=pot) for a,f,pi,m,ex in rows]

def occasion_chatgpt_prompt(o,it,ex):
    return (f"Sukurk pilną mokomosios priemonės seriją pagal šią kryptį.\n"
            f"Proga: {o['occasion']} ({o['date'].strftime('%Y-%m-%d')}).\n"
            f"Kam: {it['age']}. Formatas: {it['format']}.\n"
            f"Priemonės kryptis: {it['product_idea']}.\n"
            f"Mechanika: {it['mechanic']}.\n"
            "Išlaikyk pedagogiškai tinkamą sudėtingumą šiam amžiui. Pateik realų turinį, o ne bendrus nurodymus, ką reikėtų sugalvoti. Sukurk įvairias, nesidubliuojančias užduotis ta pačia kryptimi.\n"
            "Pavyzdžiai, rodantys norimą konkretumo lygį:\n- " + "\n- ".join(ex))

with tabs[6]:
    st.subheader("📅 Progų idėjos")
    st.caption("Rodomos tik tos artimiausios progos, kurioms Radaras turi konkrečią, realiai kuriamą priemonės kryptį. Amžiaus grupės nepritempiamos dirbtinai.")
    future=OCCASIONS[(OCCASIONS["date"]>=today-timedelta(days=2)) & (OCCASIONS["date"]<=today+timedelta(days=45))].sort_values("date")
    shown=0
    for _,o in future.iterrows():
        display_ideas=curated_occasion_ideas(o)
        if not display_ideas:
            continue
        shown+=1
        status=occasion_relevance_label(o['date'],today)
        with st.expander(f"{o['date'].strftime('%Y-%m-%d')} · {o['occasion']} · {status}"):
            for it in display_ideas:
                st.markdown(f"### {it['age']} · {it['format']} · {it['product_idea']}")
                st.write(f"**Kaip veiktų priemonė:** {it['mechanic']}")
                ex=it['examples']
                st.markdown("**🧩 Konkretūs kortelių / užduočių pavyzdžiai**")
                for x in ex:
                    st.write("• "+x)
                st.caption(f"Pardavimo potencialas pagal progos signalą: {it['sales_potential']}")
                with st.expander("📋 Paruošta kopijuoti į ChatGPT"):
                    st.code(occasion_chatgpt_prompt(o,it,ex),language=None)
                st.divider()
    if shown==0:
        st.info("Artimiausioms 45 dienoms nėra progų, kurioms šiuo metu turime pakankamai konkrečią produkto idėją. Plikų datų čia nerodome.")

with tabs[7]:
    st.subheader("🌿 Evergreen · ką verta kurti laisvesniu metu")
    st.caption("Čia tik temos, kurios gali pardavinėtis visus metus. Jei joms artėja programinis ar progos pikas, jos keliamos į DABAR / NETRUKUS / ARTĖJA, o ne dubliuojamos čia.")
    evergreen=[]
    active_fps={fp(x[0]) for x in TODAY_ROWS+WEEK_ROWS+COMING_ROWS}
    for _,r in df.sort_values("prioritetas",ascending=False).iterrows():
        if int(r.evergreen)<4:
            continue
        if fp(r) in active_fps:
            continue
        act,prod=dmap[fp(r)]
        if act=="ATLIKTA":
            continue
        # Prioritize commercial value but do not pretend there's an immediate date.
        ev_score=sales_score(r.pardavimo_potencialas)+comp_score(r.konkurencija)*0.2+int(r.evergreen)*3
        evergreen.append((ev_score,r,act,prod))
    evergreen=sorted(evergreen,key=lambda x:x[0],reverse=True)[:15]
    if not evergreen:
        st.info("Šiuo metu nėra papildomų evergreen idėjų už aktyvaus TOP ribų.")
    for sc,r,act,prod in evergreen:
        with st.expander(f"{r.tema} → {r.mikrotema} · evergreen {stars(r.evergreen)}"):
            st.write(f"**💡 {r.produkto_ideja}**")
            st.write(f"**Kam:** {r.amzius} • {r.sritis} • **Formatas:** {r.formatas}")
            st.write(f"**Pardavimo potencialas:** {r.pardavimo_potencialas} • **Konkurencija:** {r.konkurencija}")
            st.caption("Nėra būtina kurti dabar. Radar šią idėją iškels į TOP, kai atsiras stipresnis programinis, progos ar tėvų paklausos signalas.")
            st.markdown("**Užduočių pavyzdžiai**")
            for x in examples(r,5):
                st.write("• "+x)

st.caption("V11.5.1 • DABAR / NETRUKUS / ARTĖJA • realus kūrimo laikas • fiksuoti pikai • konkretūs produkto briefai • katalogo temos padengimas • SEO auditas.")
