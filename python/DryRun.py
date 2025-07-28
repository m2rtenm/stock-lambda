from dotenv import load_dotenv
load_dotenv()


import json
import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
STOCK_SYMBOLS = [s.strip() for s in os.environ.get('STOCK_SYMBOLS', 'BMW.DE,AIR.PA,VOD.L').split(',')]
THRESHOLD_PERCENT = float(os.environ.get('THRESHOLD_PERCENT', '2.0'))
MIN_PERCENT_INCREASE = float(os.environ.get('MIN_PERCENT_INCREASE', '1.0'))

# --- In-memory store simulating DynamoDB ---
notification_state = {}

# --- Market hours (Europe) ---
def is_market_open_europe():
    now = datetime.now(timezone.utc).astimezone()  # local time
    # Assume market is open Mon-Fri, 09:00–17:30 CET/CEST (Europe/Estonia time assumed as local)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    market_open = now.replace(hour=10, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=18, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

def get_notification_record(symbol):
    record = notification_state.get(symbol)
    if record:
        return record['last_notified_date'], record['last_percent_diff']
    return None, None

def store_notification_record(symbol, percent_diff):
    now = datetime.now(timezone.utc)
    notification_state[symbol] = {
        'last_notified_date': now.strftime('%Y-%m-%d'),
        'last_percent_diff': percent_diff,
    }
    print(f"[Memory] Stored state for {symbol}: {percent_diff:.2f}%")

def send_notification(symbol, first_price, last_price, percent_change):
    trend = "UP" if percent_change > 0 else "DOWN"
    action = "consider selling" if trend == "UP" else "consider buying"

    subject = f"Stock Alert: {symbol} is {trend} {abs(percent_change):.2f}% since start of day"
    message = (
        f"--- Notification (dry run) ---\n"
        f"{symbol} has moved {trend} {abs(percent_change):.2f}% since open\n"
        f"Start Price: ${first_price:.2f}\n"
        f"Current Price: ${last_price:.2f}\n"
        f"Threshold: {THRESHOLD_PERCENT}%, Δ since last: {MIN_PERCENT_INCREASE}%\n"
        f"Suggested action: {action}\n"
    )
    print(subject)
    print(message)

def analyze_symbol(symbol):
    print(f"\nFetching 1d 1m data for {symbol}...")
    try:
        df = yf.download(symbol, period='1d', interval='1m', progress=False, auto_adjust=True)
        if df.empty:
            print(f"No data returned for {symbol}")
            return False
    except Exception as e:
        print(f"Failed to fetch data for {symbol}: {e}")
        return False

    closes = df['Close']
    first_price = float(closes.iloc[0])
    last_price = float(closes.iloc[-1])

    if first_price == 0:
        print(f"Invalid open price for {symbol}")
        return False

    percent_change = ((last_price - first_price) / first_price) * 100
    print(f"{symbol}: {percent_change:.2f}% change since open")

    if abs(percent_change) < THRESHOLD_PERCENT:
        print(f"Below threshold ({THRESHOLD_PERCENT}%), skipping.")
        return False

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    last_date, last_percent = get_notification_record(symbol)

    if last_date == today_str:
        diff = abs(percent_change) - abs(last_percent)
        if diff < MIN_PERCENT_INCREASE:
            print(f"No new significant change ({diff:.2f}%), skipping.")
            return False
        else:
            print(f"Significant change since last ({diff:.2f}%), sending again.")

    send_notification(symbol, first_price, last_price, percent_change)
    store_notification_record(symbol, percent_change)
    return True

def lambda_handler(event=None, context=None):
    print("=== Dry Run StockAnalyzer Started ===")

    if not is_market_open_europe():
        print("Market is closed (Europe). Skipping analysis.")
        return {
            'statusCode': 200,
            'body': json.dumps('Market is closed. No analysis.')
        }

    notifications_sent = 0
    for symbol in STOCK_SYMBOLS:
        if analyze_symbol(symbol):
            notifications_sent += 1

    print(f"\nDry Run Complete. Notifications sent: {notifications_sent}")
    return {
        'statusCode': 200,
        'body': json.dumps(f'Notifications sent: {notifications_sent}')
    }

if __name__ == "__main__":
    lambda_handler()
