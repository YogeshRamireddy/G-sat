# PhytoMaps MVP — Steps 1 & 2 Implementation Spec

This document implements the first two workflow phases:

1. **Boundary → Segmentation → Polygons**
2. **Human validation → Zone labeling**

All geospatial data is normalized to **EPSG:4326 (WGS84)**.

---

## 1) Data Contracts

### 1.1 Course Boundary (input)

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-122.1, 37.4], [-122.0, 37.4], [-122.0, 37.5], [-122.1, 37.5], [-122.1, 37.4]]]
  },
  "properties": {
    "name": "Example Golf Club"
  }
}
```

Validation rules:
- Geometry must be Polygon or MultiPolygon
- Coordinates must be valid lon/lat (WGS84)
- Boundary must be closed and non-self-intersecting

### 1.2 Segmentation Polygon (prediction)

```json
{
  "id": "poly_123",
  "course_id": "course_1",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "class_type": "fairway",
  "hole_id": null,
  "model_version": "seg-v1.0.0",
  "created_at": "2026-05-05T00:00:00Z"
}
```

### 1.3 Validation Update Payload

```json
{
  "polygons": [
    {
      "id": "poly_123",
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "zone_type": "fairway",
      "hole_id": 6
    }
  ]
}
```

---

## 2) Asynchronous Job Model

Job statuses for these two steps:

- `queued`
- `image_acquisition`
- `tiling`
- `inference`
- `stitching`
- `post_processing`
- `polygonization`
- `segmentation_complete`
- `validation_in_progress`
- `validation_complete`
- `failed`

Failure contract should include:
- `error_code`
- `error_message`
- `failed_at_stage`

---

## 3) Step 1 — Boundary to Segmentation Polygons

### 3.1 Course creation + boundary storage
- Persist incoming GeoJSON in `courses.boundary`
- Run geometry validity checks
- Create job record in `jobs` with status `queued`

### 3.2 Segmentation worker pipeline

Worker function: `run_segmentation_job(course_id, job_id)`

1. Acquire RGB imagery for boundary extent at fixed zoom
2. Tile image to 512×512 with 20–30% overlap
3. For each tile:
   - execute model inference
   - output per-pixel class mask
4. Stitch masks into full-course aligned raster
5. Post-process mask:
   - remove small components by class threshold
   - smooth boundaries with morphological close/open
6. Polygonize raster per class (`fairway`, `green`, `tee`)
7. Clip polygons to original course boundary
8. Save polygons with model metadata
9. Mark job `segmentation_complete`

### 3.3 Spatial correctness requirements
- Every tile stores:
  - tile bounds (`min_lon, min_lat, max_lon, max_lat`)
  - affine transform metadata
- Stitching uses georeferencing metadata only (never pixel-only offsets)
- Polygon output CRS must be EPSG:4326

---

## 4) Step 2 — Human Validation and Zone Labeling

### 4.1 Admin editing capabilities
Required edit operations:
- move vertex
- add/delete vertex
- merge polygons
- split polygon
- delete polygon
- redraw polygon

### 4.2 Labeling rules
- `zone_type` required (enum: `fairway | green | tee | rough | bunker | water | other`)
- `hole_id` required for golf-playable zones (`fairway`, `green`, `tee`)
- `hole_id` integer range: 1–18 (configurable)
- Geometry must remain valid after edit

### 4.3 Finalize workflow
When admin clicks finalize:
1. Validate all edited features
2. Upsert polygons
3. Persist mapping: `polygon_id -> hole_id -> zone_type`
4. Mark current segmentation job `validation_complete`
5. Emit event `validation.finalized` for NDVI pipeline trigger

---

## 5) Minimal API Surface (for first two steps)

- `POST /courses`
  - creates course + boundary
- `POST /courses/{course_id}/jobs/segmentation`
  - creates segmentation job
- `GET /jobs/{job_id}`
  - returns status + stage + errors
- `GET /courses/{course_id}/polygons?source=predicted|validated`
- `PUT /courses/{course_id}/polygons/validated`
  - bulk update validated polygons
- `POST /courses/{course_id}/validation/finalize`

All heavy operations return `202 Accepted` with job metadata.

---

## 6) Suggested Database Tables

- `courses(id, name, boundary_geojson, created_at)`
- `jobs(id, course_id, type, status, error_code, error_message, created_at, updated_at)`
- `predicted_polygons(id, course_id, geometry, class_type, model_version, created_at)`
- `validated_polygons(id, course_id, geometry, zone_type, hole_id, created_at, updated_at)`

Geometry columns should use PostGIS geometry type with SRID 4326.

---

## 7) Deterministic Acceptance Criteria (steps 1 & 2)

1. Given valid course boundary, segmentation job reaches `segmentation_complete` and stores polygons.
2. Predicted polygons are retrievable via API and rendered on map.
3. Admin can edit geometry and assign `zone_type` + `hole_id`.
4. Finalize rejects invalid/missing labels with explicit errors.
5. Finalize success persists validated polygons and emits NDVI trigger event.
