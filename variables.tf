variable "region" {
  type    = string
  default = "eu-north-1"
}

variable "lambda_name" {
  type    = string
  default = "stock-analyzer"
}

variable "account_identifier" {
  type    = string
}

variable "notification_email" {
  type = string
}