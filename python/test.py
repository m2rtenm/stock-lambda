import yfinance as yf
import pandas as pd
import time

# AAPL: Period '1m' is invalid, must be one of: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

# def check_stock_change(ticker, interval_seconds=5, threshold_pct=1.0):
#     stock = yf.Ticker(ticker)
#     last_price = stock.history(period="1d")["Close"].iloc[-1]
# 
#     while True:
#         time.sleep(interval_seconds)
#         new_price = stock.history(period="1d")["Close"].iloc[-1]
#         change_pct = ((new_price - last_price) / last_price) * 100
# 
#         
#         print(f"{ticker} changed by {change_pct:.2f}%: {last_price} → {new_price}")
#         
#         last_price = new_price

def analyze_price_change(ticker):
    stock = yf.download(ticker, period="1d", interval="1m", group_by='column')

    if stock.empty:
        print(f"No data for {ticker}")
        return

    # Determine correct way to access Close column
    if isinstance(stock.columns, pd.MultiIndex):
        close_series = stock[("Close", ticker)]
    else:
        close_series = stock["Close"]

    # Extract first and last prices along with timestamps
    first_timestamp = close_series.index[0]
    last_timestamp = close_series.index[-1]

    first_price = close_series.iloc[0]
    last_price = close_series.iloc[-1]

    absolute_change = last_price - first_price
    percent_change = (absolute_change / first_price) * 100

    print(f"--- {ticker} Price Change Analysis ---")
    print(f"Start Time:  {first_timestamp} | Start Price: ${first_price:.2f}")
    print(f"End Time:    {last_timestamp} | End Price:   ${last_price:.2f}")
    print(f"Change:      ${absolute_change:.2f} ({percent_change:.2f}%)")

# Run it
analyze_price_change("NVDA")

#check_stock_change("NVDA", interval_seconds=5, threshold_pct=2.0)

def test(ticker):
    stock = yf.download(ticker, period="1d", interval="1m")
    print(stock)

#test("NVDA")