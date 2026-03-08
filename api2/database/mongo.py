import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

load_dotenv()

_client: Optional[MongoClient] = None


def build_uri() -> str:
    uri = os.getenv("MONGO_URI")
    if uri:
        return uri


def get_client() -> MongoClient:
    global _client

    if _client is None:
        _client = MongoClient(build_uri())

    return _client


def close_connection():
    global _client

    if _client:
        _client.close()
        _client = None


class MongoDB:
    def __init__(self, db_name: Optional[str] = None):
        name = db_name or os.getenv("DB_NAME")
        self.collection_name = os.getenv("COLLECTION_NAME")

        if not name:
            raise ValueError("DB_NAME must be set")

        if not self.collection_name:
            raise ValueError("COLLECTION_NAME must be set")

        self.db_name = name

        self.client = get_client()
        self.db: Database = self.client[name]
        self.default_collection: Collection = self.db[self.collection_name]

        # Fail fast on startup if auth/network/collection path is invalid.
        self.client.admin.command("ping")
        self.default_collection.estimated_document_count()

    def collection(self, name: str) -> Collection:
        # set collection name for later use
        self.collection_name = name
        return self.db[name]

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False
