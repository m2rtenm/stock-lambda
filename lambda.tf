data "archive_file" "stock_lambda" {
  type        = "zip"
  source_file = "${path.module}/StockAnalyzer.py"
  output_path = "${path.module}/StockAnalyzer.zip"
}


resource "aws_lambda_function" "stock_lambda" {
  function_name = "${var.account_identifier}-${var.lambda_name}"
  role          = aws_iam_role.stock_lambda.arn
  handler       = "StockAnalyzer.test" # File.function_name
  runtime       = "python3.12"
  timeout       = 30 # Seconds

  filename         = data.archive_file.stock_lambda.output_path
  source_code_hash = data.archive_file.stock_lambda.output_base64sha256

  environment { # TODO: add env variables
    variables = {
      "key"  = ""
      "key2" = ""
    }
  }
}