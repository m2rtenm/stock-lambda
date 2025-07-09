import yfinance as yf
import time

# AAPL: Period '1m' is invalid, must be one of: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

def check_stock_change(ticker, interval_seconds=5, threshold_pct=1.0):
    stock = yf.Ticker(ticker)
    last_price = stock.history(period="1d")["Close"].iloc[-1]

    while True:
        time.sleep(interval_seconds)
        new_price = stock.history(period="1d")["Close"].iloc[-1]
        change_pct = ((new_price - last_price) / last_price) * 100

        
        print(f"{ticker} changed by {change_pct:.2f}%: {last_price} → {new_price}")
        
        last_price = new_price

check_stock_change("NVDA", interval_seconds=5, threshold_pct=2.0)