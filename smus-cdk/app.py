#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from ml_ops_smus.stack import RepoSyncStack

app = App()

# Get account and region from environment or CDK context
# This will use the account/region from your AWS CLI profile or environment variables
account = os.environ.get('CDK_DEFAULT_ACCOUNT') or app.account
region = os.environ.get('CDK_DEFAULT_REGION') or app.region or 'us-east-1'

print(f"Deploying to Account: {account}, Region: {region}")

RepoSyncStack(app, "MlOpsSmusStack",
    env=Environment(
        account=account,
        region=region
    )
)

app.synth()
