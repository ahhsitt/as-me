"""原则列表格式化辅助函数"""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..principle.models import Principle, PrincipleDimension


# 维度显示名称
DIMENSION_NAMES = {
    PrincipleDimension.WORLDVIEW: "世界观",
    PrincipleDimension.VALUES: "价值观",
    PrincipleDimension.DECISION_PATTERN: "决策模式",
    PrincipleDimension.DOMAIN_THOUGHT: "领域思想",
}


def format_principle_list(principles: List[Principle], verbose: bool = False) -> str:
    """格式化原则列表

    Args:
        principles: 原则列表
        verbose: 是否显示详细信息

    Returns:
        格式化后的字符串
    """
    if not principles:
        return "暂无原则"

    lines = []
    lines.append(f"共 {len(principles)} 条原则\n")

    for principle in principles:
        line = format_principle_brief(principle)
        lines.append(line)

        if verbose:
            lines.append(f"    创建: {_format_datetime(principle.created_at)}")
            lines.append(f"    更新: {_format_datetime(principle.updated_at)}")
            lines.append(f"    证据: {principle.evidence_count} 条")
            lines.append("")

    return "\n".join(lines)


def format_principle_brief(principle: Principle) -> str:
    """格式化单条原则（简要）

    Args:
        principle: 原则对象

    Returns:
        格式化后的字符串
    """
    dimension_name = DIMENSION_NAMES.get(principle.dimension, principle.dimension.value)
    confidence_pct = int(principle.confidence * 100)
    status = "✓" if principle.confirmed_by_user else " "
    active = "" if principle.active else " [停用]"

    return f"[{principle.id[:8]}] [{dimension_name}] [{status}] {principle.statement[:40]}... ({confidence_pct}%){active}"


def format_principle_detail(principle: Principle) -> str:
    """格式化单条原则（详细）

    Args:
        principle: 原则对象

    Returns:
        格式化后的字符串
    """
    dimension_name = DIMENSION_NAMES.get(principle.dimension, principle.dimension.value)
    confidence_pct = int(principle.confidence * 100)
    confirmed = "是" if principle.confirmed_by_user else "否"
    active = "是" if principle.active else "否"

    lines = [
        f"原则 ID: {principle.id}",
        f"维度: {dimension_name}",
        f"置信度: {confidence_pct}%",
        f"用户确认: {confirmed}",
        f"活跃状态: {active}",
        "",
        f"陈述:",
        f"  {principle.statement}",
        "",
        f"证据数量: {principle.evidence_count}",
        f"创建时间: {_format_datetime(principle.created_at)}",
        f"更新时间: {_format_datetime(principle.updated_at)}",
    ]

    return "\n".join(lines)


def format_principle_table(principles: List[Principle]) -> str:
    """格式化原则为表格

    Args:
        principles: 原则列表

    Returns:
        表格格式字符串
    """
    if not principles:
        return "暂无原则"

    # 表头
    lines = [
        "| ID | 维度 | 陈述 | 置信度 | 已确认 |",
        "|----|----|----|----|------|",
    ]

    for principle in principles:
        dimension_name = DIMENSION_NAMES.get(principle.dimension, principle.dimension.value)
        confidence_pct = int(principle.confidence * 100)
        confirmed = "✓" if principle.confirmed_by_user else ""
        statement = principle.statement[:25] + "..." if len(principle.statement) > 25 else principle.statement

        lines.append(f"| {principle.id[:8]} | {dimension_name} | {statement} | {confidence_pct}% | {confirmed} |")

    return "\n".join(lines)


def _format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
