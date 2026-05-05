from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    QUEUED = "queued"
    IMAGE_ACQUISITION = "image_acquisition"
    TILING = "tiling"
    INFERENCE = "inference"
    STITCHING = "stitching"
    POST_PROCESSING = "post_processing"
    POLYGONIZATION = "polygonization"
    SEGMENTATION_COMPLETE = "segmentation_complete"
    VALIDATION_IN_PROGRESS = "validation_in_progress"
    VALIDATION_COMPLETE = "validation_complete"
    FAILED = "failed"


class ZoneType(str, Enum):
    FAIRWAY = "fairway"
    GREEN = "green"
    TEE = "tee"
    ROUGH = "rough"
    BUNKER = "bunker"
    WATER = "water"
    OTHER = "other"


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    boundary: dict[str, Any]


class Course(BaseModel):
    id: str
    name: str
    boundary: dict[str, Any]
    created_at: datetime


class Job(BaseModel):
    id: str
    course_id: str
    type: str
    status: JobStatus
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PolygonFeature(BaseModel):
    id: str
    geometry: dict[str, Any]
    class_type: str | None = None
    zone_type: ZoneType | None = None
    hole_id: int | None = None

    @field_validator("hole_id")
    @classmethod
    def validate_hole_id(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 18:
            raise ValueError("hole_id must be in range [1, 18]")
        return value


class ValidatedPolygonBulkUpdate(BaseModel):
    polygons: list[PolygonFeature]
