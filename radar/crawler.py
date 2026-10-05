"""Patikimas parduotuvės crawleris.

Strategija (nepriklauso nuo konkrečios parduotuvės platformos):
  1. sitemap(-ai) iš robots.txt ir /sitemap.xml  -> produktų kandidatai
  2. pradinis puslapis + žinomos sekcijos -> BFS per vidines nuorodas (kategorijos, puslapiavimas, produktai)
  3. puslapio klasifikavimas pagal turinį (JSON-LD / OpenGraph / microdata / formos), ne pagal CSS klases
  4. dedublikavimas pagal canonical / product_id / kelią
  5. diagnostika: aprėptis, klaidos, abejotini puslapiai, kategorijų deklaruoti kiekiai
Nieko neišgalvoja: jei laukas puslapyje nerastas, jis lieka tuščias.
"""
from __future__ import annotations

import json
import re
import time
import gzip
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from urllib import robotparser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = "Mozilla/5.0 (compatible; ProtuoliukasRadar/16; +https://mokymopriemones.eu)"
SKIP_PATH = re.compile(
    r"(/cart|/checkout|/krepsel|/account|/login|/register|/wishlist|/compare|/search|/paieska|/kontakt|"
    r"/privatum|/pirkimo-salyg|/taisykl|/pristatym|/grazinim|/slapuk|/cookie|/sitemap|/feed|/rss|/wp-admin|"
    r"/wp-login|/my-account|/atsijungti|/prisijungti|/registracija|/uzsakym|/lietuvos-pasto|/tag/)", re.I)
SKIP_EXT = re.compile(r"\.(jpe?g|png|gif|webp|svg|pdf|zip|rar|docx?|xlsx?|pptx?|mp[34]|css|js|ico|xml|json|txt)$", re.I)
DROP_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "sort", "order",
               "limit", "sessionid", "sid", "currency", "language", "lang", "view", "display", "orderby", "per_page"}
JUNK_CATS = {"pradzia", "pagrindinis", "home", "parduotuve", "visos priemones", "visi produktai", "namai", "naujienos"}
PRICE_RE = re.compile(r"(\d{1,4}(?:[ .]\d{3})*[.,]\d{1,2}|\d{1,4})\s*(?:€|eur\b|eurų|eur\.)", re.I)


# ----------------------------------------------------------------- URL utils
def norm_url(href: str, base: str, host_ok: set) -> Optional[str]:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    u = urljoin(base, href.strip())
    p = urlparse(u)
    if p.scheme not in ("http", "https"):
        return None
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in host_ok:
        return None
    if SKIP_EXT.search(p.path):
        return None
    if SKIP_PATH.search(p.path):
        return None
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False) if k.lower() not in DROP_PARAMS]
    q.sort()
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme, host, path, "", urlencode(q), ""))


def product_key(url: str) -> str:
    """Stabilus produkto raktas: product_id jei yra, kitaip kelias be užklausos."""
    p = urlparse(url)
    q = dict(parse_qsl(p.query))
    for k in ("product_id", "productid", "pid", "p", "id"):
        if k in q and q[k].isdigit():
            return f"{p.netloc}/?{k}={q[k]}"
    return f"{p.netloc}{p.path.rstrip('/')}"


def listing_base(url: str) -> str:
    p = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in ("page", "p", "pg", "paged")]
    return urlunparse((p.scheme, p.netloc, p.path, "", urlencode(sorted(q)), ""))


# ----------------------------------------------------------------- parsing
def _txt(el) -> str:
    return re.sub(r"\s+", " ", " ".join(el.stripped_strings)) if el else ""


