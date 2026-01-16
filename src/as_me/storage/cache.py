"""热数据内存缓存

实现内存索引，加速记忆检索。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from ..memory.models import MemoryAtom, MemoryTier, MemoryType
from ..principle.models import Principle, PrincipleDimension


@dataclass
class MemoryCache:
    """热数据内存缓存"""

    # 数据存储
    memories: Dict[str, MemoryAtom] = field(default_factory=dict)
    principles: Dict[str, Principle] = field(default_factory=dict)

    # 索引结构（加速检索）
    memory_by_type: Dict[MemoryType, Set[str]] = field(default_factory=dict)
    memory_by_tier: Dict[MemoryTier, Set[str]] = field(default_factory=dict)
    memory_by_tag: Dict[str, Set[str]] = field(default_factory=dict)
    memory_by_confidence: List[str] = field(default_factory=list)  # 降序排列

    principle_by_dimension: Dict[PrincipleDimension, Set[str]] = field(default_factory=dict)
    principle_by_confidence: List[str] = field(default_factory=list)  # 降序排列
    confirmed_principles: Set[str] = field(default_factory=set)

    # 脏标记（延迟写入）
    dirty_memories: Set[str] = field(default_factory=set)
    dirty_principles: Set[str] = field(default_factory=set)

    def add_memory(self, memory: MemoryAtom) -> None:
        """添加记忆到缓存"""
        self.memories[memory.id] = memory
        self.dirty_memories.add(memory.id)

        # 更新类型索引
        if memory.type not in self.memory_by_type:
            self.memory_by_type[memory.type] = set()
        self.memory_by_type[memory.type].add(memory.id)

        # 更新层级索引
        if memory.tier not in self.memory_by_tier:
            self.memory_by_tier[memory.tier] = set()
        self.memory_by_tier[memory.tier].add(memory.id)

        # 更新标签索引
        for tag in memory.tags:
            if tag not in self.memory_by_tag:
                self.memory_by_tag[tag] = set()
            self.memory_by_tag[tag].add(memory.id)

        # 更新置信度排序
        self._update_confidence_order()

    def remove_memory(self, memory_id: str) -> None:
        """从缓存移除记忆"""
        memory = self.memories.pop(memory_id, None)
        if not memory:
            return

        # 清理索引
        if memory.type in self.memory_by_type:
            self.memory_by_type[memory.type].discard(memory_id)
        if memory.tier in self.memory_by_tier:
            self.memory_by_tier[memory.tier].discard(memory_id)
        for tag in memory.tags:
            if tag in self.memory_by_tag:
                self.memory_by_tag[tag].discard(memory_id)

        if memory_id in self.memory_by_confidence:
            self.memory_by_confidence.remove(memory_id)

        self.dirty_memories.discard(memory_id)

    def add_principle(self, principle: Principle) -> None:
        """添加原则到缓存"""
        self.principles[principle.id] = principle
        self.dirty_principles.add(principle.id)

        # 更新维度索引
        if principle.dimension not in self.principle_by_dimension:
            self.principle_by_dimension[principle.dimension] = set()
        self.principle_by_dimension[principle.dimension].add(principle.id)

        # 更新确认状态索引
        if principle.confirmed_by_user:
            self.confirmed_principles.add(principle.id)

        # 更新置信度排序
        self._update_principle_confidence_order()

    def remove_principle(self, principle_id: str) -> None:
        """从缓存移除原则"""
        principle = self.principles.pop(principle_id, None)
        if not principle:
            return

        # 清理索引
        if principle.dimension in self.principle_by_dimension:
            self.principle_by_dimension[principle.dimension].discard(principle_id)

        self.confirmed_principles.discard(principle_id)

        if principle_id in self.principle_by_confidence:
            self.principle_by_confidence.remove(principle_id)

        self.dirty_principles.discard(principle_id)

    def get_top_memories(
        self,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[MemoryAtom]:
        """快速获取置信度最高的记忆

        Args:
            limit: 返回数量上限
            min_confidence: 最低置信度阈值

        Returns:
            置信度最高的记忆列表
        """
        result = []
        for memory_id in self.memory_by_confidence:
            if len(result) >= limit:
                break
            memory = self.memories.get(memory_id)
            if memory and memory.confidence >= min_confidence:
                result.append(memory)
        return result

    def get_memories_by_type(self, memory_type: MemoryType) -> List[MemoryAtom]:
        """按类型获取记忆"""
        memory_ids = self.memory_by_type.get(memory_type, set())
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]

    def get_memories_by_tier(self, tier: MemoryTier) -> List[MemoryAtom]:
        """按层级获取记忆"""
        memory_ids = self.memory_by_tier.get(tier, set())
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]

    def get_memories_by_tag(self, tag: str) -> List[MemoryAtom]:
        """按标签获取记忆"""
        memory_ids = self.memory_by_tag.get(tag, set())
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]

    def get_active_principles(self) -> List[Principle]:
        """获取活跃原则（按置信度排序）"""
        result = []
        for principle_id in self.principle_by_confidence:
            principle = self.principles.get(principle_id)
            if principle and principle.active:
                result.append(principle)
        return result

    def clear_dirty_flags(self) -> None:
        """清除脏标记"""
        self.dirty_memories.clear()
        self.dirty_principles.clear()

    def _update_confidence_order(self) -> None:
        """更新记忆置信度排序"""
        self.memory_by_confidence = sorted(
            self.memories.keys(),
            key=lambda mid: self.memories[mid].confidence,
            reverse=True
        )

    def _update_principle_confidence_order(self) -> None:
        """更新原则置信度排序"""
        self.principle_by_confidence = sorted(
            self.principles.keys(),
            key=lambda pid: self.principles[pid].confidence,
            reverse=True
        )
