# Stock Price Notifier — AWS Lambda

This repository contains an AWS Lambda function that monitors intraday stock‑price movements with [yfinance](https://github.com/ranaroussi/yfinance) and sends email alerts through Amazon SNS when price changes exceed configurable thresholds.

Running every **15 minutes** via Amazon EventBridge, the function stores daily state in DynamoDB so you’re alerted only when movements are truly significant.

---

## ⚙️ Environment Variables

| Variable               | Description                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- |
| `STOCK_SYMBOLS`        | Comma‑separated list of tickers to monitor (e.g. `AAPL,NVDA,GOOG`).                                             |
| `SNS_TOPIC_ARN`        | ARN of the SNS topic for email/SMS/Slack alerts.                                                                |
| `THRESHOLD_PERCENT`    | Percent change from the day’s first price that triggers the **first** notification (e.g. `2`).                  |
| `MIN_PERCENT_INCREASE` | Additional percent change required after the first alert to send a **repeat** alert on the same day (e.g. `1`). |
| `DYNAMODB_TABLE_NAME`  | DynamoDB table for per‑day notification state (with TTL).                                                       |
| `REGION`               | AWS Region for DynamoDB and SNS (e.g. `us‑east‑1`).                                                             |

---

## 🛠️ How It Works

1. **EventBridge** invokes the Lambda every 15 minutes.
2. Lambda downloads 1‑day/1‑minute interval OHLC data for each symbol via **yfinance**.
3. It compares the latest close to the day’s first close to calculate a percent change.
4. **Notification logic**
   - If `|percent_change| ≥ THRESHOLD_PERCENT` **and**
   - (No alert sent today **or** `|percent_change|` increased by `MIN_PERCENT_INCREASE` since the last alert), - → publish an alert to SNS and write the percent change + TTL to DynamoDB.
5. The **TTL** field ensures each record expires automatically at midnight UTC, resetting daily tracking.

---

## 🗺️ Architecture



*Generated automatically; edit **`docs/`** or regenerate via **`tools/diagram.py`** if you change the architecture.*

---

## 🚀 Deployment

> **Note**: AWS Lambda’s Python runtime doesn’t bundle `pandas` or `yfinance`. You must package them yourself (or use a Lambda Layer).

### 1 · Bundle Code & Dependencies

```bash
# From the repo root
python -m pip install -r requirements.txt -t package/
cp StockAnalyzer.py package/
cd package
zip -r ../stock-lambda.zip .
```

### 2 · Upload to Lambda

- Via AWS Console, CLI (`aws lambda update-function-code`), or Terraform `aws_lambda_function` resource.
- Set the *Environment variables* listed above.

### 3 · Create EventBridge Rule

Run every 15 minutes (cron expression):

```text
cron(0/15 * ? * * *)
```

Attach it to your Lambda.

### 4 · Permissions

Your Lambda execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/DYNAMODB_TABLE_NAME"
    },
    {
      "Effect": "Allow",
      "Action": "sns:Publish",
      "Resource": "${SNS_TOPIC_ARN}"
    }
  ]
}
```

---

## 📝 Local Testing

```bash
python StockAnalyzer.py  # Executes the handler locally (requires env vars or a .env file)
```

---



