
import streamlit as st
import pandas as pd
import math, re, requests, xml.etree.ElementTree as ET, io, json, hashlib, zipfile, os
from pathlib import Path
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse
from urllib.parse import quote_plus

st.set_page_config(page_title="Protuoliuko paklausos radaras", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

# --- V11.5 universal visual system: same readable palette in light/dark mode ---
st.markdown("""
<style>
:root{--radar-accent:#44695b;--radar-soft:#e8f0ec;--radar-border:#d9e2de;--radar-ink:#17231e;--radar-muted:#64716b;}
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#f7faf8 0,#fff 18rem)!important}.block-container{max-width:1440px;padding-top:1.35rem;padding-bottom:3rem}h1,h2,h3{color:var(--radar-ink);letter-spacing:-.025em}h1{font-weight:760!important}p,li{line-height:1.55}
.radar-hero{background:linear-gradient(135deg,#f8fbf7 0%,#eef7f1 58%,#f8fbf7 100%);border:1px solid #dce9e1;border-radius:1.35rem;padding:1.35rem 1.55rem;color:#17362c;margin:.15rem 0 1rem;box-shadow:0 16px 45px rgba(31,65,52,.09);display:flex;align-items:center;gap:1.15rem}.radar-logo{width:82px;height:82px;object-fit:contain;border-radius:20px;background:#fff;padding:5px;box-shadow:0 6px 18px rgba(24,51,41,.08)}.radar-eyebrow{font-size:.72rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;opacity:.72;margin-bottom:.45rem}.radar-hero h1{color:#17362c!important;font-size:2.05rem!important;margin:0!important;line-height:1.08}.radar-hero p{margin:.45rem 0 0;color:#5d746b;max-width:780px;font-size:.98rem}
.radar-kpi{background:#fff;border:1px solid var(--radar-border);border-radius:1rem;padding:.95rem 1rem;min-height:104px;box-shadow:0 5px 18px rgba(24,51,41,.045)}.radar-kpi .n{font-size:1.7rem;font-weight:780;color:var(--radar-ink);line-height:1.05}.radar-kpi .l{font-size:.78rem;color:var(--radar-muted);margin-top:.35rem}.radar-kpi .s{font-size:.72rem;color:#789087;margin-top:.15rem}
.radar-priority{background:#fff;border:1px solid #cad9d2;border-left:5px solid var(--radar-accent);border-radius:1rem;padding:1.15rem 1.25rem;margin:.8rem 0 1.1rem;box-shadow:0 8px 26px rgba(24,51,41,.06)}.radar-priority .tag{display:inline-block;background:var(--radar-soft);color:#315548;border-radius:999px;padding:.28rem .58rem;font-size:.72rem;font-weight:800;letter-spacing:.035em}.radar-priority h2{font-size:1.28rem!important;margin:.55rem 0 .25rem!important}.radar-priority .meta{color:var(--radar-muted);font-size:.88rem;margin-top:.3rem}.radar-section-title{font-size:.76rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase;color:#72837b;margin:1.2rem 0 .55rem}
.stTabs [data-baseweb="tab-list"]{gap:.18rem;border:1px solid var(--radar-border);background:#fff;border-radius:.9rem;padding:.24rem;overflow-x:auto;box-shadow:0 3px 14px rgba(24,51,41,.035)}.stTabs [data-baseweb="tab"]{height:2.55rem;padding:0 .72rem;border-radius:.65rem;white-space:nowrap;font-size:.88rem;color:var(--radar-muted)}.stTabs [aria-selected="true"]{background:var(--radar-accent)!important;color:#fff!important;font-weight:700}
div[data-testid="stExpander"]{border:1px solid var(--radar-border)!important;border-radius:.9rem!important;background:#fff!important;color:var(--radar-ink)!important;overflow:hidden;box-shadow:0 3px 14px rgba(24,51,41,.035);margin-bottom:.55rem}div[data-testid="stExpander"] summary{background:#fff!important;color:var(--radar-ink)!important}div[data-testid="stExpander"] summary:hover{background:#f6f9f7!important}div[data-testid="stExpander"] summary *,div[data-testid="stExpander"] [data-testid="stExpanderDetails"] *{color:var(--radar-ink)!important}div[data-testid="stExpander"] [data-testid="stExpanderDetails"]{background:#fbfcfb!important;padding-top:.8rem}
div[data-testid="stMetric"]{border:1px solid var(--radar-border)!important;border-radius:.85rem!important;background:#fff!important;padding:.78rem .9rem;box-shadow:0 3px 14px rgba(24,51,41,.035)}div[data-testid="stMetric"] *{color:var(--radar-ink)!important}.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:.7rem;border-color:var(--radar-border);font-weight:650}.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:var(--radar-accent);border-color:var(--radar-accent);color:#fff!important}div[data-baseweb="select"]>div,div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stDateInput"] input,div[data-testid="stFileUploader"] section{border-radius:.7rem!important}section[data-testid="stSidebar"]{border-right:1px solid var(--radar-border)}section[data-testid="stSidebar"]>div{background:#f4f7f5!important;color:var(--radar-ink)!important}section[data-testid="stSidebar"] *{color:var(--radar-ink)}div[data-testid="stAlert"]{border-radius:.85rem}hr{border-color:#edf1ef!important}
@media(max-width:700px){.block-container{padding:.75rem .7rem 2rem}.radar-hero{padding:1rem;border-radius:1rem;gap:.7rem}.radar-logo{width:58px;height:58px;border-radius:14px}.radar-hero h1{font-size:1.55rem!important}.radar-hero p{font-size:.88rem}.radar-kpi{min-height:88px;padding:.75rem}.radar-kpi .n{font-size:1.4rem}.stTabs [data-baseweb="tab"]{padding:0 .55rem;height:2.45rem;font-size:.82rem}h2{font-size:1.3rem!important}h3{font-size:1.08rem!important}}
.radar-30{background:#fff;border:1px solid var(--radar-border);border-radius:1.15rem;padding:1rem 1.05rem;margin:.8rem 0 1.1rem;box-shadow:0 5px 18px rgba(24,51,41,.045)}
.radar-30-head{display:flex;justify-content:space-between;gap:1rem;align-items:end;margin-bottom:.75rem}.radar-30-title{font-weight:800;color:var(--radar-ink);font-size:1rem}.radar-30-sub{font-size:.75rem;color:var(--radar-muted)}
.radar-date-group{display:grid;grid-template-columns:82px 1fr;gap:.65rem;padding:.55rem 0;border-top:1px solid #edf2ef}.radar-date-group:first-of-type{border-top:0}.radar-date{font-size:.75rem;font-weight:800;color:#315648;padding-top:.28rem}.radar-chips{display:flex;flex-wrap:wrap;gap:.38rem}.radar-chip{border:1px solid #dce9e1;background:#f8fbf9;border-radius:999px;padding:.34rem .58rem;font-size:.73rem;color:#29483d}.radar-chip b{font-weight:760}.radar-chip.now{background:#e8f6ee;border-color:#bfe2cc}.radar-chip.soon{background:#fff8e8;border-color:#f0ddb0}.radar-chip.later{background:#f2f5fb;border-color:#d9e1f1}
@media(max-width:700px){.radar-date-group{grid-template-columns:64px 1fr}.radar-chip{border-radius:.65rem;width:100%;padding:.45rem .55rem}.radar-30-head{display:block}.radar-30-sub{margin-top:.2rem}}
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


def theme_semantics(r):
    """V12 semantic guardrail: define the exact learner action before ideas/catalog matching.
    Profiles are deliberately narrow: a nearby keyword is not enough to make two topics the same.
    """
    text=_norm(f"{getattr(r,'tema','')} {getattr(r,'mikrotema','')} {getattr(r,'produkto_ideja','')}")
    profiles=[]
    if ("kalbos dal" in text) and ("sakin" in text):
        profiles.append({
            "id":"kalbos_dalys_sakinyje",
            "label":"Kalbos dalys sakinyje",
            "skill":"Atpažinti ir nustatyti, kokiai kalbos daliai priklauso konkretūs sakinio žodžiai, remiantis jų vartojimu sakinyje.",
            "object":"sakinys ir atskiri jo žodžiai",
            "include":["kalbos dal","daiktavard","būdvard","veiksmaž","įvard","prieveiksm","prielinksn","jungtuk"],
            "exclude":["sakinio dal","veiksn","tarin","skyryb","linksniav","linksnis","žodžių tvark","sakinio kūr"],
            "angles":["Kalbos dalies nustatymas pagal žodį sakinyje","Nurodytos kalbos dalies paieška sakinyje","Klaidingai pažymėtos kalbos dalies taisymas"],
            "examples":[
                "Perskaityti sakinį „Mažas šuo greitai bėga“ ir pažymėti, kuris žodis yra daiktavardis, būdvardis ir veiksmažodis.",
                "Sakinyje rasti visus veiksmažodžius ir juos pažymėti.",
                "Iš trijų paryškintų sakinio žodžių pasirinkti tą, kuris yra būdvardis.",
                "Prie kiekvieno sakinio žodžio parinkti jo kalbos dalies pavadinimą.",
                "Rasti vieną žodį, kurio kalbos dalis pažymėta neteisingai, ir pataisyti.",
                "Suskaičiuoti, kiek sakinyje yra daiktavardžių ir kiek veiksmažodžių.",
                "Duotuose dviejuose sakiniuose rasti tos pačios kalbos dalies žodžius.",
                "Įrašyti į sakinį trūkstamą nurodytos kalbos dalies žodį, kad sakinys išliktų prasmingas."
            ]
        })
    if ("sakinio dal" in text) or (("veiksn" in text or "tarin" in text) and "sakin" in text):
        profiles.append({
            "id":"sakinio_dalys", "label":"Sakinio dalys",
            "skill":"Nustatyti sakinio dalis ir jų vaidmenį sakinyje, o ne žodžio kalbos dalį.",
            "object":"sakinio sandara",
            "include":["sakinio dal","veiksn","tarin","papildin","pažymin","aplinkyb"],
            "exclude":["kalbos dal","daiktavard","būdvard","veiksmažodžių laik"],
            "angles":["Veiksnio ir tarinio nustatymas","Sakinio dalių žymėjimas","Sakinio sandaros analizė"],
            "examples":[
                "Sakinyje pažymėti veiksnį ir tarinį.","Iš kelių žodžių pasirinkti, kuris sakinyje yra veiksnys.",
                "Sujungti sakinio dalį su jai keliamu klausimu.","Rasti sakinį, kuriame neteisingai pažymėtas tarinys.",
                "Pagal pažymėtas sakinio dalis palyginti dviejų sakinių sandarą."
            ]
        })
    return profiles[0] if profiles else None

def examples(r,n=8):
    sem=theme_semantics(r)
    if sem and sem.get("examples"):
        return sem["examples"][:n]
    return [x.strip() for x in str(r.uzduociu_pavyzdziai).split(" | ") if x.strip()][:n]

def angles(r):
    sem=theme_semantics(r)
    if sem and sem.get("angles"):
        return sem["angles"]
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
    sem=theme_semantics(r)
    searchable=(catalog.pavadinimas.fillna("")+" "+catalog.nuoroda.fillna("")).str.lower().map(_norm)
    if sem:
        # Semantic topics use positive evidence and hard exclusions. A shared word such as
        # "sakinys" is never enough to claim that a product covers the same skill.
        def sem_score(x):
            if any(k in x for k in sem.get("exclude",[])): return -99
            hits=sum(k in x for k in sem.get("include",[]))
            # Generic sentence wording alone is intentionally ignored.
            return hits
        scored=searchable.apply(sem_score)
        z=catalog.assign(_score=scored)
        return z[z._score>=1].sort_values("_score",ascending=False).head(8)
    stop={"ugdymas","užduotys","priemonė","kortelės","vaikams","tema","grupės","rinkinys","sakinys","sakinyje"}
    words=[w.lower() for w in re.findall(r"[A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž]{4,}",str(r.tema)+" "+str(r.mikrotema)) if w.lower() not in stop]
    if not words:return catalog.head(0)
    scored=searchable.apply(lambda x:sum(_norm(w) in x for w in words))
    z=catalog.assign(_score=scored)
    # For generic topics require two matching meaningful words when available.
    threshold=2 if len(set(words))>=3 else 1
    return z[z._score>=threshold].sort_values("_score",ascending=False).head(8)

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
    _sem=theme_semantics(r)
    if _sem:
        st.markdown("**🧠 Ką ši tema tiksliai reiškia**")
        st.write(f"**Gebėjimas:** {_sem['skill']}")
        st.write(f"**Su kuo vaikas dirba:** {_sem['object']}")
        if _sem.get('exclude'):
            st.caption("Nesupainioti su: " + ", ".join(_sem['exclude'][:5]) + ".")
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
        st.caption("Pastaba: katalogo susiejimas pirmiausia tikrina konkretų temos gebėjimą. Vien bendras žodis (pvz., „sakinys“) nelaikomas pakankamu įrodymu, kad priemonė dengia tą pačią temą.")
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

st.markdown("""<div class="radar-hero"><img class="radar-logo" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gIoSUNDX1BST0ZJTEUAAQEAAAIYAAAAAAQwAABtbnRyUkdCIFhZWiAAAAAAAAAAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAAHRyWFlaAAABZAAAABRnWFlaAAABeAAAABRiWFlaAAABjAAAABRyVFJDAAABoAAAAChnVFJDAAABoAAAAChiVFJDAAABoAAAACh3dHB0AAAByAAAABRjcHJ0AAAB3AAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAFgAAAAcAHMAUgBHAEIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFhZWiAAAAAAAABvogAAOPUAAAOQWFlaIAAAAAAAAGKZAAC3hQAAGNpYWVogAAAAAAAAJKAAAA+EAAC2z3BhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABYWVogAAAAAAAA9tYAAQAAAADTLW1sdWMAAAAAAAAAAQAAAAxlblVTAAAAIAAAABwARwBvAG8AZwBsAGUAIABJAG4AYwAuACAAMgAwADEANv/bAEMAAwICAwICAwMDAwQDAwQFCAUFBAQFCgcHBggMCgwMCwoLCw0OEhANDhEOCwsQFhARExQVFRUMDxcYFhQYEhQVFP/bAEMBAwQEBQQFCQUFCRQNCw0UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFP/AABEIBEcGAAMBIgACEQEDEQH/xAAeAAEAAQQDAQEAAAAAAAAAAAAAAQIGBwgDBAUJCv/EAFcQAAIBAwIEAwUFBAQJBwsDBQABAgMEEQUGBxIhMUFRYQgTInGBMpGhscEUQlLRFSMzcgkWU2JzdLLh8CQ3Q4KDkvElNDU2RVRjk6LC0hcnhJQYRFWj/8QAHQEBAAEFAQEBAAAAAAAAAAAAAAcBBAUGCAMCCf/EAD0RAQACAQMCBAQEBAQGAgIDAAABAgMEBREGIRIxQVEHEyJhFDJxkUKBobEVIzNSJDQ1Q8HRFnIX4URTYv/aAAwDAQACEQMRAD8A+qYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHh69vjQNr6lpen6vq9pp19qlSVKyoXFVRncTSy4wT7tLqe2nnsWDxN4F7P4walt693Xpi1OpoVw7qypzliEKmMczWOuPmX5Rowt6MKVOKhThFRjFeCXRICsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB//Z"><div><div class="radar-eyebrow">PROTUOLIUKAS · PAKLAUSOS INTELIGENCE</div><h1>Protuoliuko paklausos radaras</h1><p>Ugdymo priemonių paklausos ir produktų sprendimų platforma. Vienoje vietoje: kas aktualėja, kada publikuoti, ką verta kurti ir kokios temos dalies dar trūksta.</p></div></div>""", unsafe_allow_html=True)

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

# V12.1: profesionali platformos apžvalga. Esamos funkcijos ir jų logika nešalinamos.
st.markdown('<div class="radar-section-title">ŠIANDIENOS APŽVALGA</div>', unsafe_allow_html=True)
k1,k2,k3,k4=st.columns(4)
for col,num,label,sub in [(k1,len(TODAY_ROWS),'Aktyvūs signalai','0–7 dienos'),(k2,len(WEEK_ROWS),'Netrukus','8–14 dienų'),(k3,len(COMING_ROWS),'Artėja','15–30 dienų'),(k4,int((df['prioritetas']>=80).sum()) if len(df) else 0,'Stiprūs signalai','80+ balų')]:
    col.markdown(f'<div class="radar-kpi"><div class="n">{num}</div><div class="l">{label}</div><div class="s">{sub}</div></div>',unsafe_allow_html=True)
if TODAY_ROWS:
    _r,_act,_prod,_sc=TODAY_ROWS[0]
    _start,_pub,_peak,_last=timing(_r,today)
    _action,_reason=execution_action(_r,today,_act,_prod)
    _delta=(_peak-today).days
    _peak_txt=(f'pikas po {_delta} d.' if _delta>0 else 'pikas šiandien' if _delta==0 else f'pikas buvo prieš {abs(_delta)} d.')
    _html=f'<div class="radar-priority"><span class="tag">DIDŽIAUSIAS PRIORITETAS DABAR · {int(_sc)}/100</span><h2>{_r.tema} → {_r.mikrotema}</h2><div><b>{_action}</b> · {_r.produkto_ideja}</div><div class="meta">Publikavimo orientyras: {_pub.strftime("%Y-%m-%d")} · {_peak_txt} · kūrybos apimtis: {effort_level(_r)}</div></div>'
    st.markdown(_html,unsafe_allow_html=True)
else:
    st.markdown('<div class="radar-priority"><span class="tag">RAMUS LANGAS</span><h2>Šiandien nėra aktyvaus 0–7 d. signalo</h2><div class="meta">Radar nepildo ekrano dirbtinai. Toliau verta žiūrėti „Netrukus“, „Artėja“ arba „Evergreen“.</div></div>',unsafe_allow_html=True)
# V12.2: tikras 30 dienų paklausos žemėlapis iš tų pačių DABAR / NETRUKUS / ARTĖJA kandidatų.
_timeline=[]
for _win,_rows in [("now",TODAY_ROWS),("soon",WEEK_ROWS),("later",COMING_ROWS)]:
    for _tr,_ta,_tp,_ts in _rows:
        _a,_b,_pk,_z=timing(_tr,today)
        if today <= _pk <= today+timedelta(days=30):
            _timeline.append((_pk,_win,_tr,_ts))
_timeline.sort(key=lambda x:(x[0],-x[3]))
if _timeline:
    from collections import defaultdict as _dd
    _groups=_dd(list)
    for _pk,_win,_tr,_ts in _timeline:
        _groups[_pk].append((_win,_tr,_ts))
    _parts=['<div class="radar-30"><div class="radar-30-head"><div><div class="radar-30-title">📡 30 dienų paklausos radaras</div><div class="radar-30-sub">Visos šiuo metu Radaro aptiktos temos pagal tikrą prognozuojamo piko datą</div></div><div class="radar-30-sub">Šiandien → +30 d.</div></div>']
    for _day,_items in sorted(_groups.items()):
        _date_label=('ŠIANDIEN' if _day==today else _day.strftime('%m-%d'))
        _chips=[]
        for _win,_tr,_ts in _items:
            _name=f'{_tr.tema} → {_tr.mikrotema}' if str(_tr.mikrotema).strip() and str(_tr.mikrotema).strip()!=str(_tr.tema).strip() else str(_tr.tema)
            _chips.append(f'<span class="radar-chip {_win}"><b>{_name}</b> · {int(_ts)}/100</span>')
        _parts.append(f'<div class="radar-date-group"><div class="radar-date">{_date_label}</div><div class="radar-chips">{"".join(_chips)}</div></div>')
    _parts.append('</div>')
    st.markdown(''.join(_parts),unsafe_allow_html=True)
else:
    st.markdown('<div class="radar-30"><div class="radar-30-title">📡 30 dienų paklausos radaras</div><div class="radar-30-sub">Per artimiausias 30 dienų nėra pakankamai patikimų piko signalų. Radar neprideda temų vien tam, kad užpildytų laiko juostą.</div></div>',unsafe_allow_html=True)

st.markdown('<div class="radar-section-title">DARBO ERDVĖ</div>', unsafe_allow_html=True)
tabs=st.tabs(['🔥 DABAR','📅 NETRUKUS','🔭 ARTĖJA','💡 PLANAI','🔎 SEO','📌 PINTEREST','📅 PROGOS','🌿 EVERGREEN','💶 PDF KAINA'])

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



def _eur(x):
    return f"{x:.2f} €".replace(".", ",")

def _psych_price(x):
    # Kainą keliame į artimiausią .90 kainos tašką, niekada nemažiname apskaičiuotos ribos.
    whole=math.floor(x)
    candidate=whole+0.90
    if candidate + 1e-9 < x:
        candidate=whole+1.90
    return round(candidate,2)

def _cut_minutes_per_a4(cards):
    # V11.6: pirmas REALUS kalibravimo taškas – 2 detalės/A4 = 2 min. rankomis žirklėmis.
    # Kiti taškai kol kas yra konservatyvi kreivė ir vėliau gali būti keičiami pagal naujus matavimus.
    pts=[(1,1.5),(2,2.0),(4,3.0),(6,4.0),(8,5.0),(12,6.5),(16,8.0),(20,9.5),(24,11.0),(30,13.0),(40,16.0)]
    cards=max(1,int(cards))
    if cards<=pts[0][0]: return pts[0][1]
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        if cards<=x2:
            return y1+(cards-x1)*(y2-y1)/(x2-x1)
    x1,y1=pts[-2]; x2,y2=pts[-1]
    return y2+(cards-x2)*(y2-y1)/(x2-x1)

def _pdf_price_score(pages, tasks, ptype, diversity, levels, extras):
    # Preliminari Protuoliuko LT auditorijos formulė. Ji sąmoningai konservatyvi:
    # lapų kiekis svarbus, bet kainą labiau kelia turinio įvairovė, lygiai ir papildoma vertė.
    score=2.0
    score += min(0.85, max(0,pages-4)*0.045)
    if tasks:
        score += min(0.55, max(0,tasks-10)*0.012)
    type_add={"Kortelės":0.15,"Užduočių lapai":0.15,"Žaidimas / veiklų rinkinys":0.35,"Plakatai / dekoras":0.0,"Teminis rinkinys / bundle":0.70,"Kita":0.10}
    score += type_add.get(ptype,0.10)
    score += {"Viena pagrindinė mechanika":0.0,"Kelios skirtingos mechanikos":0.35,"Platesnė sistema / daug veiklų":0.65}.get(diversity,0)
    score += {"Vienas lygis":0.0,"2–3 lygiai":0.30,"4+ lygiai":0.55}.get(levels,0)
    score += min(0.60, len(extras)*0.12)
    # Pavienei PDF priemonei >4 € nėra draudžiama, bet tam turi būti aiški papildoma vertė.
    premium = ptype=="Teminis rinkinys / bundle" or diversity=="Platesnė sistema / daug veiklų" or levels=="4+ lygiai" or len(extras)>=3
    if not premium:
        score=min(score,4.0)
    # Patogūs 0,50 € žingsniai; 4,00 € lieka natūralus aukštesnės pavienės priemonės taškas.
    return round(score*2)/2

with tabs[8]:
    st.subheader("💶 PDF kainos skaičiuoklė")
    st.caption("Kiek kainuoti naujai PDF priemonei? Vertinama ne gamybos savikaina, o turinio apimtis, įvairovė ir pirkėjui sukuriama vertė.")
    left,right=st.columns([1,1.2],gap="large")
    with left:
        st.markdown("### 1 · Priemonės apimtis")
        pages=st.number_input("Kiek A4 lapų?",min_value=1,value=12,step=1,key="pdf_pages")
        has_tasks=st.checkbox("Priemonėje yra atskiros užduotys / kortelės",value=True,key="pdf_has_tasks")
        tasks=st.number_input("Kiek užduočių / kortelių?",min_value=1,value=24,step=1,key="pdf_tasks",disabled=not has_tasks) if has_tasks else 0
        st.markdown("### 2 · Turinio vertė")
        ptype=st.selectbox("Priemonės tipas",["Kortelės","Užduočių lapai","Žaidimas / veiklų rinkinys","Plakatai / dekoras","Teminis rinkinys / bundle","Kita"],key="pdf_type")
        diversity=st.selectbox("Užduočių įvairovė",["Viena pagrindinė mechanika","Kelios skirtingos mechanikos","Platesnė sistema / daug veiklų"],key="pdf_div")
        levels=st.selectbox("Sudėtingumo lygiai",["Vienas lygis","2–3 lygiai","4+ lygiai"],key="pdf_levels")
        extras=st.multiselect("Papildoma vertė",["Atsakymai","Naudojimo instrukcija","Papildomi šablonai","Keli panaudojimo variantai","Redaguojami elementai"],key="pdf_extras")
        st.caption("Pavadinimo ir išankstinės kainos nereikia – skaičiuoklė skirta ir visiškai naujai priemonei.")

    pdf_rec=_pdf_price_score(int(pages),int(tasks or 0),ptype,diversity,levels,extras)
    low=max(1.5,pdf_rec-0.5); high=pdf_rec+0.5; floor=max(1.5,pdf_rec-1.0)
    premium_reason=ptype=="Teminis rinkinys / bundle" or diversity=="Platesnė sistema / daug veiklų" or levels=="4+ lygiai" or len(extras)>=3
    with right:
        st.markdown("### 3 · Kainos rekomendacija")
        st.success(f"⭐ **REKOMENDUOJAMA KAINA: {_eur(pdf_rec)}**")
        a,b=st.columns(2)
        a.metric("Racionalus intervalas",f"{_eur(low)}–{_eur(high)}")
        b.metric("Žemiau nerekomenduojama",_eur(floor))
        st.markdown("#### Kodėl tokia rekomendacija?")
        reasons=[]
        if ptype=="Plakatai / dekoras": reasons.append("plakatų ir dekoro PDF vertė skaičiuojama konservatyviau nei mokomųjų užduočių")
        if pages>=20: reasons.append(f"didelė apimtis – {pages} A4 lapai")
        elif pages>=10: reasons.append(f"vidutinė–didesnė apimtis – {pages} A4 lapų")
        else: reasons.append(f"kompaktiška apimtis – {pages} A4 lapų")
        if tasks: reasons.append(f"{tasks} atskiros užduotys / kortelės")
        reasons.append(diversity.lower())
        if levels!="Vienas lygis": reasons.append(levels.lower())
        if extras: reasons.append("papildoma vertė: "+", ".join(x.lower() for x in extras))
        for reason in reasons: st.write("• "+reason)
        st.markdown("#### Kaip pagrįstai kelti kainą?")
        upgrades=[]
        if diversity=="Viena pagrindinė mechanika": upgrades.append("pridėti antrą prasmingą užduoties mechaniką, o ne vien daugiau tokių pačių lapų")
        if levels=="Vienas lygis": upgrades.append("sukurti aiškų progresuojantį 2–3 lygių sudėtingumą")
        if len(extras)<2: upgrades.append("pridėti realią naudojimo vertę: atsakymus, papildomą šabloną ar kelis panaudojimo variantus")
        if not upgrades: upgrades.append("priemonė jau turi kelis vertės sluoksnius; aukštesnę kainą labiau turėtų pagrįsti rinkinio mastas ir reali paklausa")
        for u in upgrades[:3]: st.write("• "+u)
        if pdf_rec>=4 and not premium_reason:
            st.info("4 € ir daugiau pavienei PDF priemonei čia nelaikoma automatine norma. Vien didesnis lapų skaičius kainos nekelia – reikia aiškios papildomos vertės.")
        elif pdf_rec>4:
            st.info("Kaina virš 4 € siūloma todėl, kad priemonė turi ne vien didelę apimtį, bet ir platesnę struktūrą / papildomą vertę.")
        st.caption("PDF kainodaros modelis dar bus kalibruojamas pagal realius pardavimus. 21 A4 / 42 kortelių / vienos pagrindinės mechanikos priemonės 4 € kaina yra vienas realus atskaitos taškas, ne universali taisyklė.")

st.caption("Protuoliuko paklausos radaras V12.2 · paklausos signalai · temos semantika · katalogo spragos · konkretūs produktų briefai · SEO · PDF kainodara")
