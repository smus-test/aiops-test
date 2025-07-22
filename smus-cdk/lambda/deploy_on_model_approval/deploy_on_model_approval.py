# lambda/deploy_on_model_approval/deploy_on_model_approval.py

import json
import boto3
import requests
import os


# Name of the GitHub Actions workflow file that handles model deployment
# NOTE: When a deploy repository is created, it's populated with seed code from the template
#       which includes 'deploy_model_pipeline.yml'. This workflow is triggered when a 
#       SageMaker model is approved, and it handles:
#       - Creating/Updating SageMaker endpoints
#       - Model deployment and testing
#       - Other deployment-related tasks
# IMPORTANT: If you modify the workflow filename in your template or deploy repositories,
#           update this value accordingly

WORKFLOW_FILENAME = 'deploy_model_pipeline.yml'

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event, indent=2))
        
        # Extract project ID from ModelPackageGroupName
        model_package_group_name = event['detail']['ModelPackageGroupName']
        project_id = model_package_group_name.split('-models')[0]
        
        # Get DataZone details
        datazone_client = boto3.client('datazone')
        
        # List projects to find the domain ID for our project
        projects_response = datazone_client.list_projects()
        domain_id = None
        
        for project in projects_response.get('projects', []):
            if project['identifier'] == project_id:
                domain_id = project['domainIdentifier']
                break
                
        if not domain_id:
            raise ValueError(f"Could not find domain ID for project: {project_id}")

        # Construct repository name using organization from environment variable
        private_organization_name = os.environ.get('PRIVATE_GITHUB_ORGANIZATION')
        repo_name = f"{project_id}-{domain_id}-deploy-repo"
        
        # Get GitHub token from Secrets Manager
        secret_name = os.environ['GITHUB_TOKEN_SECRET_NAME']
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        git_token = json.loads(response['SecretString'])['token']
        
        # GitHub API endpoint
        url = f'https://api.github.com/repos/{private_organization_name}/{repo_name}/actions/workflows/{WORKFLOW_FILENAME}/dispatches'

        # Headers for GitHub API
        headers = {
            'Authorization': f'token {git_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        # Payload for the workflow
        payload = {
            'ref': 'main',
            'inputs': {
                'model_name': event['detail']['ModelPackageName'],
                'model_package_group_name': model_package_group_name,
                'model_package_arn': event['detail']['ModelPackageArn'],
                'project_id': project_id,
                'domain_id': domain_id
            }
        }

        # Trigger the workflow
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 204:
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
            error_message = f"Failed to trigger workflow. Status code: {response.status_code}, Response: {response.text}"
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
