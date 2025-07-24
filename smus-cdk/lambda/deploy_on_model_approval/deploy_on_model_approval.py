import json
import boto3
import requests
import os
from datetime import datetime

WORKFLOW_FILENAME = 'deploy_model_pipeline.yml'

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event, indent=2))
        
        # Extract project ID from ModelPackageGroupName
        model_package_group_name = event['detail']['ModelPackageGroupName']
        project_id = model_package_group_name.split('-')[1]
        
        print(f"Extracted project_id: {project_id}")

        # Get tags for the model package group
        account_id = event['account']
        region = event['region']
        model_package_group_arn = f"arn:aws:sagemaker:{region}:{account_id}:model-package-group/{model_package_group_name}"
        
        sagemaker_client = boto3.client('sagemaker')
        tags_response = sagemaker_client.list_tags(
            ResourceArn=model_package_group_arn
        )
        
        print("SageMaker Tags Response:", json.dumps(tags_response, indent=2, cls=DateTimeEncoder))
        
        # Extract domain ID from tags
        domain_id = None
        for tag in tags_response.get('Tags', []):
            if tag['Key'] == 'AmazonDataZoneDomain':
                domain_id = tag['Value']
                break
                
        if not domain_id:
            raise ValueError("Could not find AmazonDataZoneDomain tag in model package group tags")
        
        print(f"Found domain_id: {domain_id} from model package group tags")

        # Construct repository name using organization from environment variable
        private_organization_name = os.environ.get('PRIVATE_GITHUB_ORGANIZATION')
        if not private_organization_name:
            raise ValueError("PRIVATE_GITHUB_ORGANIZATION environment variable is not set")
            
        repo_name = f"{project_id}-{domain_id}-deploy-repo"
        
        # Get GitHub token from Secrets Manager
        secret_name = os.environ['GITHUB_TOKEN_SECRET_NAME']
        secrets_client = boto3.client('secretsmanager')
        secrets_response = secrets_client.get_secret_value(SecretId=secret_name)
        git_token = json.loads(secrets_response['SecretString'])['token']
        
        # GitHub API endpoint
        url = f'https://api.github.com/repos/{private_organization_name}/{repo_name}/actions/workflows/{WORKFLOW_FILENAME}/dispatches'

        # Headers for GitHub API
        headers = {
            'Authorization': f'token {git_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        # Payload for the workflow - only including the required logLevel input
        payload = {
            'ref': 'main',
            'inputs': {
                'logLevel': 'info'
            }
        }

        print(f"Triggering GitHub workflow with payload: {json.dumps(payload, indent=2)}")

        # Trigger the workflow
        github_response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if github_response.status_code == 204:
            print(f"Successfully triggered GitHub workflow for model {model_package_group_name}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Workflow triggered successfully',
                    'project_id': project_id,
                    'domain_id': domain_id,
                    'repository': f"{private_organization_name}/{repo_name}",
                    'model_package_group': model_package_group_name
                })
            }
        else:
            error_message = f"Failed to trigger workflow. Status code: {github_response.status_code}, Response: {github_response.text}"
            print(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'project_id': project_id if 'project_id' in locals() else None,
                'model_package_group': model_package_group_name if 'model_package_group_name' in locals() else None
            })
        }
