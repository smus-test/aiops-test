import setuptools

setuptools.setup(
    name="ml-ops-smus",
    version="1.0.0",
    packages=setuptools.find_packages(),
    install_requires=[
        "aws-cdk-lib>=2.188.0",
        "constructs>=10.4.2",
        "boto3>=1.38.0"
    ],
)
