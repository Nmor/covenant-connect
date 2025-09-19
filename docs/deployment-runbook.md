# Covenant Connect Deployment Runbook

This runbook documents the AWS resources, secrets, and deployment automation that keep the Covenant Connect production environment reproducible.

## AWS Resources

| Resource | AWS Service | Name / Identifier | Notes |
| --- | --- | --- | --- |
| Application load balancer | Elastic Load Balancing | `covenant-connect-alb` | Routes HTTPS traffic to the Fargate web service.
| Web service cluster | Amazon ECS (Fargate) | Cluster `covenant-connect-cluster`, service `covenant-connect-web` | Runs the Flask application using the task definition in `deploy/ecs/task-definition.json`.
| Background worker service | Amazon ECS (Fargate) | Service `covenant-connect-worker` | Executes queued jobs via `python scripts/worker.py` using `deploy/ecs/worker-task-definition.json`.
| Database | Amazon RDS for PostgreSQL | DB identifier `covenant-connect-prod-db`, database `covenantconnect` | Multi-AZ db.t3.medium instance with automated backups.
| Cache / queue backend | Amazon ElastiCache for Redis | Cluster `covenant-connect-prod-redis` | Standard Redis (cluster mode disabled) with TLS enforced.
| Secrets store | AWS Secrets Manager | `covenant-connect/app-secrets`, `covenant-connect/database-url` | Holds credentials and connection strings consumed at runtime.
| Configuration parameters | AWS Systems Manager Parameter Store | `/covenant-connect/config/*` | Non-secret configuration values referenced by ECS task definitions.
| Email sending | Amazon SES SMTP endpoint | `email-smtp.us-east-1.amazonaws.com` | Authenticated SMTP used by Flask-Mail.

## Environment Variable to AWS Mapping

Every key from `.env.example` is fulfilled by an AWS resource, parameter, or secret. Secrets use AWS Secrets Manager unless noted otherwise; boolean and informational values live in Parameter Store (typed as `SecureString` to enable ECS injection).

| Variable | AWS resource | Secret or parameter name | Value source |
| --- | --- | --- | --- |
| `DATABASE_URL` | RDS PostgreSQL | Secret `covenant-connect/database-url` | Connection string `postgresql://covenantconnect_app:<password>@covenant-connect-prod-db.cluster-<hash>.us-east-1.rds.amazonaws.com:5432/covenantconnect` generated after DB provisioning. |
| `SECRET_KEY` | Secrets Manager | Secret `covenant-connect/app-secrets` key `SECRET_KEY` | 64-byte hex key generated via `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ENVIRONMENT` | Parameter Store | `/covenant-connect/config/ENVIRONMENT` | Literal `production`. |
| `FLASK_ENV` | Parameter Store | `/covenant-connect/config/FLASK_ENV` | Literal `production` to preserve backwards compatibility. |
| `SESSION_COOKIE_SECURE` | Parameter Store | `/covenant-connect/config/SESSION_COOKIE_SECURE` | `true` to force secure cookies. |
| `SESSION_COOKIE_HTTPONLY` | Parameter Store | `/covenant-connect/config/SESSION_COOKIE_HTTPONLY` | `true`. |
| `REMEMBER_COOKIE_SECURE` | Parameter Store | `/covenant-connect/config/REMEMBER_COOKIE_SECURE` | `true`. |
| `SESSION_COOKIE_SAMESITE` | Parameter Store | `/covenant-connect/config/SESSION_COOKIE_SAMESITE` | `Lax` unless a stricter policy is required. |
| `PREFERRED_URL_SCHEME` | Parameter Store | `/covenant-connect/config/PREFERRED_URL_SCHEME` | `https`. |
| `SERVER_NAME` | Parameter Store | `/covenant-connect/config/SERVER_NAME` | Public hostname `app.covenantconnect.org`. |
| `MAIL_SERVER` | Parameter Store | `/covenant-connect/config/MAIL_SERVER` | `email-smtp.us-east-1.amazonaws.com` for SES SMTP. |
| `MAIL_PORT` | Parameter Store | `/covenant-connect/config/MAIL_PORT` | `587`. |
| `MAIL_USE_TLS` | Parameter Store | `/covenant-connect/config/MAIL_USE_TLS` | `true`. |
| `MAIL_USERNAME` | Secrets Manager | Secret `covenant-connect/app-secrets` key `MAIL_USERNAME` | SES SMTP username created when enabling production access. |
| `MAIL_PASSWORD` | Secrets Manager | Secret `covenant-connect/app-secrets` key `MAIL_PASSWORD` | SES SMTP password paired with the username. |
| `MAIL_DEFAULT_SENDER` | Parameter Store | `/covenant-connect/config/MAIL_DEFAULT_SENDER` | `notifications@covenantconnect.org`. |
| `REDIS_URL` | Parameter Store | `/covenant-connect/config/REDIS_URL` | `rediss://covenant-connect-prod-redis.<hash>.use1.cache.amazonaws.com:6379/0`. |
| `PAYSTACK_SECRET_KEY` | Secrets Manager | Secret `covenant-connect/app-secrets` key `PAYSTACK_SECRET_KEY` | API key issued by Paystack. |
| `FINCRA_SECRET_KEY` | Secrets Manager | Secret `covenant-connect/app-secrets` key `FINCRA_SECRET_KEY` | API key issued by Fincra. |
| `STRIPE_SECRET_KEY` | Secrets Manager | Secret `covenant-connect/app-secrets` key `STRIPE_SECRET_KEY` | Stripe live secret key. |
| `FLUTTERWAVE_SECRET_KEY` | Secrets Manager | Secret `covenant-connect/app-secrets` key `FLUTTERWAVE_SECRET_KEY` | Flutterwave live secret key. |
| `CORS_ORIGINS` | Parameter Store | `/covenant-connect/config/CORS_ORIGINS` | Comma-separated list such as `https://app.covenantconnect.org,https://admin.covenantconnect.org`. |

