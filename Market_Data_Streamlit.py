import streamlit as st
import pandas as pd
import yfinance as yf
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

nest_asyncio.apply()

# Title of the app
st.title("Enhanced Stock Data Processor with Web Scraping")

# File uploader
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

# Async scraping functions
async def scrape_nyse_noncompliant_issuers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.nyse.com/regulation/noncompliant-issuers")
        await page.wait_for_selector("table tbody tr")

        rows = await page.query_selector_all("table tbody tr")
        data = []

        for row in rows:
            issuer = await row.query_selector("td:nth-child(1)")
            symbols = await row.query_selector_all("td:nth-child(2) span")
            deficiency = await row.query_selector("td:nth-child(4)")
            date = await row.query_selector("td:nth-child(5)")

            issuer_text = await issuer.text_content() if issuer else None
            symbols_text = [await span.text_content() for span in symbols]
            deficiency_text = await deficiency.text_content() if deficiency else None
            date_text = await date.text_content() if date else None

            for symbol in symbols_text:
                data.append({
                    "Issuer": issuer_text.strip(),
                    "Symbol": symbol.strip(),
                    "Deficiency": deficiency_text.strip(),
                    "Date": date_text.strip(),
                    "Link": "https://www.nyse.com/regulation/noncompliant-issuers"
                })

        await browser.close()
        return pd.DataFrame(data)

async def scrape_nyse_delistings():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.nyse.com/regulation/delistings")
        await page.wait_for_selector("table tbody tr")

        rows = await page.query_selector_all("table tbody tr")
        data = []

        for row in rows:
            issuer = await row.query_selector("td:nth-child(1)")
            symbol_td = await row.query_selector("td:nth-child(2)")
            initiation = await row.query_selector("td:nth-child(3)")
            notification_date = await row.query_selector("td:nth-child(4)")

            symbols_text = []
            if symbol_td:
                symbols_spans = await symbol_td.query_selector_all("span")
                symbols_text = [await span.text_content() for span in symbols_spans]

            for symbol in symbols_text:
                data.append({
                    "Issuer": (await issuer.text_content()).strip() if issuer else "N/A",
                    "Symbol": symbol.strip(),
                    "Initiation": (await initiation.text_content()).strip() if initiation else "N/A",
                    "Notification Date": (await notification_date.text_content()).strip() if notification_date else "N/A",
                    "Link": "https://www.nyse.com/regulation/delistings"
                })

        await browser.close()
        return pd.DataFrame(data)

async def scrape_nasdaq_pending_suspension():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://listingcenter.nasdaq.com/IssuersPendingSuspensionDelisting.aspx")
        await page.wait_for_load_state('networkidle')

        data = []

        while True:
            rows = await page.query_selector_all("tbody tr.rgRow, tbody tr.rgAltRow")
            for row in rows:
                symbol = await row.query_selector("td:nth-child(2)")
                reason = await row.query_selector("td:nth-child(3)")
                effective_date = await row.query_selector("td:nth-child(5)")

                data.append({
                    "Symbol": (await symbol.text_content()).strip(),
                    "Deficiency": (await reason.text_content()).strip(),
                    "Date": (await effective_date.text_content()).strip(),
                    "Link": "https://listingcenter.nasdaq.com/IssuersPendingSuspensionDelisting.aspx"
                })

            next_button = await page.query_selector("a.rgPageNext")
            if next_button and await next_button.is_enabled():
                await next_button.click()
                await page.wait_for_load_state('networkidle')
            else:
                break

        await browser.close()
        return pd.DataFrame(data)

async def scrape_threshold_security_list():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.nasdaqtrader.com/trader.aspx?id=regshothreshold")
        await page.wait_for_selector("table tbody tr")

        rows = await page.query_selector_all("table tbody tr")
        data = []

        for row in rows:
            symbol = await row.query_selector("td:nth-child(1)")
            reason = await row.query_selector("td:nth-child(3)")
            date_added = await row.query_selector("td:nth-child(4)")

            data.append({
                "Symbol": (await symbol.text_content()).strip(),
                "Deficiency": (await reason.text_content()).strip(),
                "Date": (await date_added.text_content()).strip(),
                "Link": "https://www.nasdaqtrader.com/trader.aspx?id=regshothreshold"
            })

        await browser.close()
        return pd.DataFrame(data)

