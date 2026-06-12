"""JSON 工具函数

统一的 JSON 解析、修复和 extract-from-markdown 逻辑。
消除 skill_processor / skill_processor_enhanced / ai_service / prd_agent 中的重复实现。
"""

import json
import re
from typing import Dict, Any, Optional


def extract_json_from_text(text: str) -> str:
    """从 LLM 响应文本中提取 JSON 字符串。

    优先提取 ```json 代码块内容，否则提取 ``` 代码块内容，最后回退为原文。
    """
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        return json_match.group(1).strip()
    return text.strip()


def repair_truncated_json(raw: str) -> str:
    """尝试修复被截断的 JSON 字符串。

    1. 检测并截断不完整的字符串字面量
    2. 移除尾部逗号
    3. 补齐缺失的闭合括号/花括号（基于深度追踪，忽略字符串内部）
    """
    cleaned = raw.rstrip()

    # 1. 截断不完整的字符串
    last_safe_pos = -1
    i = 0
    in_string = False
    escape_next = False
    while i < len(cleaned):
        ch = cleaned[i]
        if escape_next:
            escape_next = False
            i += 1
            continue
        if ch == '\\':
            escape_next = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
            if not in_string:
                last_safe_pos = i
            i += 1
            continue
        i += 1

    if in_string and last_safe_pos >= 0:
        cleaned = cleaned[:last_safe_pos + 1]

    # 2. 去掉末尾的逗号
    cleaned = cleaned.rstrip().rstrip(',')

    # 3. 补齐缺失的闭合括号（忽略字符串内部）
    brace_depth = 0
    bracket_depth = 0
    in_str = False
    escape = False
    for ch in cleaned:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
            elif ch == '[':
                bracket_depth += 1
            elif ch == ']':
                bracket_depth -= 1

    cleaned += ']' * max(0, bracket_depth)
    cleaned += '}' * max(0, brace_depth)

    return cleaned


def parse_json_output(text: str) -> Dict[str, Any]:
    """从 LLM 响应中解析 JSON，自动处理 markdown 代码块和截断修复。

    Returns:
        解析后的 dict。如果所有修复都失败，返回 {"raw_response": text}。
    """
    json_str = extract_json_from_text(text)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            fixed = repair_truncated_json(json_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            return {"raw_response": text}
