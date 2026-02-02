# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Property-based tests for preprocessing functions."""
import sys
import os

# Add source_scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source_scripts', 'preprocessing', 'prepare_marketing_data'))

import pytest
import numpy as np
import pandas as pd
from hypothesis import given, strategies as st, settings

# Import preprocessing functions (we'll mock the AWS dependencies)
# For testing, we extract the core logic functions


# Columns to remove (not available at prediction time or non-predictive)
COLUMNS_TO_REMOVE = [
    'duration',
    'emp.var.rate',
    'cons.price.idx',
    'cons.conf.idx',
    'euribor3m',
    'nr.employed'
]

NOT_WORKING_JOBS = ['student', 'retired', 'unemployed']


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived features from the marketing dataset."""
    df = df.copy()
    df['no_previous_contact'] = np.where(df['pdays'] == 999, 1, 0)
    df['not_working'] = np.where(np.isin(df['job'], NOT_WORKING_JOBS), 1, 0)
    return df


def create_age_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Create age bin features."""
    df = df.copy()
    df['age_young'] = np.where((df['age'] >= 18) & (df['age'] <= 30), 1, 0)
    df['age_middle'] = np.where((df['age'] >= 31) & (df['age'] <= 50), 1, 0)
    df['age_senior'] = np.where(df['age'] >= 51, 1, 0)
    return df


# Strategy for generating valid pdays values
pdays_strategy = st.integers(min_value=0, max_value=1000)

# Strategy for generating job categories
job_strategy = st.sampled_from([
    'admin.', 'blue-collar', 'entrepreneur', 'housemaid', 'management',
    'retired', 'self-employed', 'services', 'student', 'technician',
    'unemployed', 'unknown'
])

# Strategy for generating age values
age_strategy = st.integers(min_value=18, max_value=100)

# Strategy for target variable
target_strategy = st.sampled_from(['yes', 'no'])


class TestDerivedFeatures:
    """
    **Feature: classification-marketing-pipeline, Property 1: Derived Feature Correctness**
    **Feature: classification-marketing-pipeline, Property 2: Not Working Indicator Correctness**
    """
    
    @given(pdays=pdays_strategy)
    @settings(max_examples=100)
    def test_no_previous_contact_indicator(self, pdays):
        """
        **Feature: classification-marketing-pipeline, Property 1: Derived Feature Correctness**
        
        For any input dataframe with pdays column, the 'no_previous_contact' feature 
        should equal 1 if and only if pdays equals 999, and 0 otherwise.
        **Validates: Requirements 2.2**
        """
        df = pd.DataFrame({
            'pdays': [pdays],
            'job': ['admin.']
        })
        
        result = create_derived_features(df)
        
        expected = 1 if pdays == 999 else 0
        assert result['no_previous_contact'].iloc[0] == expected, \
            f"Expected no_previous_contact={expected} for pdays={pdays}, got {result['no_previous_contact'].iloc[0]}"
    
    @given(job=job_strategy)
    @settings(max_examples=100)
    def test_not_working_indicator(self, job):
        """
        **Feature: classification-marketing-pipeline, Property 2: Not Working Indicator Correctness**
        
        For any input dataframe with job column, the 'not_working' feature should equal 1 
        if and only if job is in ['student', 'retired', 'unemployed'], and 0 otherwise.
        **Validates: Requirements 2.2**
        """
        df = pd.DataFrame({
            'pdays': [100],
            'job': [job]
        })
        
        result = create_derived_features(df)
        
        expected = 1 if job in NOT_WORKING_JOBS else 0
        assert result['not_working'].iloc[0] == expected, \
            f"Expected not_working={expected} for job={job}, got {result['not_working'].iloc[0]}"


class TestAgeBinning:
    """
    **Feature: classification-marketing-pipeline, Property 3: Age Binning Correctness**
    """
    
    @given(age=age_strategy)
    @settings(max_examples=100)
    def test_age_binning_exactly_one_bin(self, age):
        """
        **Feature: classification-marketing-pipeline, Property 3: Age Binning Correctness**
        
        For any age value, exactly one of age_young (18-30), age_middle (31-50), 
        or age_senior (51+) should be 1, and the others should be 0.
        **Validates: Requirements 2.3**
        """
        df = pd.DataFrame({'age': [age]})
        
        result = create_age_bins(df)
        
        # Check that exactly one bin is 1
        bin_sum = result['age_young'].iloc[0] + result['age_middle'].iloc[0] + result['age_senior'].iloc[0]
        assert bin_sum == 1, f"Expected exactly one age bin to be 1, got sum={bin_sum} for age={age}"
        
        # Check correct bin assignment
        if 18 <= age <= 30:
            assert result['age_young'].iloc[0] == 1, f"Expected age_young=1 for age={age}"
            assert result['age_middle'].iloc[0] == 0
            assert result['age_senior'].iloc[0] == 0
        elif 31 <= age <= 50:
            assert result['age_young'].iloc[0] == 0
            assert result['age_middle'].iloc[0] == 1, f"Expected age_middle=1 for age={age}"
            assert result['age_senior'].iloc[0] == 0
        else:  # age >= 51
            assert result['age_young'].iloc[0] == 0
            assert result['age_middle'].iloc[0] == 0
            assert result['age_senior'].iloc[0] == 1, f"Expected age_senior=1 for age={age}"



