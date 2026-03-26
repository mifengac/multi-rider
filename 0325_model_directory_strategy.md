# Model Directory Strategy

## Current problem

The `model/` directory currently mixes:

- production business models
- foundation checkpoints
- face recognition ONNX models
- prompt-model text assets
- generated compatibility models

This makes it hard to judge which files are:

- required at runtime
- required only for training
- optional assets
- deprecated or safe to remove

## Recommended logical tiers

### Tier 1: production

Files used directly by online business detection:

- `biaochezhajiev2.pt`
- `yolov8s-worldv2.pt`
- future published business models

Rule:
- keep only currently deployable models here

### Tier 2: foundation

Files used as training bases:

- `yolo26n.pt`
- `yolo26s.pt`

Rule:
- do not use these names for business models
- use them as base checkpoints only

### Tier 3: face

Files used by face detection / recognition:

- `det_10g.onnx`
- `w600k_r50.onnx`
- generated `_dyn.onnx` files

Rule:
- keep face models separate in documentation even if paths remain unchanged for now

### Tier 4: prompt assets

Files required by open-vocabulary models:

- `mobileclip_blt.ts`
- `ViT-B-32.pt`

Rule:
- treat these as dependency assets, not detection models

### Tier 5: archive

Files no longer used by the current project:

- deprecated checkpoints
- replaced experiments
- disabled models

Rule:
- move old models here before final deletion if you still need rollback

## Recommended naming rules

Business models:

- `<scene>_<task>_<date>.pt`
- example: `wheelie_detect_20260325.pt`

Base models:

- keep official names unchanged
- example: `yolo26n.pt`, `yolo26s.pt`

Prompt models:

- keep upstream names unchanged
- example: `yolov8s-worldv2.pt`

Face models:

- keep upstream names unchanged

## Recommended future physical layout

This is the target layout after a later refactor, not a required immediate change:

```text
model/
  production/
    biaochezhajiev2.pt
    wheelie_detect_20260325.pt
  foundation/
    yolo26n.pt
    yolo26s.pt
  prompt/
    yolov8s-worldv2.pt
  face/
    det_10g.onnx
    det_10g_dyn.onnx
    w600k_r50.onnx
    w600k_r50_dyn.onnx
  assets/
    mobileclip_blt.ts
    ViT-B-32.pt
  archive/
    old_or_disabled_models.pt
```

## Why not move files immediately

Current `app.env` and runtime defaults already point to files under the root `model/` directory.

Immediate large-scale moves would require:

- config path changes
- app.env migration
- deployment migration
- re-test of face and prompt dependencies

So the practical choice now is:

1. remove unused models
2. clean naming
3. update documentation
4. refactor paths later in one controlled change

## Current action for this repo

- keep `biaochezhajiev2.pt`
- keep `yolov8s-worldv2.pt`
- keep `yolo26n.pt`
- keep `yolo26s.pt`
- keep face ONNX models
- keep prompt assets
- delete the two `YOLOE` checkpoints

## Cleanup rule

Whenever a new business model is published:

1. keep the latest active model
2. keep one rollback model
3. archive or delete the rest

This avoids the `model/` directory turning into a mixed experiment dump again.
