# Protuoliuko paklausos radaras V11

Ši versija sukurta kaip savarankiškas, nemokamas Streamlit projektas be mokamų API.

## Kas pakeista
- sutvarkytas šviesaus režimo kontrastas telefone: tekstas priverstinai tamsus ant balto fono;
- mobiliesiems pritaikytos kortelės, KPI ir slenkama 30 dienų juosta;
- DABAR / NETRUKUS / ARTĖJA / PLANAI;
- temos formuluojamos konkrečiai, ne abstrakčiomis pedagoginėmis kryptimis;
- prie kiekvienos temos pateikiami bent 4 konkretūs kuriamų priemonių pavyzdžiai;
- fiksuotos piko datos – jos neslenka kartu su šiandienos data;
- paieška ir filtravimas pagal sritį;
- greitas TOP 5 kūrimo planas;
- nereikia OPENAI_API_KEY ar kitos mokamos paslaugos.

## Paleidimas
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

GitHub / Streamlit Cloud atveju pakanka repo turėti `streamlit_app.py` ir `requirements.txt`.
