def extract_region_code(zjhm: str) -> str | None:
    if not zjhm or len(zjhm) < 6:
        return None
    code = zjhm[:6]
    return code if code.isdigit() else None
