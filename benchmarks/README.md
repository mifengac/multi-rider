# 性能验收脚本

本目录提供命令行 benchmark，用于生成可追溯的验收 JSON。测试数据不提交仓库，请放在本机或内网共享目录。

## 图片检测吞吐

```powershell
uv run python benchmarks/benchmark_detection.py --image-dir D:\bench\images --model-key bczj --conf 0.25 --imgsz 640 --batch-size 8
```

输出：`runtime/benchmarks/detection_images_*.json`

## 视频抽帧检测

```powershell
uv run python benchmarks/benchmark_video.py --video D:\bench\test.mp4 --model-key bczj --frame-interval 5
```

## YOLO 标注集评估

```powershell
uv run python benchmarks/evaluate_yolo_dataset.py --data D:\bench\dataset.yaml --model-key bczj
```

## 人脸识别吞吐

```powershell
uv run python benchmarks/benchmark_face.py --image-dir D:\bench\faces
```

## 最小链路耗时

```powershell
uv run python benchmarks/benchmark_pipeline.py --image-dir D:\bench\images --model-key bczj
```

## 验收注意

- 申报书中的 330-380 张/分钟、92% 准确率等指标必须绑定固定硬件、模型版本、图片分辨率、batch size 和测试集。
- 首次运行模型会有加载耗时，正式报告建议先预热一次，再记录第二次结果。
- 离线环境要提前准备模型文件和 Python wheelhouse。

