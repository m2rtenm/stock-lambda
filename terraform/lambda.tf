resource "null_resource" "build_function" {
  triggers = {
    source_hash       = filesha256("${path.module}/../python/StockAnalyzer.py")
    requirements_hash = filesha256("${path.module}/../python/lambda-requirements.txt")
    build_script_hash = filesha256("${path.module}/../python/build_lambda.sh")
  }

  provisioner "local-exec" {
    command = "sh \"${path.module}/../python/build_lambda.sh\""
  }
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../python/package"
  output_path = "${path.module}/../python/StockAnalyzer.zip"
  depends_on  = [null_resource.build_function]
}

resource "aws_lambda_function" "stock_lambda" {
  function_name = "${var.account_identifier}-${var.lambda_name}"
  role          = aws_iam_role.stock_lambda.arn
  handler       = "StockAnalyzer.lambda_handler" # File.function_name
  runtime       = "python3.12"
  timeout       = 180 # Seconds

  filename         = data.archive_file.function_zip.output_path
  source_code_hash = data.archive_file.function_zip.output_base64sha256

  memory_size = 256 # MB

  environment {
    variables = {
      "STOCK_SYMBOLS"        = var.stock_symbols
      "SNS_TOPIC_ARN"        = aws_sns_topic.stock_lambda.arn
      "THRESHOLD_PERCENT"    = var.threshold_percent
      "MIN_PERCENT_INCREASE" = var.min_percent_increase
      "DYNAMODB_TABLE_NAME"  = aws_dynamodb_table.stock_prices.name
      "REGION"               = var.region
    }
  }
}