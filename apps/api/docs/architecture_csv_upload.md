# Architecture: CSV/Excel Upload for Data Analysis Tool

**Task:** 12  
**Status:** Design  
**Author:** Architect  
**Date:** 2026-04-15

---

## 1. Overview

The data analysis tool in Jarvis PM currently accepts only a list of metric names as text parameters. The AI then generates an analysis without access to real data, which leads to hallucinated numbers and generic insights.

This document describes the architecture for adding CSV/Excel file upload support so that users can upload real datasets, which are parsed, summarized, and then fed into the AI context for grounded, data-driven analysis.

---

## 2. User Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  User selects   │────▶│  Frontend shows │────▶│  User clicks    │
│  "data" tool    │     │  file upload UI │     │  "Analyze"      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  AI returns     │◀────│  Backend parses │◀────│  Multipart      │
│  grounded       │     │  file + calls   │     │  POST to API    │
│  analysis       │     │  ai_service     │     │  /tools/data-analysis-upload
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Result panel   │
│  (charts + text)│
└─────────────────┘
```

### Detailed Steps

1. **File Selection** — User clicks "Upload CSV/Excel" in the ToolPanel for the "data" tool.
2. **Validation** — Frontend enforces file type (`.csv`, `.xlsx`) and size (max 5MB).
3. **Preview** — First 5 rows are rendered in a small table for user confirmation.
4. **Upload** — On "Analyze", the file is sent as `multipart/form-data` to `POST /api/v1/tools/data-analysis-upload` along with `project_id`.
5. **Parsing** — Backend validates the file (magic numbers + extension), parses it into a pandas DataFrame (or stdlib equivalent), and infers schema.
6. **Summarization** — Backend generates a compact data summary (column types, basic stats, sample rows) to stay within AI token budgets.
7. **AI Analysis** — The summary is injected into the prompt and sent to `ai_service.chat()`.
8. **Response** — AI returns a structured analysis (text + optional chart suggestions). The backend also returns the inferred schema so the frontend can render a quick data preview.
9. **Cleanup** — The temporary file is deleted immediately after parsing (Phase 1) or retained briefly with auto-cleanup (Phase 2).

---

## 3. Frontend Changes

### 3.1 Location

The file upload UI is added inside:

```
apps/web/src/app/workspace/page.tsx
```

Specifically within the `ToolPanel` component that renders controls for the active tool. When `activeTool === "data"`, render the new `DataUploadPanel`.

### 3.2 New Component: `DataUploadPanel`

```tsx
// apps/web/src/components/tools/DataUploadPanel.tsx
"use client";

import { useState, useCallback } from "react";

interface DataUploadPanelProps {
  projectId: string;
  onAnalyze: (result: AnalysisResult) => void;
}

