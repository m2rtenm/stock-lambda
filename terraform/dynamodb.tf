resource "aws_dynamodb_table" "stock_prices" {
  name = "${var.account_identifier}-${var.lambda_name}-State"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "symbol"

  table_class = "STANDARD_INFREQUENT_ACCESS"

  attribute {
    name = "symbol"
    type = "S"
  }
}