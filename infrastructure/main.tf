terraform {
  backend "s3" {
    bucket = ""
    key    = ""
    region = ""
    dynamodb_table = ""
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    datadog = {
      source = "DataDog/datadog"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "eu-west-2"
}

provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
  api_url = "https://api.${var.datadog_site}"
}

resource "aws_s3_bucket" "bucket" {
  bucket = "${var.app}-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "bucket" {
  bucket = aws_s3_bucket.bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_policy" "bucket_policy" {
  name        = "${var.app}-${var.environment}-bucket-policy"
  path        = "/"
  description = "Allow access to bucket"

  policy = data.aws_iam_policy_document.bucket_policy.json
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    actions = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
    resources = [
          "${aws_s3_bucket.bucket.arn}",
          "${aws_s3_bucket.bucket.arn}/*"
        ]
    effect = "Allow"
  }
}

resource "aws_s3_bucket_versioning" "bucket_versioning" {
  bucket = aws_s3_bucket.bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "bucket_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.bucket_versioning]
  bucket = aws_s3_bucket.bucket.id

  rule {
    id = "expiration"

    filter {}

    noncurrent_version_expiration {
      newer_noncurrent_versions = 10
      # We only want noncurrent versions as above, but the terraform will error without the below
      # See https://github.com/hashicorp/terraform-provider-aws/issues/34197
      noncurrent_days = 90
    }

    status = "Enabled"
  }
}

resource "aws_backup_vault" "backup_vault" {
  name        = "${var.app}-${var.environment}-backup-vault"
}

resource "aws_backup_plan" "bucket_backup" {
  name = "${var.app}-${var.environment}-backup-plan"

  rule {
    rule_name         = "${var.app}-${var.environment}-backup-rule"
    target_vault_name = aws_backup_vault.backup_vault.name
    schedule          = "cron(0 0 * * ? *)"

    lifecycle {
      delete_after = 14
    }
  }
}

data "aws_iam_policy_document" "assume_role_backup" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "backup_user" {
  name               = "${var.app}-${var.environment}-backup-user"
  assume_role_policy = data.aws_iam_policy_document.assume_role_backup.json
}

resource "aws_iam_role_policy_attachment" "backup_role_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AWSBackupServiceRolePolicyForS3Backup"
  role       = aws_iam_role.backup_user.name
}

resource "aws_backup_selection" "backup_selection" {
  iam_role_arn = aws_iam_role.backup_user.arn
  name         = "${var.app}-${var.environment}-backup-selection"
  plan_id      = aws_backup_plan.bucket_backup.id

  resources = [
    aws_s3_bucket.bucket.arn
  ]
}

resource "aws_iam_user" "bucket_user" {
  name = "${var.app}-${var.environment}-bucket-user"
}

resource "aws_iam_user_policy_attachment" "attachment" {
  user       = aws_iam_user.bucket_user.name
  policy_arn = aws_iam_policy.bucket_policy.arn
}


resource "aws_iam_access_key" "bucket_user" {
  user    = aws_iam_user.bucket_user.name
}

### Datadog
data "aws_iam_policy_document" "datadog_aws_integration_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::464622532012:root"]
    }
    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values = [
        "${datadog_integration_aws_account.datadog_integration.auth_config.aws_auth_config_role.external_id}"
      ]
    }
  }
}

data "datadog_integration_aws_iam_permissions" "datadog_permissions" {}

locals {
  all_permissions = data.datadog_integration_aws_iam_permissions.datadog_permissions.iam_permissions

  max_policy_size = 6144
  target_chunk_size = 5900

  permission_sizes = [
    for perm in local.all_permissions :
    length(perm) + 3
  ]
  cumulative_sizes = [
    for i in range(length(local.permission_sizes)) :
    sum(slice(local.permission_sizes, 0, i + 1))
  ]

  chunk_assignments = [
    for cumulative_size in local.cumulative_sizes :
    floor(cumulative_size / local.target_chunk_size)
  ]
  chunk_numbers = distinct(local.chunk_assignments)
  permission_chunks = [
    for chunk_num in local.chunk_numbers : [
      for i, perm in local.all_permissions :
      perm if local.chunk_assignments[i] == chunk_num
    ]
  ]
}

