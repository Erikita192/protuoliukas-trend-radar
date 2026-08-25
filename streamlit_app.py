
import streamlit as st
import pandas as pd
import math, re, requests, xml.etree.ElementTree as ET, io, json, hashlib, zipfile
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse
from urllib.parse import quote_plus

st.set_page_config(page_title="Protuoliukas Trend Radar V10.5", page_icon="📡", layout="wide")
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
        "raid","abėc","skaič","raš","skaity","emoc","kūnas","spalv","forma",
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
        parent_target=today if pds["start"]<=today<=pds["end"] else pds["start"]
        candidates.append({
            "peak":parent_target,
            "kind":"tevai",
            "use_date":pds["end"],
            "detail":pds,
            "confidence":int(pds["confidence"])
        })

    eligible=[c for c in candidates if c["peak"]>=today-timedelta(days=3)]
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
        aud="pedagogai + tėvai" if any(x in (str(r.tema)+" "+str(r.mikrotema)).lower() for x in ["raid","abėc","skaič","raš","skaity","sudėt","atimt","laikrod"]) else "pedagogai / pagal temą ir tėvai"
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
    st.markdown("**📅 Laikas**")
    st.write(f"**Pradėti kurti:** {'dabar' if today>=start else start.strftime('%Y-%m-%d')}  •  **Optimalu publikuoti:** {pub.strftime('%Y-%m-%d')}  •  **Paskutinė verta diena:** {last.strftime('%Y-%m-%d')}  •  **Tikėtinas pirkimo pikas:** {peak.strftime('%Y-%m-%d')}")
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
        c1,c2=st.columns(2)
        if action_label=="ISPLESTI":
            if c1.button("✅ PRAPLĖČIAU",key=f"{key_prefix}_expanded_{fp(r)}"):
                if code.strip():set_idea_status(fp(r),"PRAPLESTA",code);st.rerun()
                else:st.warning("Įvesk naujai sukurtos priemonės kodą.")
        else:
            if c1.button("✅ SUKŪRIAU",key=f"{key_prefix}_created_{fp(r)}"):
                if code.strip():set_idea_status(fp(r),"SUKURTA",code);st.rerun()
                else:st.warning("Įvesk produkto kodą.")

def compact_done_controls(*args,**kwargs):
    return


def separate_product_angles(r):
    """Suggest distinct sellable product directions from one Radar topic.
    These are alternatives/series ideas, not a requirement to bundle everything together.
    """
    text=_norm(f"{r.tema} {r.mikrotema} {r.produkto_ideja}")
    age=str(r.amzius)
    fmt=str(r.formatas)
    candidates=[]

    def add(title,mechanic):
        if title not in [x[0] for x in candidates]:
            candidates.append((title,mechanic))

    if any(k in text for k in ["procent","trupmen","dešimtain"]):
        add("Sujunk lygiaverčius","Poravimo / trejetų sudarymo kortelės.")
        add("Kuris netinka?","Klaidos aptikimo ir argumentavimo užduotys.")
        add("Užpildyk trūkstamą","Vienos ar dviejų reikšmių konversijos užduotys.")
        add("Vaizdas → užrašas","Vizualinis modelis ir skaitinis atitikmuo.")
    elif any(k in text for k in ["skaič","sudėt","atimt","daugyb","dalyb"]):
        add("Atpažink ir pasirink","Trumpų pasirinkimo užduočių kortelės.")
        add("Vaizdas → veiksmas","Iš paveikslėlio sudaromas skaitinis veiksmas.")
        add("Klaidos detektyvas","Reikia rasti neteisingą sprendimą ar vaizdą.")
        add("Trūkstamas narys","Nežinomo skaičiaus / dėmens paieškos užduotys.")
    elif any(k in text for k in ["raid","abėc","skaity","raš"]):
        add("Atpažink ir rask","Raidės / garso / žodžio atpažinimo kortelės.")
        add("Sujunk poras","Raidė–garsas–paveikslėlis arba žodis–vaizdas.")
        add("Sudėk / sukurk","Žodžių, skiemenų ar sakinių konstravimo priemonė.")
        add("Klaidos paieška","Neteisingos raidės, žodžio ar sakinio aptikimas.")
    elif any(k in text for k in ["emoc","draug","toler","social"]):
        add("Atpažink situaciją","Paveikslėlių / situacijų kortelės.")
        add("Kaip pasielgtum?","Pasirinkimo ir sprendimo scenarijai.")
        add("Ką pasakytum?","Kalbinės reakcijos ir empatijos užduotys.")
        add("Rūšiuok elgesį","Tinka / netinka, saugu / nesaugu, pagarbu / nepagarbu.")
    else:
        aa=angles(r)
        ex=examples(r,8)
        for i,a in enumerate(aa[:4]):
            mech=ex[i] if i < len(ex) else "Atskira tos pačios temos užduočių mechanika."
            add(a,mech)

    return candidates[:4]

