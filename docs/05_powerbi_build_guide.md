# Power BI Build Guide (beginner friendly)

## PART A — Dataset: field meanings
| Table | Field | Business meaning |
|---|---|---|
| orders | OrderID | One order line (1 product per order in this data). Primary key |
| | CustomerID / ProductID | Who bought / what was bought |
| | OrderDate | When the order was placed |
| | Quantity | Units bought |
| | Discount | Fraction off list price (0.10 = 10%) |
| | PaymentMethod | Gateway, Wallet, CardToCard, Cash |
| | Status | Completed, Cancelled, Returned |
| payments | PaymentStatus | Paid, Failed, Refunded |
| customers | Age, City, SignupDate | Customer profile |
| | CustomerSegment | New, Regular, VIP (given by the dataset) |
| products | Category, UnitPrice | Product group, list price |
| **added by us** | Region | Our grouping of the 10 cities (Central, East, South, North-West, North) |
| | UnitCost / CostRatio | **ASSUMED** cost (dataset has no cost column) |
| | NetSales, Profit, IsValidSale | Calculated in `01_clean_data.py` |

**Net Sales rule:** Quantity × UnitPrice × (1 − Discount), counted only if Status = Completed AND PaymentStatus = Paid.

## PART B — Star schema
```
dim_date (DateKey) 1 ───< fact_orders >─── 1 dim_product (ProductID)
                              │
                              └─── 1 dim_customer (CustomerID)
```
All relationships: one-to-many, single direction (dimension → fact).

## PART C — Import steps
1. Power BI Desktop → **Get Data → Text/CSV** → import the 4 files in `/data` (fact_orders, dim_customer, dim_product, dim_date). Click **Transform Data**.
2. Power Query: set types — OrderDate/Date/SignupDate = Date; Quantity, IsValidSale = Whole number; money columns = Fixed decimal; text columns = Text. **Close & Apply**.
3. **Model view**: drag dim_date[DateKey] → fact_orders[DateKey], same for CustomerID and ProductID. Hide key columns in fact (right-click → Hide in report view).
4. Select dim_date → **Table tools → Mark as date table** → column `Date`.
5. In dim_date set **Sort by column**: MonthName by MonthNum, DayOfWeek by WeekdayNum.
6. **Home → Enter data** → create empty table `_Measures`; paste measures from `04_dax_measures.dax` one by one (New measure).
7. **View → Themes → Browse for themes** → `retail_theme.json`.

## PART D — Canvas, navigation bar, slicers (do once, then copy to every page)
* Page size: **View → Page view → Fit**; Format page → Canvas settings → 16:9 (1280×720).
* **Top bar (height 64 px):** Insert → Shapes → Rectangle, fill `#131A33`, round corners. Left: text box "RETAIL ANALYTICS" (white, 16 pt bold) + small teal dot.
* **5 navigation buttons:** Insert → Buttons → Blank. Text = page name; Style → Fill `#131A33`, Border `#2A3355`, radius 20. Set **Action → Type = Page navigation → Destination = that page**. Active-page look: Style → Apply settings to = **Selected** → Fill `#22D3EE`, text `#0B1020`.
* Make the bar on page 1, group it (Ctrl+G), copy-paste to the other 4 pages, and change which button is "selected" on each page.
* **Slicer row (under the bar):** Date (Between, style Between slider), Region (Dropdown), Category (Dropdown), Customer Segment (Tile/Dropdown). Copy them to every page: **View → Sync slicers** → tick all 5 pages for each slicer.
* **KPI card pattern:** Card visual → Callout = measure; add the "vs previous" measure to the same card as *Reference label* (Format → Reference labels) or use *Multi-row card*. Colour via **Conditional formatting → Font colour → Rules** (≥0 green `#22D3A6`, <0 red `#FF5C7A`).

---
## PART E — The 5 pages (exact visuals)

### Page 1 · Executive Overview — "Business performance kemon?"
| Position | Visual | Fields | Notes |
|---|---|---|---|
| Top row (4 cards) | Card ×4 | Net Sales / Profit / Total Orders / Profit Margin % + each `… vs Prev %` + Arrow Text | Sparkline: in Table/Matrix use *Add a sparkline* (Month) if you prefer |
| Middle-left (wide) | **Line chart** | X = dim_date[YearMonth]; Y = Net Sales; Secondary = Net Sales PY (optional) | Smooth line, area shading |
| Middle-right | **Clustered bar (horizontal)** | Y = dim_product[Category]; X = Net Sales | Sort descending, data labels on |
| Bottom-left | **Filled map / Bar** | Region × Net Sales | Cities are in Iran; Bing map may mis-plot → use bar chart |
| Bottom-right | **Card/Text** "Key Business Findings" | Finding 1, Finding 2, Finding 3 (measures) + 1 text box recommendation | Updates with slicers |

