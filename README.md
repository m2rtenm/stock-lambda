# Stock Price Notifier — AWS Lambda

This repository contains an AWS Lambda function ([`python/StockAnalyzer.py`](python/StockAnalyzer.py)) that monitors intraday stock‑price movements using [yfinance](https://github.com/ranaroussi/yfinance) and sends email alerts via Amazon SNS when price changes exceed configurable thresholds.

The function runs every **15 minutes** via Amazon EventBridge, storing daily state in DynamoDB so you’re alerted only when movements are truly significant.

---

## ⚙️ Environment Variables

| Variable               | Description                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------- |
| `STOCK_SYMBOLS`        | Comma‑separated list of tickers to monitor (e.g. `AAPL,NVDA,GOOG`).                                            |
| `SNS_TOPIC_ARN`        | ARN of the SNS topic for email alerts.                                                                          |
| `THRESHOLD_PERCENT`    | Percent change from the day’s first price that triggers the **first** notification (e.g. `2`).                  |
| `MIN_PERCENT_INCREASE` | Additional percent change required after the first alert to send a **repeat** alert on the same day (e.g. `1`). |
| `DYNAMODB_TABLE_NAME`  | DynamoDB table for per‑day notification state (with TTL).                                                       |
| `REGION`               | AWS Region for DynamoDB and SNS (e.g. `eu-north-1`).                                                            |

---

## 🛠️ How It Works

1. **EventBridge** invokes the Lambda every 15 minutes (see [`terraform/eventbridge.tf`](terraform/eventbridge.tf)).
2. Lambda downloads 1‑day/1‑minute interval OHLC data for each symbol via **yfinance**.
3. It compares the latest close to the day’s first close to calculate a percent change.
4. **Notification logic**:
   - If `|percent_change| ≥ THRESHOLD_PERCENT` **and**
   - (No alert sent today **or** `|percent_change|` increased by `MIN_PERCENT_INCREASE` since the last alert), → publish an alert to SNS and write the percent change + TTL to DynamoDB.
5. The **TTL** field ensures each record expires automatically at midnight UTC, resetting daily tracking.

---

## 🗺️ Architecture

- [`terraform/lambda.tf`](terraform/lambda.tf): Lambda deployment and environment variables.
- [`terraform/sns.tf`](terraform/sns.tf): SNS topic and email subscription.
- [`terraform/dynamodb.tf`](terraform/dynamodb.tf): DynamoDB table for notification state.
- [`terraform/iam-lambda.tf`](terraform/iam-lambda.tf): IAM role and permissions for Lambda.
- [`terraform/eventbridge.tf`](terraform/eventbridge.tf): EventBridge rule for scheduling.

---

## 🚀 Deployment

> **Note**: The Lambda function installs `yfinance` at runtime if not packaged, but for production you should bundle dependencies as described below.

### 1 · Bundle Code & Dependencies

Terraform automatically zips [`python/StockAnalyzer.py`](python/StockAnalyzer.py) for Lambda deployment (see [`terraform/lambda.tf`](terraform/lambda.tf)).  
For local packaging, use:

```bash
python -m pip install -r python/requirements.txt -t python/package/
cp python/StockAnalyzer.py python/package/
cd python/package
zip -r ../StockAnalyzer.zip .
```

### 2 · Deploy with Terraform

Set required variables in [`terraform/terraform.tfvars`](terraform/terraform.tfvars) or via CLI.  
Run:

```bash
cd terraform
terraform init
terraform apply
```

This will provision all AWS resources and deploy the Lambda.

---

## 📝 Local Testing

You can run the Lambda handler locally (requires environment variables or a `.env` file):

```bash
python python/StockAnalyzer.py
```

For dry-run testing without AWS dependencies, use [`python/DryRun.py`](python/DryRun.py):

```bash
python python/DryRun.py
```

---