def fast_detail_card(r,action_label=None,product=None):
    """Detail content for TOP expanders with no extra DB/network calls.
    Because Streamlit expander itself opens client-side, details appear instantly."""
    start,pub,peak,last=timing(r,today)
    action_label=action_label or "IDĖJA"

    if action_label=="PERPUBLIKUOTI" and product is not None:
        st.write(f"**📣 Priemonė:** {product.pavadinimas} • **Kodas:** {product.kodas or 'nerastas'}")
        st.write(f"**Optimalu perpublikuoti:** {pub.strftime('%Y-%m-%d')}–{min(last,peak).strftime('%Y-%m-%d')} • **Paklausos pikas:** apie {peak.strftime('%Y-%m-%d')}")
        aud="pedagogai + tėvai" if any(x in (str(r.tema)+" "+str(r.mikrotema)).lower() for x in ["raid","abėc","skaič","raš","skaity","sudėt","atimt","laikrod"]) else "pedagogai / pagal temą ir tėvai"
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
    for x in examples(r,8):
        st.write("• "+x)

    series=separate_product_angles(r)
    if len(series)>=3:
        st.markdown("**💎 Potencialas kelioms atskiroms priemonėms**")
        st.caption("Viena aktuali tema nebūtinai = vienas produktas. Žemiau – skirtingi parduodami kampai; jų nereikia sugrūsti į vieną priemonę.")
        for n,(title,mechanic) in enumerate(series,1):
            st.write(f"**{n}. {title}** — {mechanic}")

    st.markdown("**📅 Laikas**")
    st.write(
        f"**Pradėti kurti:** {'dabar' if today>=start else start.strftime('%Y-%m-%d')} "
        f"• **Optimalu publikuoti:** {pub.strftime('%Y-%m-%d')} "
        f"• **Paskutinė verta diena:** {last.strftime('%Y-%m-%d')} "
        f"• **Tikėtinas pirkimo pikas:** {peak.strftime('%Y-%m-%d')}"
    )

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
    st.markdown(f"### {i}. {label} · {int(sc)}/100")
    st.write(f"**{r.tema} → {r.mikrotema}**")

    if act=="PERPUBLIKUOTI" and prod is not None:
        st.caption(f"{prod.pavadinimas} • kodas {prod.kodas or 'nerastas'}")
    elif act=="ISPLESTI" and prod is not None:
        st.caption(f"Išplėsti: {prod.pavadinimas} → {r.produkto_ideja}")
    else:
        st.caption(str(r.produkto_ideja).replace("Pastatyk skaičių","Sudėliok skaičių"))

    st.write(time_text)

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

