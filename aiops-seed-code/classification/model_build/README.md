# Marketing Classification Model Build

This repository contains the model training pipeline for predicting customer term deposit subscriptions using the bank marketing dataset. It provides automated ML model training, evaluation, and registration using SageMaker Pipelines with MLflow tracking integration.

## Repository Structure
```
model_build/
├── README.md
├── .github/workflows/
│   └── build_sagemaker_pipeline.yml
├── ml_pipelines/
│   ├── run_pipeline.py
│   ├── training/pipeline.py
│   └── requirements.txt
├── source_scripts/
│   ├── preprocessing/prepare_marketing_data/
│   ├── training/
│   ├── evaluate/evaluate_classification/
│   └── helpers/
└── tests/
```

## Model Overview

- **Algorithm**: XGBoost Binary Classification
- **Objective**: Predict customer subscription to term deposits
- **Metrics**: AUC, Accuracy, Precision, Recall, F1 Score
- **Threshold**: AUC >= 0.7 for model registration

## Configuration Requirements

### Required GitHub Secrets
- `OIDC_ROLE_GITHUB_WORKFLOW`: IAM role ARN for GitHub Actions
- `SAGEMAKER_PIPELINE_ROLE_ARN`: IAM role for SageMaker pipeline
- `SAGEMAKER_PROJECT_NAME`: SageMaker project name
- `SAGEMAKER_PROJECT_ID`: SageMaker project identifier
- `REGION`: AWS region
- `ARTIFACT_BUCKET`: S3 bucket for artifacts
- `MODEL_PACKAGE_GROUP_NAME`: Model Registry package group
- `GLUE_DATABASE`: Glue database name
- `GLUE_TABLE`: Glue table name
- `MLFLOW_TRACKING_ARN`: MLflow tracking server ARN

### Required GitHub Variables
- `TRIGGER_PIPELINE_EXECUTION`: Set to `"true"` to enable pipeline

## Pipeline Execution

### Manual Execution
1. Navigate to Actions tab
2. Select "Marketing Classification Pipeline Build"
3. Click "Run workflow"

### Automatic Execution
Triggers on code changes to `ml_pipelines/` or `source_scripts/`

## Run Locally
```bash
cd model_build
python3 -m venv .venv
source .venv/bin/activate
pip install -r ml_pipelines/requirements.txt

python ./ml_pipelines/run_pipeline.py \
  --module-name training.pipeline \
  --role-arn <ROLE_ARN> \
  --kwargs '{"region":"<REGION>","role":"<ROLE>","default_bucket":"<BUCKET>","glue_database_name":"<DB>","glue_table_name":"<TABLE>"}'
```
