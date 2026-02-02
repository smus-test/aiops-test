"""Custom XGBoost training script with MLflow integration for marketing classification."""
import argparse
import json
import logging
import os
import tarfile

import mlflow
import mlflow.xgboost
import pandas as pd
import xgboost as xgb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    
    # Hyperparameters
    parser.add_argument("--max_depth", type=int, default=5)
    parser.add_argument("--eta", type=float, default=0.2)
    parser.add_argument("--gamma", type=float, default=4)
    parser.add_argument("--min_child_weight", type=float, default=6)
    parser.add_argument("--subsample", type=float, default=0.8)
    parser.add_argument("--num_round", type=int, default=100)
    parser.add_argument("--objective", type=str, default="binary:logistic")
    parser.add_argument("--eval_metric", type=str, default="auc")
    
    # MLflow tracking
    parser.add_argument("--mlflow_tracking_arn", type=str, default=None)
    
    # SageMaker environment variables
    parser.add_argument("--model_dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--validation", type=str, default=os.environ.get("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation"))
    
    return parser.parse_args()


def load_data(data_path):
    """Load CSV data without headers (target is first column)."""
    files = [f for f in os.listdir(data_path) if f.endswith(".csv")]
    if not files:
        raise ValueError(f"No CSV files found in {data_path}")
    
    df = pd.read_csv(os.path.join(data_path, files[0]), header=None)
    y = df.iloc[:, 0].values
    X = df.iloc[:, 1:].values
    return X, y


def train(args):
    """Train XGBoost model with MLflow tracking."""
    # Load training and validation data
    logger.info("Loading training data...")
    X_train, y_train = load_data(args.train)
    logger.info(f"Training data shape: {X_train.shape}")
    
    logger.info("Loading validation data...")
    X_val, y_val = load_data(args.validation)
    logger.info(f"Validation data shape: {X_val.shape}")
    
    # Create DMatrix for XGBoost
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    # Hyperparameters
    hyperparameters = {
        "max_depth": args.max_depth,
        "eta": args.eta,
        "gamma": args.gamma,
        "min_child_weight": args.min_child_weight,
        "subsample": args.subsample,
        "objective": args.objective,
        "eval_metric": args.eval_metric,
    }
    
    # Setup MLflow tracking if ARN provided
    mlflow_enabled = False
    if args.mlflow_tracking_arn:
        try:
            mlflow.set_tracking_uri(args.mlflow_tracking_arn)
            mlflow_enabled = True
            logger.info(f"MLflow tracking enabled: {args.mlflow_tracking_arn}")
        except Exception as e:
            logger.warning(f"Failed to connect to MLflow: {e}. Continuing without tracking.")
    
    # Start MLflow run if enabled
    if mlflow_enabled:
        mlflow.start_run()
        mlflow.log_params(hyperparameters)
        mlflow.log_param("num_round", args.num_round)
    
    # Training with evaluation
    evals = [(dtrain, "train"), (dval, "validation")]
    evals_result = {}
    
    logger.info("Starting XGBoost training...")
    model = xgb.train(
        params=hyperparameters,
        dtrain=dtrain,
        num_boost_round=args.num_round,
        evals=evals,
        evals_result=evals_result,
        early_stopping_rounds=10,
        verbose_eval=10,
    )
    
    # Log metrics to MLflow
    if mlflow_enabled:
        # Log final metrics
        train_metric = evals_result["train"][args.eval_metric][-1]
        val_metric = evals_result["validation"][args.eval_metric][-1]
        mlflow.log_metric(f"train_{args.eval_metric}", train_metric)
        mlflow.log_metric(f"validation_{args.eval_metric}", val_metric)
        
        # Log model to MLflow
        mlflow.xgboost.log_model(model, "model")
        logger.info("Model logged to MLflow")
        
        mlflow.end_run()
    
    # Save model for SageMaker
    model_path = os.path.join(args.model_dir, "xgboost-model")
    model.save_model(model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Create tar.gz for SageMaker endpoint compatibility
    tar_path = os.path.join(args.model_dir, "model.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(model_path, arcname="xgboost-model")
    logger.info(f"Model archived to {tar_path}")
    
    return model


if __name__ == "__main__":
    args = parse_args()
    train(args)
