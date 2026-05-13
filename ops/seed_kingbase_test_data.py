"""Seed KingBase source tables with test data for ETL sync.

Usage (inside Docker container):
    python ops/seed_kingbase_test_data.py

Creates test data in ywdata schema:
    - zq_zfba_ajxx: 6 theft cases
    - zq_zfba_xyrxx: 10 suspects with case links
    - zq_zfba_wcnr_xyr: 1 minor suspect
    - b_per_dqqkrygj: 2 prior records
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db.kingbase import execute, execute_many, fetch_all

SCHEMA = "ywdata"


def check_tables():
    """Verify source tables exist."""
    for tbl in ["zq_zfba_ajxx", "zq_zfba_xyrxx", "zq_zfba_wcnr_xyr", "b_per_dqqkrygj"]:
        cnt = fetch_all(f"SELECT COUNT(*) AS c FROM {SCHEMA}.{tbl}")
        print(f"  {SCHEMA}.{tbl}: {cnt[0]['c']} existing rows")
    print("[tables] source tables verified")


def clear_data():
    """Remove existing test data."""
    for table in ["b_per_dqqkrygj", "zq_zfba_wcnr_xyr", "zq_zfba_xyrxx", "zq_zfba_ajxx"]:
        execute(f"DELETE FROM {SCHEMA}.{table}")
    print("[cleared] existing data removed")


def seed_cases():
    """Insert 6 theft cases."""
    cases = [
        ("A20260101001", "盗窃电动车",   "刑事", "2026-01-15 14:30:00", "2026-01-15 14:30:00", "320100", "320100", "鼓楼分局"),
        ("A20260102002", "入室盗窃",     "刑事", "2026-02-20 03:00:00", "2026-02-20 03:00:00", "320100", "320100", "玄武分局"),
        ("A20260103003", "盗窃电缆",     "刑事", "2026-03-10 22:00:00", "2026-03-10 22:00:00", "320100", "320100", "建邺分局"),
        ("A20260104004", "盗窃商铺",     "刑事", "2026-03-25 02:30:00", "2026-03-25 02:30:00", "320200", "320200", "锡山分局"),
        ("A20260105005", "盗窃工地建材", "刑事", "2026-04-08 01:00:00", "2026-04-08 01:00:00", "320200", "320200", "惠山分局"),
        ("A20260106006", "盗窃车内财物", "刑事", "2026-04-20 23:30:00", "2026-04-20 23:30:00", "320300", "320300", "云龙分局"),
    ]
    execute_many(
        f"""INSERT INTO {SCHEMA}.zq_zfba_ajxx
            (ajxx_ajbh, ajxx_aymc, ajxx_ajlx, ajxx_fasj, ajxx_lasj, ajxx_cbqy_bh, ajxx_ssjqdm, ajxx_cbdw_mc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        cases,
    )
    print(f"[cases] inserted {len(cases)} cases")


