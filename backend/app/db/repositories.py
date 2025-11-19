from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.collection import Collection

from app.db.client import get_db
from app.db.models import EventDocument, MarketDocument, RunDocument, TraceDocument
from app.db.utils import serialize_document

_INDEXES_CREATED = False


def events_collection() -> Collection:
    return get_db()["events"]


def markets_collection() -> Collection:
    return get_db()["markets"]


def runs_collection() -> Collection:
    return get_db()["runs"]


def traces_collection() -> Collection:
    return get_db()["traces"]


def ensure_indexes() -> None:
    global _INDEXES_CREATED
    if _INDEXES_CREATED:
        return
    events_collection().create_index("slug", unique=True)
    markets_collection().create_index("slug", unique=True)
    markets_collection().create_index("polymarket_url", unique=True)
    markets_collection().create_index("event_id")
    runs_collection().create_index([("market_id", 1), ("run_at", -1)])
    runs_collection().create_index([("event_id", 1), ("run_at", -1)])
    runs_collection().create_index("slug")
    traces_collection().create_index("run_id")
    _INDEXES_CREATED = True


def upsert_event(doc: EventDocument) -> EventDocument:
    ensure_indexes()
    slug = doc.get("slug")
    if not slug:
        raise ValueError("Event slug is required to upsert.")

    insert_doc = {k: v for k, v in doc.items() if k != "updated_at"}
    updated_at = doc.get("updated_at")
    update_doc = {"updated_at": updated_at} if updated_at else {}

    result = events_collection().find_one_and_update(
        {"slug": slug},
        {"$setOnInsert": insert_doc, "$set": update_doc},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result  # type: ignore[return-value]


def upsert_market(doc: MarketDocument) -> MarketDocument:
    ensure_indexes()
    slug = doc.get("slug")
    if not slug:
        raise ValueError("Market slug is required to upsert.")

    insert_doc = {k: v for k, v in doc.items() if k != "updated_at"}
    updated_at = doc.get("updated_at")
    update_doc = {"updated_at": updated_at} if updated_at else {}

    result = markets_collection().find_one_and_update(
        {"slug": slug},
        {"$setOnInsert": insert_doc, "$set": update_doc},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result  # type: ignore[return-value]


def create_run(doc: RunDocument) -> ObjectId:
    ensure_indexes()
    result = runs_collection().insert_one(doc)
    return result.inserted_id


def create_trace(doc: TraceDocument) -> ObjectId:
    ensure_indexes()
    result = traces_collection().insert_one(doc)
    return result.inserted_id


def attach_trace_to_run(run_id: ObjectId, trace_id: ObjectId) -> None:
    runs_collection().update_one({"_id": run_id}, {"$set": {"trace_id": trace_id}})


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    ensure_indexes()
    try:
        object_id = ObjectId(run_id)
    except (InvalidId, TypeError):
        return None
    doc = runs_collection().find_one({"_id": object_id})
    return serialize_document(doc)


def list_runs_by_market(market_id: str) -> List[Dict[str, Any]]:
    ensure_indexes()
    try:
        market_object_id = ObjectId(market_id)
    except (InvalidId, TypeError) as err:
        raise ValueError("market_id must be a valid ObjectId string.") from err

    cursor = runs_collection().find({"market_id": market_object_id}).sort("run_at", -1)
    return [serialize_document(doc) for doc in cursor]
