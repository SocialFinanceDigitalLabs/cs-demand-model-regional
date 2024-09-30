output "secret_access_key" {
  description = "Secret access key for bucket-user"
  value       = aws_iam_access_key.bucket_user.secret
  sensitive   = true
}