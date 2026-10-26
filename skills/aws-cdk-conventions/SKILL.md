---
name: aws-cdk-conventions
description: AWS CDK stack naming, tagging, environments and resource defaults. Use when writing or changing infrastructure code.
metadata:
  area: aws
  applies_to: "infra/**, cdk/**, **/*.stack.ts, **/cdk.json"
  tags: "cdk, infrastructure, tagging, lambda, iam"
---
<!-- EXAMPLE CONTENT: replace with your team's actual conventions -->
# AWS CDK conventions

## Rules
- Stack names `<service>-<env>-<purpose>`, e.g. `orders-prod-api`.
- Apply tags `service`, `env`, `owner` via `Tags.of(app)`.
- Lambdas: Node 22, ARM64, `NodejsFunction`, 30-day log retention, explicit timeout.
- IAM via `resource.grantX(fn)`; never hand-written `*` policies.
- No hard-coded account ids or ARNs; read from context or SSM.

## Pitfalls
- Missing log retention creates never-expiring log groups.
