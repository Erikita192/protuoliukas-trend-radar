import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from radar.crawler import CrawlConfig, crawl, diagnose, parse_page, product_key  # noqa: E402

PRODUCTS = {i: dict(id=i, title=f"P{100 + i} Trupmenų kortelės {i}" if i % 2 else f"Helovino moliūgų užduotys {i}",
                    price=f"{3 + i}.50") for i in range(1, 31)}
CATS = {"matematika": list(range(1, 16)), "sventes": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 1], "naujausios-priemones": [30, 29, 28], "kita": list(range(15, 31))}
PER = 6


def nav():
    return ('<nav><ul><li><a href="/matematika">Matematika</a></li><li><a href="/sventes">Šventės</a></li>'
            '<li><a href="/naujausios-priemones">Naujausios</a></li><li><a href="/kita">Kita</a></li><li><a href="/kontaktai">Kontaktai</a></li></ul></nav>')


def product_page(i, style):
    p = PRODUCTS[i]
    if style == "ld":
        ld = json.dumps({"@context": "https://schema.org", "@type": "Product", "name": p["title"], "sku": f"P{100 + i}",
                         "description": f"Aprašymas produkto {i}. Amžius 7–9 m.", "offers": {"@type": "Offer", "price": p["price"], "priceCurrency": "EUR"}})
        return (f'<html><head><title>x</title><script type="application/ld+json">{ld}</script></head><body>{nav()}'
                f'<ul class="breadcrumb"><li><a href="/">Pradžia</a></li><li><a href="/matematika">Matematika</a></li></ul>'
                f'<h1>{p["title"]}</h1><div class="price">{p["price"]} €</div></body></html>')
    # senesnis HTML: be JSON-LD, su hidden product_id
    return (f'<html><body class="product-product">{nav()}<h1>{p["title"]}</h1><div class="price-new">{p["price"].replace(".", ",")} €</div>'
            f'<form><input type="hidden" name="product_id" value="{i}"><button>Į krepšelį</button></form>'
            f'<div id="tab-description">Aprašymas {i}. Skirta 1–3 kl. mokiniams, formatas PDF.</div>'
            f'<table><tr><td>Amžius</td><td>1–3 kl.</td></tr></table></body></html>')


def listing_page(slug, page, style):
    ids = CATS[slug]
    chunk = ids[(page - 1) * PER: page * PER]
    cards = "".join(f'<div class="product-thumb"><h4><a href="{prod_url(i, style)}">{PRODUCTS[i]["title"]}</a></h4>'
                    f'<span class="price">{PRODUCTS[i]["price"]} €</span><button>Į krepšelį</button></div>' for i in chunk)
    pages = (len(ids) + PER - 1) // PER
    pag = "".join(f'<li><a href="/{slug}?page={n}">{n}</a></li>' for n in range(1, pages + 1) if n != page and abs(n - page) == 1)
    return (f'<html><body>{nav()}<h1>{slug.title()}</h1>{cards}<ul class="pagination">{pag}</ul>'
            f'<p>Rodoma {(page - 1) * PER + 1}–{min(page * PER, len(ids))} iš {len(ids)} ({pages} psl.)</p></body></html>')


def prod_url(i, style):
    return f"/produktas/{i}-priemone" if style == "ld" else f"/index.php?route=product/product&product_id={i}&path=20"


def make_handler(style, sitemap):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            u = urlparse(self.path); q = parse_qs(u.query)
            body, code, ct = "", 200, "text/html; charset=utf8"
            if u.path == "/":
                body = f"<html><body>{nav()}<h1>Protuoliukas</h1></body></html>"
            elif u.path == "/robots.txt":
                body = "User-agent: *\nDisallow: /cart\n" + (f"Sitemap: http://127.0.0.1:{self.server.server_port}/sm.xml\n" if sitemap else ""); ct = "text/plain"
            elif u.path == "/sm.xml" and sitemap:
                locs = "".join(f"<url><loc>http://127.0.0.1:{self.server.server_port}{prod_url(i, style)}</loc></url>" for i in (1, 2, 3))
                body = f'<?xml version="1.0"?><urlset>{locs}</urlset>'; ct = "application/xml"
            elif u.path.strip("/") in CATS:
                body = listing_page(u.path.strip("/"), int(q.get("page", ["1"])[0]), style)
            elif u.path.startswith("/produktas/"):
                body = product_page(int(u.path.split("/")[2].split("-")[0]), "ld")
            elif u.path == "/index.php" and "product_id" in q:
                body = product_page(int(q["product_id"][0]), "oc")
            elif u.path == "/kontaktai":
                body = "<html><body><h1>Kontaktai</h1></body></html>"
            elif u.path == "/flaky":
                code = 500
            else:
                code = 404
            self.send_response(code); self.send_header("Content-Type", ct); self.end_headers()
            self.wfile.write(body.encode("utf8"))
    return H


def run(style, sitemap):
    srv = HTTPServer(("127.0.0.1", 0), make_handler(style, sitemap))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cfg = CrawlConfig(base_url=f"http://127.0.0.1:{srv.server_port}", extra_seeds=("/flaky",), workers=4, respect_robots=True, time_budget_s=60)
    res = crawl(cfg)
    srv.shutdown()
    return res


def test_ld_with_sitemap():
    res = run("ld", True)
    assert res.ok and res.complete
    assert len(res.products) == 30, len(res.products)       # visi, be dublikatų
    p = next(iter(res.products.values()))
    assert p["code"].startswith("P1") and p["price"] and p["categories"]
    d = diagnose(res)
    assert d["pages_failed"] >= 1                            # /flaky nesugadino crawl'o
    assert not d["category_mismatch"], d["category_mismatch"]
    # produktas keliose kategorijose -> viena įrašas su keliomis žymomis
    k = next(k for k, v in res.products.items() if v["title"].endswith(" 1") and "Trupmenų" in v["title"])
    assert len(res.products[k]["listing_tags"]) >= 2, res.products[k]["listing_tags"]
    assert any("Naujausios" in t for v in res.products.values() for t in v["listing_tags"])


def test_opencart_style_dedupe_by_product_id():
    res = run("oc", False)
    assert len(res.products) == 30, len(res.products)
    p = next(iter(res.products.values()))
    assert p["price"] and "." in p["price"]                   # 5,50 -> 5.50
    assert p["age_text"] == "1–3 kl."
    assert p["code"] == "" or p["code"].startswith("P")


def test_code_not_taken_from_random_number():
    html = "<html><head><title>x</title></head><body><h1>24 kortelės apie emocijas</h1><span class='price'>4,00 €</span>" \
           "<form><input type='hidden' name='product_id' value='5'><button>Į krepšelį</button></form></body></html>"
    pr = parse_page("http://x.lt/p/5", html, {"x.lt"})
    assert pr.kind == "product" and pr.product["code"] == ""


if __name__ == "__main__":
    test_ld_with_sitemap(); test_opencart_style_dedupe_by_product_id(); test_code_not_taken_from_random_number()
    print("OK")
