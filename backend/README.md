# Backend scaffold

## Run

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

## Your `backend/infer` and `backend/post_process` files
Great — keep those in place. The backend runner can call your inference entrypoint and optionally pass a `.pth` weight file path.

## For your 95MB `.pth` model file
Do **not** commit it directly to git history unless you use Git LFS.

### Recommended (simple local development)
1. Place weight file outside git tracking, e.g.:
   - `backend/model_artifacts/model_best.pth`
2. Set:
   - `SEGMENTATION_MODEL_WEIGHTS_PATH=/workspace/G-sat/backend/model_artifacts/model_best.pth`
3. Ensure your entrypoint accepts `--weights <path>`.

### If you must version it in git: use Git LFS
```bash
git lfs install
git lfs track "*.pth"
git add .gitattributes backend/model_artifacts/model_best.pth
git commit -m "Track model weights with LFS"
```

## Model integration options

### Option A (no env vars except optional weights)
- Put model repo/code in `backend/model_bundle/`
- Include one of: `run_segmentation.py`, `inference.py`, `predict.py`, `main.py`

### Option B (explicit paths)
- `SEGMENTATION_MODEL_ROOT=/absolute/path/to/model/repo`
- `SEGMENTATION_ENTRYPOINT=path/inside/repo/run_segmentation.py`
- `SEGMENTATION_MODEL_WEIGHTS_PATH=/absolute/path/to/model.pth` (optional)

## Verify wiring
```bash
curl http://127.0.0.1:8000/integration/segmentation-runner
```

## Entrypoint contract
Entrypoint should accept:
- `--course-id <course_id>`
- `--boundary '<geojson-json>'`
- `--weights <path>` (optional)

and print JSON:

```json
{
  "polygons": [
    {"id": "poly_1", "geometry": {"type": "Polygon", "coordinates": []}, "class_type": "fairway"}
  ]
}
```
