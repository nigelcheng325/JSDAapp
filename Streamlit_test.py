import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import os

async def download_nasdaq_noncompliant_file(download_dir="downloads"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless for debugging
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        await page.goto("https://www.rakuten-sec.co.jp/web/market/search/us_search/result.html?all=on&vall=on&forwarding=na&target=0&theme=na&returns=na&head_office=na&name=&code=&sector=na&pageNo=&c=us&p=result&r1=on")
        
        # Wait for the CSVèoóÕ button and click it
        await page.wait_for_selector('img[src*="btn_csvoutput.gif"]', timeout=60000)
        await page.locator('img[src*="btn_csvoutput.gif"]').click()
        
        # Wait for download event
        download = await page.wait_for_event('download')
        
        # Ensure download directory exists
        os.makedirs(download_dir, exist_ok=True)
        save_path = os.path.join(download_dir, "Rakuten_US_Cash.csv")
        await download.save_as(save_path)
        
        print(f"File downloaded and saved to {save_path}")
        await browser.close()
        return save_path

def main():
    st.title("Rakuten CSV Downloader")
    
    download_dir = st.text_input("Download Directory", value="downloads")
    
    if st.button("Download CSV"):
        with st.spinner("Downloading..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            csv_path = loop.run_until_complete(download_nasdaq_noncompliant_file(download_dir))
            
            if csv_path:
                st.success(f"File downloaded and saved to: {csv_path}")
                st.download_button("Download CSV File", data=open(csv_path, "rb"), file_name="Rakuten_US_Cash.csv")

if __name__ == "__main__":
    main()
