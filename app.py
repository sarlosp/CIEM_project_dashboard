"""
app.py – CIEM Startup Pénzügyi Dashboard
=========================================
Streamlit-alapú interaktív elemző felület.

Futtatás:
    streamlit run app.py

A bal oldali sliderekkel valós időben módosíthatók a paraméterek;
minden tab a `model.py`-ből húz adatot és `charts.py`-vel jelenít meg.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np

import model as M
import charts as C


# ============================================================
# OLDAL-KONFIG
# ============================================================
st.set_page_config(
    page_title="CIEM Startup (MeinOhr) – Pénzügyi Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Egyedi CSS – kicsit letisztultabb megjelenés
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; max-width: 1400px; }
    h1 { color: #1F4E79; margin-bottom: 0.2rem; }
    h2 { color: #1F4E79; border-bottom: 2px solid #EAF1F8; padding-bottom: 0.3rem; }
    h3 { color: #1F4E79; }
    [data-testid="stMetricValue"] { font-size: 1.6rem; }
    [data-testid="stMetricLabel"] { font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1rem; font-weight: 600;
    }
    .source-note {
        font-size: 0.8rem; color: #888; font-style: italic;
        border-left: 3px solid #EAF1F8; padding-left: 8px; margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# CÍM ÉS BEVEZETŐ
# ============================================================
st.title("CIEM Startup (MeinOhr) – Pénzügyi Dashboard")
st.markdown(
    "<p style='color:#555; margin-top:-0.5rem; margin-bottom:1rem;'>"
    "Prémium Custom In-Ear Monitor gyártó startup interaktív elemző felülete · "
    "Budapest, BME bázisú, 6 fős mérnökcsapat"
    "</p>", unsafe_allow_html=True
)


# ============================================================
# OLDALSÁV – PARAMÉTER VEZÉRLŐK
# ============================================================
def make_sidebar() -> M.ModelParams:
    """Az összes paramétert ide rakjuk – a függvény visszaad egy ModelParams-t."""
    st.sidebar.header("Paraméterek")
    st.sidebar.markdown("Állítsd a sliderekkel valós időben. Az értékek a kutatási dokumentumból jönnek.")

    with st.sidebar.expander("Eladási volumen (db/hó)", expanded=True):
        units_entry = st.slider("Belépő modell", 0, 60, 20, step=1)
        units_mid   = st.slider("Közép modell",  0, 40, 10, step=1)
        units_top   = st.slider("Csúcs modell",  0, 30, 5,  step=1)

    with st.sidebar.expander("Árazás (USD)"):
        price_entry = st.slider("Belépő ár",  500,  1500,  1000, step=50)
        price_mid   = st.slider("Közép ár",  1000,  2200,  1550, step=50)
        price_top   = st.slider("Csúcs ár",  1500,  3500,  2750, step=50)

    with st.sidebar.expander("COGS (USD/db, középérték)"):
        cogs_entry = st.slider("Belépő COGS", 100,  250,   142, step=2)
        cogs_mid   = st.slider("Közép COGS",  200,  400,   275, step=5)
        cogs_top   = st.slider("Csúcs COGS",  300,  600,   442, step=5)

    with st.sidebar.expander("Költségek és CAPEX"):
        cac_usd        = st.slider("CAC (USD/ügyfél)", 50, 350, 200, step=10,
                                   help="A kutatás 150–250 USD közötti sávot javasol; ipari átlag 68–84 USD")
        fixed_opex_usd = st.slider("Havi fix OPEX (USD)", 8_000, 25_000, 15_000, step=500,
                                   help="Bér + iroda + rezsi + szoftver, KIVA-val")
        capex_usd      = st.slider("Induló CAPEX (USD)", 15_000, 50_000, 28_500, step=500,
                                   help="3D nyomtatók, szkenner, szoftver licenc – $25–32k a kutatási sáv")

    with st.sidebar.expander("Növekedés és infláció (5 éves modell)"):
        growth_rate     = st.slider("Éves volumen-növekedés", 0.0, 1.0, 0.30, step=0.05,
                                    format="%.0f%%")
        price_inflation = st.slider("Éves árnövelés",     0.0, 0.10, 0.03, step=0.01,
                                    format="%.0f%%")
        cogs_inflation  = st.slider("COGS infláció",      0.0, 0.10, 0.04, step=0.01,
                                    format="%.0f%%")
        opex_inflation  = st.slider("OPEX infláció",      0.0, 0.15, 0.05, step=0.01,
                                    format="%.0f%%")
        forecast_years  = st.slider("Forecast hossz (év)", 3, 7, 5)

    with st.sidebar.expander("DCF paraméterek"):
        discount_rate    = st.slider("Diszkontráta (WACC)", 0.10, 0.40, 0.20, step=0.01,
                                     format="%.0f%%",
                                     help="Korai stádiumú startup: 18–25%; érettebb: 12–18%")
        terminal_growth  = st.slider("Terminal growth",    0.00, 0.05, 0.03, step=0.005,
                                     format="%.1f%%")

    with st.sidebar.expander("LTV / Visszatérő ügyfél"):
        repurchase_rate      = st.slider("Visszatérési arány", 0.0, 0.6, 0.25, step=0.05,
                                          format="%.0f%%")
        avg_repurchase_value = st.slider("Átlagos kiegészítő-vásárlás",
                                          100, 1000, 400, step=50,
                                          help="Kábel-upgrade, retune, fülminta-újraöntés")
        customer_lifetime_yr = st.slider("Ügyfél élettartam (év)", 1, 10, 5)

    return M.ModelParams(
        units_entry=units_entry, units_mid=units_mid, units_top=units_top,
        price_entry=price_entry, price_mid=price_mid, price_top=price_top,
        cogs_entry=cogs_entry, cogs_mid=cogs_mid, cogs_top=cogs_top,
        cac_usd=cac_usd, fixed_opex_usd=fixed_opex_usd, capex_usd=capex_usd,
        growth_rate=growth_rate, price_inflation=price_inflation,
        cogs_inflation=cogs_inflation, opex_inflation=opex_inflation,
        forecast_years=forecast_years,
        discount_rate=discount_rate, terminal_growth=terminal_growth,
        repurchase_rate=repurchase_rate,
        avg_repurchase_value=avg_repurchase_value,
        customer_lifetime_yr=customer_lifetime_yr,
    )


params = make_sidebar()


# ============================================================
# FELSŐ KPI SOR – minden tabban látható
# ============================================================
pnl = M.monthly_pnl(params)
ltv = M.ltv_cac(params)
dcf = M.dcf_valuation(params)
payback_m = M.payback_months(params)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Havi bevétel", f"${pnl['revenue']:,.0f}")
col2.metric("Operating margin", f"{pnl['operating_margin_pct']:.1f}%",
            delta=f"${pnl['operating_profit']:,.0f}/hó")
col3.metric("Payback period",
            f"{payback_m:.1f} hó" if np.isfinite(payback_m) else "∞")
col4.metric("NPV (DCF)",
            f"${dcf['npv']/1e6:.2f}M" if abs(dcf['npv']) >= 1e6 else f"${dcf['npv']/1000:.0f}k")
col5.metric("LTV/CAC", f"{ltv['ratio']:.1f}×",
            delta="Egészséges (>3)" if ltv['ratio'] > 3 else "Vizsgálandó")

st.markdown("---")


# ============================================================
# TAB-OK – 6 elemzési modul
# ============================================================
tab_overview, tab_unit, tab_breakeven, tab_forecast, tab_dcf, tab_scenarios, tab_mc, tab_tornado = st.tabs([
    "Áttekintés",
    "Unit Economics",
    "Break-even",
    "5Y Forecast",
    "DCF Értékelés",
    "Scenarios",
    "Monte Carlo",
    "Érzékenység",
])


# ============================================================
# TAB 1 – ÁTTEKINTÉS
# ============================================================
with tab_overview:
    st.header("Összefoglaló")

    c1, c2 = st.columns([0.55, 0.45])
    with c1:
        st.subheader("Havi P&L bontás")
        pnl_df = pd.DataFrame({
            "Tétel": ["Bevétel", "COGS", "Bruttó profit", "CAC", "Fix OPEX", "Operating profit"],
            "USD/hó": [pnl["revenue"], -pnl["cogs"], pnl["gross_profit"],
                      -pnl["cac_total"], -pnl["fixed_opex"], pnl["operating_profit"]],
            "USD/év": [pnl["revenue"]*12, -pnl["cogs"]*12, pnl["gross_profit"]*12,
                      -pnl["cac_total"]*12, -pnl["fixed_opex"]*12, pnl["operating_profit"]*12],
        })

        def _color_value(v):
            if isinstance(v, (int, float, np.number)):
                color = "#2E7D32" if v > 0 else ("#C0504D" if v < 0 else "#000")
                return f"color: {color}; font-weight: 600"
            return ""

        st.dataframe(
            pnl_df.style.format({"USD/hó": "${:,.0f}", "USD/év": "${:,.0f}"})
                       .map(_color_value, subset=["USD/hó", "USD/év"]),
            hide_index=True, use_container_width=True,
        )

        st.markdown(f"""
        **Kulcsmetrikák:**
        - Bruttó margin: **{pnl["gross_margin_pct"]:.1f}%**
        - Operating margin: **{pnl["operating_margin_pct"]:.1f}%**
        - Eladott darabszám: **{pnl["units_total"]} db/hó** ({pnl["units_total"]*12} db/év)
        - LTV/CAC arány: **{ltv["ratio"]:.2f}×** (egészséges: >3, kiváló: >5)
        """)

    with c2:
        st.plotly_chart(C.chart_revenue_mix(params), use_container_width=True)

    st.subheader("Cash-flow az 1. évben")
    cf_df = M.yearly_cashflow(params)
    st.plotly_chart(C.chart_cumulative_cf(cf_df, params.capex_usd, payback_m),
                    use_container_width=True)

    if pnl["operating_profit"] > 0:
        st.success(
            f" A forgatókönyv profitábilis. "
            f"Az induló {params.capex_usd:,.0f} CAPEX {payback_m:.1f} hónap alatt megtérül és "
            f"az 1. év végére kumulált szabad cash: {cf_df['cumulative_cf'].iloc[-1]:,.0f}."
        )
    else:
        st.error(
            f" A jelenlegi mix veszteséges! "
            f"Havi operating profit: ${pnl['operating_profit']:,.0f}. "
            "Növeld a volumeneket vagy csökkentsd a fix költséget."
        )

    st.markdown('<p class="source-note">Forrás: a kutatási dokumentum középérték-paramétereiből indul az alapszcenárió. '
                'A modellben minden szám módosítható a bal oldali sliderekkel.</p>', unsafe_allow_html=True)


# ============================================================
# TAB 2 – UNIT ECONOMICS
# ============================================================
with tab_unit:
    st.header("Unit Economics – termékszintű gazdaságtan")
    st.markdown(
        "A bevételből hogyan marad contribution margin a COGS és a CAC levonása után, "
        "termékszegmensenként. **Kulcs-megfigyelés:** a COGS szinte lineárisan, az ár "
        "viszont szuperlineárisan nő a driver-számmal – ez a flagship modellek margin-előnyének forrása."
    )

    ue = M.unit_economics(params)
    st.plotly_chart(C.chart_unit_economics(ue, params.cac_usd), use_container_width=True)

    c1, c2 = st.columns([0.55, 0.45])

    with c1:
        st.subheader("Részletes táblázat")
        display_df = ue.copy()
        display_df.columns = ["Ár (USD)", "COGS (USD)", "Bruttó margin ($)",
                              "Bruttó margin (%)", "Contribution ($)", "Contribution (%)"]
        st.dataframe(
            display_df.style.format({
                "Ár (USD)": "${:,.0f}", "COGS (USD)": "${:,.0f}",
                "Bruttó margin ($)": "${:,.0f}", "Bruttó margin (%)": "{:.1f}%",
                "Contribution ($)": "${:,.0f}", "Contribution (%)": "{:.1f}%",
            }),
            use_container_width=True,
        )

    with c2:
        st.subheader("LTV / CAC analízis")
        st.plotly_chart(C.chart_ltv_cac(ltv), use_container_width=True)

    with st.expander("Hogyan számoljuk az LTV-t?"):
        st.markdown(f"""
        - **Súlyozott bruttó margin** (a mix alapján): **${ltv['avg_gross_margin']:,.0f}** / új ügyfél
        - **Visszatérő bevétel margin**: {params.repurchase_rate*100:.0f}% × ${params.avg_repurchase_value} × 60% (margin) × {params.customer_lifetime_yr} év = **${ltv['repurchase_ltv']:,.0f}**
        - **Total LTV** = bruttó margin + visszatérő = **${ltv['ltv']:,.0f}**
        - **LTV / CAC = ${ltv['ltv']:,.0f} / ${params.cac_usd:.0f} = {ltv['ratio']:.2f}×**
        - **Akvizíciós payback**: a CAC megtérül **{ltv['payback_purchase']:.2f} darab** eladás után (azaz az első értékesítés is gyakran fedezi)

        Iparági benchmark (D2C/SaaS): 1 alatt veszteséges, 1-3 vékony, **3-5 egészséges**, 5+ kiváló.
        """)


# ============================================================
# TAB 3 – BREAK-EVEN
# ============================================================
with tab_breakeven:
    st.header("Break-even elemzés")
    st.markdown(
        "Mennyit kell havonta eladni ahhoz, hogy a fix költségek megtérüljenek? "
        "Mindhárom szegmensre külön-külön kiszámolva."
    )

    be = M.break_even(params)
    st.plotly_chart(C.chart_break_even(params, max_units=50), use_container_width=True)

    st.subheader("Break-even darabszámok")
    st.dataframe(
        be.style.format({
            "Ár (USD)": "${:,.0f}",
            "Contribution / db": "${:,.0f}",
            "BE darab / hó": "{:.1f}",
            "BE darab / év": "{:.0f}",
            "BE bevétel / hó": "${:,.0f}",
        }),
        hide_index=True, use_container_width=True,
    )

    st.markdown(f"""
    **Képlet:**
    `BE darab = Fix OPEX / Contribution Margin per egység`

    Aktuális fix OPEX: **${params.fixed_opex_usd:,.0f}/hó**
    """)

    if not np.isnan(be["BE darab / hó"].iloc[2]):
        st.info(
            f"A csúcsmodell (~{be['BE darab / hó'].iloc[2]:.0f} db/hó) "
            f"**{be['BE darab / hó'].iloc[0]/be['BE darab / hó'].iloc[2]:.1f}×** "
            f"gyorsabban viszi profitba a céget, mint a belépő modell "
            f"(~{be['BE darab / hó'].iloc[0]:.0f} db/hó)."
        )


# ============================================================
# TAB 4 – 5Y FORECAST
# ============================================================
with tab_forecast:
    st.header("5 éves előrejelzés")
    st.markdown(
        "Évről évre projekciós modell. A volumen-növekedés mellett "
        "figyelembe veszi az ár-, COGS- és OPEX-inflációt is."
    )

    fc = M.long_term_forecast(params)
    st.plotly_chart(C.chart_forecast(fc), use_container_width=True)

    st.subheader("Részletes éves bontás")
    display_fc = fc.copy()
    display_fc["Operating margin"] = display_fc["Operating margin"] * 100
    st.dataframe(
        display_fc.style.format({
            "Volumen (db/év)": "{:,.0f}",
            "Bevétel": "${:,.0f}", "COGS": "${:,.0f}", "CAC": "${:,.0f}",
            "OPEX": "${:,.0f}", "EBIT": "${:,.0f}", "Nettó profit": "${:,.0f}",
            "Operating margin": "{:.1f}%",
        }),
        hide_index=True, use_container_width=True,
    )

    cagr = (fc["Bevétel"].iloc[-1] / fc["Bevétel"].iloc[0]) ** (1/(len(fc)-1)) - 1
    st.markdown(f"""
    **Növekedési mutatók ({params.forecast_years} év alatt):**
    - Bevétel CAGR: **{cagr*100:.1f}%/év**
    - Y1 → Y{params.forecast_years} bevételnövekedés: **${fc['Bevétel'].iloc[0]:,.0f} → ${fc['Bevétel'].iloc[-1]:,.0f}**
    - Y{params.forecast_years} operating margin: **{fc['Operating margin'].iloc[-1]*100:.1f}%**
    - 5y kumulált EBIT: **${fc['EBIT'].sum():,.0f}**
    """)


# ============================================================
# TAB 5 – DCF
# ============================================================
with tab_dcf:
    st.header("DCF Értékelés – Net Present Value & IRR")
    st.markdown(
        "A diszkontált cash-flow módszer a jövőbeli pénzáramokat a befektető elvárt "
        "hozamával (WACC) hozza jelenértékre. A vállalatérték = ezek összege + terminal value."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NPV", f"${dcf['npv']:,.0f}")
    c2.metric("IRR", f"{dcf['irr']*100:.1f}%" if np.isfinite(dcf['irr']) else "N/A")
    c3.metric("Vállalatérték (EV)", f"${dcf['enterprise_value']:,.0f}")
    c4.metric("PV(Terminal)",
              f"${dcf['pv_terminal_value']:,.0f}" if np.isfinite(dcf.get('pv_terminal_value', np.nan))
              else "N/A")

    st.plotly_chart(C.chart_dcf_waterfall(dcf, params.capex_usd), use_container_width=True)

    with st.expander("DCF részletek és feltételezések"):
        years = list(range(1, len(dcf["fcfs"]) + 1))
        dcf_df = pd.DataFrame({
            "Év":               [f"Y{y}" for y in years],
            "FCF":              dcf["fcfs"],
            "Diszkont faktor":  dcf["discount_factors"],
            "PV(FCF)":          dcf["pv_fcfs"],
        })
        st.dataframe(
            dcf_df.style.format({
                "FCF": "${:,.0f}", "Diszkont faktor": "{:.3f}", "PV(FCF)": "${:,.0f}",
            }),
            hide_index=True, use_container_width=True,
        )

        st.markdown(f"""
        **Modellfeltevések:**
        - WACC (diszkontráta): **{params.discount_rate*100:.1f}%**
        - Terminal growth (Gordon-féle): **{params.terminal_growth*100:.1f}%**
        - Forecast horizont: **{params.forecast_years} év**
        - Terminal value (Y{params.forecast_years} után): **${dcf['terminal_value']:,.0f}** (jelenértékre: ${dcf['pv_terminal_value']:,.0f})
        - FCF ≈ Nettó profit (egyszerűsítve, mivel a mérnöki cégnél nincs jelentős utólagos CAPEX)
        - KIVA közvetve a fix OPEX-ben (bér × 10%); a profit-utáni KIVA-t a visszaforgatás miatt 0-nak vesszük
        """)


# ============================================================
# TAB 6 – SCENARIO PLANNING
# ============================================================
with tab_scenarios:
    st.header("Scenario-elemzés")
    st.markdown(
        "Három előre definiált forgatókönyv – mindegyik az aktuális paraméterek alapján "
        "fut le, de eltérő piaci feltételekkel. A táblázat alatt láthatod, milyen "
        "módosításokat kapnak az inputok scenarionként."
    )

    sc = M.run_scenarios(params)
    st.plotly_chart(C.chart_scenarios(sc), use_container_width=True)

    st.subheader("Részletes scenario-tábla")
    display_sc = sc.copy()
    display_sc["IRR"] = display_sc["IRR"] * 100
    display_sc["Y5 op. margin"] = display_sc["Y5 op. margin"] * 100
    st.dataframe(
        display_sc.style.format({
            "Y1 bevétel":             "${:,.0f}",
            "Y5 bevétel":             "${:,.0f}",
            "Y5 EBIT":                "${:,.0f}",
            "5y kumulált EBIT":       "${:,.0f}",
            "NPV":                    "${:,.0f}",
            "IRR":                    "{:.1f}%",
            "Vállalatérték (EV)":     "${:,.0f}",
            "Y5 op. margin":          "{:.1f}%",
        }),
        hide_index=True, use_container_width=True,
    )

    with st.expander("Mit módosítanak a scenariók?"):
        for name, mods in M.SCENARIOS.items():
            st.markdown(f"""
            **{name}**
            - Növekedési ráta: **{mods['growth_rate']*100:.0f}%/év**
            - Volumen multiplikátor: **{mods['vol_mult']:.2f}×**
            - CAC multiplikátor: **{mods['cac_mult']:.2f}×**
            - COGS multiplikátor: **{mods['cogs_mult']:.2f}×**
            - OPEX multiplikátor: **{mods['opex_mult']:.2f}×**
            - Diszkontráta: **{mods['discount_rate']*100:.0f}%**
            """)


# ============================================================
# TAB 7 – MONTE CARLO
# ============================================================
with tab_mc:
    st.header("Monte Carlo szimuláció")
    st.markdown(
        "A bemeneteket ezúttal nem fix számoknak, hanem eloszlásoknak tekintjük – "
        "úgy ahogy a valóság viselkedik. Sok ezer véletlen futtatásból megbecsüljük "
        "a kimenetek (NPV, IRR) **eloszlását** és a kockázatot."
    )

    c1, c2 = st.columns([0.6, 0.4])
    with c1:
        n_sims = st.select_slider("Szimulációk száma",
                                  options=[500, 1000, 2500, 5000, 10000],
                                  value=2500)
    with c2:
        run_btn = st.button("Szimuláció futtatása", type="primary", use_container_width=True)

    @st.cache_data(show_spinner="Szimuláció fut...")
    def _run_mc(params_dict, n):
        p = M.ModelParams(**params_dict)
        return M.monte_carlo(p, n_sims=n)

    # Csak akkor fut új MC, ha gomb meg van nyomva, vagy ha még nincs cache
    if run_btn or "mc_done" not in st.session_state:
        st.session_state["mc_done"] = True
        st.session_state["mc_data"] = _run_mc(params.as_dict(), n_sims)

    mc = st.session_state["mc_data"]

    # Statisztikák
    npv_p5, npv_p50, npv_p95 = np.percentile(mc["NPV"], [5, 50, 95])
    pct_pos = (mc["NPV"] > 0).mean() * 100
    irr_med = np.median(mc["IRR"][np.isfinite(mc["IRR"])])

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Median NPV (P50)", f"${npv_p50:,.0f}")
    s2.metric("P5 NPV (rossz eset)", f"${npv_p5:,.0f}")
    s3.metric("P95 NPV (jó eset)", f"${npv_p95:,.0f}")
    s4.metric("Pozitív kimenet", f"{pct_pos:.1f}%")

    target = st.radio("Mit nézzünk?", ["NPV", "IRR", "Y5_EBIT", "Y1_op_profit"],
                      horizontal=True, index=0)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(C.chart_mc_distribution(mc, target), use_container_width=True)
    with c2:
        st.plotly_chart(C.chart_mc_input_sensitivity(mc), use_container_width=True)

    with st.expander("Statisztikai összefoglaló"):
        stats_df = mc[["NPV", "IRR", "Y5_EBIT", "Y1_op_profit"]].describe()
        st.dataframe(stats_df.style.format({
            "NPV": "${:,.0f}", "IRR": "{:.2%}",
            "Y5_EBIT": "${:,.0f}", "Y1_op_profit": "${:,.0f}",
        }), use_container_width=True)

    with st.expander("Eloszlások, amiket használok"):
        st.markdown("""
        - **Volumen multiplikátor**: Normal(1.0, 0.30), 0.2 és 2.0 közé szűrve
        - **CAC**: Triangular(150, 200, 250) – a kutatási sáv
        - **Csúcs ár**: Triangular(2000, 2750, 3500)
        - **Belépő ár**: Triangular(900, 1000, 1200)
        - **COGS multiplikátor**: Normal(1.0, 0.10)
        - **Növekedési ráta**: Triangular(0.10, 0.30, 0.55)
        - **Diszkontráta**: Uniform(0.15, 0.30)
        """)


# ============================================================
# TAB 8 – TORNADO ÉRZÉKENYSÉG
# ============================================================
with tab_tornado:
    st.header("Érzékenységi elemzés – Tornado-diagram")
    st.markdown(
        "**Melyik input mozgatja legjobban az eredményt?** Egyenként ±20%-os lökést "
        "adunk minden paraméternek, és mérjük a hatást a választott célértékre. "
        "A leghosszabb csíkok a legkritikusabb áttételű paraméterek."
    )

    target = st.radio("Célérték:",
                      ["NPV", "IRR", "Y5 EBIT", "Y1 op. profit"],
                      horizontal=True, index=0)
    target_key = {"NPV": "npv", "IRR": "irr",
                  "Y5 EBIT": "y5_ebit", "Y1 op. profit": "y1_op_profit"}[target]

    tornado_df, base_value = M.sensitivity_tornado(params, target=target_key)
    st.plotly_chart(C.chart_tornado(tornado_df, base_value, target_label=target),
                    use_container_width=True)

    with st.expander("Tornado részletes táblázat"):
        st.dataframe(
            tornado_df.style.format({"Hatás": "${:+,.0f}", "Új érték": "${:,.0f}"}),
            hide_index=True, use_container_width=True,
        )


# ============================================================
# LÁBLÉC
# ============================================================
st.markdown("---")
st.markdown(
    '<div class="source-note">'
    '<b>Adatforrás:</b> "Startup Költségkutatás és Pénzügyi Modell" – CIEM piaci jelentés. '
    'Számítások 390 HUF/EUR, 1.07 USD/EUR középárfolyamokkal. '
    'A modell tudatosan egyszerűsít: FCF ≈ Nettó profit, KIVA közvetve a fix OPEX-ben. '
    'Részletes értékelési modellhez (taxshield, működő tőke, befektetett eszközök stb.) bővítendő.'
    '</div>',
    unsafe_allow_html=True,
)