## ECS Task Definitions and Secret Injection

The deployment pipeline registers the task definitions stored in `deploy/ecs/task-definition.json` (web) and `deploy/ecs/worker-task-definition.json` (background worker) during each release:

1. Build and push the application container to `123456789012.dkr.ecr.us-east-1.amazonaws.com/covenant-connect`.
2. Run `aws ecs register-task-definition --cli-input-json file://deploy/ecs/task-definition.json` followed by the worker variant.
3. Update the ECS services:
   ```bash
   aws ecs update-service --cluster covenant-connect-cluster \
       --service covenant-connect-web \
       --task-definition covenant-connect-web
   aws ecs update-service --cluster covenant-connect-cluster \
       --service covenant-connect-worker \
       --task-definition covenant-connect-worker
   ```

Both task definitions rely exclusively on Secrets Manager or Parameter Store entries. ECS resolves the `valueFrom` references and injects the resolved values into each container before the application process starts, satisfying the requirement to load secrets at runtime without baking them into the image.

## Background Worker Execution

`deploy/ecs/worker-task-definition.json` defines a dedicated Fargate task that runs `python scripts/worker.py`. The worker service shares the same environment variables and secrets as the web task so it can connect to Redis and RDS. Scale the worker service by adjusting the desired count on the `covenant-connect-worker` ECS service.

## Outbound Email Verification

* Ensure the web and worker tasks use the `sg-covenant-connect-app` security group with an egress rule allowing TCP 587 to `email-smtp.us-east-1.amazonaws.com` (or TCP 465 if switching to TLS/SSL).
* Validate network pathing from a running task:
  ```bash
  aws ecs execute-command --cluster covenant-connect-cluster \
      --task <task-id> --container web --command \
      "openssl s_client -starttls smtp -connect email-smtp.us-east-1.amazonaws.com:587"
  ```
* Send a smoke-test email through SES using the configured credentials:
  ```bash
  python - <<'PY'
  import os
  import smtplib
  from email.message import EmailMessage

  msg = EmailMessage()
  msg["Subject"] = "Covenant Connect SES smoke test"
  msg["From"] = os.environ["MAIL_DEFAULT_SENDER"]
  msg["To"] = os.environ["MAIL_DEFAULT_SENDER"]
  msg.set_content("SES connectivity confirmed.")

  with smtplib.SMTP(os.environ["MAIL_SERVER"], int(os.environ["MAIL_PORT"])) as smtp:
      smtp.starttls()
      smtp.login(os.environ["MAIL_USERNAME"], os.environ["MAIL_PASSWORD"])
      smtp.send_message(msg)
  PY
  ```
* Investigate failures by checking the VPC network ACLs, NAT gateway routes, and SES suppression list before re-trying.

## Change Management

* Secrets live in Secrets Manager and should be rotated annually or when staff changes occur. Update the corresponding keys in `covenant-connect/app-secrets` and re-deploy to roll the credentials.
* Parameter Store values track non-secret configuration; changes to `/covenant-connect/config/*` trigger ECS to receive new values on the next task deployment or service restart.
* Database schema migrations are applied using Alembic migrations before updating the ECS services.

## Useful Commands

```bash
# List current secret values referenced by ECS
aws secretsmanager get-secret-value --secret-id covenant-connect/app-secrets

# Inspect active task definitions
aws ecs describe-task-definition --task-definition covenant-connect-web
aws ecs describe-task-definition --task-definition covenant-connect-worker

# Restart services after changing configuration
aws ecs update-service --cluster covenant-connect-cluster \
    --service covenant-connect-web --force-new-deployment
```
