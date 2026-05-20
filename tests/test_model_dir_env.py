import importlib


def test_model_dir_can_be_overridden_by_env(monkeypatch):
    import shared.config.config as config

    monkeypatch.setenv("MODEL_DIR", "/tmp/custom_model")
    try:
        reloaded = importlib.reload(config)

        assert reloaded.MODEL_DIR == "/tmp/custom_model"
        assert reloaded.MODEL_YOLO_DIR.startswith("/tmp/custom_model")
        assert reloaded.MODEL_INSIGHTFACE_DIR.startswith("/tmp/custom_model")
        assert reloaded.DEPLOYMENT_SLOTS_PATH.startswith("/tmp/custom_model")
    finally:
        monkeypatch.delenv("MODEL_DIR", raising=False)
        importlib.reload(config)
