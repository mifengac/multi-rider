# Training Module Checklist

## Goal

Add a lightweight end-to-end labeling and training module to the current project so that users can:

1. Import images or video frames into a dataset
2. Pre-label samples with existing models
3. Manually correct labels
4. Train a new closed-set detection model
5. Evaluate and publish the trained model into the current detection workflow

## Current recommendations

- Main training line: `yolo26n.pt` and `yolo26s.pt`
- Pre-label line: `yolov8s-worldv2.pt`
- Production business model example: `biaochezhajiev2.pt`
- First version task type: detection only
- First version annotation type: bounding box only

## Scope

Include:

- Dataset management
- Image annotation
- Video frame extraction
- Model-assisted pre-labeling
- Training job management
- Validation metrics and model publishing
- Reuse of existing job history and result images as dataset sources

Exclude from V1:

- Polygon or segmentation annotation
- Multi-user collaborative conflict resolution
- Cloud storage
- Distributed training
- Automatic hyperparameter search
- Direct video timeline annotation

## UI design

Add a new top-level tab: `Train`

Subsections inside `Train`:

1. `Dataset`
- Create dataset
- Define class list
- Import ZIP images
- Import video and extract frames
- Add selected images from history/results into dataset

2. `Label`
- Show one image at a time
- Draw / edit / delete bounding boxes
- Class switch hotkeys
- Copy previous image annotations
- Mark image as reviewed
- Filter by unlabeled / reviewed / hard examples

3. `Pre-label`
- Select model
- For prompt models, input classes
- Generate initial labels
- Show confidence threshold
- Save generated labels as editable drafts

4. `Train`
- Select base checkpoint: `yolo26n.pt` or `yolo26s.pt`
- Select dataset version
- Choose preset
- Start / stop training
- View live logs and progress

5. `Evaluate & Publish`
- Show precision / recall / mAP
- Show confusion matrix
- Show sample false positives / false negatives
- Publish `best.pt` into `model/`

## Backend design

Suggested new modules:

- `routes/train_routes.py`
- `service/dataset_service.py`
- `service/annotation_service.py`
- `service/prelabel_service.py`
- `service/train_service.py`
- `service/eval_service.py`

Reuse existing patterns:

- Background task model from upload/oracle jobs
- SQLite persistence for status and history
- Existing `model/` scan behavior in `config.py`

## Storage design

Suggested directories:

- `datasets/`
- `datasets/<dataset_id>/images/`
- `datasets/<dataset_id>/labels/`
- `datasets/<dataset_id>/splits/`
- `datasets/<dataset_id>/exports/`
- `train_runs/`
- `train_runs/<run_id>/`

Suggested SQLite tables:

- `datasets`
- `dataset_assets`
- `dataset_annotations`
- `dataset_versions`
- `train_jobs`
- `train_runs`
- `model_registry`

## Workflow

1. Create dataset
2. Import images or extract video frames
3. Run pre-label with `yolov8s-worldv2.pt` or an existing private model
4. Manually correct labels
5. Freeze a dataset version
6. Train with `yolo26n.pt` or `yolo26s.pt`
7. Validate metrics
8. Publish `best.pt` into `model/`
9. Use the published model from the current upload/oracle detection entry points

## Presets for low compute machines

### Quick verify

- Base model: `yolo26n.pt`
- `imgsz=640`
- `epochs=30`
- small batch
- single training job only

### Standard

- Base model: `yolo26s.pt`
- `imgsz=640`
- `epochs=80`
- moderate batch

### Low-memory fallback

- Base model: `yolo26n.pt`
- `imgsz=512`
- `epochs=50`
- keep `workers` low on Windows
- prefer disk cache over RAM cache

## Integration with current project

- Training output should be copied into `model/`
- New model metadata should be saved into SQLite
- Current upload model selector should continue to discover `.pt` models automatically
- History detail page should support “add to dataset”
- Detection result review should support marking false positives / false negatives

## Risks and controls

- Do not make “minor” a primary visual training label for enforcement decisions
- Use identity + birthdate for age judgment when available
- Keep V1 to box detection only
- Prevent multiple concurrent training jobs on low-compute hosts
- Keep model files and dataset files on local disk only for intranet deployment

## Delivery phases

### Phase 1

- Train tab UI skeleton
- Dataset creation
- ZIP import
- Image annotation

### Phase 2

- Video frame extraction
- Pre-label service
- Dataset version export

### Phase 3

- Training jobs
- Evaluation page
- Publish to `model/`

### Phase 4

- History/result image reuse
- Hard-example feedback loop
- Model registry cleanup

## Acceptance criteria

- User can create a dataset from local files
- User can annotate at least image bounding boxes
- User can train a `YOLO26` model without leaving the project UI
- User can view metrics and publish the trained checkpoint
- Published model can be selected by the existing detection module
