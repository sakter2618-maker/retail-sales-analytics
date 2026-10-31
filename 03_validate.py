"""Independent validation: recompute headline numbers with pandas AND by hand on sample orders,
then compare with the SQL/DAX definitions."""
import pandas as pd, sqlite3
f=pd.read_csv("data/fact_orders.csv"); c=pd.read_csv("data/dim_customer.csv")
p=pd.read_csv("data/dim_product.csv"); d=pd.read_csv("data/dim_date.csv")
v=f[f.IsValidSale==1]
print("=== A. HAND CHECK on 3 sample orders (Quantity x UnitPrice x (1-Discount); cost = Qty x UnitCost)")
for oid in v.OrderID.head(3):
    r=f[f.OrderID==oid].iloc[0]
    net=r.Quantity*r.UnitPrice*(1-r.Discount); prof=net-r.Quantity*r.UnitCost
    print(f"Order {oid}: {r.Quantity:.0f} x {r.UnitPrice} x (1-{r.Discount}) = {net:.2f} | file NetSales={r.NetSales} | profit {prof:.2f} vs file {r.Profit}")
    assert abs(net-r.NetSales)<0.02 and abs(prof-r.Profit)<0.02
print("\n=== B. HEADLINE KPIs (pandas)")
ns,pr=v.NetSales.sum(),v.Profit.sum()
print(f"Net Sales {ns:,.2f} | Profit {pr:,.2f} | Margin {pr/ns:.2%} | Orders {v.OrderID.nunique():,} | AOV {ns/v.OrderID.nunique():.2f} | Units {v.Quantity.sum():,.0f}")
print(f"Total discount given (valid sales) {v.DiscountAmount.sum():,.2f}")
cu=v.groupby("CustomerID").size()
print(f"Customers {len(cu):,} | Repeat {int((cu>=2).sum()):,} | Repeat rate {(cu>=2).mean():.2%} | Rev/customer {ns/len(cu):.2f}")
print("\n=== C. SAME NUMBERS FROM SQL (SQLite engine)")
con=sqlite3.connect(":memory:")
for n,df in [("fact_orders",f),("dim_customer",c),("dim_product",p),("dim_date",d)]: df.to_sql(n,con,index=False)
q=con.execute("SELECT ROUND(SUM(NetSales),2),ROUND(SUM(Profit),2),SUM(IsValidSale) FROM fact_orders").fetchone()
print("SQL:",q); assert abs(q[0]-ns)<0.05 and q[2]==v.OrderID.nunique()
print("\n=== D. MoM / YoY spot check")
m=v.merge(d[["DateKey","YearMonth","Year"]],on="DateKey").groupby("YearMonth").NetSales.sum()
print("Feb-2026 MoM:", f"{(m['2026-02']/m['2026-01']-1):.2%}", "| Jan-Jun 2026 vs Jan-Jun 2025 YTD:",
      f"{m['2026-01':'2026-06'].sum()/m['2025-01':'2025-06'].sum()-1:.2%}")
print("2025 vs 2024:", f"{m['2025-01':'2025-12'].sum()/m['2024-01':'2024-12'].sum()-1:.2%}")
print("Best month:", m.idxmax(), round(m.max(),2), "| Worst month:", m.idxmin(), round(m.min(),2))
print("ALL CHECKS PASSED")
