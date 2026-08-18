"""
Announcement endpoints for the High School Management System API
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from pymongo import ReturnDocument

from ..database import announcements_collection, teachers_collection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)

MAX_TITLE_LENGTH = 120
MAX_MESSAGE_LENGTH = 500


class AnnouncementPayload(BaseModel):
    """Announcement data submitted by a signed in teacher"""

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    start_date: Optional[datetime] = None
    expiration_date: datetime

    @field_validator("title", "message")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty")
        return stripped

    @field_validator("start_date", "expiration_date")
    @classmethod
    def as_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("expiration_date")
    @classmethod
    def expires_after_start(cls, value: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and value <= start_date:
            raise ValueError("Expiration date must be after the start date")
        return value


def _authenticate(teacher_username: Optional[str]) -> Dict[str, Any]:
    """Ensure the request comes from a known teacher account"""
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    return teacher


def _to_object_id(announcement_id: str) -> ObjectId:
    try:
        return ObjectId(announcement_id)
    except (InvalidId, TypeError) as error:
        logger.info("Rejected malformed announcement id: %s", error)
        raise HTTPException(status_code=404, detail="Announcement not found")


def _serialize(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a stored announcement into a JSON friendly dictionary"""

    def iso(value: Optional[datetime]) -> Optional[str]:
        if not value:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    return {
        "id": str(announcement["_id"]),
        "title": announcement["title"],
        "message": announcement["message"],
        "start_date": iso(announcement.get("start_date")),
        "expiration_date": iso(announcement.get("expiration_date")),
        "created_by": announcement.get("created_by"),
        "created_at": iso(announcement.get("created_at")),
        "updated_at": iso(announcement.get("updated_at")),
    }


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get announcements ordered by expiration date.

    - active_only: when true (default) only announcements that have started and
      have not expired are returned. Set to false to list every announcement.
    """
    query: Dict[str, Any] = {}

    if active_only:
        now = datetime.now(timezone.utc)
        query = {
            "expiration_date": {"$gt": now},
            "$or": [
                {"start_date": None},
                {"start_date": {"$lte": now}},
            ],
        }

    announcements = announcements_collection.find(query).sort(
        "expiration_date", 1)
    return [_serialize(announcement) for announcement in announcements]


@router.post("", response_model=Dict[str, Any], status_code=201)
@router.post("/", response_model=Dict[str, Any], status_code=201)
def create_announcement(
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement - requires teacher authentication"""
    teacher = _authenticate(teacher_username)

    now = datetime.now(timezone.utc)
    document = {
        "title": payload.title,
        "message": payload.message,
        "start_date": payload.start_date,
        "expiration_date": payload.expiration_date,
        "created_by": teacher["_id"],
        "created_at": now,
        "updated_at": now,
    }

    result = announcements_collection.insert_one(document)
    created = announcements_collection.find_one({"_id": result.inserted_id})
    if not created:
        logger.error("Announcement %s disappeared right after insert",
                     result.inserted_id)
        raise HTTPException(
            status_code=500, detail="Failed to create announcement")

    return _serialize(created)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement - requires teacher authentication"""
    _authenticate(teacher_username)
    object_id = _to_object_id(announcement_id)

    updated = announcements_collection.find_one_and_update(
        {"_id": object_id},
        {
            "$set": {
                "title": payload.title,
                "message": payload.message,
                "start_date": payload.start_date,
                "expiration_date": payload.expiration_date,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return _serialize(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement - requires teacher authentication"""
    _authenticate(teacher_username)
    object_id = _to_object_id(announcement_id)

    result = announcements_collection.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
