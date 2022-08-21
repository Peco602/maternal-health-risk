#!/usr/bin/env python
# coding: utf-8

"""Integration tests module"""

import requests

url = "http://localhost:8082/predict"

test_data = {
    "Age": 20,
    "SystolicBP": 120,
    "DiastolicBP": 70,
    "BS": 2.0,
    "BodyTemp": 36.0,
    "HeartRate": 60,
}
response = requests.post(url, json=test_data).json()
assert response['RiskLevel'] in ['low risk', 'mid risk', 'high risk']
