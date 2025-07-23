from constructs import Construct
from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
    aws_events as events,
    Stack,
    aws_secretsmanager as secretsmanager
)

from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_lambda import CfnPermission
from ..config import config

class ModelApprovalLambdaConstruct(Construct):
    def __init__(self, scope: Construct, id: str, github_token_secret, git_layer, dependency_layer, **kwargs) -> None:
        super().__init__(scope, id)

        self.stack = Stack.of(self)

        # Create Lambda role with necessary permissions
        lambda_role = self.create_lambda_role(github_token_secret)

        # Create Lambda function
        self.lambda_function = self.create_lambda_function(
            role=lambda_role,
            git_layer=git_layer,
            dependency_layer=dependency_layer
        )

        events_role = self.create_events_role()

        # Create EventBridge rule using L1 construct
        self.event_rule = self.create_event_rule(events_role)

        # Create outputs
        self.create_outputs()

    def create_lambda_role(self, github_token_secret):
        role = iam.Role(
            self, 'ModelApprovalLambdaRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        # CloudWatch Logs permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents'
            ],
            resources=[
                f"arn:aws:logs:{self.stack.region}:{self.stack.account}:log-group:/aws/lambda/*"
            ]
        ))

        # DataZone permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'datazone:ListProjects',
                'datazone:GetProject',
                'datazone:GetDomain'
            ],
            resources=['*']
        ))

        # Secrets Manager permissions for GitHub token
        github_token_secret.grant_read(role)

        return role

    def create_lambda_function(self, role, git_layer, dependency_layer):
        return _lambda.Function(
            self, 'ModelApprovalFunction',
            function_name=f"{self.stack.stack_name}-model-approval-trigger",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='deploy_on_model_approval.lambda_handler',
            code=_lambda.Code.from_asset('lambda/deploy_on_model_approval'),
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                'GITHUB_TOKEN_SECRET_NAME': config.github_token_secret_name,
                "PRIVATE_GITHUB_ORGANIZATION": config.private_github_organization,
                'PATH': '/opt/gh:/opt/git/bin:/var/task:/opt:/var/lang/bin:/usr/local/bin:/usr/bin/:/bin',
                'LD_LIBRARY_PATH': '/opt/git/lib',
                'GIT_EXEC_PATH': '/opt/git/lib/git-core',
                'GIT_TEMPLATE_DIR': '/opt/git/share/git-core/templates',
                'GIT': '/opt/git/bin/git',
                'GH_PATH': '/opt/gh/gh'
            },
            layers=[git_layer.layer, dependency_layer.layer],
            role=role
        )

    def create_events_role(self):
        events_role = iam.Role(
            self, 'EventBridgeInvokeLambdaRole',
            assumed_by=iam.ServicePrincipal('events.amazonaws.com'),
            description='Role for EventBridge to invoke Lambda function'
        )

        events_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['lambda:InvokeFunction'],
            resources=[self.lambda_function.function_arn]
        ))

        return events_role

    def create_event_rule(self, events_role: iam.Role):
        # Create EventBridge rule using L1 construct
        rule = CfnRule(
            self, 'ModelApprovalRule',
            name=f"{self.stack.stack_name}-model-approval-rule",
            description='Triggers GitHub workflow when a model is approved in SageMaker',
            state='ENABLED',
            event_pattern={
                "source": ["aws.sagemaker"],
                "detail-type": ["SageMaker Model Package State Change"],
                "detail": {
                    "ModelApprovalStatus": ["Approved"]
                }
            },
            targets=[{
                'id': 'ModelApprovalLambda',
                'arn': self.lambda_function.function_arn,
                'roleArn': events_role.role_arn
            }]
        )

        return rule

    def create_outputs(self):
        CfnOutput(
            self, 'ModelApprovalLambdaArn',
            value=self.lambda_function.function_arn,
            description='ARN of the Model Approval Lambda function'
        )

        CfnOutput(
            self, 'ModelApprovalRuleName',
            value=self.event_rule.ref,
            description='Name of the Model Approval EventBridge rule'
        )
