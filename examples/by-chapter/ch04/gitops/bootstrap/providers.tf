terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
  }
  backend "s3" {
    bucket  = "order-demo-tfstate"
    key     = "order-demo/cluster.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
