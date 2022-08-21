"""Prediction database cleaning module"""

import os

from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DATABASE = "prediction_service"

if __name__ == "__main__":
    client = MongoClient(MONGODB_URI)
    client.drop_database(MONGO_DATABASE)
