
import streamlit as st
import pandas as pd
import yfinance as yf
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from io import BytesIO
import os
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
        nyse_noncompliant_data = []

        for row in rows:
            issuer = await row.query_selector("td:nth-child(1)")
            symbol_td = await row.query_selector("td:nth-child(2) span")
            deficiency = await row.query_selector("td:nth-child(4)")
            date = await row.query_selector("td:nth-child(5)")

            issuer_text = await issuer.text_content() if issuer else None
            symbols_text = [await span.text_content() for span in await row.query_selector_all("td:nth-child(2) span")]
            deficiency_text = await deficiency.text_content() if deficiency else None
            date_text = await date.text_content() if date else None

            for symbol in symbols_text:
                nyse_noncompliant_data.append({
                    "Issuer": issuer_text.strip(),
                    "Symbol": symbol.strip(),
                    "Deficiency": deficiency_text.strip(),
                    "Date": date_text.strip(),
                    "Link": "https://www.nyse.com/regulation/noncompliant-issuers"
                })

        await browser.close()
        return pd.DataFrame(nyse_noncompliant_data)

async def scrape_nyse_delistings():
    async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
        
            try:
                await page.goto("https://www.nyse.com/regulation/delistings")

                # Wait for the content to load
                await page.wait_for_selector("table tbody tr")

                # Extract rows from the delistings table
                rows = await page.query_selector_all("table tbody tr")

                nyse_delistings_data = []
                for row in rows:
                    issuer = await row.query_selector("td:nth-child(1)")
                    symbol_td = await row.query_selector("td:nth-child(2)")

                    # Extract all symbols within the second column
                    if symbol_td:
                        symbols_spans = await symbol_td.query_selector_all("span")
                        symbols = []
                        for span in symbols_spans:
                            span_text = await span.text_content()
                            # Split by comma and clean each symbol
                            symbols.extend([s.strip() for s in span_text.split(",")])
                    else:
                        symbols = ["N/A"]

                    initiation = await row.query_selector("td:nth-child(3)")
                    notification_date = await row.query_selector("td:nth-child(4)")

                    # Extract text or set default value if cell is empty
                    issuer_text = await issuer.text_content() if issuer else "N/A"
                    initiation_text = await initiation.text_content() if initiation else "N/A"
                    notification_date_text = await notification_date.text_content() if notification_date else "N/A"

                    # Append each symbol as a separate row
                    for symbol in symbols:
                        nyse_delistings_data.append({
                            "Issuer": issuer_text.strip(),
                            "Symbol": symbol.strip(),
                            "Initiation": initiation_text.strip(),
                            "Notification Date": notification_date_text.strip(),
                            "Link": "https://www.nyse.com/regulation/delistings"
                        })

            finally:
                await browser.close()

            print("2. nyse_delisting_df completed")
            print(" ")
            return pd.DataFrame(nyse_delistings_data)

async def scrape_nasdaq_pending_suspension():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://listingcenter.nasdaq.com/IssuersPendingSuspensionDelisting.aspx")

        # Wait for the content to load
        await page.wait_for_load_state('networkidle')  # Ensure network is idle

        nasdaq_data = []

        while True:
            # Wait for table rows to load
            await page.wait_for_selector("tbody tr.rgRow", timeout=60000)

            # Extract rows from the current page
            rows = await page.query_selector_all("tbody tr.rgRow, tbody tr.rgAltRow")

            for row in rows:
                # Extract necessary columns
                symbol = await row.query_selector("td:nth-child(2)")
                reason = await row.query_selector("td:nth-child(3)")
                effective_date = await row.query_selector("td:nth-child(5)")

                if symbol and reason and effective_date:
                    symbol_text = await symbol.inner_text()
                    reason_text = await reason.inner_text()
                    effective_date_text = await effective_date.inner_text()

                    nasdaq_data.append({
                        "Symbol": symbol_text.strip(),
                        "Deficiency": reason_text.strip(),
                        "Date": effective_date_text.strip(),
                        "Link": "https://listingcenter.nasdaq.com/IssuersPendingSuspensionDelisting.aspx"
                    })

            # Check if there's a "Next" button and click it
            next_button = await page.query_selector("a.rgPageNext")
            if next_button and await next_button.is_enabled():
                await next_button.click()
                # Wait for the next page to load
                await page.wait_for_load_state('networkidle')
            else:
                break  # Exit loop when no more pages are available

        await browser.close()

        print("4. scrape_nasdaq_pending_suspension_df completed")
        print(" ")

        # Convert to DataFrame and return
        return pd.DataFrame(nasdaq_data)


async def scrape_threshold_security_list(max_retries=5, retry_delay=5):
    retries = 0
    while retries < max_retries:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://www.nasdaqtrader.com/trader.aspx?id=regshothreshold")

                # Wait for the page to load
                await page.wait_for_load_state('networkidle')

                # Wait for the table headers to be visible
                await page.wait_for_selector("table tbody tr", timeout=60000)

                # Extract rows from the threshold security table
                rows = await page.query_selector_all("table tbody tr")

                threshold_data = []
                for row in rows:
                    symbol = await row.query_selector("td:nth-child(1)")
                    reason = await row.query_selector("td:nth-child(3)")
                    date_added = await row.query_selector("td:nth-child(4)")

                    if symbol and reason and date_added:
                        symbol_text = await symbol.inner_text()
                        reason_text = await reason.inner_text()
                        date_added_text = await date_added.inner_text()

                        threshold_data.append({
                            "Symbol": symbol_text.strip(),
                            "Deficiency": reason_text.strip(),
                            "Date": date_added_text.strip(),
                            "Link": "https://www.nasdaqtrader.com/trader.aspx?id=regshothreshold"
                        })

                print("5. scrape_threshold_security_df completed")
                await browser.close()
                return pd.DataFrame(threshold_data)

        except Exception as e:
            retries += 1
            print(f"Retry {retries}/{max_retries} due to error: {e}")
            await asyncio.sleep(retry_delay)

    # If max retries are exceeded, raise an exception
    raise RuntimeError(f"Failed after {max_retries} retries.")

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
    # Run all scraping functions and combine the results
    combined_df = pd.concat([nyse_noncompliant_df], ignore_index=True)
    return combined_df

# Process stock data
def process_data(uploaded_file, combined_df):
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

        if not stock_data.empty:
            last_three_days = stock_data['Close'].dropna().iloc[-3:]
            t_value = last_three_days[-1] if len(last_three_days) >= 1 else None
            t_1_value = last_three_days[-2] if len(last_three_days) >= 2 else None
            t_2_value = last_three_days[-3] if len(last_three_days) >= 3 else None

            closing_prices_summary.append({
                "Symbol": symbol,
                "Close_T": t_value,
                "Close_T-1": t_1_value,
                "Close_T-2": t_2_value,
            })

    summary_df = pd.DataFrame(closing_prices_summary)
    
    # Merge with scraping results
    merged_df = pd.merge(summary_df, combined_df, on="Symbol", how="left")
    return merged_df

if uploaded_file:
    st.subheader("Processing Stock Data...")
    with st.spinner("Scraping Additional Data..."):
        combined_df = asyncio.run(main_scraping())

    merged_df = process_data(uploaded_file, combined_df)
    st.subheader("Merged Data with Issues")
    st.dataframe(merged_df)

    # Provide download option
    output_file = BytesIO()
    merged_df.to_excel(output_file, index=False, engine='openpyxl')
    output_file.seek(0)

    st.download_button(
        label="Download Merged Data",
        data=output_file,
        file_name="merged_stock_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
