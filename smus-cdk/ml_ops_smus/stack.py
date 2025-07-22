from aws_cdk import (
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy,
    Aws,
    CfnOutput
)
from constructs import Construct
import boto3
from .constructs.lambda_construct import LambdaConstruct
from .constructs.model_approval_lambda_construct import ModelApprovalLambdaConstruct
from .constructs.git_layer import GitLayerConstruct
from .constructs.dependency_layer import DependencyLayerConstruct
from .config import config

class RepoSyncStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role_name = config.oidc_role_github_workflow
        

        if not role_name:
            raise ValueError("OIDC role name for GitHub workflow is not provided in the config.")

        print(f"Using role name from config: {role_name}")
        iam_client = boto3.client('iam')

        try:
            iam_client.get_role(RoleName=role_name)
            print(f"Using existing role: {role_name}")
            github_workflow_role = iam.Role.from_role_name(
                self, "ExistingGitHubWorkflowRole",
                role_name=role_name
            )
            print(f"Using existing role: {role_name}")
            print(f"Role ARN: {github_workflow_role.role_arn}")

        except iam_client.exceptions.NoSuchEntityException:
            # Create role if it doesn't exist
            print(f"Role {role_name} not found. Creating new role...")
            account_id = Aws.ACCOUNT_ID
            github_org = config.private_github_organization

            github_workflow_role = iam.Role(
                self, "GitHubWorkflowRole",
                role_name=role_name,
                assumed_by=iam.CompositePrincipal(
                    iam.FederatedPrincipal(
                        federated=f"arn:aws:iam::{account_id}:oidc-provider/token.actions.githubusercontent.com",
                        conditions={
                            "StringEquals": {
                                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                            },
                            "StringLike": {
                                "token.actions.githubusercontent.com:sub": [
                                    f"repo:{github_org}/*" 
                                ]
                            }
                        },
                        assume_role_action="sts:AssumeRoleWithWebIdentity"
                    ),
                    iam.AccountRootPrincipal()
                )
            )
            # Add policies for new role
            github_workflow_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:CreatePipeline",
                    "sagemaker:UpdatePipeline",
                    "sagemaker:StartPipelineExecution",
                    "sagemaker:DescribePipeline",
                    "sagemaker:DescribePipelineExecution",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags",
                    "sagemaker:ListProcessingJobs",
                    "sagemaker:DescribeProcessingJob",
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:StopProcessingJob"
                ],
                resources=["*"]
            ))
            
            # Add S3 permissions
            github_workflow_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:CreateBucket"
                ],
                resources=["*"]
            ))
            
            # Add Glue permissions
            github_workflow_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "glue:GetTable",
                    "glue:GetDatabase",
                    "glue:GetPartitions"
                ],
                resources=["*"]
            ))
            
            # Add IAM PassRole permission
            github_workflow_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["iam:PassRole"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "iam:PassedToService": "sagemaker.amazonaws.com"
                    }
                }
            ))
            
            # Add CloudWatch Logs permissions
            github_workflow_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            ))
        
        # Create base EventBridge role first
        events_role = iam.Role(
            self, "EventBridgeRole",
            role_name="ml-ops-smus-eventbridge-role-v2",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com")
        )
        
        github_token_secret = secretsmanager.Secret(
            self, 'GitHubTokenSecret',
            secret_name=config.github_token_secret_name,
            description='GitHub Personal Access Token for repository access',
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters='/@"\'\\',
                generate_string_key='token',
                secret_string_template='{"token":""}',
                include_space=False
            )
        )

        git_layer = GitLayerConstruct(self, "GitLayer")
        dependency_layer = DependencyLayerConstruct(self, "DependencyLayer")

        #  Create Lambda construct (includes Step Function)
        repo_sync = LambdaConstruct(
            self, 
            "RepoSyncLambda",
            github_workflow_role_arn=github_workflow_role.role_arn,
            github_token_secret=github_token_secret, 
            git_layer=git_layer, 
            dependency_layer=dependency_layer
            )

        # Create Model Approval Lambda construct
        model_approval = ModelApprovalLambdaConstruct(
            self, 
            "ModelApprovalConstruct",
            github_token_secret=github_token_secret,
            git_layer=git_layer, 
            dependency_layer=dependency_layer 
        )
        
        #  Add Step Functions execution permissions after state machine is created
        events_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["states:StartExecution"],
                resources=[repo_sync.state_machine.state_machine_arn]
            )
        )

        #  Create EventBridge rule
        rule = events.Rule(
            self, "DataZoneProjectRule",
            rule_name="ml-ops-smus-datazone-project-rule-v2",
            description="Triggers Step Functions on DataZone Project Creation",
            enabled=True,
            event_pattern=events.EventPattern(
                source=["aws.datazone"],
                detail_type=["AWS API Call via CloudTrail"],
                detail={
                    "eventSource": ["datazone.amazonaws.com"],
                    "eventName": ["CreateProject"]
                }
            ),
            targets=[
                targets.SfnStateMachine(
                    repo_sync.state_machine,
                    role=events_role
                )
            ]
        )

        #  Add removal policies
        rule.apply_removal_policy(RemovalPolicy.DESTROY)
        events_role.apply_removal_policy(RemovalPolicy.DESTROY)

        #  Outputs
        CfnOutput(self, "StateMachineArn",
                 value=repo_sync.state_machine.state_machine_arn,
                 description="ARN of the Step Functions state machine")
        
        CfnOutput(self, "EventBridgeRuleName", 
                 value=rule.rule_name,
                 description="Name of the created EventBridge rule")
        
        CfnOutput(self, "EventBridgeRoleArn", 
                 value=events_role.role_arn,
                 description="ARN of the created EventBridge role")
        
        CfnOutput(self, "GitHubWorkflowRoleArn", 
                 value=github_workflow_role.role_arn,
                 description="ARN of the SageMaker pipeline role")

        CfnOutput(
            self, "ModelApprovalLambdaArn",
            value=model_approval.lambda_function.function_arn,
            description="ARN of the Model Approval Lambda function"
        )

        CfnOutput(
            self, "ModelApprovalRuleName",
            value=model_approval.event_rule.ref,
            description="Name of the Model Approval EventBridge rule"
        )

