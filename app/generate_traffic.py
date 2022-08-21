"""Requests simulation module"""

import json
import time
import random

import requests

URL = "http://127.0.0.1:8081/predict"


AGE_MEAN = 29.9
AGE_STD = 13.5
SYSTOLIC_BP_MEAN = 113.2
SYSTOLIC_BP_STD = 18.4
DIASTOLIC_BP_MEAN = 76.5
DIASTOLIC_BP_STD = 13.9
BS_MEAN = 8.7
BS_STD = 3.3
BODY_TEMP_MEAN = 37
BODY_TEMP_STD = 0.7
HEART_RATE_MEAN = 74.3
HEART_RATE_STD = 8.1


def generate_traffic():
    """
    Sends continuous requests to prediction API
    """

    headers = {"Content-Type": "application/json"}

    while True:
        test_data = {
            "Age": random.uniform(AGE_MEAN - 2 * AGE_STD, AGE_MEAN + 2 * AGE_STD),
            "SystolicBP": random.uniform(
                SYSTOLIC_BP_MEAN - 2 * SYSTOLIC_BP_STD,
                SYSTOLIC_BP_MEAN + 2 * SYSTOLIC_BP_STD,
            ),
            "DiastolicBP": random.uniform(
                DIASTOLIC_BP_MEAN - 2 * DIASTOLIC_BP_STD,
                DIASTOLIC_BP_MEAN + 2 * DIASTOLIC_BP_STD,
            ),
            "BS": random.uniform(BS_MEAN - 2 * BS_STD, BS_MEAN + 2 * BS_STD),
            "BodyTemp": random.uniform(
                BODY_TEMP_MEAN - 2 * BODY_TEMP_STD, BODY_TEMP_MEAN + 2 * BODY_TEMP_STD
            ),
            "HeartRate": random.uniform(
                HEART_RATE_MEAN - 2 * HEART_RATE_STD,
                HEART_RATE_MEAN + 2 * HEART_RATE_STD,
            ),
        }
        payload = json.dumps(test_data)

        response = requests.request("POST", URL, headers=headers, data=payload)
        print(response.content)
        time.sleep(0.2)


if __name__ == "__main__":
    generate_traffic()
