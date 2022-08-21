SHELL:=/bin/bash

prerequisites: ## Perform the initial machine configuration
	@sudo apt update
	@sudo apt install docker.io python3.9 python3-pip -y
	@sudo pip install pipenv
	@sudo wget https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-linux-x86_64 -O /usr/bin/docker-compose
	@sudo chmod +x /usr/bin/docker-compose

setup: ## Setup the development environment
	@cd app; pipenv install --dev; pipenv run pre-commit install; pipenv shell cd ..

unit-tests: ## Run the unit tests
	@pytest app/tests

quality-checks: ## Perform the code quality checks
	isort app
	black app
	pylint --recursive=y app

build: ## Build the MLOps pipeline environment
	@docker-compose build

integration-tests: ## Run the integration tests
	@./app/integration-tests/run.sh

publish: unit-tests quality-checks build integration-tests ## Publish the prediction docker image to DockerHub
	@docker login
	@docker-compose push

pull: ## Pull latest images
	@docker-compose pull

run: ## Run the MLOps pipeline environment
	@docker-compose up -d

generate-traffic: ## Generate simulated traffic
	@docker exec -t web-app python generate_traffic.py

logs: ## Check the MLOps pipeline logs
	@docker-compose logs -f

deployment: ## Deploy the scheduled training workflow
	@docker exec -t prefect python create_prefect_storage.py
	@docker exec -t prefect prefect deployment build ./train.py:main --name "Maternal Health Deployment" --tag maternal-health-risk --cron "0 0 * * *" --storage-block remote-file-system/minio
	@docker exec -t prefect prefect deployment apply main-deployment.yaml
	@docker exec -td prefect prefect agent start --tag maternal-health-risk

train: ## Execute the training workflow
	@docker exec -ti prefect prefect deployment run "main/Maternal Health Deployment"

restart: ## Restart the MLOps pipeline environment
	@docker-compose restart

kill: ## Kill the MLOps pipeline environment
	@docker-compose down

clean-mongo: ## Clean-up Mongo database
	@docker exec -ti web-app python clean_mongo_database.py

clean: ## Clean all persisted data
	@docker-compose down -v

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
