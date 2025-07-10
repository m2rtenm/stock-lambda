# StockAnalyzer.py
# This code runs in AWS Lambda to analyze stock prices using yfinance
# and persists the last price in DynamoDB to track changes between executions.

import json
import os
import boto3
from decimal import Decimal # Use Decimal for currency to avoid float inaccuracies

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
STOCK_SYMBOLS = os.environ.get('STOCK_SYMBOLS', 'AAPL,GOOG,TSLA').split(',')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
THRESHOLD_PERCENT = float(os.environ.get('THRESHOLD_PERCENT'))
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME') # New: Table for storing state
REGION = os.environ.get('REGION')

# --- AWS CLIENTS ---
# Initialize AWS clients outside the handler for reuse
sns_client = boto3.client('sns')
dynamodb_client = boto3.client('dynamodb')

# --- HELPER FUNCTIONS ---

def get_previous_price(symbol, table_name):
    """Retrieves the last recorded price for a given stock symbol from DynamoDB."""
    if not table_name:
        print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
        return None
    try:
        response = dynamodb_client.get_item(
            TableName=table_name,
            Key={'symbol': {'S': symbol}}
        )
        if 'Item' in response:
            # Price is stored as a Number ('N') type in DynamoDB
            price = float(response['Item']['price']['N'])
            print(f"Found previous price for {symbol}: ${price:.2f}")
            return price
        else:
            print(f"No previous price found for {symbol}. Will establish a baseline on this run.")
            return None
    except Exception as e:
        print(f"ERROR: Could not get item from DynamoDB for {symbol}. {e}")
        # Fail gracefully, will just skip analysis for this symbol on this run
        return None

def store_current_price(symbol, price, table_name):
    """Stores the current price in DynamoDB for the next execution."""
    if not table_name:
        print("ERROR: DYNAMODB_TABLE_NAME environment variable not set.")
        return
    try:
        # Use Decimal for floating point precision as is best practice for currency
        price_decimal = Decimal(str(price))
        dynamodb_client.put_item(
            TableName=table_name,
            Item={
                'symbol': {'S': symbol},
                # DynamoDB expects numbers as strings when using the low-level client
                'price': {'N': str(price_decimal)}
            }
        )
        print(f"Stored/updated price for {symbol} to ${price:.2f}")
    except Exception as e:
        print(f"ERROR: Could not put item to DynamoDB for {symbol}. {e}")

def get_current_stock_data(symbol):
    """Fetches the latest stock price using yfinance."""
    if not yf:
        print("yfinance library is not available.")
        return None
    try:
        print(f"Fetching current data for {symbol} using yfinance...")
        ticker = yf.Ticker(symbol)
        # Get historical data for the last day to get the most recent closing price.
        hist = ticker.history(period="1d")
        if hist.empty:
            print(f"WARN: Could not retrieve current price for {symbol}.")
            return None
        latest_price = hist['Close'][-1]
        return { "symbol": symbol, "latest_price": latest_price }
    except Exception as e:
        print(f"ERROR: Failed to fetch data for {symbol} with yfinance. {e}")
        return None

def send_notification(analysis_result):
    """Sends a formatted message to the SNS topic."""
    symbol = analysis_result['symbol']
    price = analysis_result['latest_price']
    change = analysis_result['percent_change']
    previous_price = analysis_result['previous_price']

    trend = "UP" if change > 0 else "DOWN"
    action = "consider selling" if trend == "UP" else "becoming a buying opportunity"

    subject = f"Stock Alert: {symbol} is {trend} {abs(change):.2f}% since last check"

    message = (
        f"Significant price movement detected for {symbol} since the last check.\n\n"
        f"Symbol: {symbol}\n"
        f"Previous Price: ${previous_price:.2f}\n"
        f"Current Price: ${price:.2f}\n"
        f"Change since last execution: {change:.2f}%\n\n"
        f"This move exceeds your threshold of {THRESHOLD_PERCENT}% and may indicate it's time to {action}.\n\n"
        f"Disclaimer: This is an automated notification and not financial advice."
    )

    try:
        print(f"Sending notification for {symbol} to SNS topic: {SNS_TOPIC_ARN}")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject
        )
    except Exception as e:
        print(f"ERROR: Failed to publish message to SNS. {e}")

# --- MAIN HANDLER ---

def lambda_handler(event, context):
    """
    The main entry point for the Lambda function.
    Triggered by EventBridge.
    """
    print("--- Stock Analyzer Function (Stateful) Started ---")

    notifications_sent = 0
    for symbol in STOCK_SYMBOLS:
        symbol = symbol.strip()
        if not symbol:
            continue

        # 1. Get current market price
        current_data = get_current_stock_data(symbol)
        if not current_data:
            continue # Skip if yfinance fails for this symbol
        
        latest_price = current_data['latest_price']

        # 2. Get the price from the last execution
        previous_price = get_previous_price(symbol, DYNAMODB_TABLE_NAME)

        # 3. Analyze and notify if we have a previous price to compare against
        if previous_price is not None:
            # We have a baseline to compare against
            change = latest_price - previous_price
            percent_change = (change / previous_price) * 100 if previous_price != 0 else 0
            
            print(f"Analyzed {symbol}: Current=${latest_price:.2f}, Previous=${previous_price:.2f}, Change={percent_change:.2f}%")
            
            # Check if the absolute change exceeds our threshold
            if abs(percent_change) >= THRESHOLD_PERCENT:
                print(f"ALERT: {symbol} change {percent_change:.2f}% exceeds threshold.")
                analysis_result = {
                    "symbol": symbol,
                    "latest_price": latest_price,
                    "previous_price": previous_price,
                    "percent_change": percent_change
                }
                send_notification(analysis_result)
                notifications_sent += 1
        
        # 4. Always store the latest price for the *next* execution
        # This updates the baseline regardless of whether a notification was sent.
        store_current_price(symbol, latest_price, DYNAMODB_TABLE_NAME)

    print(f"--- Stock Analyzer Function Finished. {notifications_sent} notifications sent. ---")
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Analysis complete. {notifications_sent} notifications sent.')
    }
