# StockAnalyzer.py
# This code runs in AWS Lambda to analyze stock prices using yfinance
# and persists the last price in DynamoDB to track changes between executions.

import json
import os
import subprocess
import sys
import boto3
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Install required packages if not packaged
subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", "/tmp", "yfinance"])
sys.path.append("/tmp")

import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
STOCK_SYMBOLS = [s.strip() for s in os.environ.get('STOCK_SYMBOLS', 'AAPL,GOOG,TSLA').split(',')]
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
THRESHOLD_PERCENT = float(os.environ.get('THRESHOLD_PERCENT'))
MIN_PERCENT_INCREASE = float(os.environ.get('MIN_PERCENT_INCREASE'))
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
REGION = os.environ.get('REGION')

# AWS Clients
sns_client = boto3.client('sns')
dynamodb_client = boto3.client('dynamodb')


def is_market_open():
    '''Check if Europe's stock market is open'''
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5: # Mon is 0
        return False
    market_open = now.replace(hour=8, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_notification_record(symbol):
    try:
        response = dynamodb_client.get_item(
            TableName=DYNAMODB_TABLE_NAME,
            Key={'symbol': {'S': symbol}}
        )
        if 'Item' in response:
            item = response['Item']
            last_notified_date = item.get('last_notified_date', {}).get('S')
            last_percent_diff = float(item.get('last_percent_diff', {}).get('N', '0'))
            return last_notified_date, last_percent_diff
        return None, None
    except Exception as e:
        print(f"ERROR: Failed to get record for {symbol}: {e}")
        return None, None


def store_notification_record(symbol, percent_diff):
    try:
        now = datetime.now(timezone.utc)
        midnight_next_day = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc) + timedelta(days=1)
        ttl = int(midnight_next_day.timestamp())

        dynamodb_client.put_item(
            TableName=DYNAMODB_TABLE_NAME,
            Item={
                'symbol': {'S': symbol},
                'last_notified_date': {'S': now.strftime('%Y-%m-%d')},
                'last_percent_diff': {'N': str(percent_diff)},
                'ttl': {'N': str(ttl)}
            }
        )
        print(f"Stored record for {symbol}, TTL={ttl}")
    except Exception as e:
        print(f"ERROR: Failed to store record for {symbol}: {e}")


def send_notification(symbol, first_price, last_price, percent_change):
    trend = "UP" if percent_change > 0 else "DOWN"
    action = "consider selling" if trend == "UP" else "consider buying"
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    subject = f"Stock Alert: {symbol} {trend} {abs(percent_change):.2f}%"
    message = (
        f"[{now_utc}]\n"
        f"{symbol} has moved significantly since market open.\n\n"
        f"Start Price: ${first_price:.2f}\n"
        f"Current Price: ${last_price:.2f}\n"
        f"Change: {percent_change:.2f}%\n\n"
        f"Threshold: {THRESHOLD_PERCENT}%\n"
        f"Change since last alert: {MIN_PERCENT_INCREASE}%\n"
        f"Suggested Action: {action}\n\n"
        f"Note: This is an automated alert. Not financial advice."
    )
    try:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=subject)
        print(f"✅ Sent notification for {symbol}")
    except Exception as e:
        print(f"ERROR: Failed to send notification for {symbol}: {e}")


def analyze_symbol(symbol):
    print(f"Analyzing {symbol}...")

    try:
        df = yf.download(symbol, period='1d', interval='1m', progress=False, auto_adjust=True)
        if df.empty:
            print(f"No data for {symbol}, skipping.")
            return False
    except Exception as e:
        print(f"ERROR: Could not fetch data for {symbol}: {e}")
        return False

    closes = df['Close']
    first_price = closes.iloc[0].item()
    last_price = closes.iloc[-1].item()

    if first_price == 0:
        print(f"Invalid start price for {symbol}, skipping.")
        return False

    # Ensure data isn't stale
    last_timestamp = closes.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_minutes = (now - last_timestamp).total_seconds() / 60
    if age_minutes > 5:
        print(f"Stale data ({age_minutes:.2f} min old) for {symbol}, skipping.")
        return False

    percent_change = ((last_price - first_price) / first_price) * 100
    print(f"{symbol}: {percent_change:.2f}% change since open")

    if abs(percent_change) < THRESHOLD_PERCENT:
        print(f"Below threshold ({THRESHOLD_PERCENT}%), no alert.")
        return False

    today_str = now.strftime('%Y-%m-%d')
    last_notified_date, last_percent_diff = get_notification_record(symbol)

    if last_notified_date == today_str:
        diff_since_last = abs(percent_change) - abs(last_percent_diff)
        if diff_since_last < MIN_PERCENT_INCREASE:
            print(f"Change since last alert: {diff_since_last:.2f}%. Not enough. Skipping.")
            return False
        else:
            print(f"Change since last alert: {diff_since_last:.2f}%. Sending new alert.")

    send_notification(symbol, first_price, last_price, percent_change)
    store_notification_record(symbol, percent_change)
    return True


def lambda_handler(event, context):
    print("=== StockAnalyzer Lambda Started (UTC) ===")

    if not is_market_open():
        print("Market is closed. Skipping analysis.")
        return {
            'statusCode': 200,
            'body': json.dumps('Market is closed. No analysis performed.')
        }

    notifications_sent = 0
    for symbol in STOCK_SYMBOLS:
        if analyze_symbol(symbol):
            notifications_sent += 1

    print(f"Analysis complete. Notifications sent: {notifications_sent}")
    return {
        'statusCode': 200,
        'body': json.dumps(f'Notifications sent: {notifications_sent}')
    }
