# Python Dashboard (Streamlit + Plotly)

Same 5 pages and neon-dark theme as the Power BI report, built from the cleaned CSVs in `../data`.

```bash
cd python_dashboard
pip install -r requirements.txt
streamlit run app.py
```

- `metrics.py` - all calculations (pandas only, no UI)
- `app.py` - layout, charts, navigation, filters
- Filters: month range, Region, Category, Segment. "Previous period" = same-length window right before the selection.
- Profit is estimated (assumed category cost ratios). Region is derived from city.
