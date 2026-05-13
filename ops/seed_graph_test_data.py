"""Seed Neo4j with test data for the knowledge graph module.

Usage (from project root):
    python -m ops.seed_graph_test_data

Creates:
    - 10 Person nodes (including 2 with prior records, 1 minor)
    - 6 Case nodes (all theft-related)
    - SAME_CASE relationships (person -> case)
    - CO_SUSPECT relationships (person <-> person with weights)
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db.neo4j_db import run_query, verify_connectivity


def clear_graph():
    """Remove all existing nodes and relationships."""
    run_query("MATCH (n) DETACH DELETE n")
    print("[cleared] all nodes and relationships removed")


def create_constraints():
    """Create unique constraints (idempotent)."""
    run_query("""
        CREATE CONSTRAINT person_sfzh IF NOT EXISTS
        FOR (p:Person) REQUIRE p.sfzh IS UNIQUE
    """)
    run_query("""
        CREATE CONSTRAINT case_ajbh IF NOT EXISTS
        FOR (c:Case) REQUIRE c.ajbh IS UNIQUE
    """)
    print("[constraints] Person(sfzh), Case(ajbh)")


def seed_persons():
    """Create 10 Person nodes representing suspects."""
    persons = [
        {"sfzh": "320102199001011234", "name": "张三",   "gender": "男", "birth_date": "1990-01-01", "age": 36, "is_wcnr": False, "area_code": "320100", "has_prior": True,  "prior_record_count": 3},
        {"sfzh": "320102199205052345", "name": "李四",   "gender": "男", "birth_date": "1992-05-05", "age": 34, "is_wcnr": False, "area_code": "320100", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199508083456", "name": "王五",   "gender": "男", "birth_date": "1995-08-08", "age": 30, "is_wcnr": False, "area_code": "320100", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199303034567", "name": "赵六",   "gender": "男", "birth_date": "1993-03-03", "age": 33, "is_wcnr": False, "area_code": "320100", "has_prior": True,  "prior_record_count": 1},
        {"sfzh": "320102199807075678", "name": "钱七",   "gender": "男", "birth_date": "1998-07-07", "age": 27, "is_wcnr": False, "area_code": "320100", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102201006066789", "name": "小周",   "gender": "男", "birth_date": "2010-06-06", "age": 15, "is_wcnr": True,  "area_code": "320100", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199109097890", "name": "陈七",   "gender": "男", "birth_date": "1991-09-09", "age": 34, "is_wcnr": False, "area_code": "320200", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199412128901", "name": "刘八",   "gender": "男", "birth_date": "1994-12-12", "age": 31, "is_wcnr": False, "area_code": "320200", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199602029012", "name": "孙九",   "gender": "男", "birth_date": "1996-02-02", "age": 30, "is_wcnr": False, "area_code": "320200", "has_prior": False, "prior_record_count": 0},
        {"sfzh": "320102199704040123", "name": "周十",   "gender": "男", "birth_date": "1997-04-04", "age": 29, "is_wcnr": False, "area_code": "320300", "has_prior": False, "prior_record_count": 0},
    ]

    for batch_start in range(0, len(persons), 500):
        batch = persons[batch_start:batch_start + 500]
        run_query(
            """
            UNWIND $rows AS row
            MERGE (p:Person {sfzh: row.sfzh})
            SET p.name = row.name,
                p.gender = row.gender,
                p.birth_date = row.birth_date,
                p.age = row.age,
                p.is_wcnr = row.is_wcnr,
                p.area_code = row.area_code,
                p.has_prior = row.has_prior,
                p.prior_record_count = row.prior_record_count
            """,
            {"rows": batch},
        )
    print(f"[persons] created {len(persons)} Person nodes")


def seed_cases():
    """Create 6 theft-related Case nodes."""
    cases = [
        {"ajbh": "A20260101001", "aymc": "盗窃电动车",   "ajlx": "刑事", "fasj": "2026-01-15T14:30:00", "area_code": "320100", "cbdw_mc": "鼓楼分局"},
        {"ajbh": "A20260102002", "aymc": "入室盗窃",     "ajlx": "刑事", "fasj": "2026-02-20T03:00:00", "area_code": "320100", "cbdw_mc": "玄武分局"},
        {"ajbh": "A20260103003", "aymc": "盗窃电缆",     "ajlx": "刑事", "fasj": "2026-03-10T22:00:00", "area_code": "320100", "cbdw_mc": "建邺分局"},
        {"ajbh": "A20260104004", "aymc": "盗窃商铺",     "ajlx": "刑事", "fasj": "2026-03-25T02:30:00", "area_code": "320200", "cbdw_mc": "锡山分局"},
        {"ajbh": "A20260105005", "aymc": "盗窃工地建材", "ajlx": "刑事", "fasj": "2026-04-08T01:00:00", "area_code": "320200", "cbdw_mc": "惠山分局"},
        {"ajbh": "A20260106006", "aymc": "盗窃车内财物", "ajlx": "刑事", "fasj": "2026-04-20T23:30:00", "area_code": "320300", "cbdw_mc": "云龙分局"},
    ]

    run_query(
        """
        UNWIND $rows AS row
        MERGE (c:Case {ajbh: row.ajbh})
        SET c.aymc = row.aymc,
            c.ajlx = row.ajlx,
            c.fasj = row.fasj,
            c.area_code = row.area_code,
            c.cbdw_mc = row.cbdw_mc,
            c.is_theft = true
        """,
        {"rows": cases},
    )
    print(f"[cases] created {len(cases)} Case nodes")


def seed_same_case_rels():
    """Create SAME_CASE relationships (person -> case)."""
    rels = [
        # 案件A001: 张三、李四、王五
        {"sfzh": "320102199001011234", "ajbh": "A20260101001", "aymc": "盗窃电动车",   "case_date": "2026-01-15T14:30:00", "area_code": "320100"},
        {"sfzh": "320102199205052345", "ajbh": "A20260101001", "aymc": "盗窃电动车",   "case_date": "2026-01-15T14:30:00", "area_code": "320100"},
        {"sfzh": "320102199508083456", "ajbh": "A20260101001", "aymc": "盗窃电动车",   "case_date": "2026-01-15T14:30:00", "area_code": "320100"},
        # 案件A002: 张三、李四、赵六
        {"sfzh": "320102199001011234", "ajbh": "A20260102002", "aymc": "入室盗窃",     "case_date": "2026-02-20T03:00:00", "area_code": "320100"},
        {"sfzh": "320102199205052345", "ajbh": "A20260102002", "aymc": "入室盗窃",     "case_date": "2026-02-20T03:00:00", "area_code": "320100"},
        {"sfzh": "320102199303034567", "ajbh": "A20260102002", "aymc": "入室盗窃",     "case_date": "2026-02-20T03:00:00", "area_code": "320100"},
        # 案件A003: 张三、赵六、钱七
        {"sfzh": "320102199001011234", "ajbh": "A20260103003", "aymc": "盗窃电缆",     "case_date": "2026-03-10T22:00:00", "area_code": "320100"},
        {"sfzh": "320102199303034567", "ajbh": "A20260103003", "aymc": "盗窃电缆",     "case_date": "2026-03-10T22:00:00", "area_code": "320100"},
        {"sfzh": "320102199807075678", "ajbh": "A20260103003", "aymc": "盗窃电缆",     "case_date": "2026-03-10T22:00:00", "area_code": "320100"},
        # 案件A004: 李四、王五、小周(未成年)
        {"sfzh": "320102199205052345", "ajbh": "A20260104004", "aymc": "盗窃商铺",     "case_date": "2026-03-25T02:30:00", "area_code": "320200"},
        {"sfzh": "320102199508083456", "ajbh": "A20260104004", "aymc": "盗窃商铺",     "case_date": "2026-03-25T02:30:00", "area_code": "320200"},
        {"sfzh": "320102201006066789", "ajbh": "A20260104004", "aymc": "盗窃商铺",     "case_date": "2026-03-25T02:30:00", "area_code": "320200"},
        # 案件A005: 陈七、刘八、孙九
        {"sfzh": "320102199109097890", "ajbh": "A20260105005", "aymc": "盗窃工地建材", "case_date": "2026-04-08T01:00:00", "area_code": "320200"},
        {"sfzh": "320102199412128901", "ajbh": "A20260105005", "aymc": "盗窃工地建材", "case_date": "2026-04-08T01:00:00", "area_code": "320200"},
        {"sfzh": "320102199602029012", "ajbh": "A20260105005", "aymc": "盗窃工地建材", "case_date": "2026-04-08T01:00:00", "area_code": "320200"},
        # 案件A006: 陈七、刘八、周十
        {"sfzh": "320102199109097890", "ajbh": "A20260106006", "aymc": "盗窃车内财物", "case_date": "2026-04-20T23:30:00", "area_code": "320300"},
        {"sfzh": "320102199412128901", "ajbh": "A20260106006", "aymc": "盗窃车内财物", "case_date": "2026-04-20T23:30:00", "area_code": "320300"},
        {"sfzh": "320102199704040123", "ajbh": "A20260106006", "aymc": "盗窃车内财物", "case_date": "2026-04-20T23:30:00", "area_code": "320300"},
    ]

    run_query(
        """
        UNWIND $rows AS row
        MATCH (p:Person {sfzh: row.sfzh})
        MATCH (c:Case {ajbh: row.ajbh})
        MERGE (p)-[rel:SAME_CASE]->(c)
        SET rel.aymc = row.aymc,
            rel.case_date = row.case_date,
            rel.area_code = row.area_code
        """,
        {"rows": rels},
    )
    print(f"[same_case] created {len(rels)} SAME_CASE relationships")


def seed_co_suspect_rels():
    """Create CO_SUSPECT relationships (person <-> person with weights).

    Weight = number of cases where both persons were co-suspects.
    """
    # Pre-computed from SAME_CASE data above:
    # 张三-李四: 共同案件 A001,A002 → weight=2
    # 张三-王五: 共同案件 A001 → weight=1
    # 张三-赵六: 共同案件 A002,A003 → weight=2
    # 张三-钱七: 共同案件 A003 → weight=1
    # 李四-王五: 共同案件 A001,A004 → weight=2
    # 李四-赵六: 共同案件 A002 → weight=1
    # 王五-小周: 共同案件 A004 → weight=1
    # 赵六-钱七: 共同案件 A003 → weight=1
    # 陈七-刘八: 共同案件 A005,A006 → weight=2
    # 陈七-孙九: 共同案件 A005 → weight=1
    # 陈七-周十: 共同案件 A006 → weight=1
    # 刘八-孙九: 共同案件 A005 → weight=1
    # 刘八-周十: 共同案件 A006 → weight=1

    rels = [
        {"src": "320102199001011234", "tgt": "320102199205052345", "weight": 2, "case_types": "盗窃电动车 | 入室盗窃",   "first": "2026-01-15", "last": "2026-02-20"},
        {"src": "320102199001011234", "tgt": "320102199508083456", "weight": 1, "case_types": "盗窃电动车",             "first": "2026-01-15", "last": "2026-01-15"},
        {"src": "320102199001011234", "tgt": "320102199303034567", "weight": 2, "case_types": "入室盗窃 | 盗窃电缆",     "first": "2026-02-20", "last": "2026-03-10"},
        {"src": "320102199001011234", "tgt": "320102199807075678", "weight": 1, "case_types": "盗窃电缆",               "first": "2026-03-10", "last": "2026-03-10"},
        {"src": "320102199205052345", "tgt": "320102199508083456", "weight": 2, "case_types": "盗窃电动车 | 盗窃商铺",   "first": "2026-01-15", "last": "2026-03-25"},
        {"src": "320102199205052345", "tgt": "320102199303034567", "weight": 1, "case_types": "入室盗窃",               "first": "2026-02-20", "last": "2026-02-20"},
        {"src": "320102199205052345", "tgt": "320102201006066789", "weight": 1, "case_types": "盗窃商铺",               "first": "2026-03-25", "last": "2026-03-25"},
        {"src": "320102199303034567", "tgt": "320102199807075678", "weight": 1, "case_types": "盗窃电缆",               "first": "2026-03-10", "last": "2026-03-10"},
        {"src": "320102199508083456", "tgt": "320102201006066789", "weight": 1, "case_types": "盗窃商铺",               "first": "2026-03-25", "last": "2026-03-25"},
        {"src": "320102199109097890", "tgt": "320102199412128901", "weight": 2, "case_types": "盗窃工地建材 | 盗窃车内财物", "first": "2026-04-08", "last": "2026-04-20"},
        {"src": "320102199109097890", "tgt": "320102199602029012", "weight": 1, "case_types": "盗窃工地建材",           "first": "2026-04-08", "last": "2026-04-08"},
        {"src": "320102199109097890", "tgt": "320102199704040123", "weight": 1, "case_types": "盗窃车内财物",           "first": "2026-04-20", "last": "2026-04-20"},
        {"src": "320102199412128901", "tgt": "320102199602029012", "weight": 1, "case_types": "盗窃工地建材",           "first": "2026-04-08", "last": "2026-04-08"},
        {"src": "320102199412128901", "tgt": "320102199704040123", "weight": 1, "case_types": "盗窃车内财物",           "first": "2026-04-20", "last": "2026-04-20"},
    ]

    run_query(
        """
        UNWIND $rows AS row
        MATCH (a:Person {sfzh: row.src})
        MATCH (b:Person {sfzh: row.tgt})
        MERGE (a)-[rel:CO_SUSPECT]-(b)
        SET rel.weight = row.weight,
            rel.case_count = row.weight,
            rel.case_types = row.case_types,
            rel.first_case_date = row.first,
            rel.last_case_date = row.last
        """,
        {"rows": rels},
    )
    print(f"[co_suspect] created {len(rels)} CO_SUSPECT relationships")


def verify():
    """Print summary of the graph."""
    counts = run_query("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS cnt
        ORDER BY cnt DESC
    """)
    rel_counts = run_query("""
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS cnt
        ORDER BY cnt DESC
    """)
    print("\n--- Graph Summary ---")
    for row in counts:
        print(f"  {row['label']}: {row['cnt']}")
    for row in rel_counts:
        print(f"  {row['rel_type']}: {row['cnt']}")


def main():
    print("=== Seeding Neo4j test data ===\n")
    verify_connectivity()
    print("[connected] Neo4j is reachable\n")

    clear_graph()
    create_constraints()
    seed_persons()
    seed_cases()
    seed_same_case_rels()
    seed_co_suspect_rels()

    print("\n--- Verifying ---")
    verify()
    print("\n[done] test data seeded successfully")
    print("\nYou can now:")
    print("  1. Open http://localhost:5001/graph to view the knowledge graph")
    print("  2. POST /api/graph/detect-gangs/run-now to run Louvain gang detection")
    print("  3. GET /api/graph/predict-links to find predicted co-offender links")


if __name__ == "__main__":
    main()
