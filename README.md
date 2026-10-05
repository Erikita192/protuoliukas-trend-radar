# PROTUOLIUKO PAKLAUSOS RADARAS · V16

Kasdienis sprendimų įrankis edukacinių priemonių kūrėjui. Atsako į du **atskirus** klausimus:

* **A. Ką naujo kurti?** – 59 temos, 181 konkreti priemonė, datos, publikavimo langai, gamybos laikas, „ar spėsiu“.
* **B. Kuriuos jau turimus produktus reklamuoti?** – tik realiai `mokymopriemones.eu` rasti produktai, atskiras reklamos prioriteto balas.

## Paleidimas
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Streamlit Cloud: įkelk visą aplanką į GitHub, Main file: `streamlit_app.py`.
Logotipas: įdėk `assets/logo.png` (ar `logo.png` šaknyje) – bus rodomas automatiškai. Be jo rodomas tekstinis „PROTUOLIUKAS“ fallback.

## PIRMA, KĄ PATIKRINTI (svarbu)
Šis kodas buvo išbandytas **tik su netikra parduotuve** (dviem skirtingomis HTML struktūromis), nes kūrimo aplinkoje nebuvo prieigos prie tikros svetainės. Todėl po pirmo nuskaitymo atidaryk **⚙️ DUOMENYS**:
1. Ar „Rasta aktyvių produktų“ atitinka tavo realų skaičių?
2. Ar „Kategorijos, kuriose deklaruota daugiau produktų…“ lentelė tuščia?
3. Įklijuok kelis produktų URL į **„Testuoti vieną produkto nuorodą“** ir patikrink kodą, kainą, kategorijas, amžių.
Jei kažko trūksta – parseris pataisomas viename faile (`radar/crawler.py`, funkcija `_build_product`).

## Kaip veikia katalogas
* Crawleris: sitemap + robots.txt + BFS per visas vidines nuorodas (kategorijos, puslapiavimas, produktai). Nepriklauso nuo CSS klasių: produktas atpažįstamas pagal JSON-LD / OpenGraph / microdata / formas.
* Dublikatai: pagal canonical / `product_id` / kelią. Produktas keliose kategorijose = vienas įrašas su žymomis.
* Atsparumas: timeout, retry, vieno puslapio klaida neužgriūna visumos; nepavykęs ar tuščias nuskaitymas **neperrašo** paskutinės geros kopijos; produktas išjungiamas tik po 2 pilnų nuskaitymų, kuriuose jo nebuvo.
* Cache: `data/catalog.json` (patvarus). Mygtukas **🔄 ATNAUJINTI ASORTIMENTĄ** priverstinai skaito iš naujo; **▶ Tęsti nuskaitymą** pratęsia nutrauktą.
* **Periodinis atnaujinimas:** `.github/workflows/refresh_catalog.yml` kasdien paleidžia nuskaitymą ir įrašo `data/catalog.json` į GitHub (Streamlit Cloud failų sistema laikina, todėl taip katalogas išlieka).

## Datos ir ugdymo programos
* Švenčių datos skaičiuojamos kiekvienais metais (Velykos, Užgavėnės, Advento pradžia, Motinos / Tėvo diena).
* `data/school_calendar.json` – ŠMSM 2026–2027 m. m. atostogos. **Naudojimo klasėje data**: jei proga patenka į atostogas / savaitgalį, šventinė medžiaga naudojama iki paskutinės mokymosi dienos (Vėlinės 11-02 → 10-30). Kai ŠMSM paskelbs kitų metų datas – papildyk šį failą.
* **Bendrosios programos (2022 m.) nenurodo mėnesių** (skirstoma 2 metų koncentrais). Mėnesius lemia vadovėliai ir mokytojų ilgalaikiai planai. Todėl kiekvienas aktualumo langas turi **pagrindą** (kalendorius / vadovėlių seka / gamtos sezonas / prielaida) ir **patikimumą**. Mažo patikimumo langus (laikrodis, skaičių tiesė, procentai, neigiami skaičiai) verta patikrinti pagal savo auditorijos leidyklą ir pataisyti `data/ideas.json` → `timing.windows`.
* Pusmečių ir mokslo metų pabaigos datos apytikslės – tvirtina mokykla.

## Balai
* **Galimybių balas (idėjos)** = 0,6 × potencialas + 0,4 × laiko faktorius × įgyvendinamumas. Tai heuristika, **ne Google paklausa**.
* **Reklamos prioritetas (produktai)** = stipriausias laiko varomasis (proga / langas / tęstinė tema) + naujumas + neseniai atnaujintas puslapis + savaitės rotacija (tik tęstiniams) ± signalai. Produktas su tema siejamas pagal pavadinimą / kategoriją; aprašyme reikia ≥2 skirtingų raktažodžių.
* Būsenos: ⚡ PASKUTINĖ PROGA · 🔥 REKLAMUOTI DABAR · ↑ KYLA · 📅 RUOŠTI REKLAMĄ · 💤 DABAR NEAKTUALU.

## Ateities duomenys
`radar/signals.py` + CSV įkėlimas skirtuke **DUOMENYS**: GSC / GA4 (7 d. pokytis), pardavimai, Facebook „paskutinį kartą reklamuota“. Kol CSV neįkeltas, radaras apsimeta jų neturintis (nerodo jokių signalų).

## Struktūra
```
streamlit_app.py        UI (5 skirtukai)
radar/timing.py         progų kalendorius, fazės, gamybos įgyvendinamumas
radar/school.py         ŠMSM atostogos, „naudojimo klasėje“ data
radar/topics.py         idėjų temų vertinimas
radar/crawler.py        crawleris ir parseris
radar/catalog.py        saugykla, sujungimo taisyklės
radar/products.py       produkto praturtinimas ir reklamos prioritetas
radar/weekly.py         „Šią savaitę“ centras
radar/signals.py        ateities duomenų jungtys
radar/ui.py             stilius, kortelės
data/ideas.json         59 temos, 181 priemonė (redaguojama)
data/school_calendar.json
tests/                  pytest / python tests/test_*.py
```