export function DataUploadPanel({ projectId, onAnalyze }: DataUploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Record<string, string>[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    // Validation
    const allowedTypes = [
      "text/csv",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ];
    const allowedExtensions = [".csv", ".xlsx"];
    const isValidType = allowedTypes.includes(selected.type);
    const isValidExt = allowedExtensions.some((ext) =>
      selected.name.toLowerCase().endsWith(ext)
    );

    if (!isValidType && !isValidExt) {
      alert("Only .csv and .xlsx files are allowed.");
      return;
    }

    if (selected.size > 5 * 1024 * 1024) {
      alert("File size must be under 5MB.");
      return;
    }

    setFile(selected);

    // Local preview: first 5 rows (CSV only for preview; Excel can be skipped or use a lightweight lib)
    const rows = await extractPreviewRows(selected, 5);
    setPreview(rows);
  }, []);

  const handleAnalyze = async () => {
    if (!file) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", projectId);

    const res = await fetch("/api/v1/tools/data-analysis-upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setIsUploading(false);
    onAnalyze(data);
  };

  return (
    <div className="space-y-4">
      <input
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFileChange}
      />
      {preview.length > 0 && (
        <div className="overflow-auto border rounded">
          <table className="text-sm">
            <thead>
              <tr>
                {Object.keys(preview[0]).map((k) => (
                  <th key={k} className="px-2 py-1 border-b">{k}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.map((row, i) => (
                <tr key={i}>
                  {Object.values(row).map((v, j) => (
                    <td key={j} className="px-2 py-1 border-b">{String(v)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button
        onClick={handleAnalyze}
        disabled={!file || isUploading}
        className="btn-primary"
      >
        {isUploading ? "Analyzing..." : "Analyze Data"}
      </button>
    </div>
  );
}
```

### 3.3 File Restrictions

| Constraint | Value | Enforcement |
|------------|-------|-------------|
| Extensions | `.csv`, `.xlsx` | `accept` attribute + JS check |
| MIME types | `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | JS check |
| Max size | 5 MB | JS check before upload |
| Preview rows | 5 | Parsed locally for CSV; for Excel, show filename + sheet count only in Phase 1 |

---

## 4. Backend API Design

### 4.1 New Endpoint

```http
POST /api/v1/tools/data-analysis-upload
Content-Type: multipart/form-data
```

#### Request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | `.csv` or `.xlsx`, max 5MB |
| `project_id` | string | Yes | Project context for the analysis |

#### Response (200 OK)

```json
{
  "success": true,
  "data": {
    "analysis": "string (markdown)",
    "schema": {
      "columns": [
        { "name": "revenue", "type": "numeric", "sample": [100, 200] },
        { "name": "date", "type": "datetime", "sample": ["2024-01-01"] }
      ],
      "row_count": 1200
    },
    "preview_rows": [
      { "revenue": "100", "date": "2024-01-01" }
    ]
  }
}
```

### 4.2 Router Registration

```python
# apps/api/src/routers/tools.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.services.data_analysis_upload_service import analyze_uploaded_data

router = APIRouter(prefix="/tools", tags=["tools"])

@router.post("/data-analysis-upload")
async def data_analysis_upload(
    file: UploadFile = File(...),
    project_id: str = Form(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    result = await analyze_uploaded_data(file, project_id)
    return {"success": True, "data": result}
```

### 4.3 Service: `data_analysis_upload_service.py`

```python
# apps/api/src/services/data_analysis_upload_service.py

import os
import uuid
import shutil
from typing import Any
from fastapi import UploadFile

from src.services.ai_service import ai_service
from src.utils.file_parser import parse_uploaded_file, DataFrameSummary

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/jarvis-uploads")
MAX_ROWS = int(os.environ.get("DATA_ANALYSIS_MAX_ROWS", "10_000"))

async def analyze_uploaded_file(file: UploadFile, project_id: str) -> dict[str, Any]:
    # 1. Validate magic numbers / extension
    ext = _validate_file(file)

    # 2. Save to temp storage
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 3. Parse into summary
        summary = parse_uploaded_file(temp_path, ext, max_rows=MAX_ROWS)

        # 4. Build AI prompt with compact context
        prompt = _build_data_analysis_prompt(summary, project_id)

        # 5. Call AI
        analysis = await ai_service.chat(
            messages=[{"role": "user", "content": prompt}],
            project_id=project_id,
        )

        return {
            "analysis": analysis,
            "schema": summary.schema_dict(),
            "preview_rows": summary.head_dicts(5),
        }
    finally:
        # 6. Cleanup
        os.remove(temp_path)


def _validate_file(file: UploadFile) -> str:
    filename = file.filename or ""
    lower = filename.lower()
    if lower.endswith(".csv"):
        return ".csv"
    if lower.endswith(".xlsx"):
        return ".xlsx"
    raise ValueError("Invalid file type. Only .csv and .xlsx are supported.")


def _build_data_analysis_prompt(summary: DataFrameSummary, project_id: str) -> str:
    return f"""You are a data analyst. Analyze the following dataset and provide insights.

Project ID: {project_id}

Dataset Schema:
{summary.schema_text()}

Summary Statistics:
{summary.stats_text()}

Sample Rows (first {len(summary.sample_rows)} rows):
{summary.sample_text()}

Instructions:
- Identify trends, anomalies, and key metrics.
- Suggest 2-3 actionable recommendations.
- Return the response in Markdown.
"""
```

### 4.4 File Parser Module

#### Phase 1 (CSV only, stdlib, in-memory)

```python
# apps/api/src/utils/file_parser.py

import csv
import io
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
        return str(self.sample_rows)


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
    # Simple heuristic
    numeric_count = 0
    for v in values:
        try:
            float(str(v).replace(",", ""))
            numeric_count += 1
        except ValueError:
            pass
    if numeric_count / len(values) > 0.8:
        return "numeric"
    return "string"


def _compute_stats(columns: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    stats = {}
    for col in columns:
        name = col["name"]
        if col["type"] != "numeric":
            continue
        nums = []
        for r in rows:
            try:
                nums.append(float(str(r.get(name)).replace(",", "")))
            except (ValueError, TypeError):
                pass
        if nums:
            stats[name] = {
                "min": round(min(nums), 4),
                "max": round(max(nums), 4),
                "mean": round(sum(nums) / len(nums), 4),
            }
    return stats
```

#### Phase 2 (Excel support, pandas)

```python
def parse_uploaded_file(path: str, ext: str, max_rows: int = 10_000) -> DataFrameSummary:
    import pandas as pd

    if ext == ".csv":
        df = pd.read_csv(path, nrows=max_rows)
    elif ext == ".xlsx":
        df = pd.read_excel(path, nrows=max_rows, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type")

    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        inferred = "numeric" if dtype.startswith(("int", "float")) else "string"
        if "datetime" in dtype:
            inferred = "datetime"
        columns.append({
            "name": str(col),
            "type": inferred,
            "sample": df[col].dropna().head(3).astype(str).tolist(),
        })

    stats = {}
    for col in df.select_dtypes(include="number").columns:
        stats[str(col)] = {
            "min": round(float(df[col].min()), 4),
            "max": round(float(df[col].max()), 4),
            "mean": round(float(df[col].mean()), 4),
        }

    return DataFrameSummary(
        columns=columns,
        row_count=len(df),
        sample_rows=df.head(50).fillna("").to_dict(orient="records"),
        stats=stats,
    )
```

---

## 5. AI Context Integration

### 5.1 Token Budget Strategy

Raw datasets can easily exceed LLM context windows. We use a **three-tier summarization strategy**:

| Tier | Content | When to Use |
|------|---------|-------------|
| **Schema + Stats** | Column names, types, summary stats (min/max/mean) | Default for all files |
| **Schema + Stats + Sample** | Above + first 10-20 rows | Small files (< 50 rows) |
| **Truncated Full Data** | First N rows where N is calculated from token budget | Explicit user request for row-level analysis |

### 5.2 Token Estimation

Assume ~4 tokens per English word/cell. For a dataset with 10 columns:

- 10 rows ≈ 400 tokens
- 100 rows ≈ 4,000 tokens
- 1,000 rows ≈ 40,000 tokens

**Budget rule:**
- Reserve 2,000 tokens for schema + stats.
- Reserve 4,000 tokens for sample rows.
- If the dataset exceeds this, truncate sample rows or omit them entirely.

### 5.3 Prompt Construction

The `data_analysis_upload_service` builds a structured prompt:

```text
Dataset Schema:
- revenue (numeric)
- date (datetime)
- region (string)

Summary Statistics:
revenue: min=100.0, max=5000.0, mean=1240.5

Sample Rows (first 10 rows):
[{"revenue": 100, "date": "2024-01-01", "region": "North"}, ...]

Instructions:
- Identify trends, anomalies, and key metrics.
- Suggest 2-3 actionable recommendations.
- Return the response in Markdown.
```

This compact format keeps the context small while giving the AI enough structure to reason about the data.

---

## 6. Security & Privacy

### 6.1 File Validation

| Check | Implementation |
|-------|----------------|
| Extension whitelist | `.csv`, `.xlsx` only |
| MIME type check | `text/csv` or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| Magic number check | Read first 4 bytes: CSV starts with readable text; XLSX starts with `PK\x03\x04` (ZIP signature) |

```python
def _validate_magic_numbers(path: str, ext: str) -> bool:
    with open(path, "rb") as f:
        header = f.read(4)
    if ext == ".csv":
        # CSV should be mostly printable text; allow common BOMs
        return header[:3] == b"\xef\xbb\xbf" or all(b >= 32 and b < 127 for b in header)
    if ext == ".xlsx":
        return header == b"PK\x03\x04"
    return False
```

### 6.2 Row Count & Size Limits

| Limit | Value | Purpose |
|-------|-------|---------|
| File size | 5 MB | Prevent network DoS |
| Parsed rows | 10,000 | Prevent memory/CPU DoS |
| Cell length | 1,000 chars | Prevent pathological CSV cells |

### 6.3 Data Retention Policy

- **Phase 1:** Files are deleted immediately after parsing (`finally` block in service).
- **Phase 2:** If upload history is persisted, files are stored in an `uploads/` directory and auto-deleted after 24 hours via a background Celery/scheduler task.
- No raw user data is ever logged to application logs; only schema metadata and row counts are logged.

---

## 7. Implementation Phases

### Phase 1: CSV Only, Minimal Footprint

**Goal:** Ship file upload for CSV with zero new heavy dependencies.

**Deliverables:**
1. Frontend `DataUploadPanel` with file picker, validation, and 5-row preview.
2. Backend endpoint `POST /api/v1/tools/data-analysis-upload`.
3. Stdlib `csv` parser (`file_parser.py`) — no pandas, no openpyxl.
4. In-memory processing with immediate temp file deletion.
5. AI prompt using schema + stats + up to 20 sample rows.

**Dependencies:** None (uses Python stdlib).

### Phase 2: Excel + Pandas + Upload History

**Goal:** Add Excel support and optional upload history for repeat analysis.

**Deliverables:**
1. Add `pandas` and `openpyxl` to `requirements.txt`.
2. Extend `file_parser.py` to handle `.xlsx` via `pd.read_excel()`.
3. Add `UploadRecord` database model (SQLAlchemy):
   - `id`, `project_id`, `filename`, `stored_path`, `created_at`, `deleted_at`
4. Store files in `uploads/` with a scheduled cleanup job (APScheduler / Celery beat) to hard-delete after 24h.
5. Allow users to re-run analysis on a previously uploaded file without re-uploading.

**Dependencies:** `pandas>=2.0`, `openpyxl>=3.1`.

---

## 8. Error Handling

| Scenario | Frontend Behavior | Backend Behavior |
|----------|-------------------|------------------|
| Invalid file type | Alert + reject before upload | 400 Bad Request |
| File too large | Alert + reject before upload | 413 Payload Too Large |
| Corrupted CSV/Excel | Show generic parse error | 422 Unprocessable Entity with detail |
| Empty file | Show "No data found" | 422 with message |
| AI service failure | Show retry button | 500, log error, do not leak stack trace |

---

## 9. Open Questions

1. Should we support multiple sheet selection for Excel files in Phase 2, or default to the first sheet?
2. Do we need to support Chinese/GBK-encoded CSVs? If yes, add `chardet` for encoding detection in Phase 2.
3. Should the AI response include structured chart config (e.g., Vega-Lite JSON) for frontend rendering?

---

## 10. Appendix: Quick Reference

### API Contract

```http
POST /api/v1/tools/data-analysis-upload
Content-Type: multipart/form-data

file=<binary>
project_id=<string>
```

### Key Files to Create/Modify

| File | Action |
|------|--------|
| `apps/web/src/components/tools/DataUploadPanel.tsx` | Create |
| `apps/web/src/app/workspace/page.tsx` | Modify (mount `DataUploadPanel`) |
| `apps/api/src/routers/tools.py` | Modify (add endpoint) |
| `apps/api/src/services/data_analysis_upload_service.py` | Create |
| `apps/api/src/utils/file_parser.py` | Create |
| `apps/api/requirements.txt` | Modify (Phase 2 only) |
