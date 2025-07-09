resource "aws_cloudwatch_event_rule" "stock_lambda" {
  name                = "${var.account_identifier}-${var.lambda_name}-event-rule"
  description         = "Triggers the stock analyzer Lambda function"
  schedule_expression = "rate(15 minutes)"
}

resource "aws_cloudwatch_event_target" "stock_lambda" {
  rule      = aws_cloudwatch_event_rule.stock_lambda.name
  target_id = "TriggerStockAnalyzerLamnbda"
  arn       = aws_lambda_function.stock_lambda.arn
}

resource "aws_lambda_permission" "stock_lambda" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stock_lambda.arn
}