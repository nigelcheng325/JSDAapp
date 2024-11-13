import streamlit as st
import pandas as pd
import yfinance as yf

# Title of the app
st.title("Stock Data Processor")

# Instruction for users
st.write("Upload an Excel file containing stock symbols in a column named 'Stock Symbol'.")

# File uploader for users to upload Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    # Read the uploaded Excel file
    stocks_df = pd.read_excel(uploaded_file)
    if 'Stock Symbol' not in stocks_df.columns:
        st.error("The Excel file must have a column named 'Stock Symbol'.")
    else:
        symbols = stocks_df['Stock Symbol'].dropna().tolist()

        # Display the uploaded stock symbols
        st.write("Stock Symbols:", symbols)

        # Specify the date to fetch data for
        target_date = st.date_input("Select Target Date", pd.Timestamp.now().date())
        start_date = pd.to_datetime(target_date) - pd.Timedelta(days=7)
        end_date = pd.to_datetime(target_date) + pd.Timedelta(days=1)

        # Initialize a list to hold the results
        closing_prices_summary = []

        # Fetch data for each stock symbol
        for symbol in symbols:
            st.write(f"Processing: {symbol}")
            stock_data = yf.download(symbol, start=start_date, end=end_date)

            if not stock_data.empty:
                stock_data = stock_data['Close'].dropna().sort_index()  # Ensure data is sorted and clean
                last_three_days = stock_data.iloc[-3:]  # Get the last 3 trading days

                # Default values
                t_value = t_1_value = t_2_value = None
                t_1_pct_change = t_2_pct_change = cumulative_pct = None

                if len(last_three_days) >= 1:
                    t_value = float(last_three_days.iloc[-1].item())  # T
                if len(last_three_days) >= 2:
                    t_1_value = float(last_three_days.iloc[-2].item())  # T-1
                    t_1_pct_change = ((t_value - t_1_value) / t_1_value) * 100 if t_1_value != 0 else None
                if len(last_three_days) >= 3:
                    t_2_value = float(last_three_days.iloc[-3].item())  # T-2
                    t_2_pct_change = ((t_1_value - t_2_value) / t_2_value) * 100 if t_2_value != 0 else None
                    cumulative_pct_1 = t_2_pct_change + t_1_pct_change if t_1_pct_change is not None and t_2_pct_change is not None else None
                    cumulative_pct_2 = ((t_value - t_2_value) / t_2_value) * 100 if t_2_value != 0 else None
                closing_prices_summary.append({
                    "Symbol": symbol,
                    "Close_T": t_value,
                    "Close_T-1": t_1_value,
                    "T-1 % Change": t_1_pct_change,
                    "Close_T-2": t_2_value,
                    "T-2 % Change": t_2_pct_change,
                    "Cumulative % Change_1": cumulative_pct_1
                    "Cumulative % Change_2": cumulative_pct_2
                })
            else:
                st.warning(f"No data found for {symbol}.")

        # Convert the summary to a DataFrame
        summary_df = pd.DataFrame(closing_prices_summary)

        # Display the summary in the app
        st.subheader("Summary of Closing Prices and % Changes")
        st.dataframe(summary_df)

        # Option to download the results as an Excel file
        output_file = f"closing_prices_summary_{target_date}.xlsx"
        summary_df.to_excel(output_file, index=False)
        with open(output_file, "rb") as file:
            st.download_button(label="Download Summary as Excel", data=file, file_name=output_file)
