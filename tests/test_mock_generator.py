from __future__ import annotations

from pathlib import Path


def test_mock_generator_includes_p1_business_tables():
    source = (Path(__file__).resolve().parents[1] / "generate_mock_data.py").read_text(
        encoding="utf-8"
    )

    for csv_name in [
        "ywdata.b_per_qskjwcnr.csv",
        "ywdata.b_per_qslswcnr.csv",
        "ywdata.b_per_qswcnrbczj.csv",
        "ywdata.b_per_qsyzjszawcnr.csv",
        "ywdata.zq_zfba_wcnr_sfzxx.csv",
        "ywdata.t_wcnrxwjl_xx.csv",
        "ywdata.b_evt_jjzdbczjajxx.csv",
    ]:
        assert csv_name in source
