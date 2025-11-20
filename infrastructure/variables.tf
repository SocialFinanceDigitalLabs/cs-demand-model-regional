variable "environment" {
  description = "The environment of the application"
}

variable "app" {
  description = "The name of the application"
}

variable "account_id" {
  description = "The AWS account ID"
}

variable "datadog_api_key" {
  description = "Datadog API key for monitoring"
}

variable "datadog_app_key" {
  description = "Datadog Application key for monitoring"
}

variable "datadog_site" {
  description = "Datadog site to send metrics to"
  default     = "datadoghq.eu"
}