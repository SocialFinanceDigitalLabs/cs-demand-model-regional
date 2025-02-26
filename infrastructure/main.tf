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
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "eu-west-2"
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