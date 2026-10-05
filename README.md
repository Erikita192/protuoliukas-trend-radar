# Protuoliuko paklausos radaras V17

V17 tęsia V16 architektūrą ir pataiso pagrindinę UX problemą: tema nebegali likti abstrakti. Kiekvienoje naujos idėjos kortelėje **pirmas konkretus priemonės pavyzdys matomas iškart**, o visos idėjos išskleidžiamos žemiau.

## Kas nauja V17
- 68 naujų priemonių temos ir 200 konkrečių priemonių idėjų.
- „Dalyba“ išplėsta konkrečiomis ribomis: lygaus padalijimo užduotys iki 20, grupavimas / daugybos lentelės faktai iki 100, veiksmo parinkimas situacijai, dalyba skaičių tiesėje.
- Išplėstas vaikams ir pedagogams aktualių progų kalendorius; fiksuotos ir kintamos datos skaičiuojamos atskirai.
- Pasaulinė šypsenos diena skaičiuojama kaip **pirmasis spalio penktadienis**.
- Kintamos datos: Velykos, Užgavėnės, Adventas, Motinos diena, Tėvo diena, Šypsenos diena ir kt.
- Įtrauktos papildomos edukacinės progos: gyvūnijos, vaiko teisių, gimtosios kalbos, vandens, vaikų knygos, saugaus eismo, šeimos, bičių ir kt.
- Naujas skirtukas **DARBO EILĖ** su gamybos būsenomis.
- Naujas **14 D. FB PLANAS**, sudaromas tik iš realiai parduotuvėje nuskaitytų produktų; rodomas reklamos kampas ir redaguojamas juodraščio karkasas.
- Išliko: realiomis datomis paremti DABAR / NETRUKUS / ARTĖJA / 30 DIENŲ, gamybos įgyvendinamumas, esamų produktų crawleris, diagnostika, paskutinė gera katalogo kopija, CSV signalų vieta ateities GA4/GSC/pardavimų duomenims.

## Svarbios ribos
- Prioriteto balai yra planavimo heuristika, ne Google paklausos matavimas.
- Datos pažymėtos `approx`, kai jos yra preliminarios / kampanijinės ir vertos kasmetinio patikrinimo.
- Darbo eilė šiuo metu saugoma Streamlit sesijoje; tai nėra nuolatinė projektų duomenų bazė.
- 14 d. FB planas nieko automatiškai nepublikuoja.

## Paleidimas
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