def seed_persons():
    """Insert 10 suspects with case links."""
    persons = [
        # sfzh, name, gender, birth_date, hjd, jzdz, area_code, xzqdm, lrsj, xgsj, ajbh, aymc
        ("320102199001011234", "张三", "男", "1990-01-01", "南京市鼓楼区", "南京市鼓楼区XX路1号",   "320100", "320100", "2026-01-15 15:00:00", "2026-01-15 15:00:00", "A20260101001", "盗窃电动车"),
        ("320102199001011234", "张三", "男", "1990-01-01", "南京市鼓楼区", "南京市鼓楼区XX路1号",   "320100", "320100", "2026-02-20 04:00:00", "2026-02-20 04:00:00", "A20260102002", "入室盗窃"),
        ("320102199001011234", "张三", "男", "1990-01-01", "南京市鼓楼区", "南京市鼓楼区XX路1号",   "320100", "320100", "2026-03-10 23:00:00", "2026-03-10 23:00:00", "A20260103003", "盗窃电缆"),
        ("320102199205052345", "李四", "男", "1992-05-05", "南京市玄武区", "南京市玄武区XX路2号",   "320100", "320100", "2026-01-15 15:10:00", "2026-01-15 15:10:00", "A20260101001", "盗窃电动车"),
        ("320102199205052345", "李四", "男", "1992-05-05", "南京市玄武区", "南京市玄武区XX路2号",   "320100", "320100", "2026-02-20 04:10:00", "2026-02-20 04:10:00", "A20260102002", "入室盗窃"),
        ("320102199205052345", "李四", "男", "1992-05-05", "南京市玄武区", "南京市玄武区XX路2号",   "320100", "320100", "2026-03-25 03:00:00", "2026-03-25 03:00:00", "A20260104004", "盗窃商铺"),
        ("320102199508083456", "王五", "男", "1995-08-08", "南京市建邺区", "南京市建邺区XX路3号",   "320100", "320100", "2026-01-15 15:20:00", "2026-01-15 15:20:00", "A20260101001", "盗窃电动车"),
        ("320102199508083456", "王五", "男", "1995-08-08", "南京市建邺区", "南京市建邺区XX路3号",   "320100", "320100", "2026-03-25 03:10:00", "2026-03-25 03:10:00", "A20260104004", "盗窃商铺"),
        ("320102199303034567", "赵六", "男", "1993-03-03", "南京市鼓楼区", "南京市鼓楼区XX路4号",   "320100", "320100", "2026-02-20 04:20:00", "2026-02-20 04:20:00", "A20260102002", "入室盗窃"),
        ("320102199303034567", "赵六", "男", "1993-03-03", "南京市鼓楼区", "南京市鼓楼区XX路4号",   "320100", "320100", "2026-03-10 23:10:00", "2026-03-10 23:10:00", "A20260103003", "盗窃电缆"),
        ("320102199807075678", "钱七", "男", "1998-07-07", "南京市秦淮区", "南京市秦淮区XX路5号",   "320100", "320100", "2026-03-10 23:20:00", "2026-03-10 23:20:00", "A20260103003", "盗窃电缆"),
        ("320102201006066789", "小周", "男", "2010-06-06", "南京市栖霞区", "南京市栖霞区XX路6号",   "320100", "320100", "2026-03-25 03:20:00", "2026-03-25 03:20:00", "A20260104004", "盗窃商铺"),
        ("320102199109097890", "陈七", "男", "1991-09-09", "无锡市锡山区", "无锡市锡山区XX路7号",   "320200", "320200", "2026-04-08 02:00:00", "2026-04-08 02:00:00", "A20260105005", "盗窃工地建材"),
        ("320102199109097890", "陈七", "男", "1991-09-09", "无锡市锡山区", "无锡市锡山区XX路7号",   "320200", "320200", "2026-04-20 00:00:00", "2026-04-20 00:00:00", "A20260106006", "盗窃车内财物"),
        ("320102199412128901", "刘八", "男", "1994-12-12", "无锡市惠山区", "无锡市惠山区XX路8号",   "320200", "320200", "2026-04-08 02:10:00", "2026-04-08 02:10:00", "A20260105005", "盗窃工地建材"),
        ("320102199412128901", "刘八", "男", "1994-12-12", "无锡市惠山区", "无锡市惠山区XX路8号",   "320200", "320200", "2026-04-20 00:10:00", "2026-04-20 00:10:00", "A20260106006", "盗窃车内财物"),
        ("320102199602029012", "孙九", "男", "1996-02-02", "无锡市惠山区", "无锡市惠山区XX路9号",   "320200", "320200", "2026-04-08 02:20:00", "2026-04-08 02:20:00", "A20260105005", "盗窃工地建材"),
        ("320102199704040123", "周十", "男", "1997-04-04", "徐州市云龙区", "徐州市云龙区XX路10号",  "320300", "320300", "2026-04-20 00:20:00", "2026-04-20 00:20:00", "A20260106006", "盗窃车内财物"),
    ]
    execute_many(
        f"""INSERT INTO {SCHEMA}.zq_zfba_xyrxx
            (xyrxx_sfzh, xyrxx_xm, xyrxx_xb, xyrxx_csrq, xyrxx_hjd, xyrxx_jzdz,
             xyrxx_cbqy_bh, xyrxx_xzqdm, xyrxx_lrsj, xyrxx_xgsj, ajxx_join_ajxx_ajbh, xyrxx_ay_mc)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        persons,
    )
    print(f"[persons] inserted {len(persons)} suspect records (10 unique people)")


def seed_minor():
    """Mark 小周 as minor suspect."""
    execute(
        f"INSERT INTO {SCHEMA}.zq_zfba_wcnr_xyr (xyrxx_sfzh, ajxx_join_ajxx_ajbh) VALUES (%s, %s)",
        ("320102201006066789", "A20260104004"),
    )
    print("[minor] marked 小周 as minor (wcnr)")


def seed_trajectory():
    """Insert phone signal trajectory for suspects."""
    records = [
        # 张三: 3 trajectory points around Nanjing
        ("张三", "320102199001011234", "13800138001", "2026-01-15 14:00:00", "2026-01-15 14:30:00", 118.7969, 32.0603, "南京市公安局", "鼓楼分局", "鼓楼区XX路1号附近", "2026-01-15 15:00:00"),
        ("张三", "320102199001011234", "13800138001", "2026-02-20 02:30:00", "2026-02-20 03:00:00", 118.8025, 32.0548, "南京市公安局", "玄武分局", "玄武区XX路2号附近", "2026-02-20 04:00:00"),
        ("张三", "320102199001011234", "13800138001", "2026-03-10 21:30:00", "2026-03-10 22:00:00", 118.7515, 32.0376, "南京市公安局", "建邺分局", "建邺区XX路3号附近", "2026-03-10 23:00:00"),
        # 李四: 2 trajectory points
        ("李四", "320102199205052345", "13900139002", "2026-01-15 14:10:00", "2026-01-15 14:30:00", 118.7980, 32.0610, "南京市公安局", "鼓楼分局", "鼓楼区XX路4号附近", "2026-01-15 15:10:00"),
        ("李四", "320102199205052345", "13900139002", "2026-03-25 02:00:00", "2026-03-25 02:30:00", 118.7700, 32.0500, "无锡市公安局", "锡山分局", "锡山区XX路5号附近", "2026-03-25 03:00:00"),
        # 赵六: 2 trajectory points
        ("赵六", "320102199303034567", "13700137003", "2026-02-20 02:45:00", "2026-02-20 03:00:00", 118.8010, 32.0560, "南京市公安局", "玄武分局", "玄武区XX路6号附近", "2026-02-20 04:20:00"),
        ("赵六", "320102199303034567", "13700137003", "2026-03-10 21:45:00", "2026-03-10 22:00:00", 118.7520, 32.0380, "南京市公安局", "建邺分局", "建邺区XX路7号附近", "2026-03-10 23:10:00"),
        # 陈七: 2 trajectory points
        ("陈七", "320102199109097890", "13600136004", "2026-04-08 00:30:00", "2026-04-08 01:00:00", 120.3500, 31.5800, "无锡市公安局", "锡山分局", "锡山区XX路8号附近", "2026-04-08 02:00:00"),
        ("陈七", "320102199109097890", "13600136004", "2026-04-20 23:00:00", "2026-04-20 23:30:00", 120.3200, 31.5700, "无锡市公安局", "惠山分局", "惠山区XX路9号附近", "2026-04-20 00:00:00"),
        # 刘八: 1 trajectory point
        ("刘八", "320102199412128901", "13500135005", "2026-04-08 00:45:00", "2026-04-08 01:00:00", 120.3510, 31.5810, "无锡市公安局", "锡山分局", "锡山区XX路10号附近", "2026-04-08 02:10:00"),
    ]
    execute_many(
        f"""INSERT INTO {SCHEMA}.b_per_dqqkrygj
            (xm, zjhm, sjhm, tlkssj, tljssj, jd, wd, ssfj, sspcs, tlwz, rksj)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        records,
    )
    print(f"[trajectory] inserted {len(records)} trajectory points")