data "aws_iam_policy_document" "datadog_aws_integration" {
  count = length(local.permission_chunks)

  statement {
    actions   = local.permission_chunks[count.index]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "datadog_aws_integration" {
  count = length(local.permission_chunks)

  name   = "DatadogAWSIntegrationPolicy-${count.index + 1}"
  policy = data.aws_iam_policy_document.datadog_aws_integration[count.index].json
}

resource "aws_iam_role" "datadog_aws_integration" {
  name               = "DatadogIntegrationRole"
  description        = "Role for Datadog AWS Integration"
  assume_role_policy = data.aws_iam_policy_document.datadog_aws_integration_assume_role.json
}

resource "aws_iam_role_policy_attachment" "datadog_aws_integration" {
  count = length(local.permission_chunks)

  role       = aws_iam_role.datadog_aws_integration.name
  policy_arn = aws_iam_policy.datadog_aws_integration[count.index].arn
}

resource "aws_iam_role_policy_attachment" "datadog_aws_integration_security_audit" {
  role       = aws_iam_role.datadog_aws_integration.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}

resource "datadog_integration_aws_account" "datadog_integration" {
  account_tags   = [
    "env:${var.app}-${var.environment}",
    "aws_account:${var.account_id}"
  ]
  aws_account_id = var.account_id
  aws_partition  = "aws"
  aws_regions {
    include_all = true
  }
  auth_config {
    aws_auth_config_role {
      role_name = "DatadogIntegrationRole"
    }
  }
  resources_config {
    cloud_security_posture_management_collection = true
    extended_collection                          = true
  }
  traces_config {
    xray_services {
    }
  }
  logs_config {
    # This block should be empty on initial apply and then populated after the datadog_forwarder is applied
    # and the arn is known. This is to avoid a circular dependency. Destroy should copy the same pattern in reverse.
    lambda_forwarder {
      lambdas = [module.datadog_forwarder.datadog_forwarder_arn]
      sources = ["lambda", "s3", "cloudtrail"]
    }
  }
  metrics_config {
    namespace_filters {
    }
  }
}

module "datadog_forwarder" {
  source  = "DataDog/log-lambda-forwarder-datadog/aws"
  version = "~> 1.0"

  dd_api_key = var.datadog_api_key
  dd_site    = var.datadog_site
}


### CloudTrail
resource "aws_s3_bucket" "cloudtrail_logs" {
  #checkov:skip=CKV_AWS_145:Data encrypted at rest via SSE-S3. In future consider KMS
  #checkov:skip=CKV2_AWS_62:Passing cloudtrail logs to Datadog from S3 bucket directly, can skip SNS for now
  #checkov:skip=CKV_AWS_144:Cross-region replication not needed for cloudtrail logs. Consider in future
  #checkov:skip=CKV_AWS_18:ToDo - enable S3 access logging
  bucket = "${var.app}-${var.environment}-cloudtrail-logs"
}

resource "aws_s3_bucket_public_access_block" "cloudtrail_logs_access" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "cloudtrail_logs_versioning" {
  bucket = aws_s3_bucket.cloudtrail_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail_logs_lifecycle" {
  # Must have bucket versioning enabled first
  depends_on = [aws_s3_bucket_versioning.cloudtrail_logs_versioning]
  bucket     = aws_s3_bucket.cloudtrail_logs.id

  rule {
    id = "expiration"

    filter {}

    expiration {
      days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    status = "Enabled"
  }
}

resource "aws_s3_bucket_policy" "cloudtrail_policy" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.cloudtrail_logs.arn
        Condition = {
          StringEquals = {
            # Construct the Source ARN for the CloudTrail trail to prevent a circular dependency
            "AWS:SourceArn" = "arn:aws:cloudtrail:eu-west-2:${var.account_id}:trail/${local.trail_name}",
          }
        }
      },
      {
        Sid       = "CloudTrailWriteManagementAccount"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.cloudtrail_logs.arn}/AWSLogs/${var.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"  = "bucket-owner-full-control"
            "AWS:SourceArn" = "arn:aws:cloudtrail:eu-west-2:${var.account_id}:trail/${local.trail_name}",
          }
        }
      },
    ]
  })
}

resource "aws_cloudtrail" "s3_data_trail" {
  #checkov:skip=CKV_AWS_252:No SNS topic needed currently as we'll be forwarding logs to Datadog from S3
  #checkov:skip=CKV_AWS_35:Data encrypted at rest via SSE-S3. In future consider KMS
  #checkov:skip=CKV2_AWS_10:Passing cloudtrail logs to Datadog from S3 bucket directly, can skip Cloudwatch for now
  name                          = local.trail_name
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  s3_bucket_name                = aws_s3_bucket.cloudtrail_logs.bucket
  enable_logging                = true

  event_selector {
    include_management_events = false
    read_write_type           = "All"
    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.bucket.arn}/"]
    }
  }

  depends_on = [aws_s3_bucket_policy.cloudtrail_policy]
}

locals {
  trail_name = "${var.app}-${var.environment}-s3-cloudtrail"
}
