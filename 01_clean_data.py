"""
Step 1 - Data cleaning & star-schema build (raw CSVs -> clean fact + dimension tables)
Run:  python 01_clean_data.py   (needs pandas)
Raw files are READ ONLY. Clean files go to ./data/
"""
import pandas as pd, numpy as np, os
RAW = "raw"            # folder with orders.csv, customers.csv, payments.csv, products.csv
OUT = "data"
os.makedirs(OUT, exist_ok=True)
log = []                                   # data-quality log -> docs/data_quality_report.md
def note(issue, n, action): log.append((issue, n, action))

orders    = pd.read_csv(f"{RAW}/orders.csv")
customers = pd.read_csv(f"{RAW}/customers.csv")
payments  = pd.read_csv(f"{RAW}/payments.csv")
products  = pd.read_csv(f"{RAW}/products.csv")
raw_rows = len(orders)

# ---------- 1. Duplicates ----------
d = orders.duplicated("OrderID").sum()
orders = orders.drop_duplicates("OrderID", keep="first")
note("Duplicate OrderID rows (exact copies)", d, "Removed, kept first")

# ---------- 2. Dates ----------
orders["OrderDate"] = pd.to_datetime(orders["OrderDate"], errors="coerce")
bad = orders["OrderDate"].isna().sum()
orders = orders[orders["OrderDate"].notna()]
note("Missing / invalid OrderDate", bad, "Removed (cannot place order in time)")

# ---------- 3. Quantity ----------
q_null = orders["Quantity"].isna().sum()
q_bad  = (orders["Quantity"] <= 0).sum()
orders = orders[orders["Quantity"].notna() & (orders["Quantity"] > 0)]
note("Missing Quantity", q_null, "Removed")
note("Negative or zero Quantity (invalid)", q_bad, "Removed")

# ---------- 4. Discount ----------
d_null = orders["Discount"].isna().sum()
orders["Discount"] = orders["Discount"].fillna(0)          # assume no discount
note("Missing Discount", d_null, "Filled with 0 (assumed no discount)")
assert orders["Discount"].between(0, 1).all()

# ---------- 5. Payment method ----------
p_null = orders["PaymentMethod"].isna().sum()
orders["PaymentMethod"] = orders["PaymentMethod"].fillna("Unknown")
note("Missing PaymentMethod", p_null, "Labelled 'Unknown'")

# ---------- 6. Customers ----------
c_city_fix = customers["City"].isin(["tehran", "Mashad"]).sum()
customers["City"] = customers["City"].replace({"tehran": "Tehran", "Mashad": "Mashhad"})
note("City spelling inconsistent (tehran, Mashad)", c_city_fix, "Standardised to Tehran / Mashhad")
note("Missing City", customers["City"].isna().sum(), "Labelled 'Unknown'")
customers["City"] = customers["City"].fillna("Unknown")
note("Missing Age", customers["Age"].isna().sum(), "Left blank (not used in KPIs)")
customers["SignupDate"] = pd.to_datetime(customers["SignupDate"])
# Dataset has City only. Region = our own grouping of cities (documented in README)
region_map = {"Tehran":"Central","Karaj":"Central","Qom":"Central","Isfahan":"Central",
              "Mashhad":"East","Kerman":"East","Shiraz":"South","Ahvaz":"South",
              "Tabriz":"North-West","Rasht":"North","Unknown":"Unknown"}
customers["Region"] = customers["City"].map(region_map)

orphan = (~orders["CustomerID"].isin(customers["CustomerID"])).sum()
orders = orders[orders["CustomerID"].isin(customers["CustomerID"])]
note("Orders whose CustomerID is not in customers (e.g. 999999)", orphan, "Removed")

# ---------- 7. Join payments + products ----------
orders = orders.merge(payments[["OrderID", "PaymentStatus"]], on="OrderID", how="left")
orders = orders.merge(products, on="ProductID", how="left")
assert orders["UnitPrice"].notna().all()

# ---------- 8. Cost assumption (dataset has NO cost column) ----------
cost_ratio = {"Accessories":0.55,"Electronics":0.75,"Wearables":0.65,
              "Home Office":0.68,"Stationery":0.50,"Gaming":0.72}
products["CostRatio"] = products["Category"].map(cost_ratio)
products["UnitCost"]  = (products["UnitPrice"] * products["CostRatio"]).round(2)
orders = orders.merge(products[["ProductID","UnitCost"]], on="ProductID")

