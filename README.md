# 🎧 CIEM Startup – Pénzügyi Dashboard

Streamlit-alapú interaktív pénzügyi elemző alkalmazás egy budapesti, BME bázisú prémium Custom In-Ear Monitor (CIEM) gyártó startup pénzügyi modellezéséhez.

## Funkciók

A dashboard 8 tabot tartalmaz:

1. **📋 Áttekintés** – Vezetői összefoglaló, havi P&L, bevételi mix, kumulált CF
2. **💎 Unit Economics** – Termékszintű margin-analízis, vízesés-diagram, LTV/CAC
3. **⚖️ Break-even** – Fedezeti pont mindhárom termékszegmensre
4. **🚀 5Y Forecast** – Többéves növekedési modell inflációval
5. **💼 DCF Értékelés** – NPV, IRR, terminal value, vállalatérték
6. **🎯 Scenarios** – Pesszimista / realista / optimista forgatókönyvek
7. **🎲 Monte Carlo** – 500–10 000 szimulációval, eloszlásokkal és kockázati metrikákkal
8. **🌪️ Érzékenység** – Tornado-diagram, ±20% lökés minden inputra

## Telepítés és futtatás

```bash
# 1. Csomagok telepítése
pip install -r requirements.txt

# 2. Indítás
streamlit run app.py
```

Az alkalmazás a `http://localhost:8501` címen nyílik meg böngészőben.

## Fájlstruktúra

```
ciem_app/
├── app.py            # Streamlit UI – 8 tab, sliderek, KPI panel
├── model.py          # Pénzügyi modell – minden számítás (pandas)
├── charts.py         # Plotly vizualizációk (11 chart típus)
├── requirements.txt
└── README.md
```

## Modell-fókuszok

- **Adatforrás:** "Startup Költségkutatás és Pénzügyi Modell" – CIEM piaci jelentés
- **Pénznem:** USD-ben modellezünk, 390 HUF/EUR és 1.07 USD/EUR középárfolyamokon
- **KIVA-kezelés:** közvetve a fix OPEX-ben (bér × 10%); a profit-utáni KIVA-t a visszaforgatás miatt 0-nak vesszük
- **FCF egyszerűsítés:** FCF ≈ Nettó profit (mérnöki cégnél nincs jelentős utólagos CAPEX igény)

## Paraméter-vezérlés

A bal oldali sliderekkel valós időben módosítható:

- **Eladási volumen** termékszegmensenként (db/hó)
- **Árazás** (USD)
- **COGS** (USD/db)
- **CAC, OPEX, CAPEX**
- **Növekedési és inflációs ráták** a forecasthez
- **WACC és terminal growth** a DCF-hez
- **Visszatérési arány és élettartam** az LTV-hez

A változtatás bármelyik tabot átszámolja azonnal.

## Tipikus felhasználási minták

- **Befektetői pitch előkészítés:** állítsd a Realista scenariot, exportáld a chartokat
- **Érzékenység vizsgálat:** Tornado tab → mely paraméter mozgatja legjobban az NPV-t?
- **Kockázat-mérés:** Monte Carlo → mekkora az esélye a veszteséges kimenetnek?
- **Mit kell elérni hogy 0-szaldó legyek?:** Break-even tab + sliderek manuális próbálgatása
