# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CDK Application entry point for Marketing Classification model deployment."""

from aws_cdk import App, Environment
from deploy_endpoint.deploy_endpoint_stack import DeployEndpointStack
from config.constants import (
    DEPLOY_ACCOUNT,
    DEFAULT_DEPLOYMENT_REGION,
    AMAZON_DATAZONE_SCOPENAME,
    AMAZON_DATAZONE_PROJECT
)


app = App()

dev_env = Environment(
    account=DEPLOY_ACCOUNT,
    region=DEFAULT_DEPLOYMENT_REGION
)

DeployEndpointStack(
    app,
    f"marketing-classification-{AMAZON_DATAZONE_PROJECT}",
    env=dev_env
)

app.synth()
