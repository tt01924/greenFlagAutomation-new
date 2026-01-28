# Green Flag Automation - Deployment Guide

This guide covers deploying Green Flag Automation to production using Terraform (infrastructure) and Kubernetes (application).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Deployment (Terraform)](#infrastructure-deployment-terraform)
3. [Application Deployment (Kubernetes)](#application-deployment-kubernetes)
4. [Verification](#verification)
5. [Rollback Procedures](#rollback-procedures)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- **kubectl** (v1.25+): Kubernetes CLI
- **terraform** (v1.0+): Infrastructure as Code
- **aws-cli** (v2): AWS CLI configured with credentials
- **Docker**: For building container images
- **helm** (optional): For managing Kubernetes deployments

### AWS Requirements

- EKS cluster already provisioned (name: `cassini-eks`)
- VPC with private subnets tagged with `Type=private`
- EKS node security group tagged with `Name=cassini-eks-node-sg`
- SNS topic for infrastructure alerts
- ECR repository: `skyscanner/green-flag-automation`

### Credentials Required

- AWS credentials with permissions for RDS, ElastiCache, S3, IAM
- Jira API token
- Slack bot token
- Anthropic API key (or OpenAI API key)
- Redis AUTH token (generate with: `openssl rand -base64 32`)
- PostgreSQL master password (generate with: `openssl rand -base64 32`)

---

## Infrastructure Deployment (Terraform)

### Step 1: Configure Variables

Create `infra/terraform/terraform.tfvars` from the example:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:

```hcl
aws_region  = "eu-west-1"
environment = "production"

# RDS Configuration
rds_instance_class      = "db.t4g.large"
rds_allocated_storage   = 100
rds_max_allocated_storage = 500
rds_username            = "gfa_admin"
rds_password            = "<STRONG_PASSWORD>"  # Use AWS Secrets Manager
rds_backup_retention_days = 7

# ElastiCache Redis Configuration
redis_node_type             = "cache.t4g.medium"
redis_auth_token            = "<STRONG_TOKEN>"  # openssl rand -base64 32
redis_snapshot_retention_days = 5

# EKS Configuration (from your existing EKS cluster)
eks_oidc_provider_arn = "arn:aws:iam::ACCOUNT_ID:oidc-provider/oidc.eks.eu-west-1.amazonaws.com/id/OIDC_ID"
eks_oidc_provider     = "oidc.eks.eu-west-1.amazonaws.com/id/OIDC_ID"

# Notifications
sns_topic_arn = "arn:aws:sns:eu-west-1:ACCOUNT_ID:cassini-infrastructure-alerts"
```

**Get EKS OIDC Provider:**

```bash
# Get your EKS cluster OIDC provider
aws eks describe-cluster --name cassini-eks --query "cluster.identity.oidc.issuer" --output text
# Output: https://oidc.eks.eu-west-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

# Extract the ID and ARN
EKS_OIDC_ID=$(aws eks describe-cluster --name cassini-eks --query "cluster.identity.oidc.issuer" --output text | cut -d '/' -f 5)
EKS_OIDC_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/oidc.eks.eu-west-1.amazonaws.com/id/${EKS_OIDC_ID}"

echo "eks_oidc_provider_arn = \"${EKS_OIDC_ARN}\""
echo "eks_oidc_provider     = \"oidc.eks.eu-west-1.amazonaws.com/id/${EKS_OIDC_ID}\""
```

### Step 2: Initialize Terraform

```bash
cd infra/terraform
terraform init
```

This will:
- Download AWS provider
- Configure S3 backend for state storage

### Step 3: Plan Infrastructure Changes

```bash
terraform plan -out=tfplan
```

Review the plan carefully. Terraform will create:
- RDS PostgreSQL instance with Multi-AZ (production)
- ElastiCache Redis replication group
- S3 bucket for audit log archive
- Security groups
- IAM roles and policies

### Step 4: Apply Infrastructure

```bash
terraform apply tfplan
```

This takes approximately 15-20 minutes. Terraform will output:
- `rds_endpoint`: PostgreSQL connection endpoint
- `redis_endpoint`: Redis connection endpoint
- `s3_audit_bucket`: S3 bucket name
- `pod_role_arn`: IAM role ARN for pod service account

**Save these outputs** - you'll need them for Kubernetes configuration.

### Step 5: Retrieve Outputs

```bash
# Get sensitive outputs
terraform output rds_endpoint
terraform output redis_endpoint
terraform output pod_role_arn
terraform output s3_audit_bucket
```

---

## Application Deployment (Kubernetes)

### Step 1: Build and Push Docker Image

```bash
# Build backend image
cd backend
docker build -t skyscanner/green-flag-automation:latest .

# Build frontend (production build embedded in backend image)
cd ../frontend
npm run build
# (Frontend build is copied into backend image via Dockerfile)

# Push to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com
docker tag skyscanner/green-flag-automation:latest <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/green-flag-automation:latest
docker push <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/green-flag-automation:latest
```

### Step 2: Configure kubectl

```bash
# Configure kubectl to use your EKS cluster
aws eks update-kubeconfig --name cassini-eks --region eu-west-1

# Verify connection
kubectl get nodes
```

### Step 3: Create Kubernetes Secrets

Create secrets file from template:

```bash
cd infra/k8s
cp secrets.yaml secrets-production.yaml
```

Edit `secrets-production.yaml` and set base64-encoded values:

```bash
# Encode secrets
echo -n "postgresql://gfa_admin:<PASSWORD>@<RDS_ENDPOINT>:5432/green_flag_automation" | base64
echo -n "<REDIS_ENDPOINT>" | base64
echo -n "<REDIS_AUTH_TOKEN>" | base64
echo -n "<JIRA_API_TOKEN>" | base64
echo -n "<SLACK_BOT_TOKEN>" | base64
echo -n "<ANTHROPIC_API_KEY>" | base64
```

Apply secrets:

```bash
kubectl apply -f secrets-production.yaml
```

**Important**: Do NOT commit `secrets-production.yaml` to git. Add it to `.gitignore`.

### Step 4: Create ConfigMap for Canned Responses

```bash
# Create ConfigMap from canned_responses.yaml
kubectl create configmap green-flag-automation-config \
  --namespace=cassini \
  --from-file=canned_responses.yaml=../../backend/src/config/canned_responses.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 5: Apply Service Account and RBAC

```bash
kubectl apply -f service.yaml
```

This creates:
- ServiceAccount with IAM role annotation (IRSA)
- ClusterRole for ConfigMap/Secret access
- Service (LoadBalancer with SSL)

### Step 6: Deploy Application

```bash
# Deploy API and Worker
kubectl apply -f deployment.yaml

# Watch rollout status
kubectl rollout status deployment/green-flag-automation-api -n cassini
kubectl rollout status deployment/green-flag-automation-worker -n cassini
```

### Step 7: Deploy CronJobs

```bash
# Deploy daily summary and audit cleanup jobs
kubectl apply -f cronjob.yaml
```

Verify CronJobs:

```bash
kubectl get cronjobs -n cassini
# Expected output:
# NAME                                    SCHEDULE      SUSPEND   ACTIVE
# green-flag-automation-daily-summary     0 9 * * *     False     0
# green-flag-automation-audit-cleanup     0 2 * * 0     False     0
```

### Step 8: Run Database Migrations

```bash
# Exec into API pod
kubectl exec -it deployment/green-flag-automation-api -n cassini -- bash

# Run Alembic migrations
alembic upgrade head

# Exit pod
exit
```

### Step 9: Get LoadBalancer URL

```bash
kubectl get service green-flag-automation-api -n cassini

# Output:
# NAME                         TYPE           CLUSTER-IP      EXTERNAL-IP                                          PORT(S)
# green-flag-automation-api    LoadBalancer   10.100.X.X      a1234567890abcdef-123456789.eu-west-1.elb.amazonaws.com   443:32000/TCP
```

Configure DNS to point to the LoadBalancer EXTERNAL-IP:
```bash
# Example: Create CNAME record
green-flag-automation.cassini.skyscanner.net -> <EXTERNAL-IP>
```

---

## Verification

### Health Checks

```bash
# Check pod status
kubectl get pods -n cassini -l app=green-flag-automation

# Check logs
kubectl logs -f deployment/green-flag-automation-api -n cassini
kubectl logs -f deployment/green-flag-automation-worker -n cassini

# Test health endpoint
curl https://green-flag-automation.cassini.skyscanner.net/api/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}

# Test readiness
kubectl exec -it deployment/green-flag-automation-api -n cassini -- curl http://localhost:8000/api/health/ready
```

### Database Connection

```bash
# Test database connection from pod
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.models.base import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected:', result.fetchone())
"
```

### Redis Connection

```bash
# Test Redis connection
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.services.queue import TicketQueue
queue = TicketQueue()
print('Redis connected:', queue.redis_client.ping())
"
```

### Prometheus Metrics

```bash
# Check metrics endpoint
curl https://green-flag-automation.cassini.skyscanner.net/api/metrics
# Expected: Prometheus-formatted metrics
```

### End-to-End Test

```bash
# Send test webhook (from your local machine or test pod)
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "webhookEvent": "jira:issue_created",
    "issue": {
      "key": "TEST-123",
      "fields": {
        "summary": "Test ticket",
        "description": "How do I reset my password?",
        "reporter": {"emailAddress": "test@example.com"}
      }
    }
  }'

# Check if ticket was processed
kubectl logs -f deployment/green-flag-automation-worker -n cassini | grep "TEST-123"
```

---

## Rollback Procedures

### Rollback Kubernetes Deployment

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/green-flag-automation-api -n cassini
kubectl rollout undo deployment/green-flag-automation-worker -n cassini

# Check rollout status
kubectl rollout status deployment/green-flag-automation-api -n cassini

# Rollback to specific revision
kubectl rollout history deployment/green-flag-automation-api -n cassini
kubectl rollout undo deployment/green-flag-automation-api -n cassini --to-revision=2
```

### Rollback Terraform Infrastructure

```bash
cd infra/terraform

# Revert to previous state (if you have backup)
terraform state pull > backup-$(date +%Y%m%d-%H%M%S).tfstate

# Apply previous configuration
git checkout <previous-commit>
terraform apply
```

### Emergency Kill Switch

```bash
# Disable automation immediately via kill switch
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/disable \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# Or via kubectl
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.models.base import get_db
from src.models.system_config import SystemConfig
db = next(get_db())
config = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
config.automation_enabled = False
db.commit()
print('Automation disabled')
"
```

---

## Troubleshooting

### Pod Crashes (CrashLoopBackOff)

```bash
# Check pod logs
kubectl logs deployment/green-flag-automation-api -n cassini --previous

# Common issues:
# - Database connection failed: Check DATABASE_URL secret
# - Redis connection failed: Check REDIS_HOST and REDIS_AUTH_TOKEN
# - Missing secrets: kubectl get secrets -n cassini
```

### Database Connection Issues

```bash
# Check RDS security group
aws ec2 describe-security-groups --group-ids <SECURITY_GROUP_ID>

# Verify EKS nodes can reach RDS
kubectl run -it --rm debug --image=postgres:14 --restart=Never -- \
  psql "postgresql://gfa_admin:<PASSWORD>@<RDS_ENDPOINT>:5432/green_flag_automation" -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Check ElastiCache security group
aws elasticache describe-replication-groups --replication-group-id gfa-production

# Test Redis connection with AUTH
kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
  redis-cli -h <REDIS_ENDPOINT> -a <AUTH_TOKEN> PING
```

### Worker Not Processing Tickets

```bash
# Check worker logs
kubectl logs -f deployment/green-flag-automation-worker -n cassini

# Check Redis queue depth
kubectl exec -it deployment/green-flag-automation-api -n cassini -- python -c "
from src.services.queue import TicketQueue
queue = TicketQueue()
print('Queue depth:', queue.redis_client.llen('ticket_queue'))
"

# Manually trigger worker processing
kubectl exec -it deployment/green-flag-automation-worker -n cassini -- python -m src.workers.ticket_worker
```

### High Error Rate / Circuit Breaker Triggered

```bash
# Check Prometheus alerts
kubectl logs -f deployment/green-flag-automation-api -n cassini | grep "CIRCUIT BREAKER"

# Check metrics
curl https://green-flag-automation.cassini.skyscanner.net/api/metrics | grep tickets_failed_total

# Review recent errors in logs
kubectl logs deployment/green-flag-automation-api -n cassini --tail=100 | grep ERROR

# Re-enable automation after fix
curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/enable
```

### CronJob Not Running

```bash
# Check CronJob status
kubectl get cronjobs -n cassini
kubectl describe cronjob green-flag-automation-daily-summary -n cassini

# Manually trigger CronJob
kubectl create job manual-summary-$(date +%Y%m%d-%H%M%S) \
  --from=cronjob/green-flag-automation-daily-summary -n cassini

# Check job logs
kubectl logs job/manual-summary-<JOB_ID> -n cassini
```

### Metrics Not Appearing in Grafana

```bash
# Check Prometheus scraping
kubectl port-forward deployment/green-flag-automation-api -n cassini 8000:8000
curl http://localhost:8000/api/metrics

# Verify Prometheus ServiceMonitor (if using Prometheus Operator)
kubectl get servicemonitor -n cassini

# Check Prometheus targets (in Prometheus UI)
# Targets should show: green-flag-automation-api:8000/api/metrics
```

### SSL Certificate Issues

```bash
# Check LoadBalancer annotations
kubectl describe service green-flag-automation-api -n cassini

# Verify ACM certificate
aws acm list-certificates --region eu-west-1

# Update service annotation with correct certificate ARN
kubectl annotate service green-flag-automation-api -n cassini \
  service.beta.kubernetes.io/aws-load-balancer-ssl-cert=arn:aws:acm:eu-west-1:ACCOUNT_ID:certificate/CERT_ID \
  --overwrite
```

---

## Monitoring Setup

### Configure Grafana Dashboard

1. Import dashboard JSON:
   ```bash
   # In Grafana UI: Dashboards > Import > Upload JSON file
   # Select: infra/grafana/dashboard.json
   ```

2. Configure data source:
   - Point to Prometheus endpoint
   - Verify metrics are flowing

### Configure Alertmanager

1. Apply Prometheus alerts:
   ```bash
   # If using Prometheus Operator
   kubectl apply -f infra/prometheus/alerts.yaml
   ```

2. Configure Alertmanager receiver for circuit breaker:
   ```yaml
   receivers:
     - name: green-flag-automation
       webhook_configs:
         - url: https://green-flag-automation.cassini.skyscanner.net/api/admin/circuit-breaker/trigger
   ```

---

## Scaling

### Horizontal Pod Autoscaling

```bash
# Create HPA for API
kubectl autoscale deployment green-flag-automation-api -n cassini \
  --cpu-percent=70 \
  --min=3 \
  --max=10

# Create HPA for Worker
kubectl autoscale deployment green-flag-automation-worker -n cassini \
  --cpu-percent=70 \
  --min=2 \
  --max=8

# Check HPA status
kubectl get hpa -n cassini
```

### Database Scaling

```bash
# Scale RDS instance class
cd infra/terraform
# Edit terraform.tfvars: rds_instance_class = "db.r5.large"
terraform plan
terraform apply

# Scale storage (automatic with max_allocated_storage)
# No action needed - RDS will auto-scale storage up to max_allocated_storage
```

### Redis Scaling

```bash
# Scale Redis node type
cd infra/terraform
# Edit terraform.tfvars: redis_node_type = "cache.r5.large"
terraform plan
terraform apply
```

---

## Maintenance Windows

### Planned Maintenance

1. Enable shadow mode:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/activate
   ```

2. Perform maintenance (deployments, migrations, etc.)

3. Verify functionality in shadow mode (48 hours)

4. Deactivate shadow mode:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/shadow-mode/deactivate
   ```

### Emergency Maintenance

1. Trigger kill switch:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/disable
   ```

2. Perform emergency fix

3. Re-enable automation:
   ```bash
   curl -X POST https://green-flag-automation.cassini.skyscanner.net/api/admin/kill-switch/enable
   ```

---

## Security Best Practices

1. **Secrets Management**:
   - Use AWS Secrets Manager for production secrets
   - Rotate credentials every 90 days
   - Never commit secrets to git

2. **Network Security**:
   - RDS and Redis only accessible from EKS nodes
   - LoadBalancer uses SSL termination
   - Private subnets for databases

3. **Access Control**:
   - RBAC configured for pod service account
   - IAM roles use least privilege
   - Audit logs retained for 7 years (compliance)

4. **Monitoring**:
   - Prometheus alerts for error rates
   - Grafana dashboard for operational visibility
   - CloudWatch logs for RDS and ElastiCache

---

## Support

For issues or questions:
- **Runbook**: See [docs/runbook.md](runbook.md) for common issues
- **Slack**: #cassini-green-flag-automation
- **On-call**: PagerDuty rotation for Cassini team
