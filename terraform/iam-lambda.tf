data "aws_iam_policy_document" "stock_lambda" {
  statement {
    sid    = "Logs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs_CreateLogStream",
      "logs:PutEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    sid       = "SNS"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.stock_lambda.arn]
  }

  statement {
    sid = "DynamoDB"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ]
    resources = [aws_dynamodb_table.stock_prices.arn]
  }
}

data "aws_iam_policy_document" "stock_lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "stock_lambda" {
  name        = "${var.account_identifier}-${var.lambda_name}-policy"
  description = "Policy for the stock analyzer Lambda function"
  policy      = data.aws_iam_policy_document.stock_lambda.json
}

resource "aws_iam_role" "stock_lambda" {
  name               = "${var.account_identifier}-${var.lambda_name}-role"
  assume_role_policy = data.aws_iam_policy_document.stock_lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "stock_lambda" {
  role       = aws_iam_role.stock_lambda.name
  policy_arn = aws_iam_policy.stock_lambda.arn
}