"""Prefect storage creation module"""

import os

from prefect.filesystems import RemoteFileSystem

EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "maternal-health-risk")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MLFLOW_S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:9000")

minio_block = RemoteFileSystem(
    basepath=f"s3://{EXPERIMENT_NAME}/prefect",
    settings={
        "key": AWS_ACCESS_KEY_ID,
        "secret": AWS_SECRET_ACCESS_KEY,
        "client_kwargs": {"endpoint_url": MLFLOW_S3_ENDPOINT_URL},
    },
)
minio_block.save("minio", overwrite=True)
