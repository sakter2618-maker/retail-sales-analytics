# Data Quality Report

Raw order rows: **50,120** -> clean rows: **49,830**

| Issue | Rows affected | Action |
|---|---:|---|
| Duplicate OrderID rows (exact copies) | 120 | Removed, kept first |
| Missing / invalid OrderDate | 35 | Removed (cannot place order in time) |
| Missing Quantity | 80 | Removed |
| Negative or zero Quantity (invalid) | 25 | Removed |
| Missing Discount | 220 | Filled with 0 (assumed no discount) |
| Missing PaymentMethod | 449 | Labelled 'Unknown' |
| City spelling inconsistent (tehran, Mashad) | 110 | Standardised to Tehran / Mashhad |
| Missing City | 119 | Labelled 'Unknown' |
| Missing Age | 180 | Left blank (not used in KPIs) |
| Orders whose CustomerID is not in customers (e.g. 999999) | 30 | Removed |
| Completed orders whose payment is Failed/Refunded | 3,143 | Kept in table, excluded from Net Sales (IsValidSale = 0) |
| Customers whose SignupDate is AFTER their first order | 5,092 | Kept, flagged. SignupDate not used for KPIs (synthetic-data limitation) |
