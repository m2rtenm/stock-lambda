resource "null_resource" "yfinance_layer" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "--- Installing yfinance (no deps) ---"
      LAYER_DIR="./../python/build/yfinance/python"
      rm -rf "$LAYER_DIR"
      mkdir -p "$LAYER_DIR"
      pip install yfinance --no-deps -t "$LAYER_DIR"
      cd "./../python/build/yfinance"
      python3 -c 'import shutil; shutil.make_archive("../python/yfinance-layer", "zip", ".")'
    EOT
  }
}

data "archive_file" "yfinance_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../python/build/yfinance"
  output_path = "${path.module}/../python/yfinance-layer.zip"
  depends_on  = [null_resource.yfinance_layer]
}

resource "aws_lambda_layer_version" "yfinance" {
  layer_name          = "${var.lambda_name}-yfinance"
  filename            = data.archive_file.yfinance_layer_zip.output_path
  source_code_hash    = data.archive_file.yfinance_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.12"]
}

resource "null_resource" "deps_layer" {
  provisioner "local-exec" {
    command = <<-EOT
      echo "--- Installing dependencies ---"
      LAYER_DIR="./../python/build/deps/python"
      rm -rf "$LAYER_DIR"
      mkdir -p "$LAYER_DIR"
      pip install pandas numpy requests -t "$LAYER_DIR"
      cd "./../python/build/deps"
      python3 -c 'import shutil; shutil.make_archive("../python/deps-layer", "zip", ".")'
    EOT
  }
}

data "archive_file" "deps_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../python/build/deps"
  output_path = "${path.module}/../python/deps-layer.zip"
  depends_on  = [null_resource.deps_layer]
}

resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.lambda_name}-deps"
  filename            = data.archive_file.deps_layer_zip.output_path
  source_code_hash    = data.archive_file.deps_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.12"]
}


resource "null_resource" "build_function" {
  provisioner "local-exec" {
    command     = <<-EOT
      zip -j "${path.module}/../python/StockAnalyzer.zip" "${path.module}/../python/StockAnalyzer.py" > /dev/null
    EOT
    interpreter = ["bash", "-c"]
  }
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_file = "${path.module}/../python/StockAnalyzer.py"
  output_path = "${path.module}/../python/StockAnalyzer.zip"
  depends_on  = [null_resource.build_function]
}

resource "aws_lambda_function" "stock_lambda" {
  function_name = "${var.account_identifier}-${var.lambda_name}"
  role          = aws_iam_role.stock_lambda.arn
  handler       = "StockAnalyzer.lambda_handler" # File.function_name
  runtime       = "python3.12"
  timeout       = 30 # Seconds

  filename         = data.archive_file.function_zip.output_path
  source_code_hash = data.archive_file.function_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.dependencies.arn,
    aws_lambda_layer_version.yfinance.arn
  ]

  environment { # TODO: add env variables
    variables = {
      "STOCK_SYMBOLS"       = var.stock_symbols
      "SNS_TOPIC_ARN"       = aws_sns_topic.stock_lambda.arn
      "THRESHOLD_PERCENT"   = var.threshold_percent
      "DYNAMODB_TABLE_NAME" = aws_dynamodb_table.stock_prices.name
      "REGION"              = var.region
    }
  }
}