from constructs import Construct
from aws_cdk import aws_lambda as _lambda
import os
import subprocess
import shutil

class DependencyLayerConstruct(Construct):
    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        layer_dir = self._build_dependency_layer()

        self.layer = _lambda.LayerVersion(
            self, 'DependencyLayer',
            code=_lambda.Code.from_asset(layer_dir),  # Use layer_dir (parent of python folder)
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            layer_version_name="ml-ops-smus-dependency-layer"
        )

    def _build_dependency_layer(self) -> str:
        project_root = os.getcwd()
        layer_dir = os.path.join(project_root, "dist")        # Parent directory
        python_path = os.path.join(layer_dir, "python")       # Python packages directory
        requirements_path = os.path.join(project_root, "layers", "python-layer", "requirements.txt")

        # Clean up existing build
        if os.path.exists(layer_dir):
            shutil.rmtree(layer_dir)

        # Create fresh directories
        os.makedirs(python_path, exist_ok=True)

        try:
            print(f"Installing dependencies to {python_path}")
            subprocess.run(
                ["pip", "install", "-r", requirements_path, "-t", python_path],
                check=True,
                capture_output=True,
                text=True
            )

            # Verify installation
            print("\nInstalled packages in layer:")
            for item in os.listdir(python_path):
                print(f"- {item}")

            return layer_dir  # Return parent directory, not python path

        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {str(e)}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            raise
