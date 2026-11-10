terraform {
  backend "s3" {
    bucket  = "order-demo-tfstate"
    key     = "order-demo/cluster.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
