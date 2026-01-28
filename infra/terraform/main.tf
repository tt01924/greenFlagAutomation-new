# Green Flag Automation - Terraform Infrastructure
# Provisions RDS PostgreSQL, ElastiCache Redis, and S3 audit archive bucket

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "skyscanner-terraform-state"
    key    = "green-flag-automation/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "green-flag-automation"
      Team        = "cassini"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["cassini-vpc"]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }

  filter {
    name   = "tag:Type"
    values = ["private"]
  }
}

data "aws_security_group" "eks_nodes" {
  filter {
    name   = "tag:Name"
    values = ["cassini-eks-node-sg"]
  }
}

# Security Group for RDS and ElastiCache
resource "aws_security_group" "green_flag_automation" {
  name_prefix = "green-flag-automation-"
  description = "Security group for Green Flag Automation RDS and ElastiCache"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [data.aws_security_group.eks_nodes.id]
  }

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [data.aws_security_group.eks_nodes.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "green-flag-automation-sg"
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "green_flag_automation" {
  name       = "green-flag-automation"
  subnet_ids = data.aws_subnets.private.ids

  tags = {
    Name = "green-flag-automation"
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "green_flag_automation" {
  identifier = "green-flag-automation-${var.environment}"

  engine         = "postgres"
  engine_version = "14.10"
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "green_flag_automation"
  username = var.rds_username
  password = var.rds_password

  db_subnet_group_name   = aws_db_subnet_group.green_flag_automation.name
  vpc_security_group_ids = [aws_security_group.green_flag_automation.id]

  multi_az               = var.environment == "production" ? true : false
  backup_retention_period = var.rds_backup_retention_days
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = true
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "green-flag-automation-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  tags = {
    Name = "green-flag-automation-${var.environment}"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "green_flag_automation" {
  name       = "green-flag-automation"
  subnet_ids = data.aws_subnets.private.ids

  tags = {
    Name = "green-flag-automation"
  }
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "green_flag_automation" {
  replication_group_id       = "gfa-${var.environment}"
  replication_group_description = "Redis cluster for Green Flag Automation ticket queue"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  parameter_group_name = "default.redis7"

  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.green_flag_automation.name
  security_group_ids         = [aws_security_group.green_flag_automation.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_auth_token

  automatic_failover_enabled = var.environment == "production" ? true : false
  multi_az_enabled           = var.environment == "production" ? true : false

  snapshot_retention_limit = var.redis_snapshot_retention_days
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "mon:05:00-mon:07:00"

  notification_topic_arn = var.sns_topic_arn

  tags = {
    Name = "green-flag-automation-${var.environment}"
  }
}

# S3 Bucket for Audit Log Archive
resource "aws_s3_bucket" "audit_archive" {
  bucket = "skyscanner-green-flag-automation-audit-archive-${var.environment}"

  tags = {
    Name        = "green-flag-automation-audit-archive"
    Purpose     = "audit-log-archive"
    Retention   = "90-days"
  }
}

resource "aws_s3_bucket_versioning" "audit_archive" {
  bucket = aws_s3_bucket.audit_archive.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_archive" {
  bucket = aws_s3_bucket.audit_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_archive" {
  bucket = aws_s3_bucket.audit_archive.id

  rule {
    id     = "archive-old-logs"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_archive" {
  bucket = aws_s3_bucket.audit_archive.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for RDS Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "green-flag-automation-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# IAM Role for EKS Service Account (IRSA)
resource "aws_iam_role" "green_flag_automation_pod" {
  name = "green-flag-automation-pod-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = var.eks_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${var.eks_oidc_provider}:sub" = "system:serviceaccount:cassini:green-flag-automation"
            "${var.eks_oidc_provider}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

# IAM Policy for S3 Audit Archive Access
resource "aws_iam_policy" "s3_audit_archive" {
  name        = "green-flag-automation-s3-audit-${var.environment}"
  description = "Allow Green Flag Automation to write audit logs to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.audit_archive.arn,
          "${aws_s3_bucket.audit_archive.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "pod_s3_access" {
  role       = aws_iam_role.green_flag_automation_pod.name
  policy_arn = aws_iam_policy.s3_audit_archive.arn
}

# Outputs
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.green_flag_automation.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.green_flag_automation.primary_endpoint_address
  sensitive   = true
}

output "s3_audit_bucket" {
  description = "S3 bucket for audit log archive"
  value       = aws_s3_bucket.audit_archive.id
}

output "pod_role_arn" {
  description = "IAM role ARN for pod service account"
  value       = aws_iam_role.green_flag_automation_pod.arn
}
