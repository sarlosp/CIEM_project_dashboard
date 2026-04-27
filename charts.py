"""
charts.py – Plotly interaktív vizualizációk a CIEM dashboardhoz
================================================================
Minden függvény egy plotly.graph_objects.Figure-t ad vissza,
így a Streamlit `st.plotly_chart()`-ba közvetlenül beadható.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ============================================================
# SZÍNPALETTA – konzisztens az egész alkalmazásban
# ============================================================
COLORS = {
    "primary":  "#1F4E79",   # sötét kék
    "accent":   "#2E7D32",   # zöld (profit)
    "negative": "#C0504D",   # piros (költség)
    "warning":  "#E8A33D",   # narancs
    "neutral":  "#7A7A7A",   # szürke
    "light":    "#EAF1F8",   # halvány kék zebra
    "entry":    "#3B7FBF",
    "mid":      "#1F4E79",
    "top":      "#0D2B47",
}

TIER_COLORS = {"Belépő": COLORS["entry"], "Közép": COLORS["mid"], "Csúcs": COLORS["top"]}


# ============================================================
# 1. UNIT ECONOMICS WATERFALL (3 termék egyszerre)
# ============================================================
def chart_unit_economics(ue: pd.DataFrame, cac: float) -> go.Figure:
    """3-paneles vízesés-diagram az unit economics-hoz."""
    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=[f"<b>{tier}</b>" for tier in ue.index],
                        horizontal_spacing=0.08)

    for i, tier in enumerate(ue.index, 1):
        price = ue.loc[tier, "price"]
        cogs = ue.loc[tier, "cogs"]
        contrib = ue.loc[tier, "contribution_usd"]

        fig.add_trace(go.Waterfall(
            name=tier, orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Bevétel", "– COGS", "– CAC", "Contribution"],
            y=[price, -cogs, -cac, 0],   # az utolsó "total"
            text=[f"${price:,.0f}", f"-${cogs:,.0f}",
                  f"-${cac:,.0f}", f"${contrib:,.0f}"],
            textposition="outside",
            textfont=dict(size=12, color="black"),
            increasing={"marker": {"color": COLORS["primary"]}},
            decreasing={"marker": {"color": COLORS["negative"]}},
            totals={"marker": {"color": COLORS["accent"]}},
            connector={"line": {"color": "rgba(0,0,0,0.3)", "dash": "dot"}},
            showlegend=False,
        ), row=1, col=i)

        # margin % annotáció
        margin_pct = contrib / price * 100
        fig.add_annotation(
            xref=f"x{i}", yref=f"y{i}",
            x="Contribution", y=contrib/2,
            text=f"<b>{margin_pct:.0f}%</b><br>margin",
            showarrow=False, font=dict(size=14, color="white", family="Arial Black"),
        )

    fig.update_layout(
        title=dict(text="<b>Unit Economics</b> – Bevételből contribution margin termékenként",
                   font=dict(size=18)),
        height=480, plot_bgcolor="white",
        margin=dict(t=80, b=30, l=20, r=20),
    )
    fig.update_yaxes(showgrid=True, gridcolor="#E5E5E5", tickformat="$,.0f")
    fig.update_xaxes(showgrid=False)
    return fig


# ============================================================
# 2. BREAK-EVEN INTERAKTÍV
# ============================================================
def chart_break_even(p, max_units: int = 50) -> go.Figure:
    """Bevétel + költség görbék mindhárom szegmensre, BE pontok kiemelve."""
    units = np.arange(0, max_units + 1)
    fig = go.Figure()

    products = [
        ("Belépő", p.price_entry, p.cogs_entry, COLORS["entry"]),
        ("Közép",  p.price_mid,   p.cogs_mid,   COLORS["mid"]),
        ("Csúcs",  p.price_top,   p.cogs_top,   COLORS["top"]),
    ]

    for tier, price, cogs, color in products:
        cm = price - cogs - p.cac_usd
        revenue = units * price
        total_cost = p.fixed_opex_usd + units * (cogs + p.cac_usd)
        be_units = p.fixed_opex_usd / cm if cm > 0 else None

        fig.add_trace(go.Scatter(
            x=units, y=revenue, mode="lines",
            name=f"{tier} bevétel", line=dict(color=color, width=3),
            hovertemplate=f"<b>{tier}</b><br>Eladott: %{{x}} db<br>Bevétel: $%{{y:,.0f}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=units, y=total_cost, mode="lines",
            name=f"{tier} össz. költség", line=dict(color=color, width=2, dash="dash"),
            hovertemplate=f"<b>{tier}</b><br>Eladott: %{{x}} db<br>Össz. költség: $%{{y:,.0f}}<extra></extra>",
            showlegend=False,
        ))

        if be_units and be_units < max_units:
            fig.add_trace(go.Scatter(
                x=[be_units], y=[be_units * price],
                mode="markers+text",
                marker=dict(size=18, color="#FCBA03",
                            line=dict(color="black", width=2)),
                text=[f"BE: {be_units:.1f} db"],
                textposition="top right",
                textfont=dict(size=12, color="black"),
                name=f"{tier} BE pont", showlegend=False,
                hovertemplate=f"<b>BREAK-EVEN ({tier})</b><br>Darab: %{{x:.1f}}<br>Bevétel: $%{{y:,.0f}}<extra></extra>",
            ))

    # Fix OPEX vízszintes vonal
    fig.add_hline(y=p.fixed_opex_usd, line_dash="dot", line_color=COLORS["neutral"],
                  annotation_text=f"Fix OPEX: ${p.fixed_opex_usd:,.0f}",
                  annotation_position="bottom right")

    fig.update_layout(
        title=dict(text="<b>Break-even elemzés</b> – havi szinten, szegmensenként",
                   font=dict(size=18)),
        xaxis=dict(title="Eladott darabszám / hó", showgrid=True, gridcolor="#E5E5E5"),
        yaxis=dict(title="USD / hó", showgrid=True, gridcolor="#E5E5E5", tickformat="$,.0f"),
        plot_bgcolor="white", height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig


# ============================================================
# 3. KUMULÁLT CASH-FLOW (12 hónap)
# ============================================================
def chart_cumulative_cf(cf_df: pd.DataFrame, capex: float, payback_m: float) -> go.Figure:
    """12 hónapos kumulált CF + payback annotáció."""
    fig = go.Figure()

    # háttér zónák
    y_min = cf_df["cumulative_cf"].min() * 1.2
    y_max = cf_df["cumulative_cf"].max() * 1.15
    fig.add_hrect(y0=y_min, y1=0, fillcolor=COLORS["negative"], opacity=0.10, line_width=0)
    fig.add_hrect(y0=0, y1=y_max, fillcolor=COLORS["accent"], opacity=0.10, line_width=0)

    fig.add_trace(go.Scatter(
        x=cf_df["month"], y=cf_df["cumulative_cf"],
        mode="lines+markers",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=10, color="white", line=dict(color=COLORS["primary"], width=2)),
        name="Kumulált CF",
        hovertemplate="<b>Hónap %{x}</b><br>Kumulált CF: $%{y:,.0f}<extra></extra>",
    ))

    # 0 vonal
    fig.add_hline(y=0, line_color="black", line_width=1)

    # CAPEX kiemelés
    fig.add_annotation(
        x=0, y=-capex,
        text=f"<b>CAPEX:</b><br>-${capex:,.0f}",
        showarrow=True, arrowhead=2, ax=40, ay=20,
        bgcolor="#FFE5E5", bordercolor=COLORS["negative"],
        borderwidth=1.5, font=dict(size=11),
    )

    # Payback annotáció
    if payback_m < 12:
        fig.add_vline(x=payback_m, line_dash="dash", line_color=COLORS["warning"], line_width=2)
        fig.add_annotation(
            x=payback_m, y=cf_df["cumulative_cf"].max()*0.4,
            text=f"<b>PAYBACK</b><br>{payback_m:.1f} hónap",
            showarrow=False, bgcolor="#FFF8E1",
            bordercolor=COLORS["warning"], borderwidth=1.5,
            font=dict(size=12, color="black"),
        )

    # 12. hónap végi érték
    final_cf = cf_df["cumulative_cf"].iloc[-1]
    fig.add_annotation(
        x=12, y=final_cf,
        text=f"<b>Y1 vége:</b><br>+${final_cf:,.0f}",
        showarrow=True, arrowhead=2, ax=-40, ay=-30,
        bgcolor="#E8F5E9", bordercolor=COLORS["accent"],
        borderwidth=1.5, font=dict(size=11),
    )

    fig.update_layout(
        title=dict(text="<b>Kumulált cash-flow</b> – első 12 hónap a CAPEX-szel",
                   font=dict(size=18)),
        xaxis=dict(title="Hónap", dtick=1),
        yaxis=dict(title="USD", tickformat="$,.0f"),
        plot_bgcolor="white", height=480, showlegend=False,
    )
    return fig


# ============================================================
# 4. 5 ÉVES FORECAST – kombinált oszlop + vonal
# ============================================================
def chart_forecast(fc: pd.DataFrame) -> go.Figure:
    """Y1-Y5 bevétel, EBIT és margin együtt."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=fc["Év"], y=fc["Bevétel"], name="Bevétel",
        marker_color=COLORS["primary"], opacity=0.85,
        text=[f"${v/1000:.0f}k" for v in fc["Bevétel"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Bevétel: $%{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=fc["Év"], y=fc["EBIT"], name="EBIT",
        marker_color=COLORS["accent"], opacity=0.85,
        text=[f"${v/1000:.0f}k" for v in fc["EBIT"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>EBIT: $%{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=fc["Év"], y=fc["Operating margin"]*100,
        mode="lines+markers+text", name="Operating margin (%)",
        line=dict(color=COLORS["warning"], width=3),
        marker=dict(size=12, color=COLORS["warning"]),
        text=[f"{v*100:.0f}%" for v in fc["Operating margin"]],
        textposition="top center", textfont=dict(size=12, color=COLORS["warning"]),
        hovertemplate="<b>%{x}</b><br>Op. margin: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        title=dict(text="<b>5 éves forecast</b> – bevétel, EBIT és operating margin",
                   font=dict(size=18)),
        barmode="group", plot_bgcolor="white", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(title_text="USD", tickformat="$,.0f", secondary_y=False, showgrid=True, gridcolor="#E5E5E5")
    fig.update_yaxes(title_text="Operating margin (%)", tickformat=".0f", secondary_y=True, showgrid=False)
    return fig


# ============================================================
# 5. DCF VÍZESÉS – a vállalatérték összetétele
# ============================================================
def chart_dcf_waterfall(dcf: dict, capex: float) -> go.Figure:
    """Hogyan adódik össze az NPV: PV(FCF Y1..Y5) + PV(TV) – CAPEX."""
    pv_fcfs = dcf["pv_fcfs"]
    pv_tv = dcf["pv_terminal_value"]

    labels = ([f"PV(FCF Y{i+1})" for i in range(len(pv_fcfs))]
              + ["PV(Terminal Value)", "– CAPEX", "NPV"])
    values = list(pv_fcfs) + [pv_tv if not np.isnan(pv_tv) else 0, -capex, 0]
    measure = ["relative"] * (len(pv_fcfs) + 2) + ["total"]

    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measure,
        text=[f"${v:,.0f}" for v in values[:-1]] + [f"${dcf['npv']:,.0f}"],
        textposition="outside",
        increasing={"marker": {"color": COLORS["primary"]}},
        decreasing={"marker": {"color": COLORS["negative"]}},
        totals={"marker": {"color": COLORS["accent"]}},
        connector={"line": {"color": "rgba(0,0,0,0.3)", "dash": "dot"}},
    ))
    fig.update_layout(
        title=dict(text="<b>DCF vízesés</b> – a Net Present Value összetétele",
                   font=dict(size=18)),
        plot_bgcolor="white", height=480,
        yaxis=dict(title="USD", tickformat="$,.0f", showgrid=True, gridcolor="#E5E5E5"),
        xaxis=dict(showgrid=False),
    )
    return fig


# ============================================================
# 6. SCENARIO – best/base/worst összehasonlítás
# ============================================================
def chart_scenarios(sc: pd.DataFrame) -> go.Figure:
    """3-paneles oszlopdiagram: NPV, IRR, Y5 EBIT scenarionként."""
    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=["<b>NPV (USD)</b>", "<b>IRR (%)</b>", "<b>Y5 EBIT (USD)</b>"],
                        horizontal_spacing=0.10)

    scenario_colors = [COLORS["negative"], COLORS["primary"], COLORS["accent"]]

    fig.add_trace(go.Bar(
        x=sc["Forgatókönyv"], y=sc["NPV"],
        marker_color=scenario_colors,
        text=[f"${v/1e6:.2f}M" for v in sc["NPV"]],
        textposition="outside", showlegend=False,
        hovertemplate="<b>%{x}</b><br>NPV: $%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=sc["Forgatókönyv"], y=sc["IRR"]*100,
        marker_color=scenario_colors,
        text=[f"{v*100:.0f}%" for v in sc["IRR"]],
        textposition="outside", showlegend=False,
        hovertemplate="<b>%{x}</b><br>IRR: %{y:.1f}%<extra></extra>",
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        x=sc["Forgatókönyv"], y=sc["Y5 EBIT"],
        marker_color=scenario_colors,
        text=[f"${v/1000:.0f}k" for v in sc["Y5 EBIT"]],
        textposition="outside", showlegend=False,
        hovertemplate="<b>%{x}</b><br>Y5 EBIT: $%{y:,.0f}<extra></extra>",
    ), row=1, col=3)

    fig.update_layout(
        title=dict(text="<b>Scenario-elemzés</b> – pesszimista vs. realista vs. optimista",
                   font=dict(size=18)),
        plot_bgcolor="white", height=440,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#E5E5E5")
    fig.update_xaxes(tickangle=0)
    return fig


# ============================================================
# 7. MONTE CARLO – NPV eloszlás histogram + percentilisek
# ============================================================
def chart_mc_distribution(mc: pd.DataFrame, target: str = "NPV") -> go.Figure:
    """Histogram + KDE + percentilis vonalak."""
    values = mc[target].values
    p5, p50, p95 = np.percentile(values, [5, 50, 95])

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=values, nbinsx=60, name=target,
        marker=dict(color=COLORS["primary"], line=dict(color="white", width=1)),
        opacity=0.85,
        hovertemplate=f"<b>{target}</b><br>Sáv: %{{x:$,.0f}}<br>Esetek: %{{y}}<extra></extra>",
    ))

    # percentilis vonalak
    for p, label, color in [
        (p5,  f"P5: ${p5:,.0f}",   COLORS["negative"]),
        (p50, f"P50: ${p50:,.0f}", COLORS["warning"]),
        (p95, f"P95: ${p95:,.0f}", COLORS["accent"]),
    ]:
        fig.add_vline(x=p, line_dash="dash", line_color=color, line_width=2,
                      annotation_text=label, annotation_position="top")

    # 0 vonal (vesztés / nyerés határ)
    if target in ("NPV", "Y1_op_profit", "Y5_EBIT"):
        fig.add_vline(x=0, line_color="black", line_width=1.5,
                      annotation_text="Break-even", annotation_position="bottom")

    pct_positive = (values > 0).mean() * 100
    fig.update_layout(
        title=dict(
            text=f"<b>Monte Carlo eloszlás – {target}</b>  "
                 f"<span style='font-size:13px;color:#666'>"
                 f"({len(values):,} szimuláció · pozitív kimenet: {pct_positive:.1f}%)</span>",
            font=dict(size=18)),
        xaxis=dict(title=target + " (USD)", tickformat="$,.0f"),
        yaxis=dict(title="Szimulációk száma"),
        plot_bgcolor="white", height=460, showlegend=False,
        bargap=0.02,
    )
    return fig


# ============================================================
# 8. MONTE CARLO – bemenet vs. NPV scatter (érzékenység MC-ből)
# ============================================================
def chart_mc_input_sensitivity(mc: pd.DataFrame) -> go.Figure:
    """Korreláció minden bemenet és az NPV között."""
    input_cols = ["in_vol_mult", "in_cac", "in_price_top",
                  "in_growth", "in_discount", "in_cogs_mult"]
    nice_names = {
        "in_vol_mult":  "Volumen multiplikátor",
        "in_cac":       "CAC ($)",
        "in_price_top": "Csúcs ár ($)",
        "in_growth":    "Növekedési ráta",
        "in_discount":  "Diszkontráta",
        "in_cogs_mult": "COGS multiplikátor",
    }

    correlations = mc[input_cols].apply(lambda c: c.corr(mc["NPV"])).sort_values()
    correlations.index = [nice_names[i] for i in correlations.index]
    colors = [COLORS["negative"] if v < 0 else COLORS["accent"] for v in correlations.values]

    fig = go.Figure(go.Bar(
        x=correlations.values, y=correlations.index,
        orientation="h", marker_color=colors,
        text=[f"{v:+.2f}" for v in correlations.values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Korreláció: %{x:+.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>NPV érzékenysége a bemenetekre</b> – Monte Carlo korreláció",
                   font=dict(size=18)),
        xaxis=dict(title="Pearson-korreláció az NPV-vel", range=[-1, 1],
                   showgrid=True, gridcolor="#E5E5E5", zeroline=True, zerolinecolor="black"),
        plot_bgcolor="white", height=380, showlegend=False,
    )
    return fig


# ============================================================
# 9. TORNADO – egyenkénti ±20% lökés
# ============================================================
def chart_tornado(df: pd.DataFrame, base_value: float, target_label: str = "NPV") -> go.Figure:
    """Klasszikus tornado-diagram – melyik input mozgatja a céltényezőt legjobban."""
    low = df[df["Irány"] == "low"].set_index("Paraméter")["Hatás"]
    high = df[df["Irány"] == "high"].set_index("Paraméter")["Hatás"]
    params = low.index

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=params, x=low.values, orientation="h",
        name="–20% input", marker_color=COLORS["negative"],
        text=[f"${v:+,.0f}" for v in low.values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>–20% input → hatás: $%{x:+,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=params, x=high.values, orientation="h",
        name="+20% input", marker_color=COLORS["primary"],
        text=[f"${v:+,.0f}" for v in high.values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>+20% input → hatás: $%{x:+,.0f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="black", line_width=1.5)

    fig.update_layout(
        title=dict(text=f"<b>Tornado-elemzés – {target_label}</b>  "
                        f"<span style='font-size:13px;color:#666'>"
                        f"(base: ${base_value:,.0f} · ±20% lökés inputonként)</span>",
                   font=dict(size=18)),
        xaxis=dict(title=f"Hatás a {target_label}-ra (USD)", tickformat="$,.0f",
                   showgrid=True, gridcolor="#E5E5E5"),
        yaxis=dict(title=""),
        plot_bgcolor="white", height=520, barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


# ============================================================
# 10. LTV/CAC – arány vizualizáció
# ============================================================
def chart_ltv_cac(ltv_data: dict) -> go.Figure:
    """LTV vs CAC összehasonlító oszlopdiagram + benchmark vonalak."""
    ratio = ltv_data["ratio"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45],
                        subplot_titles=["<b>LTV vs CAC összevetés</b>",
                                        "<b>LTV/CAC arány vs. iparági benchmark</b>"])

    # bal panel - oszlopok
    fig.add_trace(go.Bar(
        x=["CAC", "LTV (gross margin)", "LTV (+ visszatérő)"],
        y=[ltv_data["cac"], ltv_data["avg_gross_margin"], ltv_data["ltv"]],
        marker_color=[COLORS["negative"], COLORS["primary"], COLORS["accent"]],
        text=[f"${ltv_data['cac']:,.0f}",
              f"${ltv_data['avg_gross_margin']:,.0f}",
              f"${ltv_data['ltv']:,.0f}"],
        textposition="outside", showlegend=False,
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    # jobb panel - LTV/CAC arány gauge-szerű
    benchmark_categories = ["Veszteséges (<1)", "Egészségtelen (1-3)",
                            "Egészséges (3-5)", "Kiváló (>5)"]
    benchmark_colors = [COLORS["negative"], COLORS["warning"],
                        COLORS["primary"], COLORS["accent"]]
    benchmark_widths = [1, 2, 2, 4]   # az utolsó tág, mert nyitott felfelé

    cumsum = 0
    for cat, color, width in zip(benchmark_categories, benchmark_colors, benchmark_widths):
        fig.add_trace(go.Bar(
            y=["LTV/CAC sáv"], x=[width], orientation="h",
            name=cat, marker_color=color,
            text=[cat], textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white", size=11),
            hovertemplate=f"<b>{cat}</b><br>Tartomány: {cumsum}-{cumsum+width}<extra></extra>",
        ), row=1, col=2)
        cumsum += width

    # Marker az aktuális arányra
    fig.add_trace(go.Scatter(
        x=[min(ratio, 9)], y=["LTV/CAC sáv"],
        mode="markers+text",
        marker=dict(size=22, color="black", symbol="diamond",
                    line=dict(color="white", width=2)),
        text=[f"<b>{ratio:.1f}×</b>"],
        textposition="top center", textfont=dict(size=14),
        showlegend=False, hovertemplate=f"<b>Aktuális: {ratio:.2f}×</b><extra></extra>",
    ), row=1, col=2)

    fig.update_layout(
        title=dict(text="<b>Customer Lifetime Value / Customer Acquisition Cost</b>",
                   font=dict(size=18)),
        plot_bgcolor="white", height=400, barmode="stack",
        showlegend=False,
    )
    fig.update_xaxes(tickformat="$,.0f", row=1, col=1, title_text="USD")
    fig.update_xaxes(range=[0, 9], row=1, col=2, title_text="LTV/CAC arány")
    fig.update_yaxes(showticklabels=False, row=1, col=2)
    return fig


# ============================================================
# 11. SZEGMENS-MIX (kördiagram a bevételhez)
# ============================================================
def chart_revenue_mix(p) -> go.Figure:
    """Kördiagram a havi bevétel termékportfólió szerinti megoszlásáról."""
    revs = {
        "Belépő": p.units_entry * p.price_entry,
        "Közép":  p.units_mid   * p.price_mid,
        "Csúcs":  p.units_top   * p.price_top,
    }
    fig = go.Figure(go.Pie(
        labels=list(revs.keys()), values=list(revs.values()),
        hole=0.55,
        marker=dict(colors=[TIER_COLORS[k] for k in revs],
                    line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=14, color="white"),
        hovertemplate="<b>%{label}</b><br>Bevétel: $%{value:,.0f}<br>Részesedés: %{percent}<extra></extra>",
    ))
    total = sum(revs.values())
    fig.update_layout(
        title=dict(text=f"<b>Bevételi mix</b><br>"
                        f"<span style='font-size:13px;color:#666'>Havi össz.: ${total:,.0f}</span>",
                   font=dict(size=16)),
        annotations=[dict(text=f"<b>${total/1000:.0f}k</b><br>/ hó",
                          x=0.5, y=0.5, font_size=18, showarrow=False)],
        height=360, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
    )
    return fig
