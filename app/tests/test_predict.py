"""testing module for prediction functions"""

import json

import predict

client = predict.app.test_client()


def test_validate_data():
    """
    Tests the validate_data function
    """
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 120,
                "DiastolicBP": 70,
                "BS": 2.0,
                "BodyTemp": 36,
                "HeartRate": 60,
            }
        )
        is None
    )
    assert (
        predict.validate_data(
            {
                "Age": 60,
                "SystolicBP": 120,
                "DiastolicBP": 70,
                "BS": 2.0,
                "BodyTemp": 36,
                "HeartRate": 60,
            }
        )
        == "Age should be between 13 and 50 years"
    )
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 120,
                "DiastolicBP": 40,
                "BS": 2.0,
                "BodyTemp": 36,
                "HeartRate": 60,
            }
        )
        == "Blood pressure should be between 50 and 200 mmHg."
    )
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 70,
                "DiastolicBP": 120,
                "BS": 2.0,
                "BodyTemp": 36,
                "HeartRate": 60,
            }
        )
        == "Systolic blood pressure should be higher that diastolic."
    )
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 120,
                "DiastolicBP": 70,
                "BS": 20.0,
                "BodyTemp": 36,
                "HeartRate": 60,
            }
        )
        == "Blood sugar level should be between 0 and 15 mmol/L."
    )
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 120,
                "DiastolicBP": 70,
                "BS": 2.0,
                "BodyTemp": 30,
                "HeartRate": 60,
            }
        )
        == "Body temperature should be between 34 and 41 celsius degrees."
    )
    assert (
        predict.validate_data(
            {
                "Age": 20,
                "SystolicBP": 120,
                "DiastolicBP": 70,
                "BS": 2.0,
                "BodyTemp": 36,
                "HeartRate": 200,
            }
        )
        == "Heart rate should be between 45 and 130 bpm."
    )


def test_calculate_risk():
    """
    Tests the calculate_risk function
    """
    assert predict.convert_risk(0) == ("high risk", "danger")
    assert predict.convert_risk(1) == ("low risk", "success")
    assert predict.convert_risk(2) == ("mid risk", "warning")


def test_predict_json_endpoint():
    """
    Tests the JSON predict endpoint
    """
    PREDICT_URL = '/predict'
    HEADER = {'Content-Type': 'application/json'}

    low_risk_test_data = {
        "Age": 20,
        "SystolicBP": 120,
        "DiastolicBP": 70,
        "BS": 2.0,
        "BodyTemp": 36,
        "HeartRate": 60,
    }
    response = client.post(
        PREDICT_URL,
        data=json.dumps(low_risk_test_data),
        headers=HEADER,
    )
    assert response.json['RiskLevel'] == 'low risk'

    mid_risk_test_data = {
        "Age": 35,
        "SystolicBP": 130,
        "DiastolicBP": 90,
        "BS": 7.0,
        "BodyTemp": 36.5,
        "HeartRate": 60,
    }
    response = client.post(
        PREDICT_URL,
        data=json.dumps(mid_risk_test_data),
        headers=HEADER,
    )
    assert response.json['RiskLevel'] == 'mid risk'

    high_risk_test_data = {
        "Age": 45,
        "SystolicBP": 160,
        "DiastolicBP": 90,
        "BS": 10,
        "BodyTemp": 38,
        "HeartRate": 70,
    }
    response = client.post(
        PREDICT_URL,
        data=json.dumps(high_risk_test_data),
        headers=HEADER,
    )
    assert response.json['RiskLevel'] == 'high risk'
