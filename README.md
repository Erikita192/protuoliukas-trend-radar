# Protuoliuko galimybių centras — V23

**V23 = V22 + „Idėjos transformatorius“.** Išsaugotas visas V22 turinys: 68 temos, 200 išsamių idėjų, 132 progos, originalus „Protuoliuko“ logotipas, esamų produktų katalogo tikrinimas, galimybių ekranas ir CSV importai.

## Kaip įkelti V23 į jau veikiančią Streamlit platformą

1. Atsisiųsk `protuoliukas_galimybiu_centras_v23.zip`, išarchyvuok jį.
2. **Visus išarchyvuotus failus ir aplankus** įkelk į **esamos** GitHub repozitorijos **pagrindinį katalogą**, kur dabar yra `streamlit_app.py`. Nekelk ZIP kaip failo, nedėk visko į papildomą poaplankį.
3. Leisk pakeisti sutampančius V22 failus. **Jeigu repo jau turi savo `data/catalog.json`, `data/signals.csv` ar `data/market_signals.csv`, jų neištrink**. V23 ZIP jų nėra.
4. Streamlit Cloud turėtų automatiškai įdiegti naujus paketus iš `requirements.txt` ir persikrauti. Paleidimo failas lieka `streamlit_app.py`.
5. Viršuje atsidaryk **„✨ IDĖJOS TRANSFORMATORIUS“**. Nauja skiltis yra tarp „Galimybės“ ir „Idėjų biblioteka“.

## „Idėjos transformatorius“: ką gali

- Įkelti **PNG / JPG / WEBP**, **PDF**, **PPTX**, **TXT** arba pateikti viešą HTML puslapio nuorodą.
- PDF skaitomas tekstas iš pirmųjų 12 puslapių; atskirai galima pasirinkti **vieną PDF puslapį, kurį rodyti kaip paveikslėlį**. PPTX tekstas iš pirmųjų 30 skaidrių. Viešos nuorodos nuskaitymas vyksta **tik paspaudus atskirą mygtuką** (neprisijungia prie uždarų puslapių).
- Įvesti trumpą turinio aprašymą, ugdymo tikslą, amžių, formato pageidavimą.
- **Nemokamai, be DI API**: pagal aprašytą/iš failo ištrauktą tekstą pateikiamos **6 redakciškai skirtingos užduočių mechanikos**. Tai taisyklėmis pagrįsti kūrybiniai pavyzdžiai, **ne paveikslėlio atpažinimas ir ne individuali generatyvinė DI analizė**. Jei šaltinis – tik paveikslėlis, būtina įrašyti bent trumpą aprašymą.
- Nukopijuoti ar atsisiųsti išsamų **ChatGPT promptą**. Ten galima pridėti tą patį pavyzdžio failą; ši programa jo savaime į ChatGPT pokalbį neperkelia.
- **Pasirenkamai** aktyvuoti DI analizę per OpenAI API. Tada DI mato pateiktą vaizdą (įkelta nuotrauka arba pasirinktas PDF puslapis) ir tekstą; siūlo 6–8 kitokias priemones. PPTX failų įdėti piešiniai automatiškai į vaizdus neatvaizduojami: jei vizualas svarbus, įkelk skaidrės ekrano kopiją kaip PNG/JPG.
- Atskirais mygtukais išsaugoti patikusias alternatyvas į **„Idėjų biblioteka“ → „Mano išsaugotos idėjos iš Transformatoriaus“**, atsisiųsti/atkurti JSON atsarginę kopiją.
- Pateiktas kūrinys nėra mechaniškai nukopijuojamas. Sistema skatina kurti kitokius mokymo veiksmus, neperkelti trečiųjų šalių tekstų, autorinių iliustracijų ar originalios kompozicijos. **Tai nėra garantija, kad niekada nebus autorių teisių konflikto, ir ne teisinė konsultacija.**

## Mokama DI analizė (visiškai neprivaloma)

Tam reikia atskiro **OpenAI API rakto**, kuris **nėra tas pats, kas ChatGPT Plus**. API naudojimas paprastai apmokestinamas atskirai; jei rakto nėra, programa veikia be DI analizės.

Saugus būdas Streamlit Community Cloud: programos nustatymuose atidaryk **Settings → Secrets** ir įrašyk:

```toml
OPENAI_API_KEY = "tavo_api_raktas"
```

**Niekada nekelk rakto į GitHub ar ZIP.** Naudojamas modelis pagal nutylėjimą `gpt-4.1-mini`; jei tavo paskyrai jo nėra, per aplinkos kintamąjį `PROTUOLIUKAS_OPENAI_MODEL` galima pasirinkti prieinamą vaizdus suprantantį modelį. DI analizė siunčia pridėtą tekstą ir pasirinktą vaizdą API paslaugai **tik paspaudus** „Analizuoti su DI“.

## Svarbu dėl išsaugojimo

Išsaugoti variantai rašomi į `data/transformer_ideas.json` (arba `PROTUOLIUKAS_DATA_DIR` katalogą), **bet Streamlit Cloud vietinis diskas nėra patikima ilgalaikė saugykla**. Idėjų bibliotekoje turi **„Atsisiųsti VISAS savo idėjas (JSON)“** ir **„Atkurti išsaugotas idėjas“**. Atsisiųsk kopiją po kiekvieno svarbaus kūrimo seanso. V23 nekeičia esamo `data/ideas.json` – todėl 200 ankstesnių idėjų lieka net jei debesies diskas išvalomas.

## Kitos V22 funkcijos

- „🎯 Galimybės“ – ką kurti, reklamuoti ir patobulinti, su aiškiai įvardytu duomenų pagrindu; jokių išgalvotų pardavimo skaičių.
- „💡 Idėjų biblioteka“ – 68 temos ir 200 idėjų; paieška, filtrai, sezonai.
- „📆 Progų kalendorius“ – 132 progos, datos ir publikavimo orientyrai, mokyklos ritmas.
- „🛍️ Mano produktai“ – etapinis nuskaitymas, fono patikra, rankinio nuskaitymo mygtukas.
- „🔎 Rinkos radiniai“ ir „⚙️ Duomenys“ – CSV importai ir realių šaltinių žymėjimas.

Katalogo skenavimas vis dar priklauso nuo išorinės parduotuvės struktūros ir Streamlit Cloud resursų. Be realių importuotų pardavimo ir paieškos rodiklių niekur nėra tariamos „išmatuotos paklausos“.

## Vietinis paleidimas ir testai

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
pytest -q
```

Patikrinimai neapima tikro Streamlit Cloud naršyklinio bandymo ar realaus API rakto – tai reikia patikrinti po įkėlimo.
