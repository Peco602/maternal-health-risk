"""Prediction module"""

import os
import pickle

import mlflow
import pandas as pd
import requests
from flask import Flask, flash, jsonify, request, render_template
from pymongo import MongoClient

EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "maternal-health-risk")
MLFLOW_ENABLED = os.getenv("MLFLOW_ENABLED", "False") == "True"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
DEFAULT_MODEL_ENABLED = os.getenv("DEFAULT_MODEL_ENABLED", "True") == "True"
MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "False") == "True"
EVIDENTLY_SERVICE_URI = os.getenv("EVIDENTLY_SERVICE_URI", "http://localhost:8085")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
if not os.getenv("MLFLOW_S3_ENDPOINT_URL"):
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"

if MONITORING_ENABLED:
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client.get_database("prediction_service")
    collection = db.get_collection(EXPERIMENT_NAME)


def load_model_from_registry():
    """
    Loads the ML model from the MLFlow registry
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    model_uri = f"models:/{EXPERIMENT_NAME}/latest"
    loaded_model = mlflow.pyfunc.load_model(model_uri)
    print("Loaded model from S3 Bucket")
    return loaded_model


def load_default_model():
    """
    Loads the default ML model from disk
    """
    with open(f"{os.path.dirname(os.path.abspath(__file__))}/model.bin", "rb") as f_in:
        loaded_model = pickle.load(f_in)
    print("Loaded default model from disk")
    return loaded_model


def load_model():
    """
    Loads the ML model
    """
    try:
        if MLFLOW_ENABLED:
            return load_model_from_registry()

        if DEFAULT_MODEL_ENABLED:
            return load_default_model()
    except:
        if DEFAULT_MODEL_ENABLED:
            return load_default_model()

    return None


def validate_data(record):
    """
    Performs data validation
    """
    if record["Age"] < 13 or record["Age"] > 50:
        return "Age should be between 13 and 50 years"

    if (
        record["SystolicBP"] < 50
        or record["SystolicBP"] > 200
        or record["DiastolicBP"] < 50
        or record["DiastolicBP"] > 200
    ):
        return "Blood pressure should be between 50 and 200 mmHg."

    if record["SystolicBP"] <= record["DiastolicBP"]:
        return "Systolic blood pressure should be higher that diastolic."

    if record["BS"] < 0.1 or record["BS"] > 15:
        return "Blood sugar level should be between 0 and 15 mmol/L."

    if record["BodyTemp"] < 34 or record["BodyTemp"] > 41:
        return "Body temperature should be between 34 and 41 celsius degrees."

    if record["HeartRate"] < 45 or record["HeartRate"] > 130:
        return "Heart rate should be between 45 and 130 bpm."

    return None


def predict(record):
    """
    Predicts the risk value
    """
    preds = [round(x) for x in model.predict(pd.DataFrame([record]))]
    return preds[0]


def convert_risk(pred):
    """
    Converts numerical risk into label
    """
    if pred == 0:
        return "high risk", "danger"
    if pred == 1:
        return "low risk", "success"
    # 2
    return "mid risk", "warning"


def save_to_db(record, risk):
    """
    Saves the prediction data to the Mongo database
    """
    rec = record.copy()
    rec["RiskLevel"] = risk
    collection.insert_one(rec)


def send_to_evidently_service(record, risk):
    """
    Sends the prediction data to the Evidently monitoring service
    """
    rec = record.copy()
    rec["RiskLevel"] = risk
    requests.post(f"{EVIDENTLY_SERVICE_URI}/iterate/maternal-health-risk", json=[rec])


def calculate_risk(record):
    """
    Calculates the maternal health risk
    """
    pred = predict(record)
    risk, category = convert_risk(pred)
    if MONITORING_ENABLED:
        save_to_db(record, risk)
        send_to_evidently_service(record, risk)
    return risk, category


app = Flask(EXPERIMENT_NAME)
app.secret_key = os.urandom(24)

model = load_model()


@app.route("/", methods=["GET", "POST"])
def predict_form_endpoint():
    """
    Prediction form endpoint
    """
    if request.method == "POST":
        record = {}
        record["Age"] = int(request.form.get("Age"))
        record["SystolicBP"] = int(request.form.get("SystolicBP"))
        record["DiastolicBP"] = int(request.form.get("DiastolicBP"))
        record["BS"] = float(request.form.get("BS"))
        record["BodyTemp"] = float(request.form.get("BodyTemp"))
        record["HeartRate"] = int(request.form.get("HeartRate"))

        error_message = validate_data(record)
        if error_message:
            flash(error_message, 'info')
        else:
            risk, category = calculate_risk(record)
            flash(risk.capitalize(), category)

    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict_json_endpoint():
    """
    Prediction API endpoint
    """
    record = request.get_json()

    error_message = validate_data(record)
    if error_message:
        return jsonify({"Error": error_message})

    risk, _ = calculate_risk(record)
    return jsonify({"RiskLevel": risk})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8081)
