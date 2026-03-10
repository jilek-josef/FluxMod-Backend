import os
from typing import Any
from urllib.parse import parse_qs, urlparse

import certifi
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from api2.debug import debug_kv, get_logger


logger = get_logger("services.data_store")

MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME") or os.getenv("DB_NAME")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME") or os.getenv(
    "COLLECTION_NAME"
)
MONGODB_DOCUMENT_ID = os.getenv("MONGODB_DOCUMENT_ID", "singleton")

_mongo_client: MongoClient | None = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _uri_uses_tls(uri: str) -> bool:
    if uri.startswith("mongodb+srv://"):
        return True

    parsed = urlparse(uri)
    params = parse_qs(parsed.query)
    tls_values = params.get("tls", []) + params.get("ssl", [])
    return any(value.strip().lower() == "true" for value in tls_values)


def default_data() -> dict[str, Any]:
    """Return the baseline data shape stored in MongoDB."""
    return {"guilds": {}, "rules": []}


def _get_collection() -> Collection:
    global _mongo_client
    uri = MONGODB_URI
    db_name = MONGODB_DB_NAME
    collection_name = MONGODB_COLLECTION_NAME

    if not uri:
        raise RuntimeError("MONGODB_URI or MONGO_URI must be set")

    if not db_name:
        raise RuntimeError("MONGODB_DB_NAME or DB_NAME must be set")

    if not collection_name:
        raise RuntimeError("MONGODB_COLLECTION_NAME or COLLECTION_NAME must be set")

    if _mongo_client is None:
        uri_requests_tls = _uri_uses_tls(uri)
        mongo_client_options: dict[str, Any] = {
            "serverSelectionTimeoutMS": int(
                os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")
            ),
            "connectTimeoutMS": int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000")),
            "socketTimeoutMS": int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "20000")),
        }

        if uri_requests_tls:
            mongo_client_options["tls"] = True
            mongo_client_options["tlsCAFile"] = os.getenv(
                "MONGODB_TLS_CA_FILE", certifi.where()
            )

        if _env_bool("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", False):
            mongo_client_options["tlsAllowInvalidCertificates"] = True

        if _env_bool("MONGODB_TLS_ALLOW_INVALID_HOSTNAMES", False):
            mongo_client_options["tlsAllowInvalidHostnames"] = True

        _mongo_client = MongoClient(uri, **mongo_client_options)
        _mongo_client.admin.command("ping")
        logger.info("Connected to MongoDB database '%s'", db_name)
    return _mongo_client[db_name][collection_name]


def ensure_data_file() -> None:
    """Ensure the MongoDB singleton document exists."""
    try:
        collection = _get_collection()
        existing = collection.find_one({"_id": MONGODB_DOCUMENT_ID})
        if existing is not None:
            return

        collection.insert_one({"_id": MONGODB_DOCUMENT_ID, **default_data()})
        logger.info(
            "Created MongoDB data document '%s' in %s.%s",
            MONGODB_DOCUMENT_ID,
            MONGODB_DB_NAME,
            MONGODB_COLLECTION_NAME,
        )
    except PyMongoError as exc:
        logger.exception("MongoDB initialization failed during startup: %s", exc)


def load_data() -> dict[str, Any]:
    """Load persisted backend data from MongoDB."""
    try:
        collection = _get_collection()
        loaded = collection.find_one({"_id": MONGODB_DOCUMENT_ID}, {"_id": 0})
    except PyMongoError as exc:
        logger.exception("MongoDB load failed: %s", exc)
        return default_data()

    if not isinstance(loaded, dict):
        debug_kv(logger, "MongoDB data document missing; returning defaults")
        return default_data()

    debug_kv(
        logger,
        "MongoDB data loaded",
        guild_count=len(loaded.get("guilds", {})) if isinstance(loaded, dict) else None,
        rule_count=len(loaded.get("rules", [])) if isinstance(loaded, dict) else None,
    )
    return loaded


def save_data(data: dict[str, Any]) -> None:
    """Persist backend data into MongoDB."""
    try:
        collection = _get_collection()
        collection.replace_one(
            {"_id": MONGODB_DOCUMENT_ID},
            {"_id": MONGODB_DOCUMENT_ID, **data},
            upsert=True,
        )
    except PyMongoError as exc:
        logger.exception("MongoDB save failed: %s", exc)
        return

    debug_kv(
        logger,
        "MongoDB data saved",
        guild_count=len(data.get("guilds", {})),
        rule_count=len(data.get("rules", [])),
    )
