#!/usr/bin/env python3

"""
This is a demo service for Evidently metrics integration with Prometheus and Grafana.

Read `README.md` for proper setup and installation.

The service gets a reference dataset from data.csv file and process current data with HTTP API.

Metrics calculation results are available with `GET /metrics` HTTP method in Prometheus compatible format.
"""
import os
import logging
import datetime
import dataclasses
from typing import Dict, List, Optional

import yaml
import flask
import pandas as pd
import prometheus_client
from flask import Flask
from pymongo import MongoClient
from evidently.dashboard import Dashboard
from evidently.dashboard.tabs import DataDriftTab, CatTargetDriftTab
from evidently.model_monitoring import (
    ModelMonitoring,
    DataDriftMonitor,
    DataQualityMonitor,
    CatTargetDriftMonitor,
    NumTargetDriftMonitor,
    RegressionPerformanceMonitor,
    ClassificationPerformanceMonitor,
    ProbClassificationPerformanceMonitor,
)
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from evidently.pipeline.column_mapping import ColumnMapping

MIN_AGE = int(os.getenv("MIN_AGE", 13))
MAX_AGE = int(os.getenv("MAX_AGE", 50))
WINDOW_SIZE = 50
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "maternal-health-risk")

mongo_client = MongoClient(MONGODB_URI)

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(
    app.wsgi_app, {"/metrics": prometheus_client.make_wsgi_app()}
)


def load_reference_data(reference_file):
    reference_data = pd.read_csv(reference_file)
    reference_data = reference_data[
        (reference_data.Age >= MIN_AGE) & (reference_data.Age <= MAX_AGE)
    ]
    reference_data.BodyTemp = reference_data.BodyTemp.apply(
        lambda temp: (temp - 32) * 5 / 9
    )
    return reference_data


@dataclasses.dataclass
class MonitoringServiceOptions:
    datasets_path: str
    min_reference_size: int
    use_reference: bool
    moving_reference: bool
    window_size: int
    calculation_period_sec: int


@dataclasses.dataclass
class LoadedDataset:
    name: str
    references: pd.DataFrame
    monitors: List[str]
    column_mapping: ColumnMapping


EVIDENTLY_MONITORS_MAPPING = {
    "cat_target_drift": CatTargetDriftMonitor,
    "data_drift": DataDriftMonitor,
    "data_quality": DataQualityMonitor,
    "num_target_drift": NumTargetDriftMonitor,
    "regression_performance": RegressionPerformanceMonitor,
    "classification_performance": ClassificationPerformanceMonitor,
    "prob_classification_performance": ProbClassificationPerformanceMonitor,
}


class MonitoringService:
    # names of monitoring datasets
    datasets: List[str]
    metric: Dict[str, prometheus_client.Gauge]
    last_run: Optional[datetime.datetime]
    # collection of reference data
    reference: Dict[str, pd.DataFrame]
    # collection of current data
    current: Dict[str, Optional[pd.DataFrame]]
    # collection of monitoring objects
    monitoring: Dict[str, ModelMonitoring]
    calculation_period_sec: float = 15
    window_size: int

    def __init__(self, datasets: Dict[str, LoadedDataset], window_size: int):
        self.reference = {}
        self.monitoring = {}
        self.current = {}
        self.column_mapping = {}
        self.window_size = window_size

        for dataset_info in datasets.values():
            self.reference[dataset_info.name] = dataset_info.references
            self.monitoring[dataset_info.name] = ModelMonitoring(
                monitors=[
                    EVIDENTLY_MONITORS_MAPPING[k]() for k in dataset_info.monitors
                ],
                options=[],
            )
            self.column_mapping[dataset_info.name] = dataset_info.column_mapping

        self.metrics = {}
        self.next_run_time = {}

    def iterate(self, dataset_name: str, new_rows: pd.DataFrame):
        """Add data to current dataset for specified dataset"""
        window_size = self.window_size

        if dataset_name in self.current:
            current_data = self.current[dataset_name].append(
                new_rows, ignore_index=True
            )

        else:
            current_data = new_rows

        current_size = current_data.shape[0]

        if current_size > self.window_size:
            # cut current_size by window size value
            current_data.drop(
                index=list(range(0, current_size - self.window_size)), inplace=True
            )
            current_data.reset_index(drop=True, inplace=True)

        self.current[dataset_name] = current_data

        if current_size < window_size:
            logging.info(
                f"Not enough data for measurement: {current_size} of {window_size}."
                f" Waiting more data"
            )
            return

        next_run_time = self.next_run_time.get(dataset_name)

        if next_run_time is not None and next_run_time > datetime.datetime.now():
            logging.info("Next run for dataset %s at %s", dataset_name, next_run_time)
            return

        self.next_run_time[dataset_name] = datetime.datetime.now() + datetime.timedelta(
            seconds=self.calculation_period_sec
        )
        self.monitoring[dataset_name].execute(
            self.reference[dataset_name],
            current_data,
            self.column_mapping[dataset_name],
        )

        for metric, value, labels in self.monitoring[dataset_name].metrics():
            metric_key = f"evidently:{metric.name}"
            found = self.metrics.get(metric_key)

            if not labels:
                labels = {}

            labels["dataset_name"] = dataset_name

            if isinstance(value, str):
                continue

            if found is None:
                found = prometheus_client.Gauge(
                    metric_key, "", list(sorted(labels.keys()))
                )
                self.metrics[metric_key] = found

            try:
                found.labels(**labels).set(value)

            except ValueError as error:
                # ignore errors sending other metrics
                logging.error("Value error for metric %s, error: ", metric_key, error)