def download_nasdaq_noncompliant_file(download_dir="C:/Users/40-366/Downloads"):
    # URL of the page
    url = "https://listingcenter.nasdaq.com/noncompliantcompanylist.aspx"

    # Headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    # Initial GET request to fetch the viewstate and eventvalidation tokens
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Ensure request was successful
    html_content = response.text

    # Parse __VIEWSTATE and __EVENTVALIDATION from the HTML
    soup = BeautifulSoup(html_content, "html.parser")
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    event_validation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]

    # Prepare the POST data to mimic the __doPostBack
    post_data = {
        "__EVENTTARGET": "ctl00$MainContent$btnExport",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": event_validation,
    }

    # POST request to trigger the download
    download_response = requests.post(url, headers=headers, data=post_data)
    download_response.raise_for_status()  # Ensure request was successful

    # Save the downloaded content as a CSV
    save_path = os.path.join(download_dir, "nasdaq_noncompliant_export.csv")
    with open(save_path, "wb") as file:
        file.write(download_response.content)
    print(f"File downloaded and saved to {save_path}")

    # Load the CSV file
    df = pd.read_csv(save_path)

    # Split the 'Affected Issues' column by spaces into lists
    df['Affected Issues'] = df['Affected Issues'].str.split()

    # Explode the lists to create new rows
    df = df.explode('Affected Issues')

    # Save the modified DataFrame to a new CSV
    output_path = os.path.join(download_dir, "modified_nasdaq_noncompliant_export.csv")
    df.to_csv(output_path, index=False)

    print(f"File processed and saved to {output_path}")
    print("3. nasdaq_noncompliant_df completed")
    print(" ")

    # Return the DataFrame
    return df


async def main_scraping():
    nyse_noncompliant_df = await scrape_nyse_noncompliant_issuers()
    nyse_delistings_df = await scrape_nyse_delistings()
    nasdaq_noncompliant_df = download_nasdaq_noncompliant_file()  
    nasdaq_pending_suspension_df = await scrape_nasdaq_pending_suspension()
    threshold_security_list_df = await scrape_threshold_security_list()

    combined_df = pd.concat(
        [nyse_noncompliant_df, nyse_delistings_df, nasdaq_pending_suspension_df, threshold_security_list_df],
        ignore_index=True
    )
    return combined_df

# Process stock data
def process_data(uploaded_file):
    stocks_df = pd.read_excel(uploaded_file)
    if 'Stock Symbol' not in stocks_df.columns:
        st.error("The Excel file must have a column named 'Stock Symbol'.")
        return None

    symbols = stocks_df['Stock Symbol'].dropna().tolist()
    target_date = pd.Timestamp.now().date() - pd.Timedelta(days=1)
    start_date = target_date - timedelta(days=7)
    end_date = target_date + timedelta(days=1)

    closing_prices_summary = []

    for i, symbol in enumerate(symbols, start=1):
        st.write(f"{i}/{len(symbols)}: Processing: {symbol}")
        stock_data = yf.download(symbol, start=start_date, end=end_date)

        if stock_data.empty or 'Close' not in stock_data.columns:
            st.warning(f"No valid 'Close' data for {symbol}. Skipping...")
            continue

        last_three_days = stock_data['Close'].dropna().iloc[-3:]
        if last_three_days.empty:
            st.warning(f"Not enough data for {symbol}. Skipping...")
            continue

        t_value = last_three_days.iloc[-1] if len(last_three_days) >= 1 else None
        t_1_value = last_three_days.iloc[-2] if len(last_three_days) >= 2 else None
        t_2_value = last_three_days.iloc[-3] if len(last_three_days) >= 3 else None

        closing_prices_summary.append({
            "Symbol": symbol,
            "Close_T": t_value,
            "Close_T-1": t_1_value,
            "Close_T-2": t_2_value,
        })

    return pd.DataFrame(closing_prices_summary)

if uploaded_file:
    st.subheader("Processing Stock Data...")
    stock_summary_df = process_data(uploaded_file)

    if stock_summary_df is not None:
        st.subheader("Stock Summary")
        st.dataframe(stock_summary_df)

        st.subheader("Scraping Additional Data...")
        with st.spinner("Scraping in progress..."):
            scraped_data = asyncio.run(main_scraping())

        st.subheader("Scraped Data")
        st.dataframe(scraped_data)

        merged_df = pd.merge(stock_summary_df, scraped_data, on="Symbol", how="outer")
        st.subheader("Merged Data")
        st.dataframe(merged_df)

        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = "C:/Users/40-366/Downloads/"

        merged_file = os.path.join(output_dir, f"merged_data_{today}.xlsx")
        merged_df.to_excel(merged_file, index=False)

        with open(merged_file, "rb") as file:
            st.download_button("Download Merged Data", file, file_name=f"merged_data_{today}.xlsx")
