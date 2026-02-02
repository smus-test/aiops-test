# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Feature engineers the marketing dataset using AWS Data Wrangler for Glue integration."""
import argparse
import logging
import os
import pathlib
import sys
import subprocess
import boto3
import numpy as np
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# Install dependencies with specific order to handle version conflicts
logger.info("Installing dependencies with specific order")
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "awswrangler==2.16.1", "pymysql"])
    logger.info("Successfully installed AWS Data Wrangler and PyMySQL")
    
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas==1.3.5", "--force-reinstall"])
    logger.info("Successfully installed pandas 1.3.5")
except subprocess.CalledProcessError as e:
    logger.error(f"Error installing dependencies: {e}")
    sys.exit(1)

# Set up region and boto3 session before importing AWS Data Wrangler
region = os.environ.get('AWS_REGION', 'us-east-1')
boto3_session = boto3.Session(region_name=region)
logger.info(f"Created boto3 session with region: {region}")

# Import AWS Data Wrangler after installing dependencies
try:
    import awswrangler as wr
    wr.config.aws_region = region
    logger.info(f"Successfully imported AWS Data Wrangler version: {wr.__version__}")
except ImportError as e:
    logger.error(f"Error importing AWS Data Wrangler: {e}")
    sys.exit(1)


# Columns to remove (not available at prediction time or non-predictive)
COLUMNS_TO_REMOVE = [
    'duration',
    'emp.var.rate',
    'cons.price.idx',
    'cons.conf.idx',
    'euribor3m',
    'nr.employed'
]

# Job categories indicating not working
NOT_WORKING_JOBS = ['student', 'retired', 'unemployed']


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create derived features from the marketing dataset.
    
    Args:
        df: Input dataframe with raw marketing data
        
    Returns:
        DataFrame with derived features added
    """
    # no_previous_contact: 1 if pdays == 999 (no previous contact), 0 otherwise
    df['no_previous_contact'] = np.where(df['pdays'] == 999, 1, 0)
    
    # not_working: 1 if job is student, retired, or unemployed, 0 otherwise
    df['not_working'] = np.where(np.isin(df['job'], NOT_WORKING_JOBS), 1, 0)
    
    return df


def create_age_bins(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create age bin features for better model interpretability.
    
    Args:
        df: Input dataframe with age column
        
    Returns:
        DataFrame with age bin columns added
    """
    # Create age bins: young (18-30), middle (31-50), senior (51+)
    df['age_young'] = np.where((df['age'] >= 18) & (df['age'] <= 30), 1, 0)
    df['age_middle'] = np.where((df['age'] >= 31) & (df['age'] <= 50), 1, 0)
    df['age_senior'] = np.where(df['age'] >= 51, 1, 0)
    
    return df


def preprocess_marketing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all preprocessing steps to the marketing dataset.
    
    Args:
        df: Raw marketing dataframe
        
    Returns:
        Preprocessed dataframe ready for model training
    """
    logger.info(f"Starting preprocessing with {len(df)} rows")
    
    # Create derived features
    logger.info("Creating derived features")
    df = create_derived_features(df)
    
    # Create age bins
    logger.info("Creating age bins")
    df = create_age_bins(df)
    
    # Remove non-predictive columns
    logger.info(f"Removing columns: {COLUMNS_TO_REMOVE}")
    columns_to_drop = [col for col in COLUMNS_TO_REMOVE if col in df.columns]
    df = df.drop(columns=columns_to_drop)
    
    # Apply one-hot encoding to categorical columns
    logger.info("Applying one-hot encoding")
    df = pd.get_dummies(df, dtype=float)
    
    logger.info(f"Preprocessing complete. Final shape: {df.shape}")
    return df


def split_data(df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.2):
    """
    Split data into train, validation, and test sets.
    
    Args:
        df: Preprocessed dataframe
        train_ratio: Ratio for training set (default 0.7)
        val_ratio: Ratio for validation set (default 0.2)
        
    Returns:
        Tuple of (train_df, validation_df, test_df)
    """
    # Shuffle the data
    df_shuffled = df.sample(frac=1, random_state=1729).reset_index(drop=True)
    
    n = len(df_shuffled)
    train_end = int(train_ratio * n)
    val_end = int((train_ratio + val_ratio) * n)
    
    train_df = df_shuffled.iloc[:train_end]
    val_df = df_shuffled.iloc[train_end:val_end]
    test_df = df_shuffled.iloc[val_end:]
    
    logger.info(f"Data split: train={len(train_df)}, validation={len(val_df)}, test={len(test_df)}")
    
    return train_df, val_df, test_df


def prepare_output_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare dataframe for output with target variable as first column.
    
    Args:
        df: Preprocessed dataframe with y_yes and y_no columns
        
    Returns:
        DataFrame with y_yes as first column, y_no removed
    """
    # Get target column (y_yes from get_dummies)
    target_col = 'y_yes'
    
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataframe")
    
    # Remove y_no column if present
    if 'y_no' in df.columns:
        df = df.drop(columns=['y_no'])
    
    # Reorder columns with target first
    cols = [target_col] + [col for col in df.columns if col != target_col]
    df = df[cols]
    
    return df



if __name__ == "__main__":
    logger.info("Starting preprocessing with AWS Data Wrangler")
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-name", type=str, required=True)
    parser.add_argument("--table-name", type=str, required=True)
    args = parser.parse_args()

    base_dir = "/opt/ml/processing"
    pathlib.Path(f"{base_dir}/train").mkdir(parents=True, exist_ok=True)
    pathlib.Path(f"{base_dir}/validation").mkdir(parents=True, exist_ok=True)
    pathlib.Path(f"{base_dir}/test").mkdir(parents=True, exist_ok=True)
    
    # Read from Glue Data Catalog
    try:
        logger.info(f"Getting table location for {args.database_name}.{args.table_name}")
        s3_location = wr.catalog.get_table_location(
            database=args.database_name,
            table=args.table_name,
            boto3_session=boto3_session
        )
        logger.info(f"Found table S3 location: {s3_location}")
        
        logger.info("Reading data from S3 location")
        df = wr.s3.read_csv(
            path=s3_location,
            boto3_session=boto3_session
        )
        logger.info(f"Successfully read {len(df)} rows from S3 location")
        
    except Exception as e:
        logger.error(f"Error reading from Glue catalog: {e}")
        sys.exit(1)
    
    # Preprocess the data
    df = preprocess_marketing_data(df)
    
    # Split data
    train_df, val_df, test_df = split_data(df)
    
    # Prepare output with target as first column
    train_df = prepare_output_dataframe(train_df)
    val_df = prepare_output_dataframe(val_df)
    test_df = prepare_output_dataframe(test_df)
    
    # Write output datasets (no headers as required by XGBoost)
    logger.info(f"Writing out datasets to {base_dir}")
    train_df.to_csv(f"{base_dir}/train/train.csv", header=False, index=False)
    val_df.to_csv(f"{base_dir}/validation/validation.csv", header=False, index=False)
    test_df.to_csv(f"{base_dir}/test/test.csv", header=False, index=False)
    
    logger.info("Data preprocessing completed successfully")