SERVICE: Optional[MonitoringService] = None


@app.before_first_request
def configure_service():
    # pylint: disable=global-statement
    global SERVICE
    config_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.yaml"
    )

    # try to find a config file, it should be generated via the data preparation script
    if not os.path.exists(config_file_path):
        logging.error("File %s does not exist", config_file_path)
        exit(
            "Cannot find a config file for the metrics service. Try to check README.md for setup instructions."
        )

    with open(config_file_path, "rb") as config_file:
        config = yaml.safe_load(config_file)

    options = MonitoringServiceOptions(**config["service"])
    datasets = {}

    for dataset_name, dataset_options in config["datasets"].items():
        reference_file = dataset_options['reference_file']
        logging.info(
            f"Load reference data for dataset {dataset_name} from {reference_file}"
        )

        reference_data = load_reference_data(reference_file)

        datasets[dataset_name] = LoadedDataset(
            name=dataset_name,
            references=reference_data,
            monitors=dataset_options['monitors'],
            column_mapping=ColumnMapping(**dataset_options["column_mapping"]),
        )
        logging.info(
            "Reference is loaded for dataset %s: %s rows",
            dataset_name,
            len(reference_data),
        )

    SERVICE = MonitoringService(datasets=datasets, window_size=options.window_size)


@app.route("/iterate/<dataset>", methods=["POST"])
def iterate(dataset: str):
    item = flask.request.json

    global SERVICE
    if SERVICE is None:
        return "Internal Server Error: service not found", 500

    SERVICE.iterate(dataset_name=dataset, new_rows=pd.DataFrame.from_dict(item))
    return "ok"


#############################################################################


def get_data_from_db():
    """fetch data from db"""
    data = (
        mongo_client.get_database("prediction_service")
        .get_collection(EXPERIMENT_NAME)
        .find()
    )
    return pd.DataFrame(list(data))


def create_dashboard():
    """create dashboard"""

    collected_data = get_data_from_db()
    if len(collected_data) < WINDOW_SIZE:
        return "Not enough data to create report, please refresh after some time!"

    reference_data = load_reference_data('./datasets/data.csv')

    numerical_features = [
        'Age',
        'SystolicBP',
        'DiastolicBP',
        'BS',
        'BodyTemp',
        'HeartRate',
    ]
    target = "RiskLevel"
    column_mapping = ColumnMapping()
    column_mapping.numerical_features = numerical_features
    column_mapping.target = target

    data_drift_dashboard = Dashboard(
        tabs=[DataDriftTab(verbose_level=1), CatTargetDriftTab(verbose_level=1)]
    )

    data_drift_dashboard.calculate(
        reference_data, collected_data, column_mapping=column_mapping
    )

    data_drift_dashboard.save("data_drift_dashboard.html")
    with open("./data_drift_dashboard.html", "r", encoding="utf-8") as file:
        dashboard = file.read()

    return dashboard


@app.get("/dashboard")
def data_drift():
    """api to get dashboard"""
    return create_dashboard()


if __name__ == "__main__":
    app.run(debug=True)
