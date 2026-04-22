"""
Contract privacy redaction helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Set


@dataclass
class RedactionResult:
    text: str
    replacement_count: int


FIELD_PATTERNS = [
    r"(?:甲方|出租方|出租人)[^：:]*[：:]",
    r"(?:乙方|承租方|承租人)[^：:]*[：:]",
    r"(?:身份证号|身份证号码|证件号码)[^：:]*[：:]",
    r"(?:联系电话|联系方式|手机号|手机号码|电话)[^：:]*[：:]",
    r"(?:电子邮箱|邮箱|Email|EMAIL)[^：:]*[：:]",
    r"(?:联系地址|通讯地址|住址|房屋地址|地址)[^：:]*[：:]",
    r"(?:银行卡号|银行账号|开户账号|收款账号)[^：:]*[：:]",
    r"(?:甲方签字|乙方签字|出租方签字|承租方签字)[^：:]*[：:]",
]

COMPILED_FIELD_PATTERNS = [
    re.compile(pattern + r"[^，,\n\r]*") for pattern in FIELD_PATTERNS
]

# 正则模式
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ID_CARD_PATTERN = re.compile(r"(?<![0-9A-Za-z])\d{17}[0-9Xx](?![0-9A-Za-z])")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
BANK_CARD_PATTERN = re.compile(r"(?<!\d)\d{12,19}(?!\d)")

# 新增：统一社会信用代码（18位，由数字和大写字母组成）
CREDIT_CODE_PATTERN = re.compile(r"(?<![0-9A-Z])[0-9A-Z]{18}(?![0-9A-Z])")

# 新增：公司名称（仅在标签字段中提取，避免误伤）
COMPANY_NAME_PATTERN = re.compile(
    r"[\u4e00-\u9fa5]{2,}(?:有限公司|股份有限公司|科技有限公司|集团有限公司|责任有限公司)"
)


def redact_sensitive_contract_info(text: str) -> RedactionResult:
    """
    增强的脱敏函数（三阶段脱敏）

    阶段 1：正则模式脱敏（电话、身份证、邮箱、银行卡、信用代码）
    阶段 2：标签字段脱敏 + 提取敏感实体
    阶段 3：全文替换敏感实体
    """
    if not text.strip():
        return RedactionResult(text=text, replacement_count=0)

    replacement_count = 0
    redacted_text = text
    sensitive_entities: Set[str] = set()

    # ========== 阶段 1：正则模式脱敏（先执行，避免被后续阶段覆盖）==========
    # 手机号
    redacted_text, count = PHONE_PATTERN.subn("[已脱敏手机号]", redacted_text)
    replacement_count += count

    # 身份证号
    redacted_text, count = ID_CARD_PATTERN.subn("[已脱敏证件号]", redacted_text)
    replacement_count += count

    # 邮箱
    redacted_text, count = EMAIL_PATTERN.subn("[已脱敏邮箱]", redacted_text)
    replacement_count += count

    # 银行卡号
    redacted_text, count = BANK_CARD_PATTERN.subn("[已脱敏账号]", redacted_text)
    replacement_count += count

    # 统一社会信用代码
    redacted_text, count = CREDIT_CODE_PATTERN.subn("[已脱敏信用代码]", redacted_text)
    replacement_count += count

    # ========== 阶段 2：标签字段脱敏 + 提取敏感实体 ==========
    for pattern in COMPILED_FIELD_PATTERNS:
        for match in pattern.finditer(redacted_text):
            # 提取实体（去掉标签部分）
            entity = _extract_entity_from_match(match)
            if entity and len(entity) >= 2:  # 至少 2 个字符
                sensitive_entities.add(entity)

        # 替换标签字段
        redacted_text, count = pattern.subn(_replace_labeled_field, redacted_text)
        replacement_count += count

    # ========== 阶段 3：全文替换敏感实体 ==========
    for entity in sensitive_entities:
        if len(entity) >= 2:  # 避免替换单字
            # 跳过已经被阶段 1 处理的实体（手机号、身份证号、邮箱、银行卡、信用代码）
            if PHONE_PATTERN.fullmatch(entity):
                continue
            if ID_CARD_PATTERN.fullmatch(entity):
                continue
            if EMAIL_PATTERN.fullmatch(entity):
                continue
            if BANK_CARD_PATTERN.fullmatch(entity):
                continue
            if CREDIT_CODE_PATTERN.fullmatch(entity):
                continue

            # 统计出现次数
            occurrences = redacted_text.count(entity)
            if occurrences > 0:
                # 全文替换
                redacted_text = redacted_text.replace(entity, "[已脱敏]")
                replacement_count += occurrences

    return RedactionResult(
        text=redacted_text,
        replacement_count=replacement_count,
    )


def _extract_entity_from_match(match: re.Match[str]) -> str:
    """
    从正则匹配中提取实体（去掉标签部分）

    例如："甲方：杭州栖雷科技有限公司，统一社会信用代码：xxx" → "杭州栖雷科技有限公司"
    """
    value = match.group(0)
    # 使用 find 找第一个冒号，而不是 rfind 找最后一个
    colon_cn = value.find("：")
    colon_en = value.find(":")

    # 取第一个出现的冒号位置
    if colon_cn == -1 and colon_en == -1:
        return ""
    elif colon_cn == -1:
        separator_index = colon_en
    elif colon_en == -1:
        separator_index = colon_cn
    else:
        separator_index = min(colon_cn, colon_en)

    # 提取冒号后的内容
    entity = value[separator_index + 1:].strip()

    # 如果已经是脱敏标记，返回空字符串
    if entity.startswith("[已脱敏"):
        return ""

    # 先按逗号分割，只取第一部分（通常是姓名或公司名）
    if "，" in entity:
        entity = entity.split("，")[0].strip()
    elif "," in entity:
        entity = entity.split(",")[0].strip()

    # 再去除尾部的标点符号
    entity = entity.rstrip("，,、。.；;")

    return entity


def _replace_labeled_field(match: re.Match[str]) -> str:
    value = match.group(0)
    # 使用 find 找第一个冒号，而不是 rfind 找最后一个
    colon_cn = value.find("：")
    colon_en = value.find(":")

    # 取第一个出现的冒号位置
    if colon_cn == -1 and colon_en == -1:
        return value
    elif colon_cn == -1:
        separator_index = colon_en
    elif colon_en == -1:
        separator_index = colon_cn
    else:
        separator_index = min(colon_cn, colon_en)

    # 检查冒号后面是否已经是脱敏标记
    after_colon = value[separator_index + 1:].strip()
    if after_colon.startswith("[已脱敏"):
        # 已经被脱敏，不再替换
        return value

    return value[: separator_index + 1] + "[已脱敏]"
