import os
from constructs import Construct
from aws_cdk import (
    Duration, 
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    CfnOutput
)

from ..config import config

class LambdaConstruct(Construct):
    def __init__(self, scope: Construct, id: str, github_workflow_role_arn: str, github_token_secret, git_layer, dependency_layer) -> None:
        super().__init__(scope, id)

        self.function_names = {
            'check_status': "ai-ops-check-project-status",
            'sync_repos': "ai-ops-sync-repositories",
            'create_deploy_repo': "ai-ops-create-deploy-repo"
        }

        self.stack = Stack.of(self)
        self.region = self.stack.region
        self.account = self.stack.account
        self.github_workflow_role_arn = github_workflow_role_arn

        self.github_token_secret = github_token_secret

        self.git_layer = git_layer
        self.dependency_layer = dependency_layer

        lambda_role = self.create_lambda_role()

        self.lambda_functions = self.create_lambda_functions(self.git_layer, self.dependency_layer, lambda_role)

        step_function_tasks = self.create_step_function_tasks(self.lambda_functions)

        self.state_machine = self.create_state_machine(step_function_tasks)

        self.create_outputs()

    def create_lambda_role(self):
        role = iam.Role(
            self, 'CommonLambdaRole',
            role_name=f"{self.stack.stack_name}-lambda-role",
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        # Create log group ARNs for each Lambda function
        log_group_arns = [
            f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/{func_name}:*"
            for func_name in self.function_names.values()
        ]

        # Add CloudWatch Logs permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents'
            ],
            resources=log_group_arns
        ))

        # Add Secrets Manager permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['secretsmanager:GetSecretValue'],
            resources=[self.github_token_secret.secret_arn]
        ))

        # Add DataZone permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'datazone:GetProjectProfile',
                'datazone:GetDomain',
                'datazone:GetProject'
            ],
            resources=[f"arn:aws:datazone:{self.region}:{self.account}:domain/*"]
        ))

        # Add SageMaker permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'sagemaker:ListDomains',
                'sagemaker:DescribeDomain',
                'sagemaker:ListSpaces',
                'sagemaker:DescribeSpace',
                'sagemaker:DescribeUserProfile',
                'sagemaker:ListTags'
            ],
            resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:domain/*",
                f"arn:aws:sagemaker:{self.region}:{self.account}:user-profile/*",
                f"arn:aws:sagemaker:{self.region}:{self.account}:space/*"
            ]
        ))

        # Add CodeStar Connections permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'codestar-connections:GetConnection',
                'codestar-connections:GetHostAccessToken'
            ],
            resources=[f"arn:aws:codestar-connections:{self.region}:{self.account}:connection/*"]
        ))
        
        # Add IAM permissions for datazone user roles
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'iam:PutRolePolicy',
                'iam:GetRolePolicy',
                'iam:DeleteRolePolicy',
                'iam:ListRolePolicies'
            ],
            resources=[f"arn:aws:iam::{self.account}:role/datazone_usr_role*"]
        ))

        return role

    def create_lambda_functions(self, git_layer, dependency_layer, lambda_role):
        common_props = {
            "runtime": _lambda.Runtime.PYTHON_3_9,
            "memory_size": 1024,
            "timeout": Duration.minutes(15),
            "layers": [git_layer.layer, dependency_layer.layer],
            "role": lambda_role,  
            "environment": {
                "PUBLIC_AIOPS_TEMPLATES_ORG": config.public_aiops_templates_org,
                "OIDC_ROLE_GITHUB_WORKFLOW": self.github_workflow_role_arn,
                "SPECIFIC_FOLDERS": str(config.specific_folders),
                "GITHUB_TOKEN_SECRET_NAME": config.github_token_secret_name,
                "PRIVATE_GITHUB_ORGANIZATION": config.private_github_organization,
                "PRIVATE_DEPLOY_REPO_DEFAULT_BRANCH": config.private_deploy_repo_default_branch,
                "PATH": "/opt/gh:/opt/git/bin:/var/task:/opt:/var/lang/bin:/usr/local/bin:/usr/bin/:/bin",
                "LD_LIBRARY_PATH": "/opt/git/lib",
                "GIT_EXEC_PATH": "/opt/git/lib/git-core",
                "GIT_TEMPLATE_DIR": "/opt/git/share/git-core/templates",
                "GIT": "/opt/git/bin/git",
                "GH_PATH": "/opt/gh/gh",
            }
        }

        functions = {
            'check_status': _lambda.Function(
                self,
                'CheckProjectStatus',
                handler='index.lambda_handler',
                code=_lambda.Code.from_asset("lambda/check-project-status"),
                function_name="ml-ops-check-project-status",
                **common_props
            ),
            'sync_repos': _lambda.Function(
                self,
                'SyncRepositories',
                handler='index.lambda_handler',
                code=_lambda.Code.from_asset("lambda/sync-repositories"),
                function_name="ml-ops-sync-repositories",
                **common_props
            ),
            'create_deploy_repo': _lambda.Function(
                self,
                'CreateDeployRepository',
                handler='index.lambda_handler',
                code=_lambda.Code.from_asset("lambda/create-deploy-repository"),
                function_name="ml-ops-create-deploy-repo",
                **common_props
            )
        }

        # Grant secret access to sync_repos function
        self.github_token_secret.grant_read(functions['sync_repos'])

        return functions

    def create_step_function_tasks(self, functions):
        return {
            name: tasks.LambdaInvoke(
                self,
                f"Invoke {name.replace('_', ' ').title()}",
                lambda_function=func,
                output_path='$.Payload'
            )
            for name, func in functions.items()
        }

    def create_state_machine(self, step_tasks):
        definition = sfn.Chain\
            .start(sfn.Wait(
                self, 
                'Wait Initial',
                time=sfn.WaitTime.duration(Duration.seconds(10))
            ))\
            .next(step_tasks['check_status'])\
            .next(
                sfn.Choice(self, 'Is Project Ready?')
                .when(
                    sfn.Condition.string_equals('$.status', 'SUCCESSFUL'),
                    step_tasks['sync_repos']
                    .next(
                        sfn.Choice(self, 'Check Space Status')
                        .when(
                            sfn.Condition.string_equals('$.status', 'WAITING_FOR_SPACE'),
                            sfn.Wait(
                                self,
                                'Wait For Space',
                                time=sfn.WaitTime.duration(Duration.minutes(3))
                            )
                            .next(
                                sfn.Pass(
                                    self,
                                    'Preserve Context',
                                    parameters={
                                        "projectId.$": "$.projectId",
                                        "domainId.$": "$.domainId",
                                        "status.$": "$.status",
                                        "buildRepo.$": "$.buildRepo",
                                        "additionalInfo.$": "$.additionalInfo"
                                    }
                                )
                            )
                            .next(step_tasks['sync_repos'])
                        )
                        .when(
                            sfn.Condition.string_equals('$.status', 'SUCCESSFUL'),
                            step_tasks['create_deploy_repo']
                            .next(
                                sfn.Choice(self, 'Create Deploy Repo Success?')
                                .when(
                                    sfn.Condition.string_equals('$.status', 'SUCCESSFUL'),
                                    sfn.Succeed(self, 'Project Setup Successful')
                                )
                                .otherwise(
                                    sfn.Fail(self, 'Deploy Repo Creation Failed', cause='$.error')
                                )
                            )
                        )
                        .otherwise(
                            sfn.Fail(self, 'Sync Repos Failed', cause='$.error')
                        )
                    )
                )
                .when(
                    sfn.Condition.string_equals('$.status', 'FAILED'),
                    sfn.Fail(self, 'Project Creation Failed', cause='$.error')
                )
                .otherwise(
                    sfn.Wait(
                        self,
                        'Wait For Project',
                        time=sfn.WaitTime.duration(Duration.seconds(60))
                    )
                    .next(step_tasks['check_status'])
                )
            )

        return sfn.StateMachine(
            self,
            'StateMachine',
            definition=definition,
            timeout=Duration.hours(2),
            state_machine_name="ml-ops-project-setup"
        )


    def create_outputs(self):
        
        CfnOutput(
            self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="ARN of the Step Functions state machine"
        )
