from __future__ import annotations

import re

from app.anpr.rag.schema_registry import allowed_columns, allowed_tables


def validate_sql(sql: str) -> bool:
    if not sql:
        return False
    normalized = sql.strip().strip(";")
    if not re.match(r"(?is)^select\s", normalized):
        return False
    if re.search(r"(?is)\b(insert|update|delete|drop|alter|create|truncate)\b", normalized):
        return False
    alias_map: dict[str, str] = {}
    table_refs = re.findall(
        r"(?is)\bfrom\s+([a-zA-Z0-9_\.]+)(?:\s+as)?\s*([a-zA-Z0-9_]+)?|"
        r"\bjoin\s+([a-zA-Z0-9_\.]+)(?:\s+as)?\s*([a-zA-Z0-9_]+)?",
        normalized,
    )
    for group in table_refs:
        table, alias, join_table, join_alias = group
        for tbl, als in ((table, alias), (join_table, join_alias)):
            if not tbl:
                continue
            name = tbl.split(".")[-1].lower()
            if name not in allowed_tables():
                return False
            if als:
                alias_map[als.lower()] = name

    for table, column in re.findall(r"([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", normalized):
        table_name = table.lower()
        actual_table = alias_map.get(table_name, table_name)
        if actual_table in allowed_tables() and column.lower() not in allowed_columns(actual_table):
            return False

    return True


__all__ = ["validate_sql"]
