terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.6.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "0.11.1"
    }
    random = {
      source = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}