st.title("📡 Protuoliukas Trend Radar — V10.4")
st.caption("V10.4 • viena aktuali tema gali virsti keliomis atskiromis priemonėmis • Pinterest įkvėpimas")

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
    for horizon,data in [("ŠIANDIEN",TODAY_ROWS),("SAVAITĖ",WEEK_ROWS),("ARTĖJANTYS",COMING_ROWS)]:
        for item in data:
            r=item[0]
            key=_norm(f"{r.tema}|{r.mikrotema}")
            if key in seen: continue
            seen.add(key)
            rows.append((horizon,r))
    return rows[:12]



# ========================= SEO OPTIMIZATORIUS · V10.5 · BE API =========================
def _seo_clean_col(c):
    return _norm(str(c)).replace(" ", "_")

def _xlsx_frames_without_openpyxl(raw):
    ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main","r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            root=ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si",ns): shared.append("".join(t.text or "" for t in si.findall(".//m:t",ns)))
        wb=ET.fromstring(z.read("xl/workbook.xml")); rr=ET.fromstring(z.read("xl/_rels/workbook.xml.rels")); rels={x.attrib["Id"]:x.attrib["Target"] for x in rr}
        out={}
        for sh in wb.findall("m:sheets/m:sheet",ns):
            name=sh.attrib.get("name","Sheet"); rid=sh.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"); target=rels.get(rid,""); path=target.lstrip("/") if target.startswith("/") else "xl/"+target.replace("../","")
            if path not in z.namelist(): continue
            root=ET.fromstring(z.read(path)); rows=[]
            for row in root.findall(".//m:sheetData/m:row",ns):
                vals={}
                for c in row.findall("m:c",ns):
                    mt=re.match(r"([A-Z]+)",c.attrib.get("r",""))
                    if not mt: continue
                    idx=0
                    for ch in mt.group(1): idx=idx*26+ord(ch)-64
                    idx-=1; typ=c.attrib.get("t"); v=c.find("m:v",ns); val=""
                    if typ=="inlineStr": val="".join(t.text or "" for t in c.findall(".//m:t",ns))
                    elif v is not None:
                        val=v.text or ""
                        if typ=="s":
                            try: val=shared[int(val)]
                            except Exception: pass
                    vals[idx]=val
                if vals:
                    a=[""]*(max(vals)+1)
                    for i,v in vals.items(): a[i]=v
                    rows.append(a)
            if rows:
                w=max(map(len,rows)); rows=[r+[""]*(w-len(r)) for r in rows]; hdr=[str(x).strip() or f"col_{i}" for i,x in enumerate(rows[0])]; out[name]=pd.DataFrame(rows[1:],columns=hdr)
        return out

def read_search_console_upload(uploaded):
    name=(getattr(uploaded,"name","") or "").lower(); raw=uploaded.getvalue()
    if name.endswith(".xlsx"):
        books=_xlsx_frames_without_openpyxl(raw); frames=list(books.values())
        if not frames: return pd.DataFrame()
        qframes=[z for z in frames if any("query" in _seo_clean_col(c) or "uzklaus" in _seo_clean_col(c) for c in z.columns)]
        x=qframes[0] if qframes else frames[0]
    elif name.endswith(".xls"):
        raise ValueError("Senas .xls formatas nepalaikomas. Eksportuok kaip .xlsx arba CSV.")
    else: x=pd.read_csv(io.BytesIO(raw),sep=None,engine="python")
    x=x.copy(); aliases={"query":"query","queries":"query","top_queries":"query","uzklausa":"query","uzklausos":"query","page":"page","pages":"page","puslapis":"page","puslapiai":"page","clicks":"clicks","click":"clicks","paspaudimai":"clicks","impressions":"impressions","impression":"impressions","parodymai":"impressions","ctr":"ctr","position":"position","average_position":"position","pozicija":"position","vidutine_pozicija":"position"}
    ren={}
    for c in x.columns:
        k=_seo_clean_col(c)
        if k in aliases: ren[c]=aliases[k]
        elif "query" in k or "uzklaus" in k: ren[c]="query"
        elif "impression" in k or "parodym" in k: ren[c]="impressions"
        elif "click" in k or "paspaud" in k: ren[c]="clicks"
        elif k=="ctr" or "click_through" in k: ren[c]="ctr"
        elif "position" in k or "pozic" in k: ren[c]="position"
        elif k in ("page","pages") or "puslap" in k: ren[c]="page"
    x=x.rename(columns=ren)
    for c in ["clicks","impressions","position"]:
        if c in x.columns: x[c]=pd.to_numeric(x[c].astype(str).str.replace(" ","",regex=False).str.replace(",",".",regex=False),errors="coerce")
    if "ctr" in x.columns:
        vals=x["ctr"].astype(str).str.replace("%","",regex=False).str.replace(",",".",regex=False); x["ctr"]=pd.to_numeric(vals,errors="coerce")
        if len(x["ctr"].dropna()) and x["ctr"].dropna().max()<=1: x["ctr"]*=100
    return x

