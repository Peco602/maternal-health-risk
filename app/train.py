"""Training module"""

import os
import time
import shutil

import mlflow
import pandas as pd
import xgboost as xgb
from prefect import flow, task
from hyperopt import STATUS_OK, Trials, hp, tpe, fmin
from sklearn.svm import SVC
from hyperopt.pyll import scope
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from prefect.task_runners import SequentialTaskRunner
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")
if KAGGLE_USERNAME and KAGGLE_KEY:
    DOWNLOAD_DATA = True
    from kaggle.api.kaggle_api_extended import KaggleApi
else:
    DOWNLOAD_DATA = False

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "maternal-health-risk")
MIN_AGE = int(os.getenv("MIN_AGE", "13"))
MAX_AGE = int(os.getenv("MAX_AGE", "50"))
MODEL_SEARCH_ITERATIONS = int(os.getenv("MODEL_SEARCH_ITERATIONS", "32"))


@task
def download_data():
    """
    Downloads training data from Kaggle
    """
    api = KaggleApi()
    api.authenticate()
    dataset = 'pyuxbhatt/maternal-health-risk'
    download_path = '/app/data'
    api.dataset_download_file(
        dataset, 'Maternal Health Risk Data Set.csv', download_path, force=True
    )

    datetime = time.strftime("%Y%m%d-%H%M%S")
    # Rename data with current datetime
    os.rename(
        f"{download_path}/Maternal%20Health%20Risk%20Data%20Set.csv",
        f"{download_path}/data-{datetime}.csv",
    )
    # Set working data
    shutil.copy(
        f"{download_path}/data-{datetime}.csv",
        f"{download_path}/data.csv",
    )


@task
def read_data(filename):
    """
    Reads data from the CSV file
    """
    df = pd.read_csv(filename)
    return df


@task
def prepare_data(df):
    """
    Prepares data for model creation and testing
    """
    # Age range limitation
    df = df[(df.Age >= MIN_AGE) & (df.Age <= MAX_AGE)]

    # Body temperature conversion from F to C
    df.BodyTemp = df.BodyTemp.apply(lambda temp: (temp - 32) * 5 / 9)

    # Sort by risk
    df.sort_values(by="RiskLevel", ascending=True, inplace=True)

    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    # Target variable encoding
    le = LabelEncoder()
    y = le.fit_transform(y)
    integer_mapping = {l: i for i, l in enumerate(le.classes_)}
    print(integer_mapping)

    return X, y


@task
def split_data(X, y):
    """
    Splits data in training and test datasets
    """
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=1
    )

    return X_train, X_val, y_train, y_val


@task
def train_model_xgboost_search(X_train, X_val, y_train, y_val):
    """
    Searches for the best XGBoost prediction model
    """
    train = xgb.DMatrix(X_train, label=y_train)
    valid = xgb.DMatrix(X_val, label=y_val)

    mlflow.xgboost.autolog()

    def objective(params):
        with mlflow.start_run():
            booster = xgb.train(
                params=params,
                dtrain=train,
                num_boost_round=100,
                evals=[(valid, "validation")],
                early_stopping_rounds=50,
            )
            y_pred = [round(x) for x in booster.predict(valid)]
            accuracy = accuracy_score(y_val, y_pred)
            mlflow.log_metric("accuracy", accuracy)

        return {"loss": (-1) * accuracy, "status": STATUS_OK}

    search_space = {
        "max_depth": scope.int(hp.uniform("max_depth", 1, 20)),
        "learning_rate": hp.uniform("learning_rate", 0.01, 0.2),
        "reg_alpha": hp.loguniform("reg_alpha", -5, -1),
        "reg_lambda": hp.loguniform("reg_lambda", -6, -1),
        "min_child_weight": hp.loguniform("min_child_weight", -1, 3),
        "objective": "reg:squarederror",
        "seed": 42,
    }

    fmin(
        fn=objective,
        space=search_space,
        algo=tpe.suggest,
        max_evals=MODEL_SEARCH_ITERATIONS,
        trials=Trials(),
    )


@task
def train_model_sklearn_search(X_train, X_val, y_train, y_val):
    """
    Searches for the best scikit-learn prediction model
    """
    mlflow.sklearn.autolog()

    def objective(params):
        with mlflow.start_run():
            classifier_type = params["type"]
            del params["type"]
            if classifier_type == "svm":
                clf = make_pipeline(StandardScaler(), SVC(**params))
            elif classifier_type == "rf":
                clf = make_pipeline(StandardScaler(), RandomForestClassifier(**params))

            clf.fit(X_train, y_train)
            accuracy = clf.score(X_val, y_val)
            mlflow.log_metric("accuracy", accuracy)

            return {"loss": -accuracy, "status": STATUS_OK}

    search_space = hp.choice(
        "classifier_type",
        [
            {
                "type": "svm",
                "C": hp.uniform("SVM_C", 0.5, 15),
                "gamma": hp.uniform("SVM_gamma", 0.05, 15),
                "kernel": hp.choice("kernel", ["linear", "rbf"]),
            },
            {
                "type": "rf",
                "max_depth": scope.int(hp.uniform("max_depth", 2, 5)),
                "criterion": hp.choice("criterion", ["gini", "entropy"]),
            },
        ],
    )

    fmin(
        fn=objective,
        space=search_space,
        algo=tpe.suggest,
        max_evals=MODEL_SEARCH_ITERATIONS,
        trials=Trials(),
    )


@task
def register_best_model():
    """
    Registers the highest accuracy model
    """
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    best_run = client.search_runs(
        experiment_ids=experiment.experiment_id,
        run_view_type=ViewType.ACTIVE_ONLY,
        max_results=1,
        order_by=["metrics.accuracy DESC"],
    )[0]
    # register the best model
    run_id = best_run.info.run_id
    model_uri = f"runs:/{run_id}/model"
    model_accuracy = round(best_run.data.metrics['accuracy'] * 100)
    model_details = mlflow.register_model(model_uri=model_uri, name=EXPERIMENT_NAME)
    client.update_registered_model(
        name=model_details.name, description=f"Current accuracy: {model_accuracy}%"
    )


@flow(task_runner=SequentialTaskRunner())
def main():
    """
    Executes the training workflow
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    if DOWNLOAD_DATA:
        download_data()
    data = read_data("data/data.csv")
    X, y = prepare_data(data)
    X_train, X_val, y_train, y_val = split_data(X, y)
    train_model_xgboost_search(X_train, X_val, y_train, y_val)
    train_model_sklearn_search(X_train, X_val, y_train, y_val)
    register_best_model()


if __name__ == "__main__":
    main()
