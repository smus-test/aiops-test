# Marketing Classification Model Deploy

This repository contains the deployment infrastructure for the Marketing Classification model. It provisions SageMaker endpoints using AWS CDK for serving real-time predictions.

## Repository Structure
```
model_deploy/
├── README.md
├── app.py                    # CDK application entry point
├── cdk.json                  # CDK configuration
├── .github/workflows/
│   └── deploy_model_pipeline.yml
├── config/
│   ├── constants.py
│   ├── config_mux.py
│   └── dev/
│       └── endpoint-config.yml
├── deploy_endpoint/
│   ├── deploy_endpoint_stack.py
│   └── get_approved_package.py
└── tests/
```

## Configuration Requirements

### Required GitHub Secrets
- `OIDC_ROLE_GITHUB_WORKFLOW`: IAM role ARN for GitHub Actions
- `DEPLOY_ACCOUNT`: AWS account ID for deployment
- `REGION`: AWS region
- `SAGEMAKER_PROJECT_NAME`: SageMaker project name
- `SAGEMAKER_PROJECT_ID`: SageMaker project identifier
- `MODEL_PACKAGE_GROUP_NAME`: Model Registry package group
- `ARTIFACT_BUCKET`: S3 bucket for artifacts
- `AMAZON_DATAZONE_DOMAIN`: DataZone domain
- `AMAZON_DATAZONE_SCOPENAME`: DataZone scope name
- `AMAZON_DATAZONE_PROJECT`: DataZone project

## Deployment

### Manual Deployment
1. Navigate to Actions tab
2. Select "Marketing Classification Model Deploy"
3. Click "Run workflow"

### Local Deployment
```bash
pip install -r requirements.txt
cdk synth
cdk deploy
```

## Endpoint Configuration
Edit `config/dev/endpoint-config.yml` to customize:
- `instance_type`: ML instance type (default: ml.m5.large)
- `initial_instance_count`: Number of instances
- `variant_name`: Endpoint variant name