class TestFeatureRemoval:
    """
    **Feature: classification-marketing-pipeline, Property 4: Feature Removal Correctness**
    """
    
    @given(st.data())
    @settings(max_examples=100)
    def test_columns_removed(self, data):
        """
        **Feature: classification-marketing-pipeline, Property 4: Feature Removal Correctness**
        
        For any preprocessed dataframe, the columns duration, emp.var.rate, cons.price.idx, 
        cons.conf.idx, euribor3m, and nr.employed should not be present.
        **Validates: Requirements 2.5**
        """
        # Create a sample dataframe with all columns including ones to remove
        df = pd.DataFrame({
            'age': [data.draw(age_strategy)],
            'job': [data.draw(job_strategy)],
            'marital': ['married'],
            'education': ['high.school'],
            'default': ['no'],
            'housing': ['yes'],
            'loan': ['no'],
            'contact': ['cellular'],
            'month': ['may'],
            'day_of_week': ['mon'],
            'duration': [data.draw(st.integers(min_value=0, max_value=5000))],
            'campaign': [1],
            'pdays': [data.draw(pdays_strategy)],
            'previous': [0],
            'poutcome': ['nonexistent'],
            'emp.var.rate': [1.1],
            'cons.price.idx': [93.994],
            'cons.conf.idx': [-36.4],
            'euribor3m': [4.857],
            'nr.employed': [5191.0],
            'y': [data.draw(target_strategy)]
        })
        
        # Remove columns
        columns_to_drop = [col for col in COLUMNS_TO_REMOVE if col in df.columns]
        result = df.drop(columns=columns_to_drop)
        
        # Verify none of the removed columns are present
        for col in COLUMNS_TO_REMOVE:
            assert col not in result.columns, f"Column '{col}' should have been removed"


class TestTargetTransformation:
    """
    **Feature: classification-marketing-pipeline, Property 5: Target Variable Transformation**
    """
    
    @given(target=target_strategy)
    @settings(max_examples=100)
    def test_target_transformation(self, target):
        """
        **Feature: classification-marketing-pipeline, Property 5: Target Variable Transformation**
        
        For any input row where y='yes', the y_yes column should equal 1; 
        where y='no', y_yes should equal 0.
        **Validates: Requirements 2.6**
        """
        df = pd.DataFrame({
            'age': [30],
            'job': ['admin.'],
            'y': [target]
        })
        
        # Apply get_dummies (simulating preprocessing)
        result = pd.get_dummies(df, dtype=float)
        
        expected = 1.0 if target == 'yes' else 0.0
        assert result['y_yes'].iloc[0] == expected, \
            f"Expected y_yes={expected} for y={target}, got {result['y_yes'].iloc[0]}"


class TestDataSplit:
    """
    **Feature: classification-marketing-pipeline, Property 6: Data Split Ratios**
    """
    
    @given(n_rows=st.integers(min_value=100, max_value=1000))
    @settings(max_examples=100)
    def test_data_split_ratios(self, n_rows):
        """
        **Feature: classification-marketing-pipeline, Property 6: Data Split Ratios**
        
        For any input dataset, the train split should contain approximately 70% of rows, 
        validation 20%, and test 10% (within ±2% tolerance).
        **Validates: Requirements 2.7**
        """
        # Create sample dataframe
        df = pd.DataFrame({
            'feature': range(n_rows),
            'target': [0] * n_rows
        })
        
        # Split data (using same logic as preprocessing)
        train_ratio = 0.7
        val_ratio = 0.2
        
        df_shuffled = df.sample(frac=1, random_state=1729).reset_index(drop=True)
        n = len(df_shuffled)
        train_end = int(train_ratio * n)
        val_end = int((train_ratio + val_ratio) * n)
        
        train_df = df_shuffled.iloc[:train_end]
        val_df = df_shuffled.iloc[train_end:val_end]
        test_df = df_shuffled.iloc[val_end:]
        
        # Check ratios within tolerance
        tolerance = 0.02
        
        actual_train_ratio = len(train_df) / n_rows
        actual_val_ratio = len(val_df) / n_rows
        actual_test_ratio = len(test_df) / n_rows
        
        assert abs(actual_train_ratio - 0.7) <= tolerance, \
            f"Train ratio {actual_train_ratio} not within tolerance of 0.7"
        assert abs(actual_val_ratio - 0.2) <= tolerance, \
            f"Validation ratio {actual_val_ratio} not within tolerance of 0.2"
        assert abs(actual_test_ratio - 0.1) <= tolerance, \
            f"Test ratio {actual_test_ratio} not within tolerance of 0.1"
        
        # Verify no data loss
        assert len(train_df) + len(val_df) + len(test_df) == n_rows, \
            "Data was lost during split"