def fetch_product_seo(url):
    headers={"User-Agent":"Mozilla/5.0 (compatible; ProtuoliukasSEO/1.0)"}; r=requests.get(url,headers=headers,timeout=15); r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
    title=(soup.title.get_text(" ",strip=True) if soup.title else ""); md=soup.find("meta",attrs={"name":re.compile("^description$",re.I)}); meta_desc=md.get("content","").strip() if md else ""; h1=soup.find("h1"); product_name=h1.get_text(" ",strip=True) if h1 else title.split("|")[0].strip()
    main=soup.find("main") or soup.find(attrs={"class":re.compile("product.*description|description.*product",re.I)}) or soup.body; text=main.get_text("\n",strip=True) if main else ""; text=re.sub(r"\n{3,}","\n\n",text)
    return {"url":url,"product_name":product_name,"meta_title":title,"meta_description":meta_desc,"description":text[:12000]}

def seo_opportunity_table(gsc, product_url=""):
    x=gsc.copy()
    if "query" not in x.columns: return pd.DataFrame()
    if product_url and "page" in x.columns:
        exact=x[x["page"].astype(str).str.rstrip("/")==product_url.rstrip("/")]
        if not exact.empty: x=exact
    for c in ["clicks","impressions","ctr","position"]:
        if c not in x.columns: x[c]=0.0
    x=x.dropna(subset=["query"]).copy(); x["query"]=x["query"].astype(str).str.strip(); x=x[x["query"]!=""]
    def wag(g,col,w="impressions"):
        ww=g[w].fillna(0)
        return float((g[col].fillna(0)*ww).sum()/ww.sum()) if ww.sum()>0 else float(g[col].fillna(0).mean())
    rows=[]
    for q,g in x.groupby("query",dropna=False):
        imp=float(g.impressions.fillna(0).sum()); clk=float(g.clicks.fillna(0).sum()); ctr=(clk/imp*100) if imp else wag(g,"ctr"); pos=wag(g,"position")
        score=min(100,round(min(55,math.log10(max(imp,1)+1)*18)+(22 if 3<=pos<=20 else 10 if pos<=30 else 2)+max(0,23-min(23,ctr*4))))
        rows.append({"Užklausa":q,"Paspaudimai":int(clk),"Parodymai":int(imp),"CTR %":round(ctr,2),"Pozicija":round(pos,1),"SEO galimybė":score})
    return pd.DataFrame(rows).sort_values(["SEO galimybė","Parodymai"],ascending=False).head(30)

def current_seo_health(product,opp):
    text=_norm(" ".join([product.get("product_name",""),product.get("meta_title",""),product.get("meta_description",""),product.get("description","")]))
    if opp.empty:return 50,[]
    top=opp.head(10); covered=sum(1 for q in top["Užklausa"] if _norm(q) in text); mt=len(product.get("meta_title","") or ""); md=len(product.get("meta_description","") or ""); score=35+min(35,covered*5)+(15 if 35<=mt<=65 else 7)+(15 if 110<=md<=165 else 7); notes=[]
    if covered<3:notes.append("Stipriausios Search Console frazės silpnai atsispindi puslapio tekste.")
    if not (35<=mt<=65):notes.append("Meta title ilgį / fokusą verta peržiūrėti.")
    if not (110<=md<=165):notes.append("Meta description ilgį / fokusą verta peržiūrėti.")
    return min(100,score),notes