# ---------- 9. Calculated columns ----------
orders["GrossSales"]     = orders["Quantity"] * orders["UnitPrice"]
orders["DiscountAmount"] = orders["GrossSales"] * orders["Discount"]
orders["NetSalesRaw"]    = orders["GrossSales"] - orders["DiscountAmount"]
orders["TotalCost"]      = orders["Quantity"] * orders["UnitCost"]
# A "valid sale" = order Completed AND payment Paid. Everything else is leakage.
orders["IsValidSale"]    = ((orders["Status"] == "Completed") & (orders["PaymentStatus"] == "Paid")).astype(int)
orders["NetSales"]       = orders["NetSalesRaw"] * orders["IsValidSale"]
orders["Profit"]         = (orders["NetSalesRaw"] - orders["TotalCost"]) * orders["IsValidSale"]
note("Completed orders whose payment is Failed/Refunded",
     ((orders.Status=="Completed") & (orders.PaymentStatus!="Paid")).sum(),
     "Kept in table, excluded from Net Sales (IsValidSale = 0)")

# customer signup after first order (data-logic flag)
first_order = orders.groupby("CustomerID")["OrderDate"].min().rename("FirstOrderDate")
customers = customers.merge(first_order, on="CustomerID", how="left")
note("Customers whose SignupDate is AFTER their first order",
     (customers["SignupDate"] > customers["FirstOrderDate"]).sum(),
     "Kept, flagged. SignupDate not used for KPIs (synthetic-data limitation)")

# ---------- 10. Date dimension ----------
dates = pd.DataFrame({"Date": pd.date_range("2024-01-01", "2026-12-31")})
dates["DateKey"]    = dates["Date"].dt.strftime("%Y%m%d").astype(int)
dates["Year"]       = dates["Date"].dt.year
dates["Quarter"]    = "Q" + dates["Date"].dt.quarter.astype(str)
dates["MonthNum"]   = dates["Date"].dt.month
dates["MonthName"]  = dates["Date"].dt.strftime("%b")
dates["YearMonth"]  = dates["Date"].dt.strftime("%Y-%m")
dates["MonthStart"] = dates["Date"].dt.to_period("M").dt.to_timestamp()
dates["DayOfWeek"]  = dates["Date"].dt.strftime("%a")
dates["WeekdayNum"] = dates["Date"].dt.dayofweek + 1

fact = orders.copy()
fact["DateKey"] = fact["OrderDate"].dt.strftime("%Y%m%d").astype(int)
fact = fact[["OrderID","DateKey","OrderDate","CustomerID","ProductID","Quantity","UnitPrice","UnitCost",
             "Discount","GrossSales","DiscountAmount","NetSalesRaw","TotalCost","NetSales","Profit",
             "Status","PaymentStatus","PaymentMethod","IsValidSale"]]
for col in fact.select_dtypes("float").columns: fact[col] = fact[col].round(2)

fact["Quantity"] = fact["Quantity"].astype(int)          # 4.0 -> 4 (SQL INT friendly)
customers["Age"] = customers["Age"].astype("Int64")      # blank stays blank
fact.to_csv(f"{OUT}/fact_orders.csv", index=False)
customers.drop(columns="FirstOrderDate").to_csv(f"{OUT}/dim_customer.csv", index=False)
products[["ProductID","ProductName","Category","UnitPrice","CostRatio","UnitCost"]].to_csv(f"{OUT}/dim_product.csv", index=False)
dates.to_csv(f"{OUT}/dim_date.csv", index=False)
# single flat file for the Excel step / quick use
fact.merge(customers[["CustomerID","Age","City","Region","CustomerSegment"]], on="CustomerID") \
    .merge(products[["ProductID","ProductName","Category"]], on="ProductID") \
    .to_csv(f"{OUT}/retail_sales_clean.csv", index=False)

# ---------- 11. Report ----------
os.makedirs("docs", exist_ok=True)
with open("docs/data_quality_report.md", "w") as fh:
    fh.write(f"# Data Quality Report\n\nRaw order rows: **{raw_rows:,}** -> clean rows: **{len(fact):,}**\n\n")
    fh.write("| Issue | Rows affected | Action |\n|---|---:|---|\n")
    for i, n, a in log: fh.write(f"| {i} | {int(n):,} | {a} |\n")
print(pd.DataFrame(log, columns=["Issue","Rows","Action"]).to_string(index=False))
print("fact rows:", len(fact), "| valid sales:", fact.IsValidSale.sum())
