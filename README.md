# Maternal Health Risk Predictor


## Context

According to the World Health Organization (WHO):

"*Maternal health refers to the health of women during pregnancy, childbirth and the postnatal period. Each stage should be a positive experience, ensuring women and their babies reach their full potential for health and well-being. Although important progress has been made in the last two decades, about 295 000 women died during and following pregnancy and childbirth in 2017. This number is unacceptably high. The most common direct causes of maternal injury and death are excessive blood loss, infection, high blood pressure, unsafe abortion, and obstructed labour, as well as indirect causes such as anemia, malaria, and heart disease. Most maternal deaths are preventable with timely management by a skilled health professional working in a supportive environment. Ending preventable maternal death must remain at the top of the global agenda. At the same time, simply surviving pregnancy and childbirth can never be the marker of successful maternal health care. It is critical to expand efforts reducing maternal injury and disability to promote health and well-being. Every pregnancy and birth is unique. Addressing inequalities that affect health outcomes, especially sexual and reproductive health and rights and gender, is fundamental to ensuring all women have access to respectful and high-quality maternity care.*"

The prediction service is currently accessible [here](http://maternal.peco602.com)


## Dataset

Data has been collected from different hospitals, community clinics, maternal health cares through the IoT based risk monitoring system.

| Feature | Description |
| --- | --- |
| Age | Age in years when a woman is pregnant. |
| SystolicBP | Upper value of Blood Pressure in mmHg, another significant attribute during pregnancy. |
| DiastolicBP | Lower value of Blood Pressure in mmHg, another significant attribute during pregnancy. |
| BS | Blood glucose levels is in terms of a molar concentration, mmol/L. |
| HeartRate | A normal resting heart rate in beats per minute. |
| BodyTemp | Average human body temperature. |
| Risk Level | Predicted Risk Intensity Level during pregnancy considering the previous attribute. |

https://www.kaggle.com/datasets/pyuxbhatt/maternal-health-risk


## MLOps pipeline deployment


## GitHub Actions

- **Continuous Integration**: On every push and pull request on `main` and `dev` branches, Docker images are built, tested and then pushed to DockerHub.
- **Continuous Deployment**: On every push and pull request on `main` branch, only if the Continuous Integration workflow is successful, the updated prediction service is deployed to the target server.


## Applied technologies

| Name | Scope |
| --- | --- |
| Jupyter Notebooks | Exploratory data analysis and pipeline prototyping. |
| Docker | Application containerization. |
| Docker-Compose | Multi-container Docker applications definition and running. |
| Prefect | Workflow orchestration. |
| MLFlow | Experiment tracking and model registry. |
| PostgreSQL | MLFLow experiment tracking database. |
| MinIO | High Performance Object Storage compatible with Amazon S3 cloud storage service. |
| MongoDB | Prediction database. |
| EvidentlyAI | ML models evaluation and monitoring. |
| Prometheus | Time Series Database for ML models real-time monitoring. |
| Grafana | ML models real-time monitoring dashboards. |
| pytest | Python unit testing suite. |
| pylint | Python static code analysis. |
| black | Python code formatting. |
| isort | Python import sorting. |
| Pre-Commit Hooks | Simple code issue identification before submission. |
| GitHub Actions | CI/CD pipelines. |


## Disclaimer

This predictor has been developed as the final project of the MLOps Zoomcamp course from DataTalksClub. It does not provide medical advice and it is intended for informational purposes only. It is not a substitute for professional medical advice, diagnosis or treatment. Never ignore professional medical advice in seeking treatment because of something you have read here.