### Page 2 · Sales Trend Analysis — "Sales barche na komche?"
| Section | Visual | Fields |
|---|---|---|
| Top cards | Card ×4 | Net Sales MoM %, Net Sales YoY %, Average Order Value, Units Sold |
| Middle | Line chart | YearMonth × Net Sales (+ Total Orders on secondary axis → shows *sales vs order count*) |
| Bottom-left | Clustered column | Month (MonthName) × Net Sales, Legend = Year (YoY compare) |
| Bottom-right | **Matrix** | Rows = Region, Columns = YearMonth (or MonthName), Values = Net Sales; Conditional formatting → Background colour scale |
Business answers: best month (`Best Month` card), MoM drops (colour bars by `Growth Color`), fastest region (Matrix + YoY%), "sales or only orders?" (Orders vs AOV lines).

### Page 3 · Product & Category — "Kon product bhalo / kharap?"
| Visual | Fields |
|---|---|
| Card: Top Category | `Top Category` |
| Card: Lowest Margin Category | `Lowest Margin Category` |
| Horizontal bar | Category × Net Sales (click = cross-filters the matrix) |
| **Matrix** (Product Performance) | Rows = ProductName; Values = Net Sales, Units Sold, Profit, Profit Margin %, Net Sales MoM %. Conditional formatting: Profit/Growth font colour green ≥0 / red <0; Margin data bars |
| **Scatter** | Details = ProductName; X = Net Sales; Y = Profit; Size = Units Sold; Legend = Category |
| Top-10 / Bottom-10 | Bar chart, Visual filter **Top N** (10, by Net Sales) and another **Bottom N** |
| Problem list | Table: ProductName, Net Sales, Profit Margin %, `Problem Product Flag` |
Drill-through: create page "Product Details" → add ProductName to **Drill-through** well → right-click any product → Drill through.
Tooltip page: new page → Page info → *Allow use as tooltip* → add Net Sales, Profit, Units Sold, MoM %; set in visual Format → Tooltips → Type = Report page.

### Page 4 · Customer Analytics — "Kon customer valuable?"
| Visual | Fields |
|---|---|
| Cards ×3 | Total Customers, Repeat Customer Rate %, Avg Revenue per Customer |
| Donut | Legend = CustomerSegment; Values = Net Sales |
| Bar | CustomerSegment × Net Sales (or Avg Revenue per Customer) |
| Matrix | Rows = CustomerSegment; Values = Total Customers, Net Sales, Total Orders, Avg Revenue per Customer, Repeat Customer Rate % |
| (Bonus) RFM | Import result of SQL Q4c as table `rfm_segments`, bar chart by rfm_segment |
**Important:** the dataset already has a segment (New / Regular / VIP) → use it directly; RFM is a bonus.

### Page 5 · Profit & Recommendations — "Profit kothay barano jabe?"
| Visual | Fields |
|---|---|
| Cards ×3 | Profit, Profit Margin %, Total Discount |
| Bar | Category × Profit |
| Scatter | ProductName; X = Net Sales; Y = Profit Margin %; Size = Total Discount |
| Matrix | Rows = Region, Columns = Category, Values = Profit Margin % (colour scale red→green) |
| Discount analysis | Column + line: X = Discount (as %), columns = Net Sales, line = Profit Margin % → create calculated column `Discount Band = FORMAT(fact_orders[Discount],"0%")` |
| Bottom | 3 rounded text boxes with recommendation + a metric card each (see README findings) |

## PART F — Interactions test (Edit interactions)
Select a slicer → **Format → Edit interactions** → check that every chart has the "filter" icon (not "none"). Keep cards/KPI of *previous period* unfiltered by Date only if you need fixed comparison. Test: pick Region = South → all charts must change.

## PART G — Design tips (look "trending")
* Dark navy canvas + neon accent (cyan/violet/pink) = the `retail_theme.json`.
* Rounded cards (radius 12–16), no gridlines, thin 1 px border, 16 px padding, same left edge for all visuals (use Align + Distribute).
* Max 3 colours per chart; red/green only for good/bad. Big numbers (28 pt), small grey labels (10 pt).
* Title every visual with a **question or insight**, e.g. "Orders fell, AOV did not" (use a measure for dynamic titles).
* Add Bookmarks "Reset filters" (button with 🔄) → Insert → Buttons → Bookmark.
