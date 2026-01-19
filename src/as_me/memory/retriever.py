"""记忆检索器

检索相关记忆用于注入到新对话中。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .confidence import apply_time_decay
from .models import MemoryAtom, MemoryTier, MemoryType
from .store import MemoryStore, QueryOptions


@dataclass
class ScoredMemory:
    """带评分的记忆"""
    memory: MemoryAtom
    relevance_score: float


class MemoryRetriever:
    """记忆检索器

    检索最相关的记忆用于注入到新对话中。
    """

    # 层级权重：长期记忆更重要
    TIER_WEIGHTS = {
        MemoryTier.LONG_TERM: 1.0,
        MemoryTier.WORKING: 0.8,
        MemoryTier.SHORT_TERM: 0.5,
    }

    # 类型权重
    TYPE_WEIGHTS = {
        MemoryType.IDENTITY: 1.0,       # 身份背景最重要
        MemoryType.VALUE: 0.95,         # 价值信念
        MemoryType.THINKING: 0.9,       # 思维认知
        MemoryType.PREFERENCE: 0.8,     # 偏好习惯
        MemoryType.COMMUNICATION: 0.7,  # 沟通表达
    }

    def __init__(self, store: MemoryStore, half_life_days: int = 30):
        """初始化检索器

        Args:
            store: 记忆存储
            half_life_days: 置信度衰减半衰期
        """
        self.store = store
        self.half_life_days = half_life_days

    def retrieve_relevant(
        self,
        limit: int = 10,
        min_confidence: float = 0.3,
        context: Optional[str] = None
    ) -> List[ScoredMemory]:
        """检索相关记忆

        Args:
            limit: 返回数量上限
            min_confidence: 最低置信度阈值
            context: 上下文（可选，用于计算相关性）

        Returns:
            带评分的记忆列表
        """
        # 获取所有符合条件的记忆
        memories = self.store.get_all(QueryOptions(
            min_confidence=min_confidence,
            limit=limit * 3,  # 多取一些用于排序
        ))

        # 计算相关性评分
        scored = []
        for memory in memories:
            score = self._calculate_relevance(memory, context)
            if score > 0:
                scored.append(ScoredMemory(memory=memory, relevance_score=score))

        # 按评分排序
        scored.sort(key=lambda x: x.relevance_score, reverse=True)

        # 触发选中的记忆
        result = scored[:limit]
        for item in result:
            self.store.trigger(item.memory.id)

        return result

    def format_for_injection(
        self,
        memories: List[ScoredMemory],
        max_length: int = 2000
    ) -> str:
        """格式化记忆用于注入

        Args:
            memories: 带评分的记忆列表
            max_length: 最大字符数

        Returns:
            格式化后的文本
        """
        if not memories:
            return ""

        lines = ["<user-profile>", "以下是用户的已知特征和偏好：", ""]

        # 按类型分组
        by_type: dict[MemoryType, List[MemoryAtom]] = {}
        for item in memories:
            mem_type = item.memory.type
            if mem_type not in by_type:
                by_type[mem_type] = []
            by_type[mem_type].append(item.memory)

        # 类型显示名称
        type_names = {
            MemoryType.IDENTITY: "身份背景",
            MemoryType.VALUE: "价值信念",
            MemoryType.THINKING: "思维认知",
            MemoryType.PREFERENCE: "偏好习惯",
            MemoryType.COMMUNICATION: "沟通表达",
        }

        current_length = sum(len(line) for line in lines)

        for mem_type in [MemoryType.IDENTITY, MemoryType.VALUE,
                         MemoryType.THINKING, MemoryType.PREFERENCE,
                         MemoryType.COMMUNICATION]:
            type_memories = by_type.get(mem_type, [])
            if not type_memories:
                continue

            section_header = f"## {type_names.get(mem_type, mem_type.value)}"
            if current_length + len(section_header) + 2 > max_length:
                break

            lines.append(section_header)
            current_length += len(section_header) + 1

            for memory in type_memories:
                # 格式化单条记忆
                confidence_indicator = self._confidence_indicator(memory.confidence)
                memory_line = f"- {memory.content} {confidence_indicator}"

                if current_length + len(memory_line) + 1 > max_length:
                    lines.append("- ...")
                    break

                lines.append(memory_line)
                current_length += len(memory_line) + 1

            lines.append("")  # 空行分隔

        lines.append("</user-profile>")
        return "\n".join(lines)

    def _calculate_relevance(
        self,
        memory: MemoryAtom,
        context: Optional[str] = None
    ) -> float:
        """计算记忆的相关性评分

        综合考虑：
        1. 置信度（应用时间衰减）
        2. 层级权重
        3. 类型权重
        4. 触发频率

        Args:
            memory: 记忆原子
            context: 上下文（可选）

        Returns:
            相关性评分 (0-1)
        """
        # 基础分：衰减后的置信度
        decayed_confidence = apply_time_decay(memory, self.half_life_days)

        # 层级权重
        tier_weight = self.TIER_WEIGHTS.get(memory.tier, 0.5)

        # 类型权重
        type_weight = self.TYPE_WEIGHTS.get(memory.type, 0.5)

        # 触发频率加成（触发越多越重要，但有上限）
        trigger_bonus = min(0.2, memory.trigger_count * 0.02)

        # 综合评分
        score = decayed_confidence * tier_weight * type_weight + trigger_bonus

        # 上下文相关性（如果提供）
        if context:
            context_relevance = self._context_relevance(memory, context)
            score = score * 0.7 + context_relevance * 0.3

        return min(1.0, score)

    def _context_relevance(self, memory: MemoryAtom, context: str) -> float:
        """计算与上下文的相关性

        基于简单的关键词匹配。

        Args:
            memory: 记忆原子
            context: 上下文文本

        Returns:
            相关性分数 (0-1)
        """
        context_lower = context.lower()
        memory_words = set(memory.content.lower().split())
        memory_words.update(tag.lower() for tag in memory.tags)

        # 计算匹配的词数
        matches = sum(1 for word in memory_words if word in context_lower)

        if not memory_words:
            return 0.0

        return min(1.0, matches / len(memory_words))

    def _confidence_indicator(self, confidence: float) -> str:
        """生成置信度指示符

        Args:
            confidence: 置信度值

        Returns:
            置信度指示符字符串
        """
        if confidence >= 0.8:
            return "(高置信度)"
        elif confidence >= 0.6:
            return "(中等置信度)"
        elif confidence >= 0.4:
            return "(较低置信度)"
        else:
            return ""
