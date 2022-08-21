"""testing module for train functions"""

import numpy as np
import train
import pandas as pd
from deepdiff import DeepDiff


def test_prepare_data():
    """
    Tests the prepare_data function
    """
    input_data = [
        (29, 90, 70, 8, 100, 80, "high risk"),
        (30, 140, 85, 7, 98, 70, "high risk"),
        (35, 120, 60, 6.1, 98, 76, "low risk"),
        (10, 140, 80, 7.01, 98, 70, "high risk"),
        (23, 130, 70, 7.01, 98, 78, "mid risk"),
    ]

    input_columns = [
        'Age',
        'SystolicBP',
        'DiastolicBP',
        'BS',
        'BodyTemp',
        'HeartRate',
        'RiskLevel',
    ]
    input_df = pd.DataFrame(input_data, columns=input_columns)

    X_output_df, y_output_df = train.prepare_data.fn(input_df)
    print(f"X_output_df={X_output_df}")
    print(f"y_output_df={y_output_df}")

    X_expected_data = [
        (29, 90, 70, 8, 37.8, 80),
        (30, 140, 85, 7, 36.7, 70),
        (35, 120, 60, 6.1, 36.7, 76),
        (23, 130, 70, 7.01, 36.7, 78),
    ]
    X_expected_columns = [
        'Age',
        'SystolicBP',
        'DiastolicBP',
        'BS',
        'BodyTemp',
        'HeartRate',
    ]
    X_expected_df = pd.DataFrame(X_expected_data, columns=X_expected_columns)

    y_expected_data = [0, 0, 1, 2]
    y_expected_df = np.array(y_expected_data)

    X_diff = DeepDiff(
        X_output_df.reset_index(drop=True).to_dict(),
        X_expected_df.reset_index(drop=True).to_dict(),
        significant_digits=1,
    )
    print(f"X_diff={X_diff}")
    assert not X_diff

    y_diff = DeepDiff(y_output_df, y_expected_df)
    print(f"y_diff={y_diff}")
    assert not y_diff
