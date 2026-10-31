-- =====================================================================
-- Retail Analytics | SQL layer  (portable: PostgreSQL / MySQL 8+ / SQLite)
-- Tables: fact_orders, dim_customer, dim_product, dim_date
-- Business rule: Net Sales / Profit count ONLY valid sales (IsValidSale = 1)
--                = Status 'Completed' AND PaymentStatus 'Paid'
-- =====================================================================

-- ---------- 0. SCHEMA (PostgreSQL syntax; load CSVs with \copy or Import Wizard) ----------
CREATE TABLE dim_product  (ProductID INT PRIMARY KEY, ProductName VARCHAR(60), Category VARCHAR(30),
                           UnitPrice DECIMAL(10,2), CostRatio DECIMAL(4,2), UnitCost DECIMAL(10,2));
CREATE TABLE dim_customer (CustomerID INT PRIMARY KEY, Age INT, City VARCHAR(30), SignupDate DATE,
                           CustomerSegment VARCHAR(20), Region VARCHAR(20));
CREATE TABLE dim_date     (Date DATE, DateKey INT PRIMARY KEY, Year INT, Quarter VARCHAR(2), MonthNum INT,
                           MonthName VARCHAR(3), YearMonth VARCHAR(7), MonthStart DATE, DayOfWeek VARCHAR(3), WeekdayNum INT);
CREATE TABLE fact_orders  (OrderID INT PRIMARY KEY, DateKey INT REFERENCES dim_date(DateKey), OrderDate DATE,
                           CustomerID INT REFERENCES dim_customer(CustomerID), ProductID INT REFERENCES dim_product(ProductID),
                           Quantity INT, UnitPrice DECIMAL(10,2), UnitCost DECIMAL(10,2), Discount DECIMAL(4,2),
                           GrossSales DECIMAL(12,2), DiscountAmount DECIMAL(12,2), NetSalesRaw DECIMAL(12,2),
                           TotalCost DECIMAL(12,2), NetSales DECIMAL(12,2), Profit DECIMAL(12,2),
                           Status VARCHAR(15), PaymentStatus VARCHAR(10), PaymentMethod VARCHAR(15), IsValidSale SMALLINT);
-- PostgreSQL load example:
-- \copy fact_orders FROM 'data/fact_orders.csv' CSV HEADER;

-- ---------- 0b. DATA CHECKS ----------
-- Q0. Row counts + orphan keys (all should be 0 orphans)
SELECT (SELECT COUNT(*) FROM fact_orders) AS fact_rows,
       (SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_customer c ON c.CustomerID=f.CustomerID WHERE c.CustomerID IS NULL) AS orphan_customers,
       (SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_product  p ON p.ProductID =f.ProductID  WHERE p.ProductID  IS NULL) AS orphan_products,
       (SELECT COUNT(*) - COUNT(DISTINCT OrderID) FROM fact_orders) AS duplicate_orders;

-- ---------- Q1. MONTHLY SALES TREND (+ MoM growth) ----------
WITH m AS (
  SELECT d.YearMonth, SUM(f.NetSales) AS net_sales, SUM(f.Profit) AS profit,
         SUM(f.IsValidSale) AS orders, SUM(CASE WHEN f.IsValidSale=1 THEN f.Quantity ELSE 0 END) AS units
  FROM fact_orders f JOIN dim_date d ON d.DateKey = f.DateKey
  GROUP BY d.YearMonth)
SELECT YearMonth, ROUND(net_sales,2) AS net_sales, orders, units,
       ROUND(net_sales*1.0/NULLIF(orders,0),2) AS aov,
       ROUND((net_sales - LAG(net_sales) OVER (ORDER BY YearMonth)) * 100.0
             / NULLIF(LAG(net_sales) OVER (ORDER BY YearMonth),0), 2) AS mom_growth_pct
FROM m ORDER BY YearMonth;

-- ---------- Q2. TOP 10 PRODUCTS BY NET SALES ----------
SELECT p.ProductName, p.Category, SUM(f.IsValidSale*f.Quantity) AS units,
       ROUND(SUM(f.NetSales),2) AS net_sales, ROUND(SUM(f.Profit),2) AS profit,
       ROUND(SUM(f.Profit)*100.0/NULLIF(SUM(f.NetSales),0),2) AS margin_pct
FROM fact_orders f JOIN dim_product p ON p.ProductID=f.ProductID
GROUP BY p.ProductName, p.Category
ORDER BY net_sales DESC LIMIT 10;

-- Q2b. High revenue but low margin (below overall margin) -> pricing/discount problem
WITH prod AS (
  SELECT p.ProductName, SUM(f.NetSales) AS ns, SUM(f.Profit) AS pr
  FROM fact_orders f JOIN dim_product p ON p.ProductID=f.ProductID GROUP BY p.ProductName)
SELECT ProductName, ROUND(ns,2) AS net_sales, ROUND(pr*100.0/ns,2) AS margin_pct
FROM prod
WHERE ns > (SELECT AVG(ns) FROM prod) AND pr*1.0/ns < (SELECT SUM(pr)*1.0/SUM(ns) FROM prod)
ORDER BY margin_pct;

