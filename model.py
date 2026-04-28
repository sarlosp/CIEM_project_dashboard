"""
model.py – CIEM Startup pénzügyi modell magja
=============================================
Tiszta számítási logika (NEM tartalmaz Streamlit-et). Minden függvény
pandas DataFrame-et vagy numpy arrayt ad vissza, így könnyen tesztelhető
és bárhonnan újra felhasználható (Jupyter, script, app).

A modulhoz tartozó alapadatok forrása:
    "Startup Költségkutatás és Pénzügyi Modell" (CIEM piaci jelentés)
    Számítások: 390 HUF/EUR, 1.07 USD/EUR középárfolyamokkal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import numpy_financial as npf
from dataclasses import dataclass, field, asdict


# ============================================================
# 1. ALAPADATOK (a kutatási dokumentumból)
# ============================================================

DEFAULT_PRODUCTS = pd.DataFrame({
    "tier":        ["Belépő",    "Közép",     "Csúcs"],
    "drivers":     ["2-4 BA",    "6-8 BA",    "12-18 BA"],
    "price_usd":   [1000,        1550,        2750],
    "cogs_low":    [122,         230,         367],
    "cogs_high":   [162,         320,         517],
    "labor_hours": [3.5,         4.5,         6.0],
}).set_index("tier")
DEFAULT_PRODUCTS["cogs_mid"] = (DEFAULT_PRODUCTS["cogs_low"] + DEFAULT_PRODUCTS["cogs_high"]) / 2

DEFAULT_OPEX_HUF = {
    "Iroda bérlet (80m² × 10 EUR/m²)":     312_000,   # 800 EUR × 390
    "Iroda rezsi (80m² × 7 EUR/m²)":       218_400,   # 560 EUR × 390
    "Könyvelés + bérszámfejtés":            71_000,
    "Cyfex szoftver (~$2750/év havi vetítve)": 83_500, # 214 EUR × 390
    "6 fő bruttó bér (6 × 725 000)":      4_350_000,
    "KIVA 10% (kiváltja SZOCHO+TAO)":       435_000,
}

DEFAULT_FX = {
    "huf_per_eur": 390.0,
    "usd_per_eur": 1.07,
}
DEFAULT_FX["huf_per_usd"] = DEFAULT_FX["huf_per_eur"] / DEFAULT_FX["usd_per_eur"]

DEFAULT_CAPEX_USD = 28_500   # középérték a $25-32k sávból
DEFAULT_CAC_USD = 200        # a $150-250 sáv középértéke


# ============================================================
# 2. PARAMÉTER OSZTÁLY – minden modell-bemenet egy helyen
# ============================================================

@dataclass
class ModelParams:
    """Egy futtatás összes inputja. A Streamlit oldalsávban fog feltöltődni."""
    # értékesítési mix (db/hó)
    units_entry: int = 20
    units_mid:   int = 10
    units_top:   int = 5

    # árazás (USD)
    price_entry: float = 1000
    price_mid:   float = 1550
    price_top:   float = 2750

    # COGS (USD/db, középérték)
    cogs_entry: float = 142
    cogs_mid:   float = 275
    cogs_top:   float = 442

    # költségek
    cac_usd:           float = 200
    fixed_opex_usd:    float = 15_000   # havi
    capex_usd:         float = 28_500

    # forecasting (évek 1..5)
    growth_rate:       float = 0.30   # éves volumen-növekedés
    price_inflation:   float = 0.03   # éves árnövelés
    cogs_inflation:    float = 0.04   # éves COGS-növekedés
    opex_inflation:    float = 0.05   # éves bér + iroda inflációs növekedés

    # DCF
    discount_rate:     float = 0.20   # WACC – startup, magas kockázat
    terminal_growth:   float = 0.03   # örökjáradék növekedés
    forecast_years:    int = 5

    # LTV
    repurchase_rate:       float = 0.25   # 25% él upgrade-szolgáltatással
    avg_repurchase_value:  float = 400    # USD (kábel-upgrade, retune)
    customer_lifetime_yr:  int = 5

    def as_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 3. UNIT ECONOMICS
# ============================================================

def unit_economics(p: ModelParams) -> pd.DataFrame:
    """Termékszintű margin-tábla."""
    rows = [
        ("Belépő", p.price_entry, p.cogs_entry),
        ("Közép",  p.price_mid,   p.cogs_mid),
        ("Csúcs",  p.price_top,   p.cogs_top),
    ]
    df = pd.DataFrame(rows, columns=["tier", "price", "cogs"]).set_index("tier")
    df["gross_margin_usd"] = df["price"] - df["cogs"]
    df["gross_margin_pct"] = df["gross_margin_usd"] / df["price"] * 100
    df["contribution_usd"] = df["gross_margin_usd"] - p.cac_usd
    df["contribution_pct"] = df["contribution_usd"] / df["price"] * 100
    return df


# ============================================================
# 4. HAVI P&L
# ============================================================

def monthly_pnl(p: ModelParams) -> dict:
    """Egyszerű havi eredménykimutatás a default mix alapján."""
    revenue = (p.units_entry*p.price_entry +
               p.units_mid*p.price_mid +
               p.units_top*p.price_top)
    cogs = (p.units_entry*p.cogs_entry +
            p.units_mid*p.cogs_mid +
            p.units_top*p.cogs_top)
    units_total = p.units_entry + p.units_mid + p.units_top
    cac_total = units_total * p.cac_usd
    gross_profit = revenue - cogs
    contribution = gross_profit - cac_total
    operating_profit = contribution - p.fixed_opex_usd

    return {
        "revenue":          revenue,
        "cogs":             cogs,
        "gross_profit":     gross_profit,
        "gross_margin_pct": gross_profit / revenue * 100 if revenue else 0,
        "cac_total":        cac_total,
        "contribution":     contribution,
        "fixed_opex":       p.fixed_opex_usd,
        "operating_profit": operating_profit,
        "operating_margin_pct": operating_profit / revenue * 100 if revenue else 0,
        "units_total":      units_total,
    }


# ============================================================
# 5. BREAK-EVEN
# ============================================================

def break_even(p: ModelParams) -> pd.DataFrame:
    """Break-even darabszám szegmensenként."""
    rows = []
    for tier, price, cogs in [
        ("Belépő", p.price_entry, p.cogs_entry),
        ("Közép",  p.price_mid,   p.cogs_mid),
        ("Csúcs",  p.price_top,   p.cogs_top),
    ]:
        cm = price - cogs - p.cac_usd
        be_units = p.fixed_opex_usd / cm if cm > 0 else np.nan
        rows.append({
            "Termék":              tier,
            "Ár (USD)":            price,
            "Contribution / db":   cm,
            "BE darab / hó":       be_units,
            "BE darab / év":       be_units * 12 if not np.isnan(be_units) else np.nan,
            "BE bevétel / hó":     be_units * price if not np.isnan(be_units) else np.nan,
        })
    return pd.DataFrame(rows)


# ============================================================
# 6. 12 HAVI KUMULÁLT CASH-FLOW (1. év)
# ============================================================

def yearly_cashflow(p: ModelParams) -> pd.DataFrame:
    """Hónapról hónapra a kumulált CF a CAPEX-szel együtt."""
    pnl = monthly_pnl(p)
    op_profit = pnl["operating_profit"]
    months = list(range(0, 13))
    monthly_cf = [-p.capex_usd] + [op_profit] * 12
    cum = np.cumsum(monthly_cf)
    return pd.DataFrame({
        "month": months,
        "monthly_cf": monthly_cf,
        "cumulative_cf": cum,
    })


def payback_months(p: ModelParams) -> float:
    pnl = monthly_pnl(p)
    if pnl["operating_profit"] <= 0:
        return np.inf
    return p.capex_usd / pnl["operating_profit"]


# ============================================================
# 7. 5 ÉVES FORECAST – növekedéssel és inflációval
# ============================================================

def long_term_forecast(p: ModelParams) -> pd.DataFrame:
    """N éves P&L előrejelzés inflációval és volumennövekedéssel."""
    rows = []
    for year in range(1, p.forecast_years + 1):
        vol_mult = (1 + p.growth_rate) ** (year - 1)
        price_mult = (1 + p.price_inflation) ** (year - 1)
        cogs_mult = (1 + p.cogs_inflation) ** (year - 1)
        opex_mult = (1 + p.opex_inflation) ** (year - 1)

        units_e = p.units_entry * vol_mult
        units_m = p.units_mid   * vol_mult
        units_t = p.units_top   * vol_mult

        revenue = (units_e*p.price_entry*price_mult +
                   units_m*p.price_mid  *price_mult +
                   units_t*p.price_top  *price_mult) * 12
        cogs = (units_e*p.cogs_entry*cogs_mult +
                units_m*p.cogs_mid  *cogs_mult +
                units_t*p.cogs_top  *cogs_mult) * 12
        units_total_year = (units_e + units_m + units_t) * 12
        cac = units_total_year * p.cac_usd
        opex_year = p.fixed_opex_usd * 12 * opex_mult
        ebit = revenue - cogs - cac - opex_year
        # KIVA közvetve a fix OPEX-ben van (bér × 10%); a profit utáni KIVA-t
        # a visszaforgatás miatt 0-ra vesszük (lásd eredeti dokumentum)
        net_profit = ebit
        rows.append({
            "Év":               f"Y{year}",
            "Volumen (db/év)":  units_total_year,
            "Bevétel":          revenue,
            "COGS":             cogs,
            "CAC":              cac,
            "OPEX":             opex_year,
            "EBIT":             ebit,
            "Nettó profit":     net_profit,
            "Operating margin": ebit / revenue if revenue else 0,
        })
    return pd.DataFrame(rows)


# ============================================================
# 8. DCF – NPV, IRR, terminal value, vállalatérték
# ============================================================

def dcf_valuation(p: ModelParams) -> dict:
    """Discounted Cash-Flow értékelés.

    Egyszerűsítések (tudatosan közlöm):
    - FCF ≈ Nettó profit (a CAPEX évente nincs jelentős utánpótlás)
    - Terminal value = utolsó évi FCF × (1+g) / (WACC - g)
    - Y1-től diszkontálunk
    """
    fc = long_term_forecast(p)
    fcfs = fc["Nettó profit"].values

    # diszkontált CF-ek
    discount_factors = np.array([(1 + p.discount_rate) ** y for y in range(1, len(fcfs)+1)])
    pv_fcfs = fcfs / discount_factors

    # terminal value
    if p.discount_rate <= p.terminal_growth:
        tv = np.nan
        pv_tv = np.nan
    else:
        tv = fcfs[-1] * (1 + p.terminal_growth) / (p.discount_rate - p.terminal_growth)
        pv_tv = tv / discount_factors[-1]

    enterprise_value = np.nansum(pv_fcfs) + (pv_tv if not np.isnan(pv_tv) else 0)

    # IRR – figyelembe vesszük a Y0-ban a CAPEX-et
    cf_for_irr = [-p.capex_usd] + list(fcfs)
    try:
        irr = npf.irr(cf_for_irr)
    except Exception:
        irr = np.nan

    # NPV (a Y0 CAPEX figyelembevételével)
    npv = -p.capex_usd + np.nansum(pv_fcfs) + (pv_tv if not np.isnan(pv_tv) else 0)

    return {
        "fcfs":               fcfs,
        "discount_factors":   discount_factors,
        "pv_fcfs":            pv_fcfs,
        "terminal_value":     tv,
        "pv_terminal_value":  pv_tv,
        "enterprise_value":   enterprise_value,
        "npv":                npv,
        "irr":                irr,
    }


# ============================================================
# 9. LTV / CAC
# ============================================================

def ltv_cac(p: ModelParams) -> dict:
    """Customer Lifetime Value és LTV/CAC arány."""
    ue = unit_economics(p)
    # Súlyozott átlag – eladási mix alapján
    weights = np.array([p.units_entry, p.units_mid, p.units_top])
    total = weights.sum()
    if total == 0:
        return {"ltv": 0, "cac": p.cac_usd, "ratio": 0}
    avg_contribution = (ue["contribution_usd"].values * weights / total).sum()
    avg_gross_margin = (ue["gross_margin_usd"].values * weights / total).sum()

    # LTV = elsődleges eladás bruttó margin + visszatérő ügyfél-bevételek margin-je
    repurchase_ltv = (p.repurchase_rate
                      * p.avg_repurchase_value
                      * 0.6  # ~60% margin a kiegészítőkön
                      * p.customer_lifetime_yr)
    ltv = avg_gross_margin + repurchase_ltv

    return {
        "ltv":               ltv,
        "cac":               p.cac_usd,
        "ratio":             ltv / p.cac_usd if p.cac_usd else 0,
        "payback_purchase":  p.cac_usd / avg_contribution if avg_contribution > 0 else np.inf,
        "avg_gross_margin":  avg_gross_margin,
        "avg_contribution":  avg_contribution,
        "repurchase_ltv":    repurchase_ltv,
    }


# ============================================================
# 10. SCENARIO PLANNING – best / base / worst case
# ============================================================

SCENARIOS = {
    "Pesszimista": {
        "growth_rate":     0.10,
        "vol_mult":        0.6,    # 40%-kal kevesebb induló eladás
        "cac_mult":        1.4,    # drágább akvizíció
        "cogs_mult":       1.15,   # alapanyag-infláció
        "opex_mult":       1.10,   # béremelési nyomás
        "discount_rate":   0.30,
    },
    "Realista": {
        "growth_rate":     0.30,
        "vol_mult":        1.0,
        "cac_mult":        1.0,
        "cogs_mult":       1.0,
        "opex_mult":       1.0,
        "discount_rate":   0.20,
    },
    "Optimista": {
        "growth_rate":     0.55,
        "vol_mult":        1.4,
        "cac_mult":        0.75,   # endorsement átüt, organikus növekedés
        "cogs_mult":       0.95,   # méretgazdaságosság
        "opex_mult":       1.0,
        "discount_rate":   0.15,
    },
}


def run_scenarios(base: ModelParams) -> pd.DataFrame:
    """Best/base/worst forgatókönyvek 5 évre, összehasonlítható módon."""
    results = []
    for scen_name, mods in SCENARIOS.items():
        p = ModelParams(**base.as_dict())
        p.growth_rate = mods["growth_rate"]
        p.units_entry = max(1, int(round(base.units_entry * mods["vol_mult"])))
        p.units_mid   = max(1, int(round(base.units_mid   * mods["vol_mult"])))
        p.units_top   = max(1, int(round(base.units_top   * mods["vol_mult"])))
        p.cac_usd     = base.cac_usd * mods["cac_mult"]
        p.cogs_entry  = base.cogs_entry * mods["cogs_mult"]
        p.cogs_mid    = base.cogs_mid   * mods["cogs_mult"]
        p.cogs_top    = base.cogs_top   * mods["cogs_mult"]
        p.fixed_opex_usd = base.fixed_opex_usd * mods["opex_mult"]
        p.discount_rate = mods["discount_rate"]

        fc = long_term_forecast(p)
        dcf = dcf_valuation(p)
        results.append({
            "Forgatókönyv":          scen_name,
            "Y1 bevétel":            fc.iloc[0]["Bevétel"],
            "Y5 bevétel":            fc.iloc[-1]["Bevétel"],
            "Y5 EBIT":               fc.iloc[-1]["EBIT"],
            "5y kumulált EBIT":      fc["EBIT"].sum(),
            "NPV":                   dcf["npv"],
            "IRR":                   dcf["irr"],
            "Vállalatérték (EV)":    dcf["enterprise_value"],
            "Y5 op. margin":         fc.iloc[-1]["Operating margin"],
        })
    return pd.DataFrame(results)


# ============================================================
# 11. MONTE CARLO SZIMULÁCIÓ
# ============================================================

def monte_carlo(
    base: ModelParams,
    n_sims: int = 5000,
    seed: int = 42,
) -> pd.DataFrame:
    """Random-bemenetekkel futtatott éves NPV-eloszlás.

    Bizonytalansági eloszlások (priorok), a kutatási dokumentum sávjai alapján:
    - havi eladott volumen multiplikátor: Normal(1.0, 0.30)  – 30% szórás
    - CAC: Triangular(150, 200, 250)                          – a kutatási sáv
    - Csúcs ár: Triangular(2000, 2750, 3500)
    - Belépő ár: Triangular(900, 1000, 1200)
    - COGS multiplikátor: Normal(1.0, 0.10)
    - growth_rate: Triangular(0.10, 0.30, 0.55)
    - discount_rate: Uniform(0.15, 0.30)
    """
    rng = np.random.default_rng(seed)

    vol_mult        = rng.normal(1.0, 0.30, n_sims).clip(0.2, 2.0)
    cac_draw        = rng.triangular(150, 200, 250, n_sims)
    price_top       = rng.triangular(2000, 2750, 3500, n_sims)
    price_entry     = rng.triangular(900,  1000, 1200, n_sims)
    cogs_mult       = rng.normal(1.0, 0.10, n_sims).clip(0.5, 1.5)
    growth          = rng.triangular(0.10, 0.30, 0.55, n_sims)
    discount        = rng.uniform(0.15, 0.30, n_sims)

    npvs, irrs, y5_ebits, y1_op_profits = [], [], [], []

    for i in range(n_sims):
        p = ModelParams(**base.as_dict())
        p.units_entry = max(1, int(round(base.units_entry * vol_mult[i])))
        p.units_mid   = max(1, int(round(base.units_mid   * vol_mult[i])))
        p.units_top   = max(1, int(round(base.units_top   * vol_mult[i])))
        p.cac_usd     = float(cac_draw[i])
        p.price_top   = float(price_top[i])
        p.price_entry = float(price_entry[i])
        p.cogs_entry *= float(cogs_mult[i])
        p.cogs_mid   *= float(cogs_mult[i])
        p.cogs_top   *= float(cogs_mult[i])
        p.growth_rate    = float(growth[i])
        p.discount_rate  = float(discount[i])

        dcf = dcf_valuation(p)
        fc = long_term_forecast(p)
        pnl = monthly_pnl(p)

        npvs.append(dcf["npv"])
        irrs.append(dcf["irr"])
        y5_ebits.append(fc.iloc[-1]["EBIT"])
        y1_op_profits.append(pnl["operating_profit"] * 12)

    return pd.DataFrame({
        "NPV":           npvs,
        "IRR":           irrs,
        "Y5_EBIT":       y5_ebits,
        "Y1_op_profit":  y1_op_profits,
        # bemenetek megőrzése – érzékenységi vizsgálatra
        "in_vol_mult":   vol_mult,
        "in_cac":        cac_draw,
        "in_price_top":  price_top,
        "in_growth":     growth,
        "in_discount":   discount,
        "in_cogs_mult":  cogs_mult,
    })


# ============================================================
# 12. ÉRZÉKENYSÉGI ELEMZÉS – tornado chart adatok
# ============================================================

def sensitivity_tornado(base: ModelParams, target: str = "npv") -> pd.DataFrame:
    """Egyenként ±20% lökést ad minden inputra, méri a hatást a célértékre.

    target: 'npv' | 'irr' | 'y5_ebit' | 'y1_op_profit'
    """
    # base érték
    def _target(p: ModelParams) -> float:
        dcf = dcf_valuation(p)
        fc = long_term_forecast(p)
        pnl = monthly_pnl(p)
        return {
            "npv":          dcf["npv"],
            "irr":          dcf["irr"],
            "y5_ebit":      fc.iloc[-1]["EBIT"],
            "y1_op_profit": pnl["operating_profit"] * 12,
        }[target]

    base_value = _target(base)

    # paraméter -> (címke, lekérő, frissítő)
    params = {
        "Eladási volumen":   ("units_total",
                              lambda p: (p.units_entry, p.units_mid, p.units_top)),
        "CAC":               ("cac_usd",      None),
        "Csúcs eladási ár":  ("price_top",    None),
        "Belépő eladási ár": ("price_entry",  None),
        "COGS (összes)":     ("cogs_total",
                              lambda p: (p.cogs_entry, p.cogs_mid, p.cogs_top)),
        "Fix OPEX":          ("fixed_opex_usd", None),
        "Növekedési ráta":   ("growth_rate",   None),
        "Diszkontráta":      ("discount_rate", None),
        "CAPEX":             ("capex_usd",     None),
    }

    rows = []
    for label, (param_key, _) in params.items():
        for direction, mult in [("low", 0.8), ("high", 1.2)]:
            p = ModelParams(**base.as_dict())
            if param_key == "units_total":
                p.units_entry = max(1, int(round(base.units_entry * mult)))
                p.units_mid   = max(1, int(round(base.units_mid   * mult)))
                p.units_top   = max(1, int(round(base.units_top   * mult)))
            elif param_key == "cogs_total":
                p.cogs_entry = base.cogs_entry * mult
                p.cogs_mid   = base.cogs_mid   * mult
                p.cogs_top   = base.cogs_top   * mult
            else:
                setattr(p, param_key, getattr(base, param_key) * mult)

            new_val = _target(p)
            rows.append({
                "Paraméter": label,
                "Irány":     direction,
                "Hatás":     new_val - base_value,
                "Új érték":  new_val,
            })

    df = pd.DataFrame(rows)
    # rendezés a max abszolút hatás szerint
    impact_order = (df.assign(abs_impact=df["Hatás"].abs())
                      .groupby("Paraméter")["abs_impact"].max()
                      .sort_values(ascending=True))
    df["Paraméter"] = pd.Categorical(df["Paraméter"], categories=impact_order.index, ordered=True)
    return df.sort_values(["Paraméter", "Irány"]), base_value