def extract_jsonld(soup) -> list:
    out = []
    for s in soup.find_all("script", type=lambda t: t and "ld+json" in t):
        raw = (s.string or s.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
            except Exception:
                continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                out.append(x)
                for k in ("@graph", "mainEntity", "itemListElement"):
                    if k in x:
                        stack.append(x[k])
    return out


def _types(d: dict) -> set:
    t = d.get("@type", [])
    return {t} if isinstance(t, str) else set(t or [])


def _price_from_offers(offers):
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return "", ""
    p = offers.get("price") or offers.get("lowPrice")
    return (str(p) if p not in (None, "") else ""), str(offers.get("priceCurrency") or "")


def _num(s: str) -> str:
    s = (s or "").strip().replace(" ", "").replace(",", ".")
    m = re.search(r"\d+(?:\.\d{1,2})?", s)
    return m.group(0) if m else ""


def extract_attributes(soup) -> dict:
    """Specifikacijų lentelės / dl / 'Etiketė: reikšmė' eilutės."""
    attrs = {}
    for tr in soup.select("table tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) == 2:
            k, v = _txt(cells[0]), _txt(cells[1])
            if 0 < len(k) < 40 and 0 < len(v) < 200:
                attrs.setdefault(k.rstrip(":"), v)
    for dl in soup.find_all("dl"):
        for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
            k, v = _txt(dt), _txt(dd)
            if 0 < len(k) < 40 and 0 < len(v) < 200:
                attrs.setdefault(k.rstrip(":"), v)
    return attrs


LABELS = {
    "age": ("amzius", "amžius", "klase", "klasė", "amziaus grupe", "amžiaus grupė", "tinka"),
    "format": ("formatas", "failo formatas", "failo tipas", "formatai"),
    "code": ("kodas", "produkto kodas", "prekes kodas", "prekės kodas", "sku", "nr", "produkto nr", "artikulas"),
    "topic": ("tema", "temos", "ugdymo sritis", "sritis", "dalykas"),
}


def pick_attr(attrs: dict, group: str) -> str:
    keys = LABELS[group]
    for k, v in attrs.items():
        if k.lower().strip() in keys:
            return v
    return ""


def breadcrumbs(soup, ld) -> list:
    out = []
    for d in ld:
        if "BreadcrumbList" in _types(d):
            items = d.get("itemListElement", [])
            if isinstance(items, dict):
                items = [items]
            for it in items:
                if isinstance(it, dict):
                    nm = it.get("name")
                    if not nm and isinstance(it.get("item"), dict):
                        nm = it["item"].get("name")
                    if nm:
                        out.append(str(nm))
    if not out:
        for sel in ("nav[aria-label*=read] a", "[class*=breadcrumb] a", "[class*=breadcrumb] li", "ul.breadcrumb li",
                    "[itemtype*=BreadcrumbList] [itemprop=name]"):
            els = soup.select(sel)
            if els:
                out = [_txt(e) for e in els]
                break
    res = []
    for c in out:
        c = c.strip()
        if c and norm_cat(c) not in JUNK_CATS and c not in res and len(c) < 80:
            res.append(c)
    return res


def norm_cat(s: str) -> str:
    return (s or "").translate(str.maketrans("ąčęėįšųūžĄČĘĖĮŠŲŪŽ", "aceeisuuzaceeisuuz")).lower().strip()


@dataclass
class PageResult:
    url: str
    ok: bool = True
    error: str = ""
    kind: str = "other"           # product | listing | other
    product: Optional[dict] = None
    canonical: str = ""
    links: list = field(default_factory=list)          # visos vidinės nuorodos
    card_links: list = field(default_factory=list)     # nuorodos iš turinio (ne meniu) – tik listing
    title: str = ""
    declared_total: Optional[int] = None
    uncertain: bool = False
    status: int = 0


def parse_page(url: str, html: str, host_ok: set, now: str = "") -> PageResult:
    soup = BeautifulSoup(html, "html.parser")
    res = PageResult(url=url)
    ld = extract_jsonld(soup)
    ld_prod = next((d for d in ld if "Product" in _types(d)), None)
    can = soup.find("link", rel="canonical")
    if can and can.get("href"):
        cu = norm_url(can["href"], url, host_ok)
        res.canonical = cu or ""
    h1 = soup.find("h1")
    h1t = _txt(h1)
    res.title = h1t or _txt(soup.title)
    og_type = (soup.find("meta", property="og:type") or {}).get("content", "") if soup.find("meta", property="og:type") else ""
    micro = bool(soup.find(attrs={"itemtype": re.compile("schema.org/Product", re.I)}))
    pid_inputs = soup.select("input[name=product_id], input[name=product-id], input[name=add-to-cart], button[name=add-to-cart]")
    body_cls = " ".join(soup.body.get("class", [])) if soup.body else ""
    card_sel = soup.select(".product-thumb, .product-layout, .product-card, .product-item, li.product, .product-miniature, [class*=product-grid] > *")
    score = 0
    if ld_prod: score += 3
    if og_type.lower() in ("product", "og:product", "product.item"): score += 3
    if micro: score += 3
    if len(pid_inputs) == 1: score += 2
    if re.search(r"\b(product-product|single-product|product-template|page-product|woocommerce-page)\b", body_cls): score += 1
    # puslapis, turintis daug produktų kortelių, bet be stiprių signalų – tai sąrašas
    many_cards = len(card_sel) >= 6
    is_product = score >= 3 and not (many_cards and score < 5 and not ld_prod)
    # silpnas fallback: h1 + viena kaina + pirkimo mygtukas ir nėra daug kortelių
    if not is_product and h1t and not many_cards:
        main = soup.find("main") or soup
        txt = _txt(main)
        buy_n = len(re.findall(r"į krepšel|add to cart|pirkti", txt, re.I))
        price_n = len(PRICE_RE.findall(txt))
        paged = bool(soup.select("a[rel=next], .pagination a, [class*=pagination] a")) or _declared_total(txt)
        if 1 <= buy_n <= 2 and 1 <= price_n <= 3 and not card_sel and not paged:
            is_product = True
            res.uncertain = True
    if is_product:
        res.kind = "product"
        res.product = _build_product(soup, url, res.canonical, ld, ld_prod, h1t, now)
        if not res.product["title"]:
            res.kind = "other"; res.product = None; res.uncertain = True
    else:
        res.kind = "listing" if (many_cards or soup.select("a[rel=next], .pagination a, nav.pagination a, [class*=pagination] a")) else "other"
        res.declared_total = _declared_total(_txt(soup))
    # nuorodos
    seen = set(); links = []; cards = []
    for a in soup.find_all("a", href=True):
        u = norm_url(a["href"], url, host_ok)
        if not u or u in seen:
            continue
        seen.add(u); links.append(u)
        if res.kind != "product" and not _in_chrome(a):
            cards.append(u)
    res.links = links
    res.card_links = cards
    return res


def _in_chrome(a) -> bool:
    for p in a.parents:
        n = getattr(p, "name", "")
        if n in ("nav", "header", "footer", "aside"):
            return True
        cls = " ".join(p.get("class", [])) if hasattr(p, "get") else ""
        if re.search(r"(^|[\s_-])(menu|navbar|nav|breadcrumb|footer|header|topbar|sidebar|filter)([\s_-]|$)", cls, re.I):
            return True
    return False


def _declared_total(text: str) -> Optional[int]:
    m = re.search(r"(?:rodoma|showing)\s*\d+\s*[–\-]\s*\d+\s*(?:iš|of)\s*(\d{1,5})", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:rasta|found|iš viso)\D{0,15}(\d{1,5})\s*(?:prek|produkt|priemon)", text, re.I)
    return int(m.group(1)) if m else None


def _build_product(soup, url, canonical, ld, ld_prod, h1t, now) -> dict:
    title = h1t
    code = price = currency = desc = image = ""
    available = True
    cats = []
    if ld_prod:
        title = title or str(ld_prod.get("name", ""))
        code = str(ld_prod.get("sku") or ld_prod.get("mpn") or "")
        price, currency = _price_from_offers(ld_prod.get("offers"))
        desc = _clean_html_text(str(ld_prod.get("description", "")))
        im = ld_prod.get("image")
        image = im[0] if isinstance(im, list) and im else (im if isinstance(im, str) else "")
        off = ld_prod.get("offers")
        off = off[0] if isinstance(off, list) and off else off
        if isinstance(off, dict) and "OutOfStock" in str(off.get("availability", "")):
            available = False
        c = ld_prod.get("category")
        if isinstance(c, str):
            cats += [x.strip() for x in re.split(r"[>/,]", c) if x.strip()]
    if not price:
        m = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount")
        if m and m.get("content"):
            price = m["content"]
            currency = (soup.find("meta", property="product:price:currency") or {}).get("content", "") if soup.find("meta", property="product:price:currency") else currency
    if not price:
        el = soup.find(attrs={"itemprop": "price"})
        if el:
            price = el.get("content") or _txt(el)
    if not price:
        for sel in (".price-new", ".price", "[class*=price]"):
            el = soup.select_one(sel)
            if el:
                mm = PRICE_RE.search(_txt(el))
                if mm:
                    price = mm.group(1); break
    price = _num(price)
    if price and not currency:
        currency = "EUR"
    attrs = extract_attributes(soup)
    # Protuoliuko produkto numeris pavadinime (pvz. P213) yra patikimesnis už
    # bendrus puslapio atributus, kuriuose gali pasitaikyti kiekiai ar vidiniai ID.
    m_title = re.search(r"\b(P\s*[-–]?\s*\d{1,5})\b", title or "", re.I)
    if m_title:
        code = m_title.group(1)
    if not code:
        code = pick_attr(attrs, "code")
    if not code:
        m = re.search(r"(?:produkto|prekės|prekes)?\s*(?:kodas|nr\.?)\s*[:\-]?\s*(P?[\s\-]?\d{1,6})\b", _txt(soup.find("main") or soup)[:6000], re.I)
        if m:
            code = m.group(1)
    code = re.sub(r"[\s\-]", "", code).upper()[:20]
    if not desc:
        for sel in ("#tab-description", "[itemprop=description]", ".product-description", "#description", ".woocommerce-Tabs-panel--description",
                    ".description", ".tab-content", ".product-short-description"):
            el = soup.select_one(sel)
            if el and len(_txt(el)) > 30:
                desc = _txt(el); break
    if not desc:
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        desc = md.get("content", "") if md else ""
    desc = re.sub(r"\s+", " ", desc)[:4000]
    cats = breadcrumbs(soup, ld) + cats
    for sel in ("meta[property='article:section']", "meta[property='product:category']"):
        m = soup.select_one(sel)
        if m and m.get("content"):
            cats.append(m["content"].strip())
    seen = []
    for c in cats:
        if c and c != title and norm_cat(c) not in JUNK_CATS and c not in seen:
            seen.append(c)
    page_text = _txt(soup.find("main") or soup)
    if re.search(r"išparduota|nėra sandėlyje|out of stock|nebeparduodama", page_text[:6000], re.I):
        available = False
    if not image:
        m = soup.find("meta", property="og:image")
        image = m.get("content", "") if m else ""
    return {
        "url": canonical or url, "title": title.strip(), "code": code, "price": price, "currency": currency,
        "description": desc, "categories": seen, "attributes": dict(list(attrs.items())[:25]),
        "age_text": pick_attr(attrs, "age"), "format_text": pick_attr(attrs, "format"),
        "topic_text": pick_attr(attrs, "topic"), "image": image, "available": available, "fetched_at": now,
    }


def _clean_html_text(s: str) -> str:
    if "<" in s:
        s = BeautifulSoup(s, "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------- crawler
@dataclass
class CrawlConfig:
    base_url: str = "https://mokymopriemones.eu"
    extra_seeds: tuple = ("/naujausios-priemones", "/veiklos-ir-mokomieji-dalykai", "/temos-progos-ir-sezonai",
                          "/pagal-ugdymo-tiksla", "/rinkiniai")
    max_pages: int = 3000
    time_budget_s: int = 540
    workers: int = 6
    connect_timeout: int = 8
    read_timeout: int = 20
    respect_robots: bool = True
    max_errors_kept: int = 200


@dataclass
class CrawlResult:
    ok: bool = False
    complete: bool = False
    products: dict = field(default_factory=dict)         # key -> product dict
    link_tags: dict = field(default_factory=dict)        # key -> set(listing titles)
    visited: set = field(default_factory=set)
    frontier: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    uncertain: list = field(default_factory=list)
    sitemap_urls: int = 0
    sitemap_unfetched: int = 0
    listings: dict = field(default_factory=dict)         # base -> {title, declared_total, found:set}
    pages_fetched: int = 0
    pages_failed: int = 0
    started: str = ""
    finished: str = ""
    stop_reason: str = ""


def make_session(cfg: CrawlConfig) -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]), respect_retry_after_header=True)
    ad = HTTPAdapter(max_retries=retry, pool_connections=cfg.workers + 2, pool_maxsize=cfg.workers + 2)
    s.mount("https://", ad); s.mount("http://", ad)
    s.headers.update({"User-Agent": UA, "Accept-Language": "lt,en;q=0.8", "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5"})
    return s


