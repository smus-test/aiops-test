"""Evaluation script for marketing classification model."""
import argparse
import json
import logging
import os
import tarfile

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlflow-tracking-arn", type=str, default=None)
    return parser.parse_args()


def load_model(model_path):
    """Load XGBoost model from tar.gz artifact."""
    logger.info(f"Loading model from {model_path}")
    
    # Find the model tar.gz file
    model_tar = os.path.join(model_path, "model.tar.gz")
    if not os.path.exists(model_tar):
        # Try to find any tar.gz file
        for f in os.listdir(model_path):
            if f.endswith(".tar.gz"):
                model_tar = os.path.join(model_path, f)
                break
    
    # Extract the model
    extract_dir = "/tmp/model"
    os.makedirs(extract_dir, exist_ok=True)
    
    with tarfile.open(model_tar, "r:gz") as tar:
        tar.extractall(extract_dir)
    
    # Load the XGBoost model
    model_file = os.path.join(extract_dir, "xgboost-model")
    if not os.path.exists(model_file):
        # Try to find the model file
        for f in os.listdir(extract_dir):
            if "xgboost" in f.lower() or "model" in f.lower():
                model_file = os.path.join(extract_dir, f)
                break
    
    model = xgb.Booster()
    model.load_model(model_file)
    logger.info("Model loaded successfully")
    return model


def load_test_data(test_path):
    """Load test data (CSV without headers, target is first column)."""
    logger.info(f"Loading test data from {test_path}")
    
    files = [f for f in os.listdir(test_path) if f.endswith(".csv")]
    if not files:
        raise ValueError(f"No CSV files found in {test_path}")
    
    df = pd.read_csv(os.path.join(test_path, files[0]), header=None)
    y_true = df.iloc[:, 0].values
    X = df.iloc[:, 1:].values
    
    logger.info(f"Test data shape: X={X.shape}, y={y_true.shape}")
    return X, y_true


def compute_metrics(y_true, y_pred_proba):
    """Compute classification metrics."""
    # Convert probabilities to binary predictions
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    metrics = {
        "auc": roc_auc_score(y_true, y_pred_proba),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    
    return metrics


def main():
    args = parse_args()
    
    # Paths
    model_path = "/opt/ml/processing/model"
    test_path = "/opt/ml/processing/test"
    output_path = "/opt/ml/processing/evaluation"
    
    os.makedirs(output_path, exist_ok=True)
    
    # Load model and test data
    model = load_model(model_path)
    X_test, y_true = load_test_data(test_path)
    
    # Generate predictions
    dtest = xgb.DMatrix(X_test)
    y_pred_proba = model.predict(dtest)
    
    logger.info(f"Predictions range: [{y_pred_proba.min():.4f}, {y_pred_proba.max():.4f}]")
    
    # Compute metrics
    metrics = compute_metrics(y_true, y_pred_proba)
    
    logger.info("Classification Metrics:")
    for name, value in metrics.items():
        logger.info(f"  {name}: {value:.4f}")
    
    # Write evaluation.json
    evaluation_output = {
        "classification_metrics": {
            "auc": {"value": metrics["auc"]},
            "accuracy": {"value": metrics["accuracy"]},
            "precision": {"value": metrics["precision"]},
            "recall": {"value": metrics["recall"]},
            "f1": {"value": metrics["f1"]},
        }
    }
    
    output_file = os.path.join(output_path, "evaluation.json")
    with open(output_file, "w") as f:
        json.dump(evaluation_output, f, indent=2)
    
    logger.info(f"Evaluation results written to {output_file}")
    
    # Log to MLflow if tracking ARN provided
    if args.mlflow_tracking_arn:
        try:
            import mlflow
            mlflow.set_tracking_uri(args.mlflow_tracking_arn)
            
            with mlflow.start_run():
                for name, value in metrics.items():
                    mlflow.log_metric(name, value)
                mlflow.log_artifact(output_file)
            
            logger.info("Metrics logged to MLflow")
        except Exception as e:
            logger.warning(f"Failed to log to MLflow: {e}")


if __name__ == "__main__":
    main()
