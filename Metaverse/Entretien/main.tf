#--------------------------------------------------------------Provider--------------------------------------------------------------
data "aws_caller_identity" "current" {
}
variable "aws_region" {
  description = "Region we are deploying into"
  type        = string
  default     = "us-east-1"
}

variable "keys" {
  description = "Authentication keys"
  type        = map(string)
  default     = {
    access_key = ""
    secret_key = ""
  }
}

provider "aws" {
  access_key = var.keys["access_key"]
  secret_key = var.keys["secret_key"]
  region = var.aws_region
}
#--------------------------------------------------------------IAM Role--------------------------------------------------------------
resource "aws_iam_role" "quick_sight_admin_console" {
  name = "QuickSightAdminConsole"

  assume_role_policy = <<POLICY
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": [
              "lambda.amazonaws.com"
            ]
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    POLICY
}
resource "aws_iam_policy_attachment" "quick_sight_attachment" {
  name       = "QuickSight-AdminConsolePolicyAttachment"
  roles      = [aws_iam_role.quick_sight_admin_console.name]
  policy_arn = aws_iam_policy.quick_sight_admin_console_policy.arn
}
resource "aws_iam_policy" "quick_sight_admin_console_policy" {
  name        = "QuickSight-AdminConsolePolicy"
  description = "Allow access to ssm, lambda, log, qs, s3 and sts"
  policy      = data.aws_iam_policy_document.quick_sight_admin_console_policy_document.json
}
data "aws_iam_policy_document" "quick_sight_admin_console_policy_document" {
  statement {
    sid    = "BasePermissions"
    effect = "Allow"
    actions = [
      "ssm:GetParameters",
      "ssm:GetParameter",
      "ssm:GetParametersByPath",
      "lambda:InvokeFunction",
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents",
      "quicksight:ListNamespaces",
      "quicksight:DescribeNamespace",
      "quicksight:PassDataSet",
      "quicksight:ListThemeVersions",
      "quicksight:ListUserGroups",
      "quicksight:DescribeThemeAlias",
      "quicksight:SearchDashboards",
      "quicksight:DescribeUser",
      "quicksight:GetAuthCode",
      "quicksight:DescribeDataSetPermissions",
      "quicksight:DescribeDashboard",
      "quicksight:ListDataSources",
      "quicksight:ListGroups",
      "quicksight:DescribeDataSourcePermissions",
      "quicksight:DescribeAnalysisPermissions",
      "quicksight:ListThemeAliases",
      "quicksight:DescribeDataSource",
      "quicksight:ListGroupMemberships",
      "quicksight:DescribeDashboardPermissions",
      "quicksight:ListDashboards",
      "quicksight:PassDataSource",
      "quicksight:ListDataSets",
      "quicksight:ListUsers",
      "quicksight:ListIngestions",
      "quicksight:SearchAnalyses",
      "quicksight:ListAnalyses",
      "quicksight:ListDashboardVersions",
      "quicksight:DescribeIngestion",
      "quicksight:DescribeGroup",
      "quicksight:DescribeAnalysis",
      "quicksight:DescribeDataSet",
      "quicksight:GetGroupMapping",
      "quicksight:DescribeTheme",
      "quicksight:DescribeThemePermissions",
      "quicksight:ListThemes",
      "s3:HeadBucket",
      "s3:ListAllMyBuckets",
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:GetObjectVersionForReplication",
      "s3:GetBucketPolicy",
      "s3:GetObjectVersion",
      "cloudwatch:PutMetricData",
      "sts:GetCallerIdentity",
    "sts:AssumeRole"]
    resources = [
      "*"
    ]
  }
}
#--------------------------------------------------------------S3 Bucket--------------------------------------------------------------
module "adminconsole_bucket" {
  source = "terraform-aws-modules/s3-bucket/aws"

  bucket = join("", ["admin-console", data.aws_caller_identity.current.account_id])


  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  attach_deny_insecure_transport_policy = true
  attach_require_latest_tls_policy      = true

}
#--------------------------------------------------------------Lambda Function--------------------------------------------------------------
resource "aws_lambda_function" "adminconsoledataprepare" {
  filename      = "data_prepare.zip"
  function_name = "data_prepare"
  description   = "admin console dataprepare lambda function"

  environment {
    variables = {
      aws_region = var.aws_region
    }
  }
  handler          = "data_prepare.lambda_handler"
  source_code_hash = filebase64sha256("data_prepare.zip")

  runtime     = "python3.9"
  memory_size = "512"
  timeout     = "900"
  role        = aws_iam_role.quick_sight_admin_console.arn

  #   code_signing_config_arn = {
  #     S3Bucket = "admin-console-dataprepare-code"
  #     S3Key = "data_prepare.zip"
  #   }
}
resource "aws_lambda_permission" "adminconsolehourlyscheduledataprepare" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adminconsoledataprepare.arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adminconsolehourlyschedule.arn
}
#--------------------------------------------------------------CloudWatch Event Rule--------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "adminconsolehourlyschedule" {
  description         = "CloudWatch rule to run lambda every hour"
  name                = "admin-console-every-hour"
  schedule_expression = "cron(0 * * * ? *)"
}
resource "aws_cloudwatch_event_target" "check_adminconsolehourlyschedule" {
  rule      = aws_cloudwatch_event_rule.adminconsolehourlyschedule.name
  target_id = "adminconsoledataprepare"
  arn       = aws_lambda_function.adminconsoledataprepare.arn
}
resource "aws_lambda_permission" "allow_cloudwatch_to_call_adminconsoledataprepare" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.adminconsoledataprepare.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.adminconsolehourlyschedule.arn
}
#--------------------------------------------------------------Athena--------------------------------------------------------------
locals {
  create_tables_query = templatefile("athena/create_athena_tables.sql", {
    account_id = data.aws_caller_identity.current.account_id
  })
}
resource "aws_s3_bucket" "QlInsightsworkgroup" {
  bucket = join("", ["admin-console", data.aws_caller_identity.current.account_id])
}
resource "aws_kms_key" "QlInsightKMSKey" {
  deletion_window_in_days = 7
  description             = "Athena KMS Key"
}
resource "aws_athena_workgroup" "QlInsightsworkgroup" {
  name = "QlInsightsworkgroup"

  configuration {
    result_configuration {
      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = aws_kms_key.QlInsightKMSKey.arn
      }
    }
  }
}
resource "aws_athena_database" "insightsdb" {
  name   = "insightsdb"
  bucket = aws_s3_bucket.QlInsightsworkgroup.id
}
resource "aws_athena_named_query" "create_tables" {
  name      = "create_external_tables"
  database  = aws_athena_database.insightsdb.name
  workgroup = aws_athena_workgroup.QlInsightsworkgroup.id
  query     = local.create_tables_query
}
#--------------------------------------------------------------Outputs--------------------------------------------------------------
output "s3_bucket_id" {
  description = "The name of the bucket."
  value       = module.adminconsole_bucket.s3_bucket_id
}
#--------------------------------------------------------------End of File--------------------------------------------------------------