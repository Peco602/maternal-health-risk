#!/usr/bin/env bash

cd "$(dirname "$0")"

function print_info {
    RESET="\e[0m"
    BOLD="\e[1m"
    YELLOW="\e[33m"
    echo -e "$YELLOW$BOLD [+] $1 $RESET"
}

export AWS_REGION=eu-west-1
export AWS_DEFAULT_REGION=eu-west-1
export AWS_ACCESS_KEY_ID=admin
export AWS_SECRET_ACCESS_KEY=adminadmin
export POSTGRES_DB=mlflowdb
export POSTGRES_USER=mlflow
export POSTGRES_PASSWORD=password
export EXPERIMENT_NAME=test-maternal-health-risk
export MIN_AGE=13
export MAX_AGE=50

print_info "Creating MLOps test pipeline"
docker-compose up -d

print_info "Waiting for test pipeline to be ready"
sleep 10

print_info "Executing test training workflow"
docker exec -t test-prefect python train.py

ERROR_CODE=$?

if [ ${ERROR_CODE} != 0 ]; then
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

sleep 10

print_info "Model re-loading"
docker restart test-web-app

sleep 5

print_info "Prediction tests"
python test_predict.py

ERROR_CODE=$?

if [ ${ERROR_CODE} != 0 ]; then
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

print_info "Clean-up"
docker-compose down
