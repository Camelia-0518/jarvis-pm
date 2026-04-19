"""File parser utilities for CSV/Excel upload."""

import csv
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DataFrameSummary:
    columns: list[dict[str, Any]]
    row_count: int
    sample_rows: list[dict[str, Any]]
    stats: dict[str, dict[str, float]] = field(default_factory=dict)

    def schema_dict(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "row_count": self.row_count,
        }

    def head_dicts(self, n: int) -> list[dict[str, Any]]:
        return self.sample_rows[:n]

    def schema_text(self) -> str:
        lines = [f"- {c['name']} ({c['type']})" for c in self.columns]
        return "\n".join(lines)

    def stats_text(self) -> str:
        lines = []
        for col, s in self.stats.items():
            lines.append(f"{col}: min={s.get('min')}, max={s.get('max')}, mean={s.get('mean')}")
        return "\n".join(lines) if lines else "N/A"

    def sample_text(self) -> str:
        return str(self.sample_rows[:20])


def parse_uploaded_file(path: str, ext: str, max_rows: int = 10_000) -> DataFrameSummary:
    if ext == ".csv":
        return _parse_csv(path, max_rows)
    raise NotImplementedError("Excel support coming in Phase 2")


def _parse_csv(path: str, max_rows: int) -> DataFrameSummary:
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(row)

    columns = _infer_columns(headers, rows)
    stats = _compute_stats(columns, rows)
    return DataFrameSummary(
        columns=columns,
        row_count=len(rows),
        sample_rows=rows[:50],
        stats=stats,
    )


def _infer_columns(headers: list[str], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = []
    for h in headers:
        sample_vals = [r.get(h) for r in rows[:20] if r.get(h) is not None]
        inferred = _infer_type(sample_vals)
        columns.append({"name": h, "type": inferred, "sample": sample_vals[:3]})
    return columns


def _infer_type(values: list[Any]) -> str:
    if not values:
        return "unknown"

    cleaned = [str(v).strip() for v in values if v is not None and str(v).strip() != ""]
    if not cleaned:
        return "unknown"

    total = len(cleaned)
    bool_map = {"true", "false", "yes", "no", "y", "n", "1", "0", "on", "off"}
    bool_count = sum(1 for v in cleaned if v.lower() in bool_map)
    if bool_count / total > 0.8:
        return "boolean"

    numeric_count = 0
    int_count = 0
    for v in cleaned:
        num_str = _normalize_numeric(v)
        try:
            f = float(num_str)
            numeric_count += 1
            if f == int(f) and "." not in num_str:
                int_count += 1
        except ValueError:
            pass

    if numeric_count / total > 0.8:
        if int_count == numeric_count:
            return "integer"
        return "numeric"

    return "string"


def _normalize_numeric(value: str) -> str:
    """Strip common currency/percentage wrappers and thousands separators."""
    v = value.strip()
    # Remove common currency symbols
    for symbol in ("$", "¥", "€", "£", "₹", "%", " "):
        v = v.replace(symbol, "")
    # Remove thousands separators (commas between digits)
    # Keep decimal points
    parts = v.split(".")
    integer_part = parts[0].replace(",", "")
    if len(parts) == 2:
        return f"{integer_part}.{parts[1]}"
    return integer_part


def _compute_stats(columns: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    stats = {}
    for col in columns:
        name = col["name"]
        if col["type"] != "numeric":
            continue
        nums = []
        for r in rows:
            raw = r.get(name)
            if raw is None:
                continue
            try:
                nums.append(float(_normalize_numeric(str(raw))))
            except (ValueError, TypeError):
                pass
        if nums:
            stats[name] = {
                "min": round(min(nums), 4),
                "max": round(max(nums), 4),
                "mean": round(sum(nums) / len(nums), 4),
            }
    return stats


def validate_file(filename: str | None) -> str:
    if not filename:
        raise ValueError("No filename provided")
    lower = filename.lower()
    if lower.endswith(".csv"):
        return ".csv"
    if lower.endswith(".xlsx"):
        return ".xlsx"
    raise ValueError("Invalid file type. Only .csv and .xlsx are supported.")


def validate_magic_numbers(path: str, ext: str) -> bool:
    with open(path, "rb") as f:
        header = f.read(1024)
    if ext == ".csv":
        # Allow UTF-8 CSVs with or without BOM; reject binary files
        if b"\x00" in header:
            return False
        try:
            header.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    if ext == ".xlsx":
        return header[:4] == b"PK\x03\x04"
    return False
