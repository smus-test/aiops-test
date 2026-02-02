# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Configuration constants for Marketing Classification model deployment."""

import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DEPLOYMENT_REGION = os.getenv("AWS_REGION")
DEPLOY_ACCOUNT = os.getenv("DEPLOY_ACCOUNT")

PROJECT_NAME = os.getenv("SAGEMAKER_PROJECT_NAME")
PROJECT_ID = os.getenv("SAGEMAKER_PROJECT_ID")
MODEL_PACKAGE_GROUP_NAME = os.getenv("MODEL_PACKAGE_GROUP_NAME")
ARTIFACT_BUCKET = os.getenv("ARTIFACT_BUCKET")
MODEL_BUCKET_ARN = f"arn:aws:s3:::{ARTIFACT_BUCKET}"
ECR_REPO_ARN = os.getenv("ECR_REPO_ARN")
AMAZON_DATAZONE_DOMAIN = os.getenv("AMAZON_DATAZONE_DOMAIN")
AMAZON_DATAZONE_SCOPENAME = os.getenv("AMAZON_DATAZONE_SCOPENAME")
SAGEMAKER_DOMAIN_ARN = os.getenv("SAGEMAKER_DOMAIN_ARN")
AMAZON_DATAZONE_PROJECT = os.getenv("AMAZON_DATAZONE_PROJECT")
