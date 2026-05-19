Model directory notes
=====================

Current runtime focus:
- `biaochezhajiev2.pt`: private production model for wheelie detection
- `yolov8s-worldv2.pt`: default open-vocabulary runtime model
- `yolo26n.pt`: 26年最新微型版，仅5M，适合极低算力场景
- `yolo26s.pt`: 26年最新小型版，19M，平衡速度与精度进行训练
- `det_10g.onnx`, `w600k_r50.onnx`: face detection and face recognition models
- `mobileclip_blt.ts`, `mobileclip2_b.ts`, `ViT-B-32.pt`: prompt-model text assets

Recommended logical groups:
- `yolo/production`: business models used directly by the app
- `yolo/foundation`: base training checkpoints such as `yolo26n.pt` and `yolo26s.pt`
- `insightface`: InsightFace-compatible ONNX models
- `assets`: prompt/text encoder assets such as `mobileclip_blt.ts` and `ViT-B-32.pt`
- `archive`: disabled or deprecated models

Current layout:
- Runtime and tests support recursive model lookup under `model/`.
- Place business detection models in `model/yolo/production`.
- Place base checkpoints in `model/yolo/foundation`.
- Place face models in `model/insightface`.
- Place prompt/text assets in `model/assets`.
- Runtime slot overrides are stored in `deployment_slots.json`, which controls:
  - `upload_default`
  - `general`
  - `bczj`

These binaries are intentionally not tracked in Git.
