# StockAnalyzer.py
# This code runs in AWS Lambda to analyze stock prices using yfinance
# and persists the last price in DynamoDB to track changes between executions.

import json
import os
import subprocess
import sys
import boto3
from decimal import Decimal # Use Decimal for currency to avoid float inaccuracies
from datetime import datetime, timezone


subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", "/tmp", 'yfinance'])
sys.path.append('/tmp')

# --- IMPORTANT DEPLOYMENT NOTE ---
# The 'yfinance' and 'pandas' libraries are not included in the AWS Lambda
# runtime. You must package them with your function into a .zip file.
try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: 'yfinance' or 'pandas' not found. Please package them with the Lambda function.")
    yf = None
    pd = None

# --- CONFIGURATION ---
# Load configuration from Lambda environment variables
STOCK_SYMBOLS = [s.strip() for s in os.environ.get('STOCK_SYMBOLS', 'AAPL,GOOG,TSLA').split(',')]
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
THRESHOLD_PERCENT = float(os.environ.get('THRESHOLD_PERCENT'))
MIN_PERCENT_INCREASE = float(os.environ.get('MIN_PERCENT_INCREASE'))
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')
REGION = os.environ.get('REGION')

# --- AWS CLIENTS ---
# Initialize AWS clients outside the handler for reuse
sns_client = boto3.client('sns')
dynamodb_client = boto3.client('dynamodb')

def get_notification_record(symbol):
    """Retrieve last notification record for the symbol from DynamoDB."""
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
        print(f"ERROR: Failed to get notification record for {symbol} from DynamoDB: {e}")
        return None, None

def store_notification_record(symbol, percent_diff):
    """Store notification info in DynamoDB with TTL set to midnight UTC next day."""
    try:
        now = datetime.now(timezone.utc)
        # Set TTL to midnight UTC next day to reset daily
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
        print(f"Stored notification record for {symbol} with percent_diff={percent_diff:.2f}% and TTL={ttl}")
    except Exception as e:
        print(f"ERROR: Failed to store notification record for {symbol} in DynamoDB: {e}")

def send_notification(symbol, first_price, last_price, percent_change):
    """Send SNS notification about price change."""
    trend = "UP" if percent_change > 0 else "DOWN"
    action = "consider selling" if trend == "UP" else "consider buying"

    subject = f"Stock Alert: {symbol} is {trend} {abs(percent_change)}% since start of day"
    message = (
        f"Significant price movement detected for {symbol}.\n\n"
        f"Start Price: ${first_price:.2f}\n"
        f"Current Price: ${last_price:.2f}\n"
        f"Change since start of day: {percent_change:.2f}%\n\n"
        f"This move exceeds your threshold of {THRESHOLD_PERCENT}% and the minimum increase of {MIN_PERCENT_INCREASE}% since last notification.\n"
        f"You may want to {action}.\n\n"
        f"Disclaimer: Automated notification, not financial advice."
    )
    try:
        sns_client.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=subject)
        print(f"Sent notification for {symbol}")
    except Exception as e:
        print(f"ERROR: Failed to send SNS notification for {symbol}: {e}")

def analyze_symbol(symbol):
    """Analyze price changes for one symbol and decide if notification is needed."""
    if not yf:
        print("yfinance not available, skipping.")
        return False

    print(f"Fetching 1d 1m interval data for {symbol}...")
    try:
        df = yf.download(symbol, period='1d', interval='1m', progress=True, auto_adjust=True)
        if df.empty:
            print(f"No data returned for {symbol}")
            return False
    except Exception as e:
        print(f"Error downloading data for {symbol}: {e}")
        return False

    # Use Close prices
    closes = df['Close']
    first_price = closes.iloc[0].item()
    last_price = closes.iloc[-1].item()

    if first_price == 0:
        print(f"Invalid first price for {symbol}, skipping")
        return False

    percent_change = ((last_price - first_price) / first_price) * 100
    print(f"{symbol} price change since start of day: {percent_change:.2f}%")

    if abs(percent_change) < THRESHOLD_PERCENT:
        print(f"Change {percent_change:.2f}% below threshold {THRESHOLD_PERCENT}%, no notification.")
        return False

    # Check DynamoDB for last notification info
    last_notified_date, last_percent_diff = get_notification_record(symbol)
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    if last_notified_date == today_str:
        # Already notified today, check if new percent change is at least MIN_PERCENT_INCREASE above last percent diff
        diff_since_last = abs(percent_change) - abs(last_percent_diff)
        print(f"Already notified today. Change since last notification: {diff_since_last:.2f}%")
        if diff_since_last < MIN_PERCENT_INCREASE:
            print(f"Increase less than minimum {MIN_PERCENT_INCREASE}%, skipping notification.")
            return False
        else:
            print(f"Increase above minimum {MIN_PERCENT_INCREASE}%, sending notification.")

    # Send notification and update DynamoDB
    send_notification(symbol, first_price, last_price, percent_change)
    store_notification_record(symbol, percent_change)
    return True

def lambda_handler(event, context):
    print("--- Stock Analyzer Lambda (Stateful) Started ---")

    print(f"DEBUG: DYNAMODB_TABLE_NAME = {DYNAMODB_TABLE_NAME}")

    notifications_sent = 0
    for symbol in STOCK_SYMBOLS:
        notified = analyze_symbol(symbol)
        if notified:
            notifications_sent += 1

    print(f"--- Finished. Notifications sent: {notifications_sent} ---")
    return {
        'statusCode': 200,
        'body': json.dumps(f'Notifications sent: {notifications_sent}')
    }