# Protuoliuko galimybių centras — V22

**V22 iš pagrindų pakeičia pirmąjį V21 ekraną, tačiau nepraranda sukauptų idėjų ir progų kalendoriaus.**

## Įkėlimas į GitHub / Streamlit

1. Išarchyvuok `protuoliukas_galimybiu_centras_v22.zip`.
2. **Įkelk visus išarchyvuotus failus ir katalogus tiesiai į esamos GitHub repozitorijos šaknį** (ten, kur dabar yra `streamlit_app.py`). Nekelk paties ZIP ir nesukurk papildomo projekto aplanko repozitorijoje.
3. GitHub pakeisk senus failus naujais. **Nepanaikink savų saugomų `data/catalog.json` ar `data/signals.csv`, jeigu jų jau yra GitHub ir jie tau reikalingi**. Šiame ZIP jų nėra, todėl jie automatiškai neperrašomi.
4. Streamlit Cloud paprastai pats persikrauna po GitHub atnaujinimo. Pagrindinis failas lieka `streamlit_app.py`.

Vietinis paleidimas:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Kas naujo

- **🎯 Galimybės**: konkrečios idėjos `ką kurti`, realių katalogo produktų reklamos galimybės `ką reklamuoti`, importuotais rodikliais pagrįsti `ką pagerinti`. Pasirinkimas pagal laiką (iki 2 / iki 5 val. / 1–2 d. d.).
- **💡 Idėjų biblioteka**: **visos 68 temos ir 200 konkrečių idėjų** iš V21 `data/ideas.json` be jokio karpymo. Paieška, amžiaus, dalyko, formato ir sezoniškumo filtrai. Praėjusios datos neištrina idėjų.
- **📆 Progų kalendorius**: V21 **132 progų įrašai** (įskaitant apytiksles / kintamas), metai ir mėnuo pasirenkami, rodomas publikavimo orientyras. Išsaugotas mokyklos kalendorius.
- **🛍️ Mano produktai**: saugus V21 katalogo nuskaitymas etapais, automatinis foninis tikrinimas, rankinio paleidimo galimybė, esamo katalogo reklamos periodai.
- **🔎 Rinkos radiniai**: galima įkelti tikrų šaltinių su nuorodomis ir datomis CSV, be spėjamų „rinkos populiarumo“ skaičių.
- **⚙️ Duomenys**: du CSV importai ir jų šablonai. Kiekviena išvada aiškiai pažymi, ar ji grindžiama realiais duomenimis, ar tik redakcine / kalendorine prielaida.
- Integruotas tikras **„Protuoliuko“ logotipas** `assets/logo.png`. Šviesi tema ir skaitomas kontrastas visais įrenginio režimais.

## Svarbios ribos

**V22 automatiškai neskaito Google Search Console, GA4, pardavimų ir konkurentų platformų paskyrų.** Tam reikalingas autorizuotas ryšys arba CSV importas. Jei duomenų nėra, sistema jų **neišgalvoja**, o siūlo tik kalendorinius / redakcinius veiksmus. Produkto reklamos balai yra planavimo orientyras, ne išmatuotos paklausos matas.

**Esamų produktų nuskaitymas:** katalogo pradinis nuskaitymas gali užtrukti, kol sukaups produktus. Fono atnaujinimas ir `.github/workflows/refresh_catalog.yml` išsaugoti. Jei shop svetainės struktūra pasikeičia ar Streamlit Cloud nutraukia procesą, gali prireikti paspausti `Patikrinti katalogą dabar` / `Tęsti dalinį nuskaitymą`. Jei ankstesnis katalogas GitHub `data/catalog.json` jau buvo, jo nenaikink.

**Streamlit Cloud duomenys nėra garantuotai išsaugomi tarp paleidimų.** Importuotų CSV nepalik vien debesies laikiname diske. Prireikus atsisiųsk kopijas arba laikyk tinkamai apsaugotame saugyklos sprendime. Į viešą GitHub repozitoriją nedėk privačių pardavimo ataskaitų.

### Signalų CSV

Minimalus failas turi `code` (pvz., `P213`) arba `url`; neprivalomi stulpeliai:
`organic_clicks_7d`, `organic_clicks_prev_7d`, `views_7d`, `views_prev_7d`, `sales_30d`, `revenue_30d`, `impressions_28d`, `clicks_28d`, `views_30d`, `last_promoted`, `promoted_channel`.

Kol nėra realių `impressions_28d`/`clicks_28d` ar `views_30d`/`sales_30d`, sistema nerodo išgalvotų konkretaus produkto tobulinimo problemų.

### Rinkos radinių CSV

Stulpeliai `title,source,url,observed_at,note`; užpildomi tik faktiniais, nurodytu šaltiniu patikrinamais pastebėjimais. Tai ne automatinis konkurentų duomenų rinkimas.

## Patikra

- `python -m py_compile streamlit_app.py radar/*.py`
- `pytest -q`
- Programos pradinio vykdymo smoke testas naudoja `tests/fake_streamlit.py`, nes tai ne tikras naršyklinis Streamlit Cloud testas. Naują versiją verta įvertinti ir tikroje platformoje.
