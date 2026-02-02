# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CDK Stack for deploying Marketing Classification SageMaker Endpoint."""

from aws_cdk import (
    Aws,
    Stack,
    Tags,
    aws_iam as iam,
    aws_kms as kms,
    aws_sagemaker as sagemaker,
)
import constructs
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from yamldataclassconfig import create_file_path_field

from .get_approved_package import get_approved_package
from config.constants import (
    PROJECT_NAME,
    PROJECT_ID,
    MODEL_PACKAGE_GROUP_NAME,
    DEPLOY_ACCOUNT,
    ECR_REPO_ARN,
    MODEL_BUCKET_ARN,
    AMAZON_DATAZONE_DOMAIN,
    AMAZON_DATAZONE_SCOPENAME,
    SAGEMAKER_DOMAIN_ARN,
    AMAZON_DATAZONE_PROJECT
)
from config.config_mux import StageYamlDataClassConfig


@dataclass
class EndpointConfigProductionVariant(StageYamlDataClassConfig):
    """Endpoint Config Production Variant Dataclass."""

    initial_instance_count: float = 1
    initial_variant_weight: float = 1
    instance_type: str = "ml.m5.large"
    variant_name: str = "AllTraffic"

    FILE_PATH: Path = create_file_path_field(
        "endpoint-config.yml", path_is_absolute=True
    )

    def get_endpoint_config_production_variant(self, model_name):
        """Create CDK SageMaker Endpoint Config Production Variant."""
        return sagemaker.CfnEndpointConfig.ProductionVariantProperty(
            initial_instance_count=self.initial_instance_count,
            initial_variant_weight=self.initial_variant_weight,
            instance_type=self.instance_type,
            variant_name=self.variant_name,
            model_name=model_name,
        )


class DeployEndpointStack(Stack):
    """Deploy Endpoint Stack for Marketing Classification Model."""

    def __init__(self, scope: constructs, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Add resource tags
        Tags.of(self).add("sagemaker:project-id", PROJECT_ID)
        Tags.of(self).add("sagemaker:project-name", PROJECT_NAME)
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)
        Tags.of(self).add("AmazonDataZoneDomain", AMAZON_DATAZONE_DOMAIN)
        Tags.of(self).add("AmazonDataZoneScopeName", AMAZON_DATAZONE_SCOPENAME)
        Tags.of(self).add("sagemaker:domain-arn", SAGEMAKER_DOMAIN_ARN)
        Tags.of(self).add("AmazonDataZoneProject", AMAZON_DATAZONE_PROJECT)

        # IAM role for model endpoint inference
        model_execution_policy = iam.ManagedPolicy(
            self,
            "ModelExecutionPolicy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["s3:Put*", "s3:Get*", "s3:List*"],
                        effect=iam.Effect.ALLOW,
                        resources=[MODEL_BUCKET_ARN, f"{MODEL_BUCKET_ARN}/*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[f"arn:aws:kms:{Aws.REGION}:{DEPLOY_ACCOUNT}:key/*"],
                    ),
                ]
            ),
        )

        if ECR_REPO_ARN:
            model_execution_policy.add_statements(
                iam.PolicyStatement(
                    actions=["ecr:Get*"],
                    effect=iam.Effect.ALLOW,
                    resources=[ECR_REPO_ARN],
                )
            )

        model_execution_role = iam.Role(
            self,
            "ModelExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                model_execution_policy,
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
        )

        # Timestamp for unique resource names
        now = datetime.now().replace(tzinfo=timezone.utc)
        timestamp = now.strftime("%Y%m%d%H%M%S")

        # Get latest approved model package
        latest_approved_model_package = get_approved_package()

        # SageMaker Model
        model_name = f"{MODEL_PACKAGE_GROUP_NAME}-{timestamp}"
        model = sagemaker.CfnModel(
            self,
            "Model",
            execution_role_arn=model_execution_role.role_arn,
            model_name=model_name,
            containers=[
                sagemaker.CfnModel.ContainerDefinitionProperty(
                    model_package_name=latest_approved_model_package
                )
            ],
        )

        # Endpoint Config
        endpoint_config_name = f"{MODEL_PACKAGE_GROUP_NAME}-ec-{timestamp}"
        endpoint_config_production_variant = EndpointConfigProductionVariant()
        endpoint_config_production_variant.load_for_stack(self)

        # KMS key for endpoint encryption
        kms_key = kms.Key(
            self,
            "endpoint-kms-key",
            description="Key for Marketing Classification SageMaker Endpoint encryption",
            enable_key_rotation=True,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["kms:*"],
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                        principals=[iam.AccountRootPrincipal()],
                    )
                ]
            ),
        )

        endpoint_config = sagemaker.CfnEndpointConfig(
            self,
            "EndpointConfig",
            endpoint_config_name=endpoint_config_name,
            kms_key_id=kms_key.key_id,
            production_variants=[
                endpoint_config_production_variant.get_endpoint_config_production_variant(
                    model.model_name
                )
            ],
        )
        endpoint_config.add_depends_on(model)

        # SageMaker Endpoint
        endpoint_name = f"{MODEL_PACKAGE_GROUP_NAME}-{AMAZON_DATAZONE_PROJECT}-{AMAZON_DATAZONE_SCOPENAME}"
        endpoint = sagemaker.CfnEndpoint(
            self,
            "Endpoint",
            endpoint_config_name=endpoint_config.endpoint_config_name,
            endpoint_name=endpoint_name,
        )
        endpoint.add_depends_on(endpoint_config)

        self.endpoint = endpoint
