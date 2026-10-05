# Protuoliuko paklausos radaras · V20

V20 yra stabilizavimo ir logikos versija.

## Kas sutvarkyta
- Visi pasikartojantys Streamlit filtrų valdikliai turi unikalius `key`, todėl pašalinta `StreamlitDuplicateElementId` klaidos priežastis.
- Įdėtas tikras vartotojos pateiktas „Protuoliuko“ logotipas (`assets/logo.png`).
- Esamų produktų katalogas kiekvienos naujos sesijos pradžioje automatiškai tikrinamas fone. Nuskaitymas vyksta trumpesniais etapais ir, jei nespėja, automatiškai tęsiamas nuo išsaugotos vietos, o ne pradedamas iš naujo.
- Kol katalogas pildomas, visada paliekama paskutinė gera kopija; dalinis nuskaitymas neišjungia anksčiau rastų produktų.
- „Mokyklos kalendorius“ rodo ne vien atostogas: mokslo metų pradžią, paskutines mokymosi dienas prieš pertraukas, atostogas, apytikslę pusmečio ir mokslo metų pabaigą.
- Progų bazė papildyta vaikams ir pedagogams aktualiomis datomis iš pateiktų kalendorių. Neoficialios / kintamos datos pažymėtos kaip apytikslės.
- Mokomųjų temų kortelėse atskirtas tikėtinas pagrindinis pikas nuo rekomenduojamo publikavimo lango; nebenaudojamas klaidinantis ilgas „aktualu iki...“ kaip vienas pikas.
- Produkto numeriui pirmenybė teikiama pavadinime esančiam Protuoliuko kodui, pvz. `P213`, o ne atsitiktiniam puslapio vidiniam ID.
- Kūrėjo JSON produkto diagnostika nebėra rodoma kasdienėje vartotojo sąsajoje.

## Paleidimas
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Patikra
`pytest -q` – 13 testų.
