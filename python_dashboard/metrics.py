"""Pure-pandas data layer for the dashboard (no Streamlit/Plotly needed -> easy to test)."""
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"


def load():
    f = pd.read_csv(DATA / "fact_orders.csv", parse_dates=["OrderDate"])
    c = pd.read_csv(DATA / "dim_customer.csv")[["CustomerID", "City", "CustomerSegment", "Region"]]
    p = pd.read_csv(DATA / "dim_product.csv")[["ProductID", "ProductName", "Category"]]
    df = f.merge(c, on="CustomerID", how="left").merge(p, on="ProductID", how="left")
    df["Region"] = df["Region"].fillna("Unknown")
    df["Month"] = df["OrderDate"].dt.to_period("M").dt.to_timestamp()
    return df


def apply_filters(df, start, end, regions, cats, segs):
    """start/end are month-start Timestamps (inclusive). Returns (current, previous) frames."""
    n = (end.year - start.year) * 12 + (end.month - start.month) + 1
    p_end = start - pd.offsets.MonthBegin(1)
    p_start = start - pd.offsets.MonthBegin(n)
    base = df[df["Region"].isin(regions) & df["Category"].isin(cats) & df["CustomerSegment"].isin(segs)]
    cur = base[(base["Month"] >= start) & (base["Month"] <= end)]
    prev = base[(base["Month"] >= p_start) & (base["Month"] <= p_end)]
    return cur, prev


def kpis(d):
    v = d[d["IsValidSale"] == 1]
    sales, profit, orders, units = v["NetSales"].sum(), v["Profit"].sum(), v["OrderID"].nunique(), v["Quantity"].sum()
    return dict(sales=sales, profit=profit, orders=orders, units=units,
                margin=profit / sales if sales else 0, aov=sales / orders if orders else 0)


def pct_change(cur, prev):
    return None if not prev else (cur - prev) / prev


def monthly(d):
    v = d[d["IsValidSale"] == 1]
    return (v.groupby("Month").agg(Sales=("NetSales", "sum"), Profit=("Profit", "sum"),
                                   Orders=("OrderID", "nunique"), Units=("Quantity", "sum"))
              .reset_index())


def by(d, col):
    v = d[d["IsValidSale"] == 1]
    g = v.groupby(col).agg(Sales=("NetSales", "sum"), Profit=("Profit", "sum"),
                           Orders=("OrderID", "nunique"), Units=("Quantity", "sum")).reset_index()
    g["Margin"] = np.where(g["Sales"] > 0, g["Profit"] / g["Sales"], 0)
    return g.sort_values("Sales", ascending=False)


def growth_by(cur, prev, col):
    a = by(cur, col)[[col, "Sales"]].rename(columns={"Sales": "Cur"})
    b = by(prev, col)[[col, "Sales"]].rename(columns={"Sales": "Prev"})
    m = a.merge(b, on=col, how="left").fillna({"Prev": 0})
    m["Growth"] = np.where(m["Prev"] > 0, (m["Cur"] - m["Prev"]) / m["Prev"], np.nan)
    return m


def yoy_by_month(df_filtered_all_dates):
    v = df_filtered_all_dates[df_filtered_all_dates["IsValidSale"] == 1].copy()
    v["Year"], v["M"] = v["Month"].dt.year, v["Month"].dt.month
    return v.groupby(["M", "Year"])["NetSales"].sum().reset_index()


def region_month(d):
    v = d[d["IsValidSale"] == 1]
    return v.pivot_table(index="Region", columns="Month", values="NetSales", aggfunc="sum", fill_value=0)


def segments(d):
    v = d[d["IsValidSale"] == 1]
    g = v.groupby("CustomerSegment").agg(Customers=("CustomerID", "nunique"), Sales=("NetSales", "sum"),
                                         Orders=("OrderID", "nunique")).reset_index()
    g["AvgRevenue"] = g["Sales"] / g["Customers"]
    return g


def customer_stats(d):
    v = d[d["IsValidSale"] == 1]
    per = v.groupby("CustomerID").agg(Orders=("OrderID", "nunique"), Sales=("NetSales", "sum"),
                                      Last=("OrderDate", "max"))
    n = len(per)
    return dict(customers=n, repeat=(per["Orders"] > 1).mean() if n else 0,
                avg_rev=per["Sales"].mean() if n else 0), per


def rfm(d):
    _, per = customer_stats(d)
    if per.empty:
        return per.assign(Segment=[])
    ref = d["OrderDate"].max()
    per = per.assign(Recency=(ref - per["Last"]).dt.days)
    r = pd.qcut(per["Recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    f = pd.qcut(per["Orders"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    m = pd.qcut(per["Sales"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    s = r + f + m
    per["Segment"] = pd.cut(s, [0, 4, 7, 9, 12], labels=["Lost", "At Risk", "Loyal", "Champions"])
    return per


def discount_bands(d):
    v = d[d["IsValidSale"] == 1].copy()
    v["Band"] = pd.cut(v["Discount"], [-0.001, 0.0, 0.10, 0.20, 1.0],
                       labels=["No discount", "1-10%", "11-20%", "21%+"])
    g = v.groupby("Band", observed=True).agg(Sales=("NetSales", "sum"), Profit=("Profit", "sum"),
                                              Orders=("OrderID", "nunique")).reset_index()
    g["Margin"] = np.where(g["Sales"] > 0, g["Profit"] / g["Sales"], 0)
    return g


def margin_matrix(d):
    v = d[d["IsValidSale"] == 1]
    s = v.pivot_table(index="Region", columns="Category", values="NetSales", aggfunc="sum")
    p = v.pivot_table(index="Region", columns="Category", values="Profit", aggfunc="sum")
    return (p / s)


def payment_leakage(d):
    x = d[(d["Status"] == "Completed") & (d["PaymentStatus"] != "Paid")]
    return x["NetSalesRaw"].sum(), x["OrderID"].nunique()


def products(cur, prev):
    a = by(cur, "ProductName")
    g = growth_by(cur, prev, "ProductName")[["ProductName", "Growth"]]
    cat = cur.drop_duplicates("ProductName").set_index("ProductName")["Category"]
    a = a.merge(g, on="ProductName", how="left")
    a["Category"] = a["ProductName"].map(cat)
    return a
