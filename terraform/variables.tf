variable "region" {
  type    = string
  default = "eu-north-1"
}

variable "lambda_name" {
  type    = string
  default = "stock-analyzer"
}

variable "account_identifier" {
  type = string
}

variable "notification_email" {
  type = string
}

variable "stock_symbols" {
  type        = string
  description = "A comma-separated list of stock symbols to monitor"
}

variable "threshold_percent" {
  type = number
}