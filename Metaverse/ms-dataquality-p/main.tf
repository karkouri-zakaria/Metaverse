provider "aws" {
    region = "us-east-1"  # AWS region
    access_key                  = "test"
    secret_key                  = "test"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true

    endpoints {
      apigateway     = "http://localhost:4566"
      kms            = "http://localhost:4566"
      cloudformation = "http://localhost:4566"
      cloudwatch     = "http://localhost:4566"
      dynamodb       = "http://localhost:4566"
      ec2            = "http://localhost:4566"
      elasticache    = "http://localhost:4566"
      iam            = "http://localhost:4566"
      lambda         = "http://localhost:4566"
      rds            = "http://localhost:4566"
      s3             = "http://s3.localhost.localstack.cloud:4566"
      ses            = "http://localhost:4566"
      stepfunctions  = "http://localhost:4566"
    }
}

variable "user_id" {
  description = "The user ID"
  type        = string
}

variable "instance_id" {
  description = "The instance ID"
  type        = string
}

variable "instance_type" {
  description = "The instance type: s3 or google_drive"
  type        = string
  default     = "s3"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

locals {
  lambda_function_name = "${var.instance_id}_${var.instance_type}_lambda" # Removed user_id as the IAM role name has a limit of 64 characters
  iam_role_name        = "${var.instance_id}_${var.instance_type}_lambda_role" # Removed user_id as the IAM role name has a limit of 64 characters  
  kms_key_alias        = "${var.user_id}_${var.instance_id}_${var.instance_type}_kms_key"
}

# KMS Key for Lambda
resource "aws_kms_key" "my_key" {
  description             = "KMS key for encrypting credentials"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

resource "aws_kms_alias" "my_key_alias" {
  name          = "alias/${local.kms_key_alias}"
  target_key_id = aws_kms_key.my_key.id
}


# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_exec_role" {
  name = local.iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach policy to IAM role
resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Create a policy allowing secretsmanager:GetSecretValue action
resource "aws_iam_policy" "secretsmanager_policy" {
  name        = "${var.user_id}_${var.instance_id}_${var.instance_type}_secretsmanager_policy"
  description = "Policy to allow secretsmanager:GetSecretValue action"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach the secretsmanager policy to the IAM role
resource "aws_iam_role_policy_attachment" "secretsmanager_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.secretsmanager_policy.arn
}

# Create a policy allowing kms:Decrypt action
resource "aws_iam_policy" "kms_decrypt_policy" {
  name        = "${var.user_id}_${var.instance_id}_${var.instance_type}_kms_decrypt_policy"
  description = "Policy to allow kms:Decrypt action"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kms:Decrypt"
        ],
        Resource = aws_kms_key.my_key.arn
      }
    ]
  })
}

# Attach the kms:Decrypt policy to the IAM role
resource "aws_iam_role_policy_attachment" "kms_decrypt_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.kms_decrypt_policy.arn
}

# Lambda function resource
resource "aws_lambda_function" "S3_lambda" {
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  s3_bucket     = "handlers"
  s3_key        = "lambda_function.zip"
  timeout       = 900

  environment {
    variables = {
      USER_ID       = var.user_id
      INSTANCE_ID   = var.instance_id
      INSTANCE_TYPE = var.instance_type
      SECRET_NAME   = aws_secretsmanager_secret.credentials_secret.name
    }
  }
}


# Create a policy allowing necessary actions
resource "aws_iam_policy" "lambda_additional_permissions" {
  name        = "${var.user_id}_${var.instance_id}_${var.instance_type}_additional_permissions_policy"
  description = "Policy to allow additional permissions for Lambda functions"


  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
        "kms:*",       
        "ecr:*",     
        "lambda:*",
        "iam:*"       
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach the additional permissions policy to the IAM role
resource "aws_iam_role_policy_attachment" "additional_permissions_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_additional_permissions.arn
}



#----------------- Secrets Manager -----------------#
resource "aws_secretsmanager_secret" "credentials_secret" {
  name = "${var.user_id}_${var.instance_id}_${var.instance_type}_secrets"

  description = "Secrets for ${var.user_id} and ${var.instance_id}"
}

resource "aws_secretsmanager_secret_version" "credentials_secret_version" {
  secret_id     = aws_secretsmanager_secret.credentials_secret.id
  secret_string = jsonencode({
    "ENCRYPTED_ACCESS_KEY": "test",
    "ENCRYPTED_SECRET_KEY": "test",
    "REGION": "us-east-1"
})
}