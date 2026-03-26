Model directory notes
=====================

Current runtime focus:
- `biaochezhajiev2.pt`: private production model for wheelie detection
- `yolov8s-worldv2.pt`: default open-vocabulary runtime model
- `yolo26n.pt`: low-compute training base model
- `yolo26s.pt`: balanced training base model
- `det_10g.onnx`, `w600k_r50.onnx`: face detection and face recognition models
- `mobileclip_blt.ts`, `ViT-B-32.pt`: prompt-model text assets

Recommended logical groups:
- `production`: business models used directly by the app
- `foundation`: base training checkpoints such as `yolo26n.pt` and `yolo26s.pt`
- `face`: InsightFace-compatible ONNX models
- `assets`: prompt/text encoder assets such as `mobileclip_blt.ts` and `ViT-B-32.pt`
- `archive`: disabled or deprecated models

Current decision:
- Keep files in the root `model/` directory for now to avoid breaking existing `app.env` paths.
- Use `0325_model_directory_strategy.md` in the project root as the source of truth for future reorganization.
- Runtime slot overrides are stored in `deployment_slots.json`, which controls:
  - `upload_default`
  - `general`
  - `bczj`

These binaries are intentionally not tracked in Git.
