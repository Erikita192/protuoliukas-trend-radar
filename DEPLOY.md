# V5 – paleidimas ir privati internetinė versija

## Paprasčiausias paleidimas Windows kompiuteryje
1. Įdiek Python 3.11+.
2. Išarchyvuok šį aplanką.
3. Dukart spustelėk `run_windows.bat`.
4. Pirmą kartą bus įdiegtos priklausomybės, tada naršyklėje atsidarys Trend Radar.

## Streamlit Community Cloud
V5 paruoštas talpinimui:
- pagrindinis failas: `streamlit_app.py`
- priklausomybės: `requirements.txt`
- konfigūracija: `.streamlit/config.toml`

Talpinimo eiga:
1. Sukurk privatų GitHub repository.
2. Įkelk VISUS šio aplanko failus.
3. Streamlit Community Cloud pasirink `Create app`.
4. Pasirink repository ir `streamlit_app.py`.
5. Jei nori, programėlės Sharing nustatymuose palik tik konkrečius vartotojus.

Pastaba: Streamlit Community Cloud privatumo ir planų ribos gali keistis, todėl prieš diegiant patikrink dabartines Streamlit sąlygas.

## Ką V5 išsprendžia
- V4 funkcijos viename deploy-ready pakete.
- Paleidimas Windows vienu BAT failu.
- Paruošta GitHub + Streamlit Cloud struktūra.
- Nereikia keisti Python kodo, kad programėlę būtų galima deployinti.

## Ko V5 dar nedaro automatiškai
Search Console OAuth prijungimas reikalauja tavo Google Cloud projekto ir autorizacijos.
Jo negalima saugiai „įkepti“ į ZIP be tavo Google paskyros autorizacijos.
Iki tol Search Console CSV/XLSX importas lieka saugus ir veikiantis būdas.
