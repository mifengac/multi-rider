from __future__ import annotations

import importlib


def test_kingbase_db_falls_back_to_dbname_env(monkeypatch):
    import shared.db.kingbase as kingbase

    monkeypatch.delenv("KINGBASE_DB", raising=False)
    monkeypatch.setenv("KINGBASE_DBNAME", "yfywk")

    reloaded = importlib.reload(kingbase)

    assert reloaded.KINGBASE_DB == "yfywk"
