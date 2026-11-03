"""Retail & E-commerce Sales Analytics - Streamlit + Plotly dashboard (neon dark theme).
Run:  pip install -r requirements.txt  &&  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import metrics as M

st.set_page_config(page_title="Retail Sales Analytics", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------- palette ----------
BG, CARD, BORDER, TEXT, MUTED = "#0B1020", "#131A33", "#2A3355", "#E6EAF5", "#8B95B0"
CYAN, VIOLET, PINK, GREEN, AMBER, BLUE = "#22D3EE", "#A78BFA", "#F472B6", "#34D399", "#FBBF24", "#60A5FA"
GOOD, BAD = "#22D3A6", "#FF5C7A"
CAT_COLORS = [CYAN, VIOLET, PINK, GREEN, AMBER, BLUE]
SCALE = [[0, "#18214A"], [0.2, "#243A8A"], [0.55, "#2F6FE0"], [1, "#22D3EE"]]  # deep navy -> blue -> cyan

st.markdown(f"""
<style>
.stApp {{ background:{BG}; font-family:'Segoe UI',sans-serif; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1.2rem; max-width:1500px; }}
div[role="radiogroup"] {{ gap:.5rem; flex-wrap:wrap; }}
div[role="radiogroup"] > label {{ background:{CARD}; border:1px solid {BORDER}; border-radius:999px;
   padding:.35rem 1.1rem; cursor:pointer; transition:.2s; }}
div[role="radiogroup"] > label:hover {{ border-color:{CYAN}; }}
div[role="radiogroup"] > label > div:first-child {{ display:none; }}
div[role="radiogroup"] > label:has(input:checked) {{ background:linear-gradient(90deg,{VIOLET},{CYAN});
   border-color:transparent; }}