def make_chatgpt_prompt(product,opp,health,notes):
    rows=json.dumps(opp.head(20).to_dict("records"),ensure_ascii=False,indent=2)
    return ("Padėk optimizuoti šį Protuoliuko produkto puslapį pagal realius Google Search Console duomenis.\n\n"
        "SVARBU: URL nekeisti. Neišgalvoti amžiaus, klasės, formato, turinio ar funkcijų. "
        "Netinkamų paieškos intencijų nenaudoti vien dėl parodymų. Jei kažko keisti nereikia, rašyti PALIKTI.\n\n"
        f"PRODUKTAS\nURL: {product.get('url','')}\nPavadinimas: {product.get('product_name','')}\nMeta title: {product.get('meta_title','')}\nMeta description: {product.get('meta_description','')}\n"
        f"Aprašymas:\n{product.get('description','')}\n\nRADARO SEO BŪKLĖ: {health}/100\nPastabos: {'; '.join(notes) if notes else 'nėra'}\n\n"
        f"SEARCH CONSOLE UŽKLAUSOS:\n{rows}\n\n"
        "Pateik: 1) verdiktą NEKEISTI / PAPILDYTI / OPTIMIZUOTI; 2) pagrindinę ir antrines frazes; "
        "3) produkto pavadinimą PALIKTI arba naują; 4) Meta title PALIKTI arba gatavą naują; "
        "5) Meta description PALIKTI arba gatavą naują; 6) jei aprašymą keisti – VISĄ galutinį aprašymą; "
        "7) ko nekeisti ir kokių klaidinančių frazių nenaudoti.")


def render_copy_field(label,value,height=100):
    st.markdown(f"**{label}**");st.code(str(value or ""),language=None)


tabs=st.tabs(["🏠 ŠIANDIEN","📅 SAVAITĖ","🚀 ARTĖJANTYS TOPAI","💡 PRODUKTŲ PLANAI","🔎 SEO OPTIMIZATORIUS","📌 PINTEREST ĮKVĖPIMAS","📅 PROGŲ IDĖJOS","🌿 EVERGREEN","🧠 IDĖJŲ BANKAS"])


def days_to_peak(r,today):
    p,kind,use_date,detail,signals,extra,conf=pedagogical_peak(r,today)
    return (p-today).days

def demand_window(r,today):
    d=days_to_peak(r,today)
    if d < -3:return "OUT"
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
        exact.sort(key=lambda x:float(x[0][col])+effort_bonus(x[0]),reverse=True)
        rows=exact[:n]
        # V9 deliberately does not fill a time window with unrelated dates.
        # A shorter list is more truthful than a fake "today" recommendation.
        used|={fp(x[0]) for x in rows}
        out.append([(r,a,p,float(r[col])+effort_bonus(r)) for r,a,p in rows])
    return out

TODAY_ROWS,WEEK_ROWS,COMING_ROWS=allocate_v74(df)

