from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

CANDIDATE_ENTRYPOINTS = [
    "run_segmentation.py",
    "inference.py",
    "predict.py",
    "main.py",
]


class SegmentationRunner:
    """Adapter for invoking an external segmentation model repository.

    Priority order:
    1) SEGMENTATION_MODEL_ROOT + SEGMENTATION_ENTRYPOINT
    2) SEGMENTATION_MODEL_ROOT + auto-detected entrypoint
    3) backend/model_bundle + auto-detected entrypoint

    Entrypoint must accept:
      --course-id <id> --boundary '<geojson json>'

    and print JSON:
      {"polygons": [{"id": "...", "geometry": {...}, "class_type": "fairway"}]}
    """

    def __init__(self) -> None:
        self.explicit_root = os.getenv("SEGMENTATION_MODEL_ROOT")
        self.explicit_entrypoint = os.getenv("SEGMENTATION_ENTRYPOINT")
        self.model_weights_path = os.getenv("SEGMENTATION_MODEL_WEIGHTS_PATH")

    def _default_bundle_root(self) -> Path:
        return Path(__file__).resolve().parents[1] / "model_bundle"

    def _resolve_root(self) -> Path | None:
        if self.explicit_root:
            root = Path(self.explicit_root)
            if root.exists():
                return root
        default_root = self._default_bundle_root()
        if default_root.exists():
            return default_root
        return None

    def _resolve_entrypoint(self, root: Path) -> Path | None:
        if self.explicit_entrypoint:
            explicit = root / self.explicit_entrypoint
            if explicit.exists():
                return explicit

        for rel in CANDIDATE_ENTRYPOINTS:
            p = root / rel
            if p.exists():
                return p
        return None

    def config(self) -> dict[str, str | None]:
        root = self._resolve_root()
        if not root:
            return {"configured": "false", "root": None, "entrypoint": None}
        entry = self._resolve_entrypoint(root)
        return {
            "configured": "true" if entry else "false",
            "root": str(root),
            "entrypoint": str(entry) if entry else None,
            "weights": self.model_weights_path,
        }

    def run(self, boundary: dict[str, Any], course_id: str) -> list[dict[str, Any]]:
        root = self._resolve_root()
        if not root:
            return []

        entrypoint = self._resolve_entrypoint(root)
        if not entrypoint:
            raise RuntimeError(
                "No entrypoint found. Set SEGMENTATION_ENTRYPOINT or add one of: "
                + ", ".join(CANDIDATE_ENTRYPOINTS)
            )

        cmd = ["python", str(entrypoint), "--course-id", course_id, "--boundary", json.dumps(boundary)]
        if self.model_weights_path:
            cmd.extend(["--weights", self.model_weights_path])
        proc = subprocess.run(cmd, cwd=root, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Segmentation process failed: {proc.stderr.strip()}")

        payload = json.loads(proc.stdout)
        polygons = payload.get("polygons", [])
        if not isinstance(polygons, list):
            raise RuntimeError("Segmentation output invalid: 'polygons' must be a list")
        return polygons


runner = SegmentationRunner()
