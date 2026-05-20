import os


def get_age_filter_threshold() -> int:
    """Return case SQL age threshold; <= 0 means no age filter."""
    raw = os.getenv("WCNR_AGE_FILTER", "18").strip()
    try:
        return int(raw)
    except ValueError:
        return 18


def build_age_exists_clause(case_alias: str = "a", suspect_alias: str = "x") -> str:
    """Build a KingBase/PostgreSQL EXISTS clause for suspect age filtering."""
    threshold = get_age_filter_threshold()
    if threshold <= 0:
        return ""
    return f"""AND EXISTS (
              SELECT 1 FROM "ywdata"."zq_zfba_xyrxx" {suspect_alias}
              WHERE {suspect_alias}."ajxx_join_ajxx_ajbh" = {case_alias}."ajxx_ajbh"
                AND LENGTH({suspect_alias}."xyrxx_sfzh") = 18
                AND DATE_PART('year',
                      AGE(COALESCE({case_alias}."ajxx_fasj"::date, CURRENT_DATE),
                          TO_DATE(SUBSTR({suspect_alias}."xyrxx_sfzh", 7, 8), 'YYYYMMDD'))
                    ) < {threshold}
          )"""
