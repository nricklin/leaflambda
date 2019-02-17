variable "nissan_username" {
	default = "your-nissan-username(email-address)"
}

variable "nissan_password" {
	default = "your-nissan-password"
}


variable "cache_and_data_s3_bucket" {
	default = "your-s3-bucket-for-caching-data-sfdhsahjd"
}

variable "role_for_lambda_name" {
	default = "lambda_role_for_leaf"
}

variable "region" {
  default = "us-east-1"
}

