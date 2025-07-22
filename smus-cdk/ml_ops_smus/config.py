from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GitConfig:
    public_aiops_templates_org: str
    public_repo_branch: str
    oidc_role_github_workflow: str
    private_github_organization: str  # IMPORTANT: This should match the GitHub organization configured in your AWS CodeStar Connections and we will be creating our build and deploy repo under this git organization.
    private_deploy_repo_default_branch: str  
    specific_folders: Optional[List[str]]
    github_token_secret_name: str  # Add this field to the class definition
    
    def __init__(
        self,
        public_aiops_templates_org: str,
        public_repo_branch: str,
        oidc_role_github_workflow: str,
        private_github_organization: str,
        private_deploy_repo_default_branch: str,
        github_token_secret_name: str,
        specific_folders: Optional[List[str]] = None,
        ):
        self.public_aiops_templates_org = public_aiops_templates_org
        self.public_repo_branch = public_repo_branch
        self.oidc_role_github_workflow = oidc_role_github_workflow
        self.private_github_organization = private_github_organization
        self.private_deploy_repo_default_branch = private_deploy_repo_default_branch
        self.specific_folders = specific_folders
        self.github_token_secret_name = github_token_secret_name
        

# Single configuration instance
config = GitConfig(
    public_aiops_templates_org="smus-test/aiops-test",
    public_repo_branch="main",
    oidc_role_github_workflow="aiops-smus-github-action",
    private_github_organization ="smus-test", # IMPORTANT: This should match the GitHub organization configured in your AWS CodeStar Connections and we will be creating our build and deploy repo under this git organization.
    private_deploy_repo_default_branch="main",
    specific_folders=[],
    github_token_secret_name="ml-ops-smus-github-token",
)
