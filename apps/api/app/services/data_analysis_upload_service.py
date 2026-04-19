"""Data analysis upload service for CSV/Excel files."""

import os
import uuid
from typing import Any

from fastapi import UploadFile

from app.services.ai_service import ai_service
from app.utils.file_parser import (
    DataFrameSummary,
    parse_uploaded_file,
    validate_file,
    validate_magic_numbers,
)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/jarvis-uploads")
MAX_ROWS = int(os.environ.get("DATA_ANALYSIS_MAX_ROWS", "10000"))
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


async def analyze_uploaded_data(
    file: UploadFile,
    project_id: str,
) -> dict[str, Any]:
    """Analyze an uploaded data file and return AI-generated insights."""
    if not file.filename:
        raise ValueError("No file provided")

    ext = validate_file(file.filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

    try:
        # Stream the upload to disk while enforcing the size limit early
        _write_upload_limited(file, temp_path, MAX_FILE_SIZE)

        if not validate_magic_numbers(temp_path, ext):
            raise ValueError("File content does not match expected format for the extension")

        summary = parse_uploaded_file(temp_path, ext, max_rows=MAX_ROWS)

        if summary.row_count == 0:
            raise ValueError("No data rows found in the uploaded file")

        prompt = _build_data_analysis_prompt(summary, project_id)
        analysis = await ai_service.chat(prompt)

        return {
            "analysis": analysis,
            "schema": summary.schema_dict(),
            "preview_rows": summary.head_dicts(5),
            "markdown": analysis,
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _write_upload_limited(file: UploadFile, dest_path: str, max_size: int) -> None:
    """Write uploaded file to dest_path, aborting if max_size is exceeded.

    Also explicitly closes the upload stream when done.
    """
    written = 0
    chunk_size = 8192
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = file.file.read(chunk_size)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_size:
                    raise ValueError(
                        f"File too large. Max size is {max_size / 1024 / 1024}MB"
                    )
                out.write(chunk)
    finally:
        file.file.close()


def _build_data_analysis_prompt(summary: DataFrameSummary, project_id: str) -> str:
    return f"""你是一位数据分析师。请基于以下用户上传的真实数据集生成数据分析报告。

项目ID: {project_id}
数据集行数: {summary.row_count}

数据集Schema:
<user_data>
{summary.schema_text()}
</user_data>

摘要统计:
<user_data>
{summary.stats_text()}
</user_data>

样本数据（前20行）:
<user_data>
{summary.sample_text()}
</user_data>

要求：
1. 输出包含摘要(summary)、趋势(trends)、异常(anomalies)、建议(recommendations)
2. 使用 Markdown 格式
3. 基于上面提供的真实数据进行分析，禁止编造数据集中不存在的数字或趋势
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：基于用户上传数据
- 可信度等级：高
- 使用建议：可直接用于决策（但仍建议结合业务背景复核）
---"""
