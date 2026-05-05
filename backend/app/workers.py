from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .models import JobStatus, PolygonFeature
from .segmentation_runner import runner
from .store import store


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StubQueue:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def enqueue_segmentation(self, job_id: str) -> None:
        task = asyncio.create_task(self._run_segmentation(job_id))
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))

    async def _run_segmentation(self, job_id: str) -> None:
        job = store.jobs[job_id]
        course = store.courses[job.course_id]

        for status in [
            JobStatus.IMAGE_ACQUISITION,
            JobStatus.TILING,
            JobStatus.INFERENCE,
            JobStatus.STITCHING,
            JobStatus.POST_PROCESSING,
            JobStatus.POLYGONIZATION,
            JobStatus.SEGMENTATION_COMPLETE,
        ]:
            await asyncio.sleep(0.1)
            job.status = status
            job.updated_at = utcnow()
            store.jobs[job_id] = job

        try:
            external_polygons = runner.run(boundary=course.boundary, course_id=course.id)
            if external_polygons:
                store.predicted_polygons[course.id] = [PolygonFeature(**poly) for poly in external_polygons]
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_code = "SEGMENTATION_RUNNER_ERROR"
            job.error_message = str(exc)
            job.updated_at = utcnow()
            store.jobs[job_id] = job

    def enqueue_validation_finalize(self, job_id: str) -> None:
        task = asyncio.create_task(self._run_validation_finalize(job_id))
        self._tasks.add(task)
        task.add_done_callback(lambda t: self._tasks.discard(t))

    async def _run_validation_finalize(self, job_id: str) -> None:
        job = store.jobs[job_id]
        await asyncio.sleep(0.05)
        job.status = JobStatus.VALIDATION_COMPLETE
        job.updated_at = utcnow()
        store.jobs[job_id] = job


queue = StubQueue()
