from __future__ import annotations

import json
import re
from typing import Any


def extract_json_payload(text: str) -> Any:
    """
    从文本中提取 JSON，支持：
    1. 纯 JSON
    2. Markdown 代码块包裹的 JSON (```json ... ```)
    3. 文本中嵌入的 JSON
    """
    # 先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 markdown 代码块中的 JSON
    # 匹配 ```json ... ``` 或 ``` ... ```
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)

    if matches:
        # 使用第一个代码块
        json_text = matches[0].strip()
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    # 尝试查找 JSON 对象或数组
    # 优先查找数组 []
    array_start = text.find("[")
    array_end = text.rfind("]")

    if array_start != -1 and array_end != -1 and array_end > array_start:
        try:
            candidate = text[array_start : array_end + 1]
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 查找对象 {}
    obj_start = text.find("{")
    obj_end = text.rfind("}")

    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        try:
            candidate = text[obj_start : obj_end + 1]
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON payload found in model response. Text preview: {text[:200]}")
