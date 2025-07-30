# MLOps SageMaker Unified Studio with GitHub Actions

This repository contains resources required to deploy an MLOps SageMaker Unified Studio (SMUS) Project using GitHub Actions for CI/CD.

## Table of Contents
1. [Solution Architecture](#solution-architecture)
2. [Repository Structure](#repository-structure)
3. [GitHub Connection and Setup](#github-connection-and-setup)
4. [GitHub Secrets and Variables Configuration](#github-secrets-and-variables-configuration)
5. [Glue Database Configuration](#glue-database-configuration)
6. [Pipeline Execution Control](#pipeline-execution-control)
7. [Workflow Execution](#workflow-execution)
8. [Local Deployment and Testing](#local-deployment-and-testing)
9. [Pipeline Monitoring](#pipeline-monitoring)
10. [Troubleshooting](#troubleshooting)
11. [Clean-up](#clean-up)

## Solution Architecture

![mlops project architecture](diagrams/github_action_mlops_architecture.jpg)

## Repository Structure

```
.
├── LICENSE.txt
├── README.md
├── diagrams
├── .github <--- contains the GitHub Action WorkFlow script
│   └── workflows
│       └── build_sagemaker_pipeline.yml
├── ml_pipelines  <--- code samples to be used to setup the build of the sagemaker pipeline
├── source_scripts  <--- code samples to be used to setup the build of the sagemaker pipeline
```

## GitHub Connection and Setup

1. **Setup IAM OpenID Connect (OIDC) identity provider for GitHub** [AWS Documentation](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services). This connection will be used to perform GitHub CI/CD using the GitHub Action Pipeline CI/CD (preferred method). Skip this step if you already have a GitHub connection or check with your organization if they already have GitHub connection enabled.

2. **Create an IAM role using the OIDC identity provider**. OIDC allows your GitHub Actions workflows to access resources in Amazon Web Services (AWS) without storing the AWS credentials as long-lived GitHub secrets. Follow the [GitHub Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) for instructions to configure the IAM trust policy.

    **Required permissions for this role** (_Note: For setup, broad permissions are provided for these services. Later, trim down the permissions to only required ones_):
    ```
    AmazonEC2ContainerRegistryFullAccess
    AmazonS3FullAccess
    AWSServiceCatalogAdminFullAccess
    AWSCloudFormationFullAccess
    IAMFullAccess
    AmazonSageMakerFullAccess
    AmazonSSMFullAccess
    ```

    **Additional SageMaker permissions required**:
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sagemaker:ListPipelineExecutions",
                    "sagemaker:DescribePipelineExecution",
                    "sagemaker:ListPipelineExecutionSteps"
                ],
                "Resource": "*"
            }
        ]
    }
    ```

## GitHub Secrets and Variables Configuration

Create the following GitHub secrets and variables which will be consumed by the GitHub action job. These secrets will be needed for both model build and model deploy GitHub actions. See [GitHub documentation](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) for instructions on how to create GitHub secrets.

### Required Secrets:

- `OIDC_ROLE_GITHUB_WORKFLOW`: The ARN of the IAM role that GitHub Actions will assume. Example: `"arn:aws:iam::<account-id>:role/aiops-smus-github-action"`

- `SAGEMAKER_PIPELINE_ROLE_ARN`: The ARN of the IAM role used to execute SageMaker pipelines. Example: `"arn:aws:iam::<account-id>:role/datazone_usr_role_4gym2gsxqde80g_d6a5f304hfrspc"`

- `SAGEMAKER_PROJECT_NAME`: The name of the SageMaker project associated with the pipeline. Example: `"Build_model_project_finance"`

- `SAGEMAKER_PROJECT_ID`: The unique identifier for the SageMaker project. Example: `"4gym2gsxqde80g"`

- `AMAZON_DATAZONE_DOMAIN`: The domain name for Amazon DataZone integration. Example: `"dzd_d2hu7wi9b2nro0"`

- `AMAZON_DATAZONE_SCOPENAME`: The scope name within Amazon DataZone for resource access. Example: `"dev"`

- `SAGEMAKER_DOMAIN_ARN`: The ARN of the SageMaker Studio domain. Example: `"arn:aws:sagemaker:us-west-2:<account-id>:domain/d-yzd7xzpwhgk9"`

- `SAGEMAKER_SPACE_ARN`: The ARN of the SageMaker Studio space for user collaboration. Example: `"arn:aws:sagemaker:us-west-2:<account-id>:space/d-yzd7xzpwhgk9/default-b8214310-a081-7072-2dc2-f03e4fb04a0e"`

- `AMAZON_DATAZONE_PROJECT`: The Amazon DataZone project name linked to the SageMaker resources. Example: `"4gym2gsxqde80g"`

- `REGION`: The AWS region where SageMaker resources are deployed. Example: `"us-east-1"`

- `ARTIFACT_BUCKET`: The S3 bucket used to store artifacts like datasets and models. Example: `"amazon-sagemaker-643732685158-us-west-2-f16345659560"`

- `MODEL_PACKAGE_GROUP_NAME`: The name of the model package group for organizing model versions in SageMaker Model Registry. The name should follow the regex Pattern: `^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,255}`. Note: Do not use underscore. Example: `"github-actions-abalone"`

- `GLUE_DATABASE`: The name of the Glue database containing your data table. Example: `"glue_db_3hwskube5dybhj"`

- `GLUE_TABLE`: The name of the Glue table containing your dataset. Example: `"abalone"`

### Required Variables:

- `TRIGGER_PIPELINE_EXECUTION`: Controls whether the pipeline should execute. Set to `"true"` to enable pipeline execution, `"false"` to disable. **Default: `"false"`**

## Glue Database Configuration

Before enabling pipeline execution, you must configure the Glue database and table:

1. **Create a Glue table in SageMaker Unified Studio**:
   - Navigate to Data → Lakehouse → awsdatacatalog
   - Find your Glue database (format: `glue_db_****`)
   - Upload your dataset (e.g., abalone-dataset.csv)
   - Note the exact database and table names

2. **Update GitHub secrets with actual names**:
   - Update `GLUE_DATABASE` secret with your actual database name
   - Update `GLUE_TABLE` secret with your actual table name

## Pipeline Execution Control

This repository includes a safety mechanism to prevent pipeline failures due to incomplete configuration:

### Default Behavior:
- **Pipeline execution is DISABLED by default** (`TRIGGER_PIPELINE_EXECUTION = "false"`)
- When disabled, the workflow will show instructions and skip pipeline execution
- This prevents failures when Glue configuration is not yet updated

### Enabling Pipeline Execution:
1. **Complete Glue configuration** (see section above)
2. **Set the trigger variable**:
   - Go to repository Settings → Secrets and variables → Actions → Variables tab
   - Set `TRIGGER_PIPELINE_EXECUTION` to `"true"`
3. **Re-run the workflow** or push new changes

### Workflow Structure:
The workflow consists of two jobs:
- **`check-trigger`**: Validates the trigger variable and provides instructions
- **`GitHub-Actions-SMUS-Build`**: Executes only when trigger is enabled

## Workflow Execution

### Automatic Triggers:
The GitHub Actions workflow triggers automatically on:
- **Push** to main branch (paths: `ml_pipelines/**`, `source_scripts/**`)
- **Pull request** to main branch (same paths)

### Manual Trigger:
1. Go to repository Actions tab
2. Select "Sagemaker Pipeline build SMUS project"
3. Click "Run workflow"

### Execution Flow:
1. **Trigger Check**: Validates `TRIGGER_PIPELINE_EXECUTION` variable
2. **Environment Setup**: Python, AWS credentials, dependencies
3. **Data Preparation**: Upload datasets and requirements to S3
4. **Pipeline Execution**: Run SageMaker pipeline with monitoring
5. **Status Reporting**: Real-time pipeline status updates with timeout protection

## Local Deployment and Testing

Manually deploy SMUS pipeline for local development and testing.

### Pre-requisites:
- Python 3.10 or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- [AWS CLI](https://aws.amazon.com/cli/)
- [Docker](https://docs.docker.com/desktop/)
- AWS credentials with sufficient permissions
- SageMaker Unified Studio Domain, user profile and login credentials

### Project Build:

1. **Clone this repository** in your work environment (e.g., your laptop or SMUS project notebook command line)

2. **Change to the model build folder**:
    ```bash
    cd model_build
    ```

3. **Install dependencies** in a separate Python virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

4. **Deploy the SMUS pipeline**:
    ```bash
    python ./ml_pipelines/run_pipeline.py \
      --module-name training.pipeline \
      --role-arn <SAGEMAKER_PIPELINE_ROLE_ARN> \
      --tags '[{"Key":"sagemaker:project-name", "Value":"<SAGEMAKER_PROJECT_NAME>"}, {"Key":"sagemaker:project-id", "Value":"<SAGEMAKER_PROJECT_ID>"}, {"Key":"AmazonDataZoneDomain", "Value":"<AMAZON_DATAZONE_DOMAIN>"}, {"Key":"AmazonDataZoneScopeName", "Value":"<AMAZON_DATAZONE_SCOPENAME>"}, {"Key":"sagemaker:domain-arn", "Value":"<SAGEMAKER_DOMAIN_ARN>"}, {"Key":"sagemaker:space-arn", "Value":"<SAGEMAKER_SPACE_ARN>"}, {"Key":"AmazonDataZoneProject", "Value":"<AMAZON_DATAZONE_PROJECT>"}]' \
      --kwargs '{"region":"<REGION>","role":"<SAGEMAKER_PIPELINE_ROLE_ARN>","default_bucket":"<ARTIFACT_BUCKET>","pipeline_name":"githubactions-<SAGEMAKER_PROJECT_ID>","model_package_group_name":"<MODEL_PACKAGE_GROUP_NAME>","base_job_prefix":"SMUSMLOPS","glue_database_name":"<GLUE_DATABASE>","glue_table_name":"<GLUE_TABLE>"}'
    ```

## Pipeline Monitoring

The GitHub Actions workflow includes comprehensive pipeline monitoring:

### Features:
- **Real-time status updates** every 30 seconds
- **Timeout protection** (1-hour maximum execution time)
- **Failure debugging** with detailed error messages and failed step information
- **Execution summary** with start/end times on completion

### Monitoring Output:
```
=== Monitoring Pipeline Execution ===
Pipeline Name: githubactions-<project-id>
Monitoring execution: arn:aws:sagemaker:...
Pipeline Status: Executing (Elapsed: 30s)
Pipeline Status: Executing (Elapsed: 60s)
Pipeline execution completed successfully!
```

### Status Checking:
You can also check pipeline status manually:
```bash
# List recent executions
aws sagemaker list-pipeline-executions --pipeline-name "githubactions-<project-id>"

# Check specific execution status
aws sagemaker describe-pipeline-execution --pipeline-execution-arn "<execution-arn>"
```

## Troubleshooting

### Common Issues:

1. **Pipeline execution is disabled**:
   - **Cause**: `TRIGGER_PIPELINE_EXECUTION` variable is not set to `"true"`
   - **Solution**: Set the variable to `"true"` in repository settings

2. **Glue database/table not found**:
   - **Cause**: `GLUE_DATABASE` or `GLUE_TABLE` secrets have incorrect values
   - **Solution**: Update secrets with actual database and table names from SageMaker Unified Studio

3. **Pipeline monitoring fails**:
   - **Cause**: Missing `sagemaker:ListPipelineExecutions` permission
   - **Solution**: Ensure IAM role has required SageMaker permissions

4. **GitHub Actions cannot assume role**:
   - **Cause**: OIDC trust relationship not configured correctly
   - **Solution**: Verify trust relationship includes correct GitHub organization

5. **Workflow shows "skipped"**:
   - **Cause**: `TRIGGER_PIPELINE_EXECUTION` is set to `"false"`
   - **Solution**: This is expected behavior when pipeline execution is disabled

### Log Locations:
- **GitHub Actions**: Repository → Actions tab → Workflow run
- **SageMaker Pipeline**: AWS Console → SageMaker → Pipelines
- **CloudWatch Logs**: `/aws/sagemaker/ProcessingJobs` and `/aws/sagemaker/TrainingJobs`

### Debug Commands:
```bash
# Check pipeline executions
aws sagemaker list-pipeline-executions --pipeline-name "githubactions-<project-id>"

# Check failed steps
aws sagemaker list-pipeline-execution-steps --pipeline-execution-arn "<execution-arn>" --query 'PipelineExecutionSteps[?StepStatus==`Failed`]'
```

## Clean-up

To clean up resources:
1. Delete the SageMaker pipeline from the AWS Console
2. Remove model packages from SageMaker Model Registry
3. Clean up S3 artifacts if no longer needed
4. Delete GitHub repository if no longer needed

**Note**: Be careful when deleting resources as this action cannot be undone.