def verify():
    """Print summary."""
    counts = fetch_all(f"""
        SELECT 'zq_zfba_ajxx' AS tbl, COUNT(*) AS cnt FROM {SCHEMA}.zq_zfba_ajxx
        UNION ALL
        SELECT 'zq_zfba_xyrxx', COUNT(*) FROM {SCHEMA}.zq_zfba_xyrxx
        UNION ALL
        SELECT 'zq_zfba_wcnr_xyr', COUNT(*) FROM {SCHEMA}.zq_zfba_wcnr_xyr
        UNION ALL
        SELECT 'b_per_dqqkrygj (trajectory)', COUNT(*) FROM {SCHEMA}.b_per_dqqkrygj
    """)
    print("\n--- Source Table Summary ---")
    for row in counts:
        print(f"  {SCHEMA}.{row['tbl']}: {row['cnt']} rows")

    unique_persons = fetch_all(f"""
        SELECT DISTINCT xyrxx_sfzh, xyrxx_xm FROM {SCHEMA}.zq_zfba_xyrxx ORDER BY xyrxx_sfzh
    """)
    print(f"\n  Unique suspects: {len(unique_persons)}")
    for p in unique_persons:
        print(f"    {p['xyrxx_sfzh']} - {p['xyrxx_xm']}")


def main():
    print("=== Seeding KingBase source tables ===\n")
    check_tables()
    clear_data()
    seed_cases()
    seed_persons()
    seed_minor()
    seed_trajectory()
    print("\n--- Verifying ---")
    verify()
    print("\n[done] source tables seeded successfully")
    print("\nYou can now trigger ETL sync from the web UI or:")
    print("  POST /api/graph/sync {\"theft_only\": true}")


if __name__ == "__main__":
    main()