-- ---------- Q3. CATEGORY-WISE PROFIT ----------
SELECT p.Category, ROUND(SUM(f.NetSales),2) AS net_sales, ROUND(SUM(f.Profit),2) AS profit,
       ROUND(SUM(f.Profit)*100.0/NULLIF(SUM(f.NetSales),0),2) AS margin_pct,
       ROUND(SUM(f.DiscountAmount*f.IsValidSale)*100.0/NULLIF(SUM(f.GrossSales*f.IsValidSale),0),2) AS discount_pct
FROM fact_orders f JOIN dim_product p ON p.ProductID=f.ProductID
GROUP BY p.Category ORDER BY profit DESC;

-- ---------- Q4. REPEAT CUSTOMER ANALYSIS ----------
WITH cust AS (
  SELECT CustomerID, COUNT(*) AS orders, SUM(NetSales) AS spend
  FROM fact_orders WHERE IsValidSale=1 GROUP BY CustomerID)
SELECT COUNT(*) AS total_customers,
       SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END) AS repeat_customers,
       ROUND(SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS repeat_rate_pct,
       ROUND(SUM(spend)/COUNT(*),2) AS avg_revenue_per_customer
FROM cust;

-- Q4b. Repeat rate by the dataset's own segment (New / Regular / VIP)
WITH cust AS (
  SELECT f.CustomerID, c.CustomerSegment, COUNT(*) AS orders, SUM(f.NetSales) AS spend
  FROM fact_orders f JOIN dim_customer c ON c.CustomerID=f.CustomerID
  WHERE f.IsValidSale=1 GROUP BY f.CustomerID, c.CustomerSegment)
SELECT CustomerSegment, COUNT(*) AS customers, SUM(orders) AS orders, ROUND(SUM(spend),2) AS net_sales,
       ROUND(SUM(spend)/COUNT(*),2) AS avg_spend,
       ROUND(SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS repeat_rate_pct
FROM cust GROUP BY CustomerSegment ORDER BY net_sales DESC;

-- Q4c. RFM segmentation (reference date = day after last order)
WITH ref AS (SELECT MAX(OrderDate) AS max_d FROM fact_orders),
rfm AS (
  SELECT f.CustomerID,
         (SELECT MAX(OrderDate) FROM fact_orders) AS max_d,
         MAX(f.OrderDate) AS last_order, COUNT(*) AS frequency, SUM(f.NetSales) AS monetary
  FROM fact_orders f WHERE f.IsValidSale=1 GROUP BY f.CustomerID),
scored AS (
  SELECT CustomerID, frequency, monetary,
         NTILE(4) OVER (ORDER BY last_order)  AS r_score,   -- 4 = most recent
         NTILE(4) OVER (ORDER BY frequency)   AS f_score,
         NTILE(4) OVER (ORDER BY monetary)    AS m_score
  FROM rfm)
SELECT CASE WHEN r_score>=3 AND f_score>=3 AND m_score>=3 THEN 'High Value'
            WHEN r_score<=2 AND (f_score>=3 OR m_score>=3)  THEN 'At Risk'
            WHEN r_score<=2                                  THEN 'Lost / Low'
            ELSE 'Regular' END AS rfm_segment,
       COUNT(*) AS customers, ROUND(SUM(monetary),2) AS net_sales
FROM scored GROUP BY 1 ORDER BY net_sales DESC;

-- ---------- Q5. SALES GROWTH BY REGION (2025 vs 2024, full years) ----------
WITH r AS (
  SELECT c.Region, d.Year, SUM(f.NetSales) AS ns
  FROM fact_orders f JOIN dim_customer c ON c.CustomerID=f.CustomerID JOIN dim_date d ON d.DateKey=f.DateKey
  WHERE d.Year IN (2024,2025) GROUP BY c.Region, d.Year)
SELECT a.Region, ROUND(a.ns,2) AS sales_2024, ROUND(b.ns,2) AS sales_2025,
       ROUND((b.ns-a.ns)*100.0/a.ns,2) AS yoy_growth_pct
FROM r a JOIN r b ON a.Region=b.Region AND a.Year=2024 AND b.Year=2025
ORDER BY yoy_growth_pct DESC;

-- ---------- Q6. DISCOUNT vs PROFIT ----------
SELECT CAST(f.Discount*100 AS INT) AS discount_pct, SUM(f.IsValidSale) AS orders,
       ROUND(SUM(f.NetSales),2) AS net_sales, ROUND(SUM(f.Profit),2) AS profit,
       ROUND(SUM(f.Profit)*100.0/NULLIF(SUM(f.NetSales),0),2) AS margin_pct
FROM fact_orders f GROUP BY CAST(f.Discount*100 AS INT) ORDER BY discount_pct;

-- Q6b. Category x Discount margin (where does discounting destroy profit?)
SELECT p.Category, CAST(f.Discount*100 AS INT) AS discount_pct,
       ROUND(SUM(f.Profit)*100.0/NULLIF(SUM(f.NetSales),0),2) AS margin_pct
FROM fact_orders f JOIN dim_product p ON p.ProductID=f.ProductID
GROUP BY p.Category, CAST(f.Discount*100 AS INT) ORDER BY p.Category, discount_pct;

-- ---------- Q7. ORDER LEAKAGE (cancelled / returned / failed payment) ----------
SELECT Status, PaymentStatus, COUNT(*) AS orders, ROUND(SUM(NetSalesRaw),2) AS lost_potential_sales
FROM fact_orders WHERE IsValidSale=0 GROUP BY Status, PaymentStatus ORDER BY lost_potential_sales DESC;
