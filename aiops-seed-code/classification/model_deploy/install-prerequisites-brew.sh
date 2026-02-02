#!/bin/bash
# Install prerequisites for Marketing Classification model deployment

# Install miniconda
brew install --cask miniconda

# Install nodejs (required for AWS CDK)
brew install node

# Install docker (for CDK asset bundling)
brew install --cask docker

# Install AWS CDK
npm install -g aws-cdk

# Setup Python environment
conda create -n cdk-env python=3.8
conda activate cdk-env

# Install AWS CLI
pip install awscli
