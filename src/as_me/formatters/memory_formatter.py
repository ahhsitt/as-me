"""记忆列表格式化辅助函数"""

from __future__ import annotations

from datetime import datetime
from typing import List

from ..memory.models import MemoryAtom, MemoryTier, MemoryType


# 类型显示名称
TYPE_NAMES = {
    MemoryType.TECH_PREFERENCE: "技术偏好",
    MemoryType.THINKING_PATTERN: "思维模式",
    MemoryType.BEHAVIOR_HABIT: "行为习惯",
    MemoryType.LANGUAGE_STYLE: "语言风格",
}

# 层级显示名称
TIER_NAMES = {
    MemoryTier.SHORT_TERM: "短期",
    MemoryTier.WORKING: "工作",
    MemoryTier.LONG_TERM: "长期",
}


def format_memory_list(memories: List[MemoryAtom], verbose: bool = False) -> str:
    """格式化记忆列表

    Args:
        memories: 记忆列表
        verbose: 是否显示详细信息

    Returns:
        格式化后的字符串
    """
    if not memories:
        return "暂无记忆"

    lines = []
    lines.append(f"共 {len(memories)} 条记忆\n")

    for memory in memories:
        line = format_memory_brief(memory)
        lines.append(line)

        if verbose:
            lines.append(f"    创建: {_format_datetime(memory.created_at)}")
            lines.append(f"    触发: {memory.trigger_count} 次")
            if memory.tags:
                lines.append(f"    标签: {', '.join(memory.tags)}")
            lines.append("")

    return "\n".join(lines)


def format_memory_brief(memory: MemoryAtom) -> str:
    """格式化单条记忆（简要）

    Args:
        memory: 记忆原子

    Returns:
        格式化后的字符串
    """
    type_name = TYPE_NAMES.get(memory.type, memory.type.value)
    tier_name = TIER_NAMES.get(memory.tier, memory.tier.value)
    confidence_pct = int(memory.confidence * 100)

    return f"[{memory.id[:8]}] [{type_name}] [{tier_name}] {memory.content[:50]}... ({confidence_pct}%)"


def format_memory_detail(memory: MemoryAtom) -> str:
    """格式化单条记忆（详细）

    Args:
        memory: 记忆原子

    Returns:
        格式化后的字符串
    """
    type_name = TYPE_NAMES.get(memory.type, memory.type.value)
    tier_name = TIER_NAMES.get(memory.tier, memory.tier.value)
    confidence_pct = int(memory.confidence * 100)

    lines = [
        f"记忆 ID: {memory.id}",
        f"类型: {type_name}",
        f"层级: {tier_name}",
        f"置信度: {confidence_pct}%",
        "",
        f"内容:",
        f"  {memory.content}",
        "",
        f"来源会话: {memory.source_session_id}",
        f"创建时间: {_format_datetime(memory.created_at)}",
        f"最后触发: {_format_datetime(memory.last_triggered_at)}",
        f"触发次数: {memory.trigger_count}",
    ]

    if memory.tags:
        lines.append(f"标签: {', '.join(memory.tags)}")

    if memory.related_principle_id:
        lines.append(f"关联原则: {memory.related_principle_id}")

    return "\n".join(lines)


def format_memory_table(memories: List[MemoryAtom]) -> str:
    """格式化记忆为表格

    Args:
        memories: 记忆列表

    Returns:
        表格格式字符串
    """
    if not memories:
        return "暂无记忆"

    # 表头
    lines = [
        "| ID | 类型 | 层级 | 内容 | 置信度 |",
        "|----|----|----|----|------|",
    ]

    for memory in memories:
        type_name = TYPE_NAMES.get(memory.type, memory.type.value)
        tier_name = TIER_NAMES.get(memory.tier, memory.tier.value)
        confidence_pct = int(memory.confidence * 100)
        content = memory.content[:30] + "..." if len(memory.content) > 30 else memory.content

        lines.append(f"| {memory.id[:8]} | {type_name} | {tier_name} | {content} | {confidence_pct}% |")

    return "\n".join(lines)


def _format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
