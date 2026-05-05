from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from .models import (
    Course,
    CourseCreateRequest,
    Job,
    JobStatus,
    PolygonFeature,
    ValidatedPolygonBulkUpdate,
)
from .store import store
from .workers import queue
from .segmentation_runner import runner

app = FastAPI(title="PhytoMaps MVP API", version="0.1.0")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@app.post("/courses", response_model=Course, status_code=201)
def create_course(payload: CourseCreateRequest) -> Course:
    course = Course(id=f"course_{uuid4().hex[:8]}", name=payload.name, boundary=payload.boundary, created_at=utcnow())
    store.courses[course.id] = course
    return course


@app.post("/courses/{course_id}/jobs/segmentation", response_model=Job, status_code=202)
def trigger_segmentation_job(course_id: str) -> Job:
    if course_id not in store.courses:
        raise HTTPException(status_code=404, detail="course not found")

    now = utcnow()
    job = Job(
        id=f"job_{uuid4().hex[:10]}",
        course_id=course_id,
        type="segmentation",
        status=JobStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )
    store.jobs[job.id] = job
    queue.enqueue_segmentation(job.id)
    return job


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    if job_id not in store.jobs:
        raise HTTPException(status_code=404, detail="job not found")
    return store.jobs[job_id]


@app.get("/courses/{course_id}/polygons")
def get_polygons(course_id: str, source: str = Query(pattern="^(predicted|validated)$")) -> dict[str, list[PolygonFeature]]:
    if course_id not in store.courses:
        raise HTTPException(status_code=404, detail="course not found")
    if source == "predicted":
        return {"polygons": store.predicted_polygons[course_id]}
    return {"polygons": store.validated_polygons[course_id]}


@app.put("/courses/{course_id}/polygons/validated", status_code=200)
def upsert_validated_polygons(course_id: str, payload: ValidatedPolygonBulkUpdate) -> dict[str, int]:
    if course_id not in store.courses:
        raise HTTPException(status_code=404, detail="course not found")
    store.validated_polygons[course_id] = payload.polygons
    return {"updated": len(payload.polygons)}


@app.post("/courses/{course_id}/validation/finalize", response_model=Job, status_code=202)
def finalize_validation(course_id: str) -> Job:
    if course_id not in store.courses:
        raise HTTPException(status_code=404, detail="course not found")

    polygons = store.validated_polygons[course_id]
    if not polygons:
        raise HTTPException(status_code=400, detail="no validated polygons found")

    for poly in polygons:
        if poly.zone_type is None:
            raise HTTPException(status_code=400, detail=f"zone_type required for polygon {poly.id}")
        if poly.zone_type.value in {"fairway", "green", "tee"} and poly.hole_id is None:
            raise HTTPException(status_code=400, detail=f"hole_id required for playable zone on polygon {poly.id}")

    now = utcnow()
    job = Job(
        id=f"job_{uuid4().hex[:10]}",
        course_id=course_id,
        type="validation_finalize",
        status=JobStatus.VALIDATION_IN_PROGRESS,
        created_at=now,
        updated_at=now,
    )
    store.jobs[job.id] = job
    queue.enqueue_validation_finalize(job.id)
    return job


@app.get("/integration/segmentation-runner")
def segmentation_runner_config() -> dict[str, str | None]:
    return runner.config()