with tabs[0]:
    st.subheader("🏠 ŠIANDIEN · ką labiausiai apsimoka daryti dabar")
    st.caption("Iki 12 stipriausių galimybių. Matai trumpą santrauką; jei idėja sudomina – išskleidi visą aprašymą. Atliktą pažymėk iškart, kad ji daugiau nebekabėtų.")
    for i,(r,act,prod,sc) in enumerate(TODAY_ROWS,1):
        start,pub,peak,last=timing(r,today)
        time_text=(
            f"**Iki prognozuojamo pirkimo piko:** {days_to_peak(r,today)} d. "
            f"• **Kūrybos apimtis:** {effort_level(r)} "
            f"• **Grąža už pastangas:** {roi_label(r,sc)}  \n"
            f"**Pradėti:** {start.strftime('%Y-%m-%d')} "
            f"• **Publikuoti:** {pub.strftime('%Y-%m-%d')}–{(peak-timedelta(days=2)).strftime('%Y-%m-%d')} "
            f"• **Pirkimo pikas:** {peak.strftime('%Y-%m-%d')}"
        )
        compact_recommendation(r,act,prod,sc,i,f"today{i}",time_text)

with tabs[1]:
    st.subheader("📅 SAVAITĖ · kas taps stipru po savaitės")
    st.caption("8–14 dienų iki piko. Ir čia idėją gali iškart pažymėti atlikta – nereikia laukti, kol ji pereis į ŠIANDIEN.")
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
    st.subheader("🚀 ARTĖJANTYS TOPAI · 15–30 dienų iki piko")
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
        wtxt={"TODAY":"0–7 d. / ŠIANDIEN","WEEK":"8–14 d. / SAVAITĖ","COMING":"15–30 d. / ARTĖJA","OUT":"už aktyvaus 30 d. lango"}[w]
        with st.expander(f"{r.tema} → {r.mikrotema} · {int(r[f'{horizon}d'])}/100 · {wtxt}"):
            full_card(r,act if act in ["KURTI","ISPLESTI","PERPUBLIKUOTI"] else "IDĖJA",prod,key_prefix=f"plan{i}",show_buttons=False)




with tabs[4]:
    st.subheader("🔎 SEO optimizatorius")
    st.caption("Įkelk Search Console eksportą ir pateik produktą. Radaras išanalizuos signalus ir paruoš viską ChatGPT – be API rakto ir papildomų mokamų paslaugų.")
    gsc_file=st.file_uploader("1. Search Console eksportas",type=["xlsx","xls","csv"],key="seo_gsc")
    source=st.radio("2. Produkto informacija",["Produkto nuoroda","Įklijuosiu ranka"],horizontal=True,key="seo_source")
    product=None;product_url=""
    if source=="Produkto nuoroda":
        product_url=st.text_input("Produkto nuoroda",placeholder="https://mokymopriemones.eu/...",key="seo_url").strip()
        if product_url:
            try:product=fetch_product_seo(product_url);st.success(f"Nuskaityta: {product.get('product_name','produktas')}")
            except Exception:st.warning("Nepavyko patikimai nuskaityti produkto puslapio. Gali pasirinkti „Įklijuosiu ranka“.")
    else:
        pn=st.text_input("Produkto pavadinimas",key="seo_pn");mt=st.text_input("Dabartinis Meta title",key="seo_mt");md=st.text_area("Dabartinis Meta description",height=80,key="seo_md");desc=st.text_area("Dabartinis produkto aprašymas",height=220,key="seo_desc")
        if pn and desc:product={"url":"","product_name":pn,"meta_title":mt,"meta_description":md,"description":desc}
    if gsc_file is not None and product:
        try:
            gsc=read_search_console_upload(gsc_file)
            if "query" not in gsc.columns:st.error("Eksporte neradau užklausų (Queries / Užklausos) stulpelio. Įkelk Search Console Performance eksportą su užklausomis.")
            else:
                opp=seo_opportunity_table(gsc,product_url)
                if opp.empty:st.info("Šiam produktui Search Console užklausų neradau.")
                else:
                    health,notes=current_seo_health(product,opp);st.divider();c1,c2,c3=st.columns(3);c1.metric("Dabartinė SEO būklė",f"{health}/100");c2.metric("Analizuojamų užklausų",len(opp));c3.metric("TOP parodymų",f"{int(opp.iloc[0]['Parodymai']):,}".replace(","," "));st.markdown("### Search Console signalai");st.dataframe(opp.head(15),use_container_width=True,hide_index=True)
                    if notes:st.caption(" • ".join(notes))
                    if health>=85: st.success("🟢 SEO atrodo tvarkingai · produkto nereikia perrašyti vien dėl perrašymo")
                    elif health>=65: st.info("🟡 Yra ką peržiūrėti · gali pakakti papildymo")
                    else: st.warning("🟠 Verta SEO peržiūra · yra neišnaudotų signalų")
                    st.markdown("### 📋 Paruošta analizei ChatGPT")
                    st.caption("Nukopijuok visą tekstą žemiau ir įklijuok į mūsų ChatGPT pokalbį. Aš pateiksiu gatavą aprašymą, Meta title ir Meta description.")
                    st.code(make_chatgpt_prompt(product,opp,health,notes),language=None)
                    st.caption("🔒 Be API rakto ir be papildomų mokamų paslaugų. Produkto URL nekeičiamas.")
        except Exception as e:st.error("SEO analizės nepavyko užbaigti.");st.caption(str(e)[:500])
    else:st.info("Pradėk nuo Search Console failo ir produkto nuorodos arba aprašymo.")


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