def _fetch(session, url, cfg):
    r = session.get(url, timeout=(cfg.connect_timeout, cfg.read_timeout), allow_redirects=True)
    return r


def read_sitemaps(session, cfg, host_ok, log) -> list:
    base = cfg.base_url.rstrip("/")
    cands = [base + "/sitemap.xml", base + "/sitemap_index.xml", base + "/sitemap-index.xml"]
    try:
        r = _fetch(session, base + "/robots.txt", cfg)
        if r.ok:
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    cands.insert(0, line.split(":", 1)[1].strip())
    except Exception as e:
        log(f"robots.txt: {type(e).__name__}")
    urls, seen_maps, queue = [], set(), list(dict.fromkeys(cands))
    while queue and len(seen_maps) < 40:
        sm = queue.pop(0)
        if sm in seen_maps:
            continue
        seen_maps.add(sm)
        try:
            r = _fetch(session, sm, cfg)
            if not r.ok:
                continue
            body = r.content
            if sm.endswith(".gz") or body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            text = body.decode("utf8", "ignore")
        except Exception as e:
            log(f"sitemap {sm}: {type(e).__name__}")
            continue
        locs = re.findall(r"<loc>\s*(?:<!\[CDATA\[)?\s*([^<\]\s]+)", text)
        if "<sitemapindex" in text:
            queue.extend(locs)
        else:
            for l in locs:
                u = norm_url(l, base, host_ok)
                if u:
                    urls.append(u)
    return list(dict.fromkeys(urls))


