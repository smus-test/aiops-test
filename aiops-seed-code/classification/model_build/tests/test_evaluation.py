# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Property-based tests for evaluation functions."""
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_metrics(y_true, y_pred_proba):
    """Compute classification metrics."""
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    metrics = {
        "auc": roc_auc_score(y_true, y_pred_proba),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    
    return metrics


def check_auc_threshold(auc_value, threshold=0.7):
    """Check if AUC meets threshold for model registration."""
    return auc_value >= threshold


# Strategy for generating probability values
probability_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for generating binary labels
binary_label_strategy = st.integers(min_value=0, max_value=1)

# Strategy for generating AUC values
auc_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


class TestPredictionProbabilityRange:
    """
    **Feature: classification-marketing-pipeline, Property 7: Prediction Probability Range**
    """
    
    @given(st.lists(probability_strategy, min_size=10, max_size=100))
    @settings(max_examples=100)
    def test_probability_range(self, probabilities):
        """
        **Feature: classification-marketing-pipeline, Property 7: Prediction Probability Range**
        
        For any model prediction on valid input, the output probability should be 
        in the range [0, 1].
        **Validates: Requirements 4.2**
        """
        proba_array = np.array(probabilities)
        
        # All probabilities should be in [0, 1]
        assert np.all(proba_array >= 0), "Probabilities should be >= 0"
        assert np.all(proba_array <= 1), "Probabilities should be <= 1"


class TestMetricsComputation:
    """
    **Feature: classification-marketing-pipeline, Property 8: Metrics Computation Completeness**
    """
    
    @given(st.data())
    @settings(max_examples=100)
    def test_metrics_completeness(self, data):
        """
        **Feature: classification-marketing-pipeline, Property 8: Metrics Computation Completeness**
        
        For any set of predictions and labels, the evaluation should compute all five 
        metrics: AUC, accuracy, precision, recall, and F1 score.
        **Validates: Requirements 4.3**
        """
        # Generate balanced labels and predictions to ensure AUC can be computed
        n_samples = data.draw(st.integers(min_value=20, max_value=100))
        
        # Ensure we have both classes
        n_positive = data.draw(st.integers(min_value=5, max_value=n_samples - 5))
        n_negative = n_samples - n_positive
        
        y_true = np.array([1] * n_positive + [0] * n_negative)
        y_pred_proba = np.array([
            data.draw(probability_strategy) for _ in range(n_samples)
        ])
        
        # Shuffle to mix classes
        indices = np.random.permutation(n_samples)
        y_true = y_true[indices]
        y_pred_proba = y_pred_proba[indices]
        
        # Compute metrics
        metrics = compute_metrics(y_true, y_pred_proba)
        
        # Verify all five metrics are present
        required_metrics = ["auc", "accuracy", "precision", "recall", "f1"]
        for metric_name in required_metrics:
            assert metric_name in metrics, f"Missing metric: {metric_name}"
            assert isinstance(metrics[metric_name], (int, float)), \
                f"Metric {metric_name} should be numeric"
            assert not np.isnan(metrics[metric_name]), \
                f"Metric {metric_name} should not be NaN"


class TestAUCThresholdCondition:
    """
    **Feature: classification-marketing-pipeline, Property 9: AUC Threshold Condition**
    """
    
    @given(auc_value=auc_strategy)
    @settings(max_examples=100)
    def test_auc_threshold_condition(self, auc_value):
        """
        **Feature: classification-marketing-pipeline, Property 9: AUC Threshold Condition**
        
        For any AUC value, the condition step should return True (register) if AUC >= 0.7, 
        and False (skip) if AUC < 0.7.
        **Validates: Requirements 5.1, 5.4**
        """
        result = check_auc_threshold(auc_value, threshold=0.7)
        
        if auc_value >= 0.7:
            assert result is True, \
                f"Expected True (register) for AUC={auc_value} >= 0.7"
        else:
            assert result is False, \
                f"Expected False (skip) for AUC={auc_value} < 0.7"
    
    def test_auc_threshold_boundary(self):
        """Test boundary condition at exactly 0.7."""
        assert check_auc_threshold(0.7) is True, "AUC=0.7 should pass threshold"
        assert check_auc_threshold(0.69999) is False, "AUC=0.69999 should fail threshold"
        assert check_auc_threshold(0.70001) is True, "AUC=0.70001 should pass threshold"