with tabs[6]:
    st.subheader("📅 Progų idėjos pagal amžių")
    st.caption("Čia proga nėra vien priminimas – matai konkrečius produktų kampus skirtingoms amžiaus grupėms.")
    future=OCCASIONS[(OCCASIONS["date"]>=today-timedelta(days=2)) & (OCCASIONS["date"]<=today+timedelta(days=45))].sort_values("date")
    if future.empty:
        st.info("Artimiausioms 45 dienoms progų bazėje nieko nėra.")
    else:
        for _,o in future.iterrows():
            ideas=OCCASION_IDEAS[OCCASION_IDEAS["occasion"]==o["occasion"]]
            with st.expander(f"{o['date'].strftime('%Y-%m-%d')} · {o['occasion']}"):
                if ideas.empty:
                    st.caption("Šiai progai konkrečių produktų kampų bazę dar pildysime.")
                else:
                    for _,it in ideas.iterrows():
                        st.markdown(f"**{it['age']} · {it['format']} · {it['product_idea']}**")
                        st.write(it["mechanic"])
                        st.caption(f"Pardavimo potencialas: {it['sales_potential']}")
                        st.divider()

with tabs[7]:
    st.subheader("🌿 Evergreen · ką verta kurti laisvesniu metu")
    st.caption("Čia tik temos, kurios gali pardavinėtis visus metus. Jei joms artėja programinis ar progos pikas, jos keliamos į ŠIANDIEN / SAVAITĘ / ARTĖJANČIUS, o ne dubliuojamos čia.")
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

with tabs[8]:
    st.subheader("🧠 Idėjų bankas")
    st.caption("Čia lieka anksčiau Radaro užfiksuotos idėjos. Rankinio ATLIKTA žymėjimo nebenaudojame.")
    bank=idea_bank()
    if bank.empty:
        st.info("Bankas dar tuščias.")
    else:
        # Bankas paliekamas kaip istorinis idėjų sąrašas; rankinio atlikimo darbo srauto nebėra.
        active_bank=bank[~bank.status.isin(["SUKURTA","PRAPLESTA","PASIDALINTA"])].copy()
        done_bank=bank[bank.status.isin(["SUKURTA","PRAPLESTA","PASIDALINTA"])].copy()

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
                    label="SUKURTA" if it.status in ["SUKURTA","PASIDALINTA"] else "PRAPLĖSTA"
                    st.write(f"**{label}** · {it.product_code or 'be kodo'} · {it.tema} → {it.mikrotema}")

st.caption("V9.0.1 FIX • tiksli data tik iš patikrinto 2–3 sav. lango • PASIDALINAU saugiai išsaugoma per ideas istoriją.")
