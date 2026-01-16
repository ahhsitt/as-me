"""演化时间线格式化辅助函数"""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..principle.models import EvolutionEvent, EvolutionTrigger


# 触发类型显示名称
TRIGGER_NAMES = {
    EvolutionTrigger.NEW_EVIDENCE: "新证据",
    EvolutionTrigger.CONFLICTING_EVIDENCE: "冲突证据",
    EvolutionTrigger.USER_CONFIRMATION: "用户确认",
    EvolutionTrigger.USER_CORRECTION: "用户修正",
    EvolutionTrigger.TIME_DECAY: "时间衰减",
    EvolutionTrigger.AGGREGATION: "记忆聚合",
}


def format_evolution_list(events: List[EvolutionEvent], verbose: bool = False) -> str:
    """格式化演化事件列表

    Args:
        events: 演化事件列表
        verbose: 是否显示详细信息

    Returns:
        格式化后的字符串
    """
    if not events:
        return "暂无演化事件"

    lines = []
    lines.append(f"共 {len(events)} 条演化事件\n")

    for event in events:
        line = format_evolution_brief(event)
        lines.append(line)

        if verbose:
            lines.append(f"    原因: {event.reason}")
            if event.evidence_ids:
                lines.append(f"    证据: {len(event.evidence_ids)} 条")
            lines.append("")

    return "\n".join(lines)


def format_evolution_brief(event: EvolutionEvent) -> str:
    """格式化单条演化事件（简要）

    Args:
        event: 演化事件对象

    Returns:
        格式化后的字符串
    """
    trigger_name = TRIGGER_NAMES.get(event.trigger, event.trigger.value)
    prev_pct = int(event.previous_confidence * 100)
    new_pct = int(event.new_confidence * 100)

    # 置信度变化箭头
    if new_pct > prev_pct:
        change = f"↑ {prev_pct}% → {new_pct}%"
    elif new_pct < prev_pct:
        change = f"↓ {prev_pct}% → {new_pct}%"
    else:
        change = f"= {prev_pct}%"

    time_str = _format_datetime_short(event.timestamp)
    principle_short = event.principle_id[:8]

    return f"[{time_str}] [{principle_short}] [{trigger_name}] {change}"


def format_evolution_detail(event: EvolutionEvent) -> str:
    """格式化单条演化事件（详细）

    Args:
        event: 演化事件对象

    Returns:
        格式化后的字符串
    """
    trigger_name = TRIGGER_NAMES.get(event.trigger, event.trigger.value)
    prev_pct = int(event.previous_confidence * 100)
    new_pct = int(event.new_confidence * 100)

    lines = [
        f"事件 ID: {event.id}",
        f"原则 ID: {event.principle_id}",
        f"触发类型: {trigger_name}",
        f"置信度变化: {prev_pct}% → {new_pct}%",
        f"时间: {_format_datetime(event.timestamp)}",
        "",
        f"变化原因:",
        f"  {event.reason}",
    ]

    if event.evidence_ids:
        lines.append("")
        lines.append(f"相关证据 ({len(event.evidence_ids)} 条):")
        for eid in event.evidence_ids[:5]:
            lines.append(f"  - {eid}")
        if len(event.evidence_ids) > 5:
            lines.append(f"  ... 及其他 {len(event.evidence_ids) - 5} 条")

    return "\n".join(lines)


def format_evolution_timeline(events: List[EvolutionEvent], principle_id: str | None = None) -> str:
    """格式化演化时间线

    Args:
        events: 演化事件列表（按时间排序）
        principle_id: 可选，用于显示原则信息

    Returns:
        时间线格式字符串
    """
    if not events:
        return "暂无演化事件"

    lines = []

    if principle_id:
        lines.append(f"原则 {principle_id[:8]} 的演化时间线")
        lines.append("")

    lines.append("时间线:")
    lines.append("-" * 60)

    for event in events:
        trigger_name = TRIGGER_NAMES.get(event.trigger, event.trigger.value)
        prev_pct = int(event.previous_confidence * 100)
        new_pct = int(event.new_confidence * 100)
        time_str = _format_datetime(event.timestamp)

        lines.append(f"  {time_str}")
        lines.append(f"  │ {trigger_name}: {prev_pct}% → {new_pct}%")
        lines.append(f"  │ {event.reason}")
        lines.append("  │")

    lines.append("-" * 60)

    return "\n".join(lines)


def _format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_datetime_short(dt: datetime) -> str:
    """格式化日期时间（短格式）"""
    return dt.strftime("%m-%d %H:%M")
