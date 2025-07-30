# AWS MLOps Repository Synchronization Framework (SMUS)

A robust AWS CDK-based solution that automates the synchronization of ML model build and deployment repositories while managing GitHub secrets and repository configurations for MLOps workflows.

This project provides an automated infrastructure for managing machine learning operations (MLOps) workflows by synchronizing repositories, handling GitHub secrets, and orchestrating the deployment process through AWS Step Functions. It leverages AWS CDK for infrastructure as code and includes Lambda functions for repository management and status monitoring.

The framework integrates with AWS DataZone and SageMaker Unified Studio, providing a seamless experience for ML project deployment while maintaining security best practices through AWS Secrets Manager and IAM role management. It also supports Glue database and table integration for data processing workflows.

## Table of Contents
1. [Prerequisites and Setup](#1-prerequisites-and-setup)
2. [Configuration](#2-configuration)
3. [CDK Deployment](#3-cdk-deployment)
4. [Post-Deployment Configuration](#4-post-deployment-configuration)
   - 4.5. [Git Connection Setup](#45-git-connection-setup)
   - 4.6. [Create Custom Project Profile](#46-create-custom-project-profile)
5. [SageMaker Unified Studio Project Creation](#5-sagemaker-unified-studio-project-creation)
6. [Glue Database and Table Configuration](#6-glue-database-and-table-configuration)
7. [Build and Model Creation Process](#7-build-and-model-creation-process)
8. [Model Approval and Deployment Process](#8-model-approval-and-deployment-process)
9. [Troubleshooting](#9-troubleshooting)
10. [Architecture Overview](#10-architecture-overview)

## Repository Structure
```
smus-cdk/
├── app.py                  # Main CDK application entry point
├── cdk.json               # CDK configuration file
├── lambda/                # Lambda function implementations
│   ├── check-project-status/    # Project status monitoring
│   ├── create-deploy-repository/ # Repository creation and setup
│   └── sync-repositories/       # Repository synchronization
├── layers/                # Lambda layer definitions
│   ├── git-layer/        # Git binary layer for Lambda
│   └── python-layer/     # Python dependencies layer
├── ml_ops_smus/          # Core framework implementation
│   └── constructs/       # CDK construct definitions
└── requirements.txt      # Project dependencies
```

## 1. Prerequisites and Setup

### AWS Account Requirements
- AWS Account with appropriate IAM permissions for CDK deployment
- AWS CLI configured with credentials
- Access to AWS services: CDK, Lambda, Step Functions, EventBridge, Secrets Manager, IAM, SageMaker, DataZone, Glue, S3

### Development Environment
- **Python**: 3.9 or later
- **AWS CDK CLI**: v2.188.0 or later - Follow [AWS CDK Getting Started Guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
- **Docker Desktop**: Required for building Lambda layers - Follow [Docker Desktop installation guide](https://docs.docker.com/desktop/) and ensure Docker is running
- **Git**: For repository operations
- **Node.js**: 18.x or later (for CDK)

### GitHub Requirements
- **GitHub Organization**: You need a GitHub organization where build and deploy repositories will be created
- **Personal Access Token**: GitHub PAT with the following permissions:
  - `repo` (Full control of private repositories)
  - `workflow` (Update GitHub Action workflows)
  - `write:packages` (Upload packages to GitHub Package Registry)

## 2. Configuration

### Update Configuration File
Before deployment, configure the `config.py` file located in `smus-cdk/ml_ops_smus/config.py`:

```python
# smus-cdk/ml_ops_smus/config.py configuration parameters:
GitConfig(
    public_smus_aiops_org="smus-test",  # Organization with AIOPs templates 
    public_smus_aiops_org_repo="aiops-test",  # Source repository name
    public_smus_aiops_org_repo_folder="aiops-seed-code",  # Folder containing templates
    public_repo_branch="main",  # Source repository branch
    oidc_role_github_workflow="aiops-smus-github-action",  # GitHub workflow execution role
    private_github_organization="your-github-organization",  # Your GitHub organization
    private_deploy_repo_default_branch="main",  # Branch name for repositories
    github_token_secret_name="ml-ops-smus-github-token",  # Secret name in AWS Secrets Manager
)
```

### Configuration Parameters Details
- **`public_smus_aiops_org`**: GitHub organization containing the template repositories
- **`public_smus_aiops_org_repo`**: Repository name containing ML project templates
- **`public_smus_aiops_org_repo_folder`**: Folder within the template repository containing project templates
- **`oidc_role_github_workflow`**: IAM role name that GitHub Actions can assume
- **`private_github_organization`**: Your GitHub organization where build/deploy repos will be created
- **`github_token_secret_name`**: Name of the secret in AWS Secrets Manager for GitHub token

## 3. CDK Deployment

### Environment Setup
1. **Clone the repository**:
```bash
git clone https://github.com/smus-test/aiops-test.git
cd aiops-test/smus-cdk
```

2. **Create and activate virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/MacOS
# or
.venv\Scripts\activate  # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

### CDK Bootstrap and Deployment
1. **Verify Docker is running**:
```bash
docker info
```

2. **Bootstrap CDK** (if not already done):
```bash
cdk bootstrap
```

3. **Synthesize the stack** (optional verification):
```bash
cdk synth
```

4. **Deploy the stack**:
```bash
cdk deploy --require-approval never
```

### Verify Deployment
After successful deployment, verify the following resources are created:
- **Lambda Functions**:
  - `ai-ops-check-project-status`
  - `ai-ops-sync-repositories`
  - `ai-ops-create-deploy-repo`
  - `MlOpsSmusStack-model-approval-trigger`
- **Step Functions**: `ml-ops-project-setup`
- **EventBridge Rules**: 
  - `ml-ops-smus-datazone-project-rule-v2`
  - `MlOpsSmusStack-model-approval-rule`
- **IAM Role**: `aiops-smus-github-action`
- **Secrets Manager**: `ml-ops-smus-github-token`

## 4. Post-Deployment Configuration

### Update GitHub Token Secret
1. **Navigate to AWS Secrets Manager Console**
2. **Find the secret**: `ml-ops-smus-github-token`
3. **Click "Retrieve secret value" → "Edit"**
4. **Update the `token` field** with your GitHub Personal Access Token
5. **Save the changes**

### Verify IAM Role Trust Relationship
Check that the GitHub workflow role has the correct trust relationship:
```bash
aws iam get-role --role-name aiops-smus-github-action --query 'Role.AssumeRolePolicyDocument'
```

The trust relationship should include:
```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:your-github-organization/*"
  }
}
```

### Verify EventBridge Rules
Confirm EventBridge rules are active:
```bash
aws events describe-rule --name "ml-ops-smus-datazone-project-rule-v2"
aws events describe-rule --name "MlOpsSmusStack-model-approval-rule"
```

## 4.5. Git Connection Setup

### Create SageMaker Unified Studio Domain (if needed)
1. **Navigate to SageMaker Unified Studio Console**
2. **Create a new domain** or use existing domain following [Create a Amazon SageMaker Unified Studio domain - quick setup](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/domain-quick-setup.html)
3. **Note the domain ID** (format: `dzd_xxxxxxxxxx`)

### Configure Git Connection in SageMaker Unified Studio
Before creating projects, you need to set up a Git connection to enable integration between SMUS and your GitHub repository.

1. **Navigate to your SageMaker Unified Studio domain**
2. **Go to domain details page → Connections tab**
3. **Click "Create Git connection" → Select "GitHub"**
4. **Configure connection**:
   - **Connection name**: `aws-github-smus-connection`
   - **Click "Connect to GitHub"**
   - **You'll be redirected to Authorization page**
   - **Click "Authorize AWS connector for GitHub"**
   - **Select "Install a new app"**
5. **Install AWS connector for GitHub**:
   - **Select your target organization** (same as `private_github_organization` in config)
   - **Repository access**: Select "All repositories"
   - **Click "Install & Authorize" → "Connect"**
6. **Enable connection**:
   - **Select your newly created connection**
   - **Click "Enable" to complete setup**

## 4.6. Create Custom Project Profile

### Create Project Profile
You need to create a custom project profile that will be used for your ML projects.

1. **Navigate to domain details page**
2. **Find "Project profiles" tile → Click "Create"**
3. **Configure profile**:
   - **Name**: `regression`
   - **Creation option**: "Create from a template"
   - **Capabilities**: "All capabilities"
4. **Default tooling blueprint deployment settings**:
   - **Keep default Account and region settings**
   - **Git connection**: Select `aws-github-smus-connection`
   - **Enable**: "Users can edit Git connection"
   - **Authorization**: "Users and groups"
5. **Authorization settings**:
   - **Choose**: "Selected users and groups"
   - **Select SSO users and groups** who can access this project profile
6. **Project profile readiness**: Check "Enable project profile on creation"

## 5. SageMaker Unified Studio Project Creation

### Create SageMaker Project
1. **Navigate to your SMUS domain** by clicking "Open unified studio"
2. **Sign in with SSO** using the username and password for the user granted access to the project profile
3. **In the SMUS home page, click "Create project"**
4. **Configure project**:
   - **Project name**: Enter your project name (e.g., `smus-blog-test`)
   - **Project profile**: Select `regression`
   - **Click "Continue"**
5. **Customize blueprint parameters**:
   - **Under Tooling**: Select `aws-github-smus-connection` as the connection name
   - **Connection provider**: Select "New repository and new branch"
   - **Repository name**: Enter build repo name (e.g., `smus-blog-build-repo`)
   - **Click "Continue"**
6. **Review and create**:
   - **Review your selections**
   - **Click "Create project"**
   - **Wait 5-10 minutes for project creation to complete**

### Repository Naming Convention
After project creation, you'll see two repositories created in your private GitHub organization:
- **Build repository**: `{your-specified-name}` (e.g., `smus-blog-build-repo`)
- **Deploy repository**: `{project-id}-{datazone-domain-id}-deploy-repo`

### Workflow Trigger Behavior
- **Build Repository**: Workflow triggers on code changes but requires `TRIGGER_PIPELINE_EXECUTION=true` to execute
- **Deploy Repository**: Workflow only triggers via model approval events or manual execution (no automatic triggers on code changes)


## 6. Glue Database and Table Configuration

#### Create Table in SageMaker Unified Studio
After project creation, you need to create a Glue table with your data:

1. **Login to your project in SageMaker Unified Studio**
2. **Navigate to Data → Lakehouse → awsdatacatalog**
3. **Find your Glue database**: `glue_db_****`
4. **Click the table tile option on the side**
5. **Upload dataset**:
   - **Download abalone dataset** from your build repository: `ml_pipelines/data/abalone-dataset.csv`
   - **Table name**: `abalone`
   - **Click "Next"**
6. **In the add data page**:
   - **Review the schema**
   - **Click "Create table"**

**Note**: During table creation, you'll see both the Glue database name and table name in the SageMaker Unified Studio interface. Make note of these exact names for the next step.

#### Update GitHub Secrets
Update the GitHub secrets in both build and deploy repositories with the actual names you saw during table creation:

**For Build Repository**
1. **Navigate to**: `your-org/project-build-repo`
2. **Go to Settings → Secrets and variables → Actions**
3. **Update the following secrets**:
   - `GLUE_DATABASE`: Update from `glue_db` to your actual database name (e.g., `glue_db_3hwskube5dybhj`)
   - `GLUE_TABLE`: Update from `abalone` to your actual table name (e.g., `abalone`)

**For Deploy Repository**
1. **Navigate to**: `your-org/project-deploy-repo`
2. **Go to Settings → Secrets and variables → Actions**
3. **Update the same secrets**:
   - `GLUE_DATABASE`: Your actual database name
   - `GLUE_TABLE`: Your actual table name

#### Enable Pipeline Execution
After updating the Glue database and table secrets, you need to enable pipeline execution:

**For Build Repository**
1. **Navigate to**: `your-org/project-build-repo`
2. **Go to Settings → Secrets and variables → Actions → Variables tab**
3. **Create a new repository variable**:
   - **Name**: `TRIGGER_PIPELINE_EXECUTION`
   - **Value**: `true`
4. **Click "Add variable"**

**Note**: By default, pipeline execution is disabled to prevent failures when Glue configuration is not yet updated. This variable must be set to `true` to enable the SageMaker pipeline execution.

### 7. Build and Model Creation Process

After updating the GitHub secrets and enabling pipeline execution, the build workflow can be triggered. The workflow includes a safety check that prevents execution until the `TRIGGER_PIPELINE_EXECUTION` variable is set to `true`, ensuring that Glue database and table configurations are properly updated before running the pipeline.

#### Manual Workflow Trigger 
Follow these steps to manually trigger the workflow:
1. **Ensure Prerequisites**:
   - Glue database and table secrets are updated (Section 6)
   - `TRIGGER_PIPELINE_EXECUTION` variable is set to `true`
2. **Go to build repository GitHub Actions**
3. **Select the workflow**
4. **Click "SageMaker Pipeline build SMUS project"**
5. **Click "Run workflow"**

**Note**: If the `TRIGGER_PIPELINE_EXECUTION` variable is not set to `true`, the workflow will exit gracefully with instructions on how to enable it.

#### Verify Model Registration
After successful build pipeline execution:
1. **Navigate to SageMaker Unified Studio**
2. **Go to Build → AI OPS → Model Registry**
3. **Find your model package group**: `aiops-{project-id}-models`
4. **Verify model version 1** with status "PendingManualApproval"

### 8. Model Approval and Deployment Process

#### Manual Model Approval
1. **Navigate to SageMaker Unified Studio**
2. **Go to Build → AI OPS → Model Registry**
3. **Find your model package group**: `aiops-{project-id}-models`
4. **Select the model package** you want to approve
5. **Click "Update model approval status"**
6. **Change status from "PendingManualApproval" to "Approved"**
7. **Add approval comments** (optional)
8. **Click "Update status"**

#### Automated Deployment Trigger
When a model is approved:
1. **SageMaker emits approval event** to EventBridge
2. **EventBridge rule** `MlOpsSmusStack-model-approval-rule` detects the event
3. **Model approval Lambda** `MlOpsSmusStack-model-approval-trigger` is invoked to:
      **Extracts project information** from the event
      **Constructs deploy repository name**: `project-deploy-repo`
      **Triggers GitHub Actions workflow** in deploy repository via API
      **Uses workflow_dispatch** trigger with appropriate inputs

Once the automated deployment Lambda successfully triggers the workflow, the following deployment steps are executed in the deploy repository:
#### Deploy Workflow Execution
1. **Find approved model** in SageMaker Model Registry
2. **Create SageMaker model** from approved model package
3. **Create endpoint configuration** with instance settings
4. **Deploy SageMaker endpoint** for real-time inference
5. **Test endpoint** with sample data
6. **Update endpoint** if already exists

#### Monitor Deployment
1. **Check GitHub Actions** in deploy repository
2. **Monitor workflow execution** status and logs
3. **Monitor SageMaker endpoints**:
```bash
# List endpoints
aws sagemaker list-endpoints --sort-by "CreationTime" --sort-order "Descending"

# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name "your-endpoint-name"
```
Finally, to ensure successful deployment:
#### Verify Deployed Endpoint
1. **Navigate to SageMaker Unified Studio**
2. **Go to Model Development → Inference → Endpoints**
3. **Verify endpoint status**: "InService"
4. **Test endpoint** with sample data if needed

### 9. Troubleshooting

#### Common Issues and Solutions

**1. GitHub Token Issues**
- Problem: Repository creation fails with authentication errors
- Solution: Verify GitHub token in Secrets Manager, ensure correct permissions

**2. IAM Role Trust Relationship**
- Problem: GitHub Actions cannot assume IAM role
- Solution: Verify trust relationship includes correct GitHub organization

**3. EventBridge Not Triggering**
- Problem: Step Functions not triggered on project creation
- Solution: Check EventBridge rule is enabled and pattern matches

**4. Model Approval Not Triggering Deploy**
- Problem: Deploy workflow not triggered after model approval
- Solution: Verify model approval EventBridge rule and Lambda logs

**5. Glue Database/Table Not Found**
- Problem: Build pipeline fails with Glue database errors
- Solution: Update GitHub secrets with correct Glue database/table names

#### Log Locations
- **Lambda Functions**: `/aws/lambda/{function-name}`
- **Step Functions**: `/aws/stepfunctions/{state-machine-name}`
- **EventBridge**: `/aws/events/rule/{rule-name}`
- **GitHub Actions**: Repository → Actions tab

### 10. Architecture Overview

#### Initial Setup and Infrastructure

    AWS CDK deploys the infrastructure including:
        AWS Lambda functions for project status, repository sync, and deployment
        AWS Step Functions for workflow orchestration
        EventBridge rules for event monitoring
        IAM roles and GitHub OIDC integration
        AWS Secrets Manager for GitHub token management

Project Creation and Repository Setup Flow

    When a user creates a project in SageMaker Unified Studio:
        EventBridge detects the project creation event
        Triggers Step Function workflow to orchestrate the repository setup process

    The Step Function workflow orchestrates three Lambda functions in sequence:
        check-project-status Lambda validates the project creation, gathers project details, and verifies SageMaker domain and space configurations
        sync-repositories Lambda creates necessary GitHub secrets for AWS integration, syncs the build repository with model building code from the template repository, which then triggers a workflow responsible for creating SageMaker pipeline for model building
        create-deploy-repository Lambda creates a separate deploy repository, configures required GitHub secrets, and sets up model deployment code from the template repository, which will be responsible for creating and updating SageMaker endpoints when triggered
