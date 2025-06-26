resource "aws_sns_topic" "stock_lambda" {
  name = "${var.account_identifier}-${var.lambda_name}-topic"
}

resource "aws_sns_topic_subscription" "stock_lambda" {
  topic_arn = aws_sns_topic.stock_lambda.arn
  protocol  = "email"
  endpoint  = var.notification_email
}