from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .models import Course, Job, PolygonFeature


@dataclass
class InMemoryStore:
    courses: dict[str, Course] = field(default_factory=dict)
    jobs: dict[str, Job] = field(default_factory=dict)
    predicted_polygons: dict[str, list[PolygonFeature]] = field(default_factory=lambda: defaultdict(list))
    validated_polygons: dict[str, list[PolygonFeature]] = field(default_factory=lambda: defaultdict(list))


store = InMemoryStore()