def crawl(cfg: CrawlConfig = None, resume: Optional[dict] = None,
          progress: Optional[Callable[[dict], None]] = None, session=None) -> CrawlResult:
    cfg = cfg or CrawlConfig()
    host = urlparse(cfg.base_url).netloc.lower().replace("www.", "")
    host_ok = {host}
    session = session or make_session(cfg)
    res = CrawlResult(started=datetime.now().isoformat(timespec="seconds"))
    log = lambda m: res.errors.append({"url": "", "error": m}) if len(res.errors) < cfg.max_errors_kept else None
    rp = None
    if cfg.respect_robots:
        try:
            rp = robotparser.RobotFileParser()
            r = _fetch(session, cfg.base_url.rstrip("/") + "/robots.txt", cfg)
            if r.ok:
                rp.parse(r.text.splitlines())
            else:
                rp = None
        except Exception:
            rp = None
    allowed = lambda u: True if rp is None else rp.can_fetch(UA, u)

    base = cfg.base_url.rstrip("/")
    home = norm_url(base + "/", base, host_ok)
    frontier = []
    queued = set()

    def push(u, front=False):
        if u and u not in res.visited and u not in queued:
            queued.add(u)
            (frontier.insert(0, u) if front else frontier.append(u))

    if resume:
        res.visited = set(resume.get("visited", []))
        for u in resume.get("frontier", []):
            push(u)
    sm_urls = read_sitemaps(session, cfg, host_ok, log)
    res.sitemap_urls = len(sm_urls)
    sm_set = set(sm_urls)
    push(home, front=True)
    for sp in cfg.extra_seeds:
        push(norm_url(sp, base, host_ok))
    for u in sm_urls:
        push(u)

    t0 = time.time()
    lock = threading.Lock()
    pages_ok_homepage = False
    now = datetime.now().isoformat(timespec="seconds")

    def work(u):
        try:
            if not allowed(u):
                return PageResult(url=u, ok=False, error="robots.txt draudžia")
            r = _fetch(session, u, cfg)
            if r.status_code >= 400:
                return PageResult(url=u, ok=False, error=f"HTTP {r.status_code}", status=r.status_code)
            ct = r.headers.get("Content-Type", "")
            if "html" not in ct.lower() and ct:
                return PageResult(url=u, ok=True, kind="other")
            pr = parse_page(r.url if r.url else u, r.text, host_ok, now)
            pr.url = u
            pr.status = r.status_code
            return pr
        except Exception as e:
            return PageResult(url=u, ok=False, error=f"{type(e).__name__}: {str(e)[:120]}")

    pending = {}
    ex = ThreadPoolExecutor(max_workers=cfg.workers)
    try:
        while (frontier or pending):
            elapsed = time.time() - t0
            if elapsed > cfg.time_budget_s:
                res.stop_reason = "time_budget"; break
            if res.pages_fetched + len(pending) >= cfg.max_pages:
                res.stop_reason = "max_pages"; break
            while frontier and len(pending) < cfg.workers * 2 and res.pages_fetched + len(pending) < cfg.max_pages:
                u = frontier.pop(0)
                res.visited.add(u)
                pending[ex.submit(work, u)] = u
            if not pending:
                break
            done, _ = wait(list(pending), timeout=2, return_when=FIRST_COMPLETED)
            for f in done:
                u = pending.pop(f)
                pr = f.result()
                res.pages_fetched += 1
                if not pr.ok:
                    res.pages_failed += 1
                    if len(res.errors) < cfg.max_errors_kept:
                        res.errors.append({"url": u, "error": pr.error})
                    continue
                if u == home:
                    pages_ok_homepage = True
                if pr.uncertain and len(res.uncertain) < 60:
                    res.uncertain.append({"url": u, "kind": pr.kind, "title": pr.title[:80]})
                if pr.kind == "product" and pr.product:
                    p = pr.product
                    key = product_key(pr.canonical or u)
                    old = res.products.get(key)
                    if not old or len(p.get("description", "")) > len(old.get("description", "")):
                        res.products[key] = p
                    res.products[key].setdefault("source_urls", [])
                    if u not in res.products[key]["source_urls"] and len(res.products[key]["source_urls"]) < 5:
                        res.products[key]["source_urls"].append(u)
                    # produkto puslapiai kitus produktus randa per susijusius sąrašus
                    for l in pr.links:
                        push(l)
                else:
                    lb = listing_base(u)
                    ls = res.listings.setdefault(lb, {"title": pr.title[:80], "declared_total": None, "found": set()})
                    if pr.declared_total and not ls["declared_total"]:
                        ls["declared_total"] = pr.declared_total
                    if pr.title and not ls["title"]:
                        ls["title"] = pr.title[:80]
                    for l in pr.card_links:
                        res.link_tags.setdefault(product_key(l), set()).add(pr.title[:80])
                        ls["found"].add(product_key(l))
                    # kategorijų puslapiai pirmiau: naujos nuorodos į priekį, jei atrodo kaip sąrašas
                    for l in pr.links:
                        push(l, front=(pr.kind == "listing" and "page=" in l))
            if progress:
                progress({"fetched": res.pages_fetched, "queued": len(frontier), "products": len(res.products),
                          "failed": res.pages_failed, "elapsed": int(time.time() - t0)})
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    res.frontier = list(frontier) + list(pending.values())
    res.finished = datetime.now().isoformat(timespec="seconds")
    res.complete = not res.frontier and not res.stop_reason
    if not res.stop_reason and res.frontier:
        res.stop_reason = "unknown"
    res.ok = pages_ok_homepage or bool(res.products)
    # sitemap aprėptis
    prod_keys = set(res.products)
    fetched_sm = [u for u in sm_set if u in res.visited]
    res.sitemap_unfetched = len([u for u in sm_set if u not in res.visited])
    # susieti kategorijų žymes su produktais
    for key, p in res.products.items():
        tags = res.link_tags.get(key, set())
        p["listing_tags"] = sorted(t for t in tags if t and norm_cat(t) not in JUNK_CATS and t != p["title"])[:12]
    return res


def diagnose(res: CrawlResult) -> dict:
    """Žmogui suprantama aprėpties diagnostika."""
    mismatch = []
    for base, ls in res.listings.items():
        dt = ls.get("declared_total")
        if dt and len(ls["found"]) < dt * 0.9:
            mismatch.append({"listing": base, "title": ls["title"], "deklaruota": dt, "rasta": len(ls["found"])})
    return {
        "pages_fetched": res.pages_fetched, "pages_failed": res.pages_failed, "products": len(res.products),
        "sitemap_urls": res.sitemap_urls, "sitemap_unfetched": res.sitemap_unfetched,
        "listings": len(res.listings), "complete": res.complete, "stop_reason": res.stop_reason,
        "category_mismatch": mismatch[:25], "uncertain": res.uncertain[:20], "errors": res.errors[:30],
    }
