"""Keeps the free Streamlit Community Cloud app awake.

Opens the dashboard in a headless browser. If the app has gone to sleep, it clicks
the "Yes, get this app back up!" button, then stays on the page briefly so the visit
counts as real traffic. Run on a schedule by .github/workflows/keep-alive.yml.
"""
from playwright.sync_api import sync_playwright

URL = "https://retail-sales-analytics-9hmxelrt8quhekpdjudupp.streamlit.app/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(8_000)

    wake_button = page.get_by_role("button", name="Yes, get this app back up!")
    if wake_button.count():
        print("App was asleep - waking it up")
        wake_button.first.click()
        page.wait_for_timeout(60_000)
    else:
        print("App is already awake")

    page.wait_for_timeout(15_000)  # stay connected for a moment
    print("Page title:", page.title())
    browser.close()