div[role="radiogroup"] > label:has(input:checked) p {{ color:#0B1020; font-weight:700; }}
.kpi {{ background:{CARD}; border:1px solid {BORDER}; border-radius:14px; padding:14px 18px 12px;
   position:relative; overflow:hidden; height:118px; }}
.kpi:before {{ content:''; position:absolute; left:0; top:0; right:0; height:4px; background:var(--g); }}
.kpi .l {{ color:{MUTED}; font-size:.78rem; letter-spacing:.06em; text-transform:uppercase; }}
.kpi .v {{ color:{TEXT}; font-size:1.9rem; font-weight:700; margin:.15rem 0; }}
.kpi .d {{ font-size:.82rem; }}
.panel {{ background:{CARD}; border:1px solid {BORDER}; border-radius:14px; padding:14px 18px; }}
.panel h4 {{ margin:0 0 .4rem; color:{TEXT}; font-size:1rem; }}
.panel li, .panel p {{ color:{TEXT}; font-size:.9rem; line-height:1.5; }}
.reco {{ border-left:4px solid var(--c); }}
.note {{ color:{MUTED}; font-size:.78rem; }}
h1,h2,h3 {{ color:{TEXT}; }}
/* ---- force readable colours (works even without .streamlit/config.toml) ---- */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li {{ color:{TEXT}; }}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {{ color:{MUTED} !important; font-size:.8rem; }}
div[role="radiogroup"] > label p {{ color:{TEXT} !important; font-size:.92rem; margin:0; }}
div[data-baseweb="select"] > div {{ background:{CARD} !important; border:1px solid {BORDER} !important; border-radius:10px; }}
div[data-baseweb="select"] * {{ color:{TEXT} !important; }}
div[data-baseweb="select"] svg {{ fill:{MUTED} !important; }}
span[data-baseweb="tag"] {{ background:linear-gradient(90deg,{VIOLET},{CYAN}) !important; border-radius:8px; }}
span[data-baseweb="tag"] * {{ color:#0B1020 !important; font-weight:600; }}
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li {{ background:{CARD} !important; color:{TEXT} !important; }}
[data-testid="stSlider"] [role="slider"] {{ background:{CYAN} !important; box-shadow:0 0 0 4px rgba(34,211,238,.25); }}
[data-testid="stSlider"] [data-testid="stThumbValue"], [data-testid="stSlider"] div {{ color:{CYAN} !important; }}
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] {{ color:{MUTED} !important; }}
.topbar {{ background:{CARD}; border:1px solid {BORDER}; border-radius:14px; padding:12px 20px; margin-bottom:.6rem; }}
.topbar .t {{ font-size:1.25rem; font-weight:800; color:{TEXT}; letter-spacing:.04em; }}
.topbar .t span {{ color:{CYAN}; }}
[data-testid="stMarkdownContainer"] h5 {{ color:{TEXT}; }}
</style>""", unsafe_allow_html=True)


# ---------- helpers ----------
def fmt_money(x):
    a = abs(x)
    return f"{x/1e6:.2f}M" if a >= 1e6 else f"{x/1e3:.0f}K" if a >= 1e4 else f"{x:,.0f}"


def kpi(label, value, delta=None, grad=(CYAN, VIOLET), pts=False, suffix=" vs prev period"):
    d = ""
    if delta is not None and not (isinstance(delta, float) and np.isnan(delta)):
        up = delta >= 0
        txt = f"{delta*100:+.1f} pts" if pts else f"{delta*100:+.1f}%"
        d = f"<div class='d' style='color:{GOOD if up else BAD}'>{'▲' if up else '▼'} {txt}<span style='color:{MUTED}'>{suffix}</span></div>"
    return (f"<div class='kpi' style='--g:linear-gradient(90deg,{grad[0]},{grad[1]})'>"
            f"<div class='l'>{label}</div><div class='v'>{value}</div>{d}</div>")


def style_fig(fig, h=330, legend=False):
    fig.update_layout(height=h, paper_bgcolor=CARD, plot_bgcolor=CARD, font=dict(color=TEXT, family="Segoe UI"),
                      margin=dict(l=14, r=14, t=44, b=14), showlegend=legend,
                      legend=dict(orientation="h", y=-0.2, font=dict(color=MUTED)),
                      title=dict(font=dict(size=15, color=TEXT), x=0.01))
    fig.update_xaxes(gridcolor="#1E2748", zerolinecolor="#1E2748", color=MUTED)
    fig.update_yaxes(gridcolor="#1E2748", zerolinecolor="#1E2748", color=MUTED)
    return fig


def show(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def panel(title, body_html, color=CYAN, cls=""):
    st.markdown(f"<div class='panel {cls}' style='--c:{color}'><h4>{title}</h4>{body_html}</div>",
                unsafe_allow_html=True)


# ---------- data + filters ----------
@st.cache_data
def get_data():
    return M.load()


df = get_data()
months = sorted(df["Month"].unique())
labels = [pd.Timestamp(m).strftime("%b %Y") for m in months]

st.markdown(f"<div class='topbar'><div class='t'>📊 RETAIL & E-COMMERCE <span>SALES ANALYTICS</span></div></div>",
            unsafe_allow_html=True)
PAGES = ["Executive Overview", "Sales Trend", "Product & Category", "Customer Analytics", "Profit & Recommendations"]
page = st.radio("page", PAGES, horizontal=True, label_visibility="collapsed")

f1, f2, f3, f4 = st.columns([2.2, 1, 1, 1])
with f1:
    a, b = st.select_slider("Date range (month)", options=labels, value=(labels[-12], labels[-1]))
def pick(label, values):
    """Dropdown with 'All' on top (like the Power BI slicer). Returns the list of selected values."""
    choice = st.selectbox(label, ["All"] + list(values))
    return list(values) if choice == "All" else [choice]


with f2:
    regions = pick("Region", sorted(df["Region"].unique()))
with f3:
    cats = pick("Category", sorted(df["Category"].unique()))
with f4:
    segs = pick("Segment", sorted(df["CustomerSegment"].dropna().unique()))

start, end = pd.Timestamp(months[labels.index(a)]), pd.Timestamp(months[labels.index(b)])
if not (regions and cats and segs):
    st.warning("Select at least one value in every filter.")
    st.stop()
cur, prev = M.apply_filters(df, start, end, regions, cats, segs)
K, P = M.kpis(cur), M.kpis(prev)
ch = {k: M.pct_change(K[k], P[k]) for k in K}
mon = M.monthly(cur)
st.markdown("")

# =====================================================================
if page == "Executive Overview":
    c = st.columns(4)
    c[0].markdown(kpi("Net Sales", fmt_money(K["sales"]), ch["sales"], (CYAN, BLUE)), unsafe_allow_html=True)
    c[1].markdown(kpi("Profit (est.)", fmt_money(K["profit"]), ch["profit"], (VIOLET, PINK)), unsafe_allow_html=True)
    c[2].markdown(kpi("Orders", f"{K['orders']:,}", ch["orders"], (GREEN, CYAN)), unsafe_allow_html=True)
    c[3].markdown(kpi("Profit Margin", f"{K['margin']*100:.1f}%", K["margin"] - P["margin"], (AMBER, PINK), pts=True),
                  unsafe_allow_html=True)
    st.markdown("")
    l, r = st.columns([1.6, 1])
    with l:
        fig = go.Figure(go.Scatter(x=mon["Month"], y=mon["Sales"], mode="lines", line=dict(color=CYAN, width=3),
                                   fill="tozeroy", fillcolor="rgba(34,211,238,.12)", name="Net Sales"))
        fig.add_trace(go.Scatter(x=mon["Month"], y=mon["Profit"], mode="lines", line=dict(color=PINK, width=2, dash="dot"),
                                 name="Profit"))
        show(style_fig(fig.update_layout(title="Monthly Net Sales & Profit"), legend=True))
    with r:
        cb = M.by(cur, "Category").sort_values("Sales")
        fig = go.Figure(go.Bar(x=cb["Sales"], y=cb["Category"], orientation="h", marker_color=CAT_COLORS[:len(cb)][::-1],
                               text=[fmt_money(v) for v in cb["Sales"]], textposition="outside", cliponaxis=False))
        show(style_fig(fig.update_layout(title="Net Sales by Category"), 330))
    l, r = st.columns([1, 1.6])
    with l:
        rb = M.by(cur, "Region")
        fig = go.Figure(go.Bar(x=rb["Region"], y=rb["Sales"], marker_color=VIOLET,
                               text=[fmt_money(v) for v in rb["Sales"]], textposition="outside", cliponaxis=False))
        show(style_fig(fig.update_layout(title="Net Sales by Region"), 300))
    with r:
        cg = M.growth_by(cur, prev, "Category").dropna(subset=["Growth"])
        cb = M.by(cur, "Category")
        bullets = []
        if len(mon) >= 2:
            mom = M.pct_change(mon["Sales"].iloc[-1], mon["Sales"].iloc[-2])
            if mom is not None:
                bullets.append(f"Latest month net sales are <b>{mom*100:+.1f}%</b> vs the previous month.")
        if ch["sales"] is not None:
            bullets.append(f"Net sales are <b>{ch['sales']*100:+.1f}%</b> vs the previous period; orders "
                           f"<b>{ch['orders']*100:+.1f}%</b>, while AOV moved <b>{ch['aov']*100:+.1f}%</b>.")
        if not cb.empty:
            bullets.append(f"<b>{cb.iloc[0]['Category']}</b> drives {cb.iloc[0]['Sales']/K['sales']*100:.0f}% of net sales.")
        if not cg.empty:
            w = cg.sort_values("Growth").iloc[0]
            bullets.append(f"Fastest declining category: <b>{w[cg.columns[0]]}</b> ({w['Growth']*100:+.1f}%).")
        panel("Key Findings", "<ul>" + "".join(f"<li>{x}</li>" for x in bullets) + "</ul>"
              "<p><b style='color:" + CYAN + "'>Recommendation:</b> the sales drop is driven by fewer orders, not smaller "
              "baskets - focus on traffic and conversion first, then on the weakest category.</p>")

# =====================================================================
elif page == "Sales Trend":
    mom = M.pct_change(mon["Sales"].iloc[-1], mon["Sales"].iloc[-2]) if len(mon) >= 2 else None
    yoy_prev_start = start - pd.DateOffset(years=1)
    base = df[df["Region"].isin(regions) & df["Category"].isin(cats) & df["CustomerSegment"].isin(segs)]
    ly = M.monthly(base[(base["Month"] >= yoy_prev_start) & (base["Month"] <= end - pd.DateOffset(years=1))])
    yoy = M.pct_change(K["sales"], ly["Sales"].sum()) if not ly.empty else None
    c = st.columns(4)
    c[0].markdown(kpi("MoM Growth (latest month)", f"{mom*100:+.1f}%" if mom is not None else "n/a", None, (CYAN, BLUE)), unsafe_allow_html=True)
    c[1].markdown(kpi("YoY Growth", f"{yoy*100:+.1f}%" if yoy is not None else "n/a", None, (VIOLET, PINK)), unsafe_allow_html=True)
    c[2].markdown(kpi("Avg Order Value", f"{K['aov']:.2f}", ch["aov"], (GREEN, CYAN)), unsafe_allow_html=True)
    c[3].markdown(kpi("Units Sold", f"{K['units']:,}", ch["units"], (AMBER, PINK)), unsafe_allow_html=True)
    st.markdown("")
    fig = go.Figure()
    fig.add_bar(x=mon["Month"], y=mon["Orders"], name="Orders", opacity=0.95,
                marker=dict(color=mon["Orders"], colorscale=[[0, "#5B6CFF"], [0.5, "#A855F7"], [1, "#F472B6"]],
                            line=dict(width=0)))
    fig.add_scatter(x=mon["Month"], y=mon["Sales"], name="Net Sales", mode="lines+markers", yaxis="y2",
                    line=dict(color="#2EE6FF", width=4),
                    marker=dict(size=10, color="#2EE6FF", line=dict(color="#FFFFFF", width=2)))
    fig.update_layout(bargap=0.35, title="Orders (columns) vs Net Sales (line)",
                      yaxis=dict(title="Orders"), yaxis2=dict(title="Net Sales", overlaying="y", side="right", showgrid=False, color=MUTED))
    show(style_fig(fig, 360, legend=True))
    l, r = st.columns(2)
    with l:
        y = M.yoy_by_month(base)
        fig = go.Figure()
        for i, (yr, g) in enumerate(y.groupby("Year")):
            fig.add_bar(x=g["M"].map(lambda m: pd.Timestamp(2000, m, 1).strftime("%b")), y=g["NetSales"],
                        name=str(yr), marker_color=[BLUE, VIOLET, CYAN][i % 3])
        fig.update_layout(barmode="group", title="Net Sales by Month - Year over Year (ignores date filter)")
        show(style_fig(fig, 340, legend=True))
    with r:
        rm = M.region_month(cur)
        rm = rm.loc[rm.sum(axis=1).sort_values(ascending=False).index]   # biggest region on top
        fig = go.Figure(go.Heatmap(
            z=rm.values, x=[pd.Timestamp(c).strftime("%b %y") for c in rm.columns], y=list(rm.index),
            colorscale=SCALE, xgap=3, ygap=3,
            text=[[fmt_money(v) for v in row] for row in rm.values], texttemplate="%{text}",
            textfont=dict(color="#FFFFFF", size=10),
            colorbar=dict(thickness=10, len=0.9, tickfont=dict(color=MUTED), outlinewidth=0),
            hovertemplate="%{y} · %{x}<br>Net Sales: %{z:,.0f}<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=False, tickangle=-45)
        show(style_fig(fig.update_layout(title="Net Sales: Region x Month"), 340))
    st.markdown("<span class='note'>2026 is a partial year (data ends Jun 2026) - compare like-for-like months.</span>", unsafe_allow_html=True)

# =====================================================================
elif page == "Product & Category":
    cg = M.growth_by(cur, prev, "Category").dropna(subset=["Growth"])
    cb = M.by(cur, "Category")
    c = st.columns(2)
    if not cb.empty:
        c[0].markdown(kpi("Top Category", f"{cb.iloc[0]['Category']}", None, (CYAN, VIOLET)).replace("</div></div>",
                       f"</div><div class='d' style='color:{MUTED}'>{fmt_money(cb.iloc[0]['Sales'])} net sales ({cb.iloc[0]['Sales']/K['sales']*100:.0f}%)</div></div>"), unsafe_allow_html=True)
    if not cg.empty:
        w = cg.sort_values("Growth").iloc[0]
        c[1].markdown(kpi("Fastest Declining Category", f"{w['Category']}", w["Growth"], (PINK, AMBER)), unsafe_allow_html=True)
    st.markdown("")
    l, r = st.columns(2)
    with l:
        s = cb.sort_values("Sales")
        fig = go.Figure(go.Bar(x=s["Sales"], y=s["Category"], orientation="h", marker_color=CYAN,
                               text=[fmt_money(v) for v in s["Sales"]], textposition="outside", cliponaxis=False))
        show(style_fig(fig.update_layout(title="Net Sales by Category"), 330))
    with r:
        # one coloured bubble per category + legend (no labels on the bubbles, so nothing can overlap)
        fig = go.Figure()
        ref = 2.0 * max(cb["Orders"].max(), 1) / (44 ** 2)
        for k, (_, row) in enumerate(cb.iterrows()):
            fig.add_trace(go.Scatter(
                x=[row["Sales"]], y=[row["Profit"]], mode="markers", name=row["Category"],
                marker=dict(size=[row["Orders"]], sizemode="area", sizeref=ref, sizemin=12,
                            color=CAT_COLORS[k % len(CAT_COLORS)], opacity=0.92, line=dict(color="#FFFFFF", width=1.5)),
                hovertemplate=f"<b>{row['Category']}</b><br>Net Sales: {row['Sales']:,.0f}<br>Profit: {row['Profit']:,.0f}"
                              f"<br>Orders: {row['Orders']:,.0f}<br>Margin: {row['Margin']*100:.1f}%<extra></extra>"))
        style_fig(fig, 370, legend=True)
        fig.update_layout(title="Net Sales vs Profit (bubble size = orders)", margin=dict(l=14, r=14, t=44, b=60),
                          xaxis=dict(title="Net Sales", range=[0, cb["Sales"].max() * 1.15]),
                          yaxis=dict(title="Profit", range=[0, cb["Profit"].max() * 1.2]),
                          legend=dict(orientation="h", y=-0.32, x=0.5, xanchor="center", font=dict(color=TEXT, size=12)))
        show(fig)
    pr = M.products(cur, prev)
    pr["Product"] = np.where(pr["Growth"] < -0.20, "⚠ " + pr["ProductName"], pr["ProductName"])
    tbl = pr[["Product", "Category", "Sales", "Profit", "Margin", "Growth"]].reset_index(drop=True)
    tbl["Margin"] = tbl["Margin"] * 100
    st.markdown("##### Product matrix  <span class='note'>⚠ = sales down more than 20% vs previous period</span>", unsafe_allow_html=True)
    sty = (tbl.style.format({"Sales": "{:,.0f}", "Profit": "{:,.0f}", "Margin": "{:.1f}", "Growth": "{:+.1%}"})
           .map(lambda v: f"color:{BAD}" if isinstance(v, float) and v < 0 else f"color:{GOOD}", subset=["Growth"])
           .map(lambda v: f"color:{GOOD}", subset=["Profit"]))
    st.dataframe(sty, use_container_width=True, hide_index=True, height=420,
                 column_config={"Margin": st.column_config.ProgressColumn(
                     "Margin %", min_value=0.0, max_value=50.0, format="%.1f%%")})

# =====================================================================
elif page == "Customer Analytics":
    cs, _ = M.customer_stats(cur)
    seg = M.segments(cur)
    c = st.columns(3)
    c[0].markdown(kpi("Total Customers", f"{cs['customers']:,}", None, (CYAN, BLUE)), unsafe_allow_html=True)
    c[1].markdown(kpi("Repeat Customer Rate", f"{cs['repeat']*100:.1f}%", None, (VIOLET, PINK)), unsafe_allow_html=True)
    c[2].markdown(kpi("Avg Revenue / Customer", f"{cs['avg_rev']:.0f}", None, (GREEN, AMBER)), unsafe_allow_html=True)
    st.markdown("")
    l, r = st.columns(2)
    segcol = {"New": CYAN, "Regular": VIOLET, "VIP": PINK}
    with l:
        fig = go.Figure(go.Pie(labels=seg["CustomerSegment"], values=seg["Customers"], hole=.62,
                               marker=dict(colors=[segcol.get(s, BLUE) for s in seg["CustomerSegment"]], line=dict(color=BG, width=2))))
        show(style_fig(fig.update_layout(title="Customers by Segment"), 330, legend=True))
    with r:
        fig = go.Figure(go.Bar(x=seg["CustomerSegment"], y=seg["Sales"], marker_color=[segcol.get(s, BLUE) for s in seg["CustomerSegment"]],
                               text=[fmt_money(v) for v in seg["Sales"]], textposition="outside", cliponaxis=False))
        show(style_fig(fig.update_layout(title="Net Sales by Segment"), 330))
    l, r = st.columns([1.2, 1])
    with l:
        st.markdown("##### Segment table")
        t = seg.rename(columns={"CustomerSegment": "Segment", "AvgRevenue": "Avg revenue"})
        st.dataframe(t.style.format({"Sales": "{:,.0f}", "Avg revenue": "{:,.1f}", "Customers": "{:,}", "Orders": "{:,}"}),
                     hide_index=True, use_container_width=True)
    with r:
        rf = M.rfm(cur)
        if not rf.empty:
            vc = rf["Segment"].value_counts().reindex(["Champions", "Loyal", "At Risk", "Lost"]).fillna(0)
            fig = go.Figure(go.Bar(x=vc.index, y=vc.values, marker_color=[GREEN, CYAN, AMBER, BAD]))
            show(style_fig(fig.update_layout(title="Bonus: RFM segments (quartile scores)"), 300))
    st.markdown("<span class='note'>A repeat rate this high is a sign of synthetic data - mention it as a limitation.</span>", unsafe_allow_html=True)

# =====================================================================
else:
    c = st.columns(4)
    c[0].markdown(kpi("Profit (est.)", fmt_money(K["profit"]), ch["profit"], (VIOLET, PINK)), unsafe_allow_html=True)
    c[1].markdown(kpi("Profit Margin", f"{K['margin']*100:.1f}%", K["margin"] - P["margin"], (AMBER, PINK), pts=True), unsafe_allow_html=True)
    v = cur[cur["IsValidSale"] == 1]
    disc = v["DiscountAmount"].sum() / v["GrossSales"].sum() if v["GrossSales"].sum() else 0
    c[2].markdown(kpi("Avg Discount Rate", f"{disc*100:.1f}%", None, (CYAN, BLUE)), unsafe_allow_html=True)
    leak, leak_n = M.payment_leakage(cur)
    c[3].markdown(kpi("Payment Leakage", fmt_money(leak), None, (BAD, AMBER)), unsafe_allow_html=True)
    st.markdown("")
    l, r = st.columns(2)
    with l:
        cb = M.by(cur, "Category").sort_values("Profit")
        fig = go.Figure(go.Bar(x=cb["Profit"], y=cb["Category"], orientation="h", marker_color=VIOLET,
                               text=[f"{fmt_money(p)}  ({m*100:.0f}%)" for p, m in zip(cb["Profit"], cb["Margin"])],
                               textposition="outside", cliponaxis=False))
        show(style_fig(fig.update_layout(title="Estimated Profit by Category (margin %)"), 330))
    with r:
        db = M.discount_bands(cur)
        fig = go.Figure(go.Bar(x=db["Band"].astype(str), y=db["Margin"], marker_color=[GOOD, CYAN, AMBER, BAD],
                               text=[f"{m*100:.1f}%" for m in db["Margin"]], textposition="outside"))
        show(style_fig(fig.update_layout(title="Profit Margin by Discount Band", yaxis_tickformat=".0%"), 330))
    mm = M.margin_matrix(cur)
    fig = go.Figure(go.Heatmap(z=mm.values * 100, x=list(mm.columns), y=list(mm.index), colorscale=SCALE, zmin=0,
                               xgap=3, ygap=3, text=np.round(mm.values * 100, 1), texttemplate="%{text}%",
                               textfont=dict(color="#FFFFFF", size=11),
                               colorbar=dict(thickness=10, tickfont=dict(color=MUTED), outlinewidth=0)))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False)
    show(style_fig(fig.update_layout(title="Margin %: Region x Category"), 320))
    st.markdown("### Recommendations")
    o, a = ch["orders"], ch["aov"]
    r1, r2, r3 = st.columns(3)
    with r1:
        panel("1 · Win back order volume", f"<p>Orders {o*100:+.1f}% while AOV {a*100:+.1f}% - the problem is traffic/conversion, "
              "not basket size. Run re-engagement campaigns for 'At Risk' customers.</p>", CYAN, "reco")
    with r2:
        worst = db.iloc[-1]
        panel("2 · Cap deep discounts", f"<p>Orders with {worst['Band']} discount earn only <b>{worst['Margin']*100:.1f}%</b> margin vs "
              f"{db.iloc[0]['Margin']*100:.1f}% with no discount. Limit discounts to ~10-15%.</p>", AMBER, "reco")
    with r3:
        panel("3 · Fix payment leakage", f"<p><b>{leak_n:,}</b> completed orders (~{fmt_money(leak)}) did not get paid. "
              "Add payment retries and reminders.</p>", PINK, "reco")
    st.markdown("<span class='note'>Profit is ESTIMATED: the dataset has no cost column, so cost ratios per category were assumed.</span>",
                unsafe_allow_html=True)
