resource "null_resource" "lambda_layer_packer" {
  triggers = {
    requirements_hash = filebase64sha256("${path.module}/../python/requirements.txt")
  }

  provisioner "local-exec" {
    command     = <<-EOT
      echo "--- Packaging Lambda Layer dependencies ---"
      LAYER_BUILD_DIR="../python/build/layer"
      LAYER_ZIP_PATH="../python/dependencies.zip"
      
      # Clean up previous build
      rm -rf $LAYER_BUILD_DIR
      rm -f $LAYER_ZIP_PATH
      
      # Recreate directory with the 'python' subdirectory required by Lambda Layers
      mkdir -p $LAYER_BUILD_DIR/python
      
      # Install dependencies from requirements.txt into that specific folder
      pip install -r ../python/requirements.txt -t $LAYER_BUILD_DIR/python --quiet
      
      # Create the zip file from within the build directory
      cd $LAYER_BUILD_DIR && zip -r $LAYER_ZIP_PATH . -q
      echo "--- Layer packaging complete ---"
    EOT
    interpreter = ["bash", "-c"]
  }
}

data "archive_file" "stock_lambda" {
  type        = "zip"
  source_file = "${path.module}/../python/StockAnalyzer.py"
  output_path = "${path.module}/../python/StockAnalyzer.zip"
}

resource "aws_lambda_layer_version" "stock_lambda" {
  depends_on          = [null_resource.lambda_layer_packer]
  layer_name          = "${var.lambda_name}-Dependencies"
  filename            = "${path.module}/../python/dependencies.zip"
  source_code_hash    = null_resource.lambda_layer_packer.triggers.requirements_hash
  compatible_runtimes = ["python3.12"]
}


resource "aws_lambda_function" "stock_lambda" {
  function_name = "${var.account_identifier}-${var.lambda_name}"
  role          = aws_iam_role.stock_lambda.arn
  handler       = "StockAnalyzer.test" # File.function_name
  runtime       = "python3.12"
  timeout       = 30 # Seconds

  filename         = data.archive_file.stock_lambda.output_path
  source_code_hash = data.archive_file.stock_lambda.output_base64sha256

  layers = [aws_lambda_layer_version.stock_lambda.arn]
  environment { # TODO: add env variables
    variables = {
      "STOCK_SYMBOLS"       = var.stock_symbols
      "SNS_TOPIC_ARN"       = aws_sns_topic.stock_lambda.arn
      "THRESHOLD_PERCENT"   = var.threshold_percent
      "DYNAMODB_TABLE_NAME" = aws_dynamodb_table.stock_prices.name
      "AWS_REGION"          = var.region
    }
  }
}