# Backend scaffold

## Run

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

## I can do most of it for you — one-time local step from you

I cannot directly open your Google Drive from this environment, so please do **one** of these:

### Option A (easiest): copy model repo into this project
1. Download your model repo/folder from Google Drive.
2. Place it at: `backend/model_bundle/`
3. Ensure one of these files exists in that folder:
   - `run_segmentation.py`
   - `inference.py`
   - `predict.py`
   - `main.py`

No env vars needed in this option.

### Option B: keep model repo elsewhere
Set env vars:
- `SEGMENTATION_MODEL_ROOT=/absolute/path/to/model/repo`
- `SEGMENTATION_ENTRYPOINT=path/inside/repo/run_segmentation.py` (optional if file name is auto-detected)

## Verify integration
Use:

```bash
curl http://127.0.0.1:8000/integration/segmentation-runner
```

If configured correctly, response includes resolved `root` and `entrypoint`.

## Contract for model entrypoint
Entrypoint script should accept:
- `--course-id <course_id>`
- `--boundary '<geojson-json>'`

and print JSON to stdout:

```json
{
  "polygons": [
    {"id": "poly_1", "geometry": {"type": "Polygon", "coordinates": []}, "class_type": "fairway"}
  ]
}
```
