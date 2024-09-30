terraform {
  backend "s3" {
    bucket = "demand-model-terraform-state"
    key    = "state"
    region = "eu-west-2"
    dynamodb_table = "demand-model-terraform-state-dynamodb"
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