resource "null_resource" "lambda_layer_packer" {
  # These triggers tell Terraform to re-run this resource if the source files change.
  triggers = {
    source_code_hash  = filebase64sha256("${path.module}/../python/StockAnalyzer.py")
    requirements_hash = filebase64sha256("${path.module}/../python/requirements.txt")
  }

  # This provisioner runs local shell commands to create the package.
  provisioner "local-exec" {
    # These commands are run from your 'terraform' directory.
    command = <<-EOT
      echo "--- Packaging Lambda function ---"
      PACKAGE_DIR="../python/package"
      ZIP_FILE="../python/StockAnalyzer.zip"
      
      # Clean up previous package to ensure a fresh build
      rm -rf $PACKAGE_DIR
      rm -f $ZIP_FILE
      
      # Create package directory and install dependencies from requirements.txt
      mkdir -p $PACKAGE_DIR
      pip install -r ../python/requirements.txt -t $PACKAGE_DIR --quiet
      
      # Copy your source code into the package
      cp ../python/StockAnalyzer.py $PACKAGE_DIR/
      
      # Create the zip file from within the package directory
      cd $PACKAGE_DIR && zip -r $ZIP_FILE . -q
      echo "--- Packaging complete ---"
    EOT
    # Using bash is recommended for cross-platform compatibility (e.g., Windows with Git Bash)
    interpreter = ["bash", "-c"]
  }
}

resource "aws_lambda_function" "stock_lambda" {
  function_name = "${var.account_identifier}-${var.lambda_name}"
  role          = aws_iam_role.stock_lambda.arn
  handler       = "StockAnalyzer.lambda_handler" # File.function_name
  runtime       = "python3.12"
  timeout       = 30 # Seconds

  filename         = "${path.module}/../python/StockAnalyzer.zip"
  source_code_hash = null_resource.lambda_layer_packer.triggers.source_code_hash

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