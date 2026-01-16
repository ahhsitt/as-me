"""记忆强化机制

当记忆被重复触发或与现有记忆模式匹配时，提升其置信度。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from .models import MemoryAtom, MemoryTier


# 触发增益基础值
BASE_TRIGGER_BOOST = 0.05

# 重复模式增益
PATTERN_MATCH_BOOST = 0.1

# 最大增益上限
MAX_BOOST_PER_TRIGGER = 0.15

# 触发间隔阈值（小时）- 太频繁的触发不会重复计算
MIN_TRIGGER_INTERVAL_HOURS = 1

# 层级升级阈值
TIER_UPGRADE_THRESHOLDS = {
    MemoryTier.SHORT_TERM: (0.6, 3),   # 置信度 >= 60% 且触发次数 >= 3
    MemoryTier.WORKING: (0.8, 7),       # 置信度 >= 80% 且触发次数 >= 7
}


class MemoryStrengthening:
    """记忆强化器

    负责在记忆被触发时提升其置信度和管理层级升级。
    """

    def __init__(
        self,
        base_boost: float = BASE_TRIGGER_BOOST,
        pattern_boost: float = PATTERN_MATCH_BOOST,
        max_boost: float = MAX_BOOST_PER_TRIGGER,
    ):
        """初始化强化器

        Args:
            base_boost: 基础触发增益
            pattern_boost: 模式匹配增益
            max_boost: 最大增益上限
        """
        self.base_boost = base_boost
        self.pattern_boost = pattern_boost
        self.max_boost = max_boost

    def trigger(
        self,
        memory: MemoryAtom,
        pattern_matched: bool = False,
        trigger_time: Optional[datetime] = None,
    ) -> MemoryAtom:
        """触发记忆强化

        Args:
            memory: 记忆原子
            pattern_matched: 是否匹配到重复模式
            trigger_time: 触发时间

        Returns:
            更新后的记忆
        """
        if trigger_time is None:
            trigger_time = datetime.now()

        # 检查触发间隔
        time_since_last = trigger_time - memory.last_triggered_at
        min_interval = timedelta(hours=MIN_TRIGGER_INTERVAL_HOURS)

        if time_since_last < min_interval:
            # 触发太频繁，不增加计数但更新时间
            memory.last_triggered_at = trigger_time
            return memory

        # 计算增益
        boost = self.base_boost
        if pattern_matched:
            boost += self.pattern_boost

        # 应用递减收益（触发次数越多，增益越小）
        diminishing_factor = 1.0 / (1.0 + memory.trigger_count * 0.1)
        boost *= diminishing_factor

        # 限制最大增益
        boost = min(boost, self.max_boost)

        # 更新记忆
        memory.confidence = min(1.0, memory.confidence + boost)
        memory.trigger_count += 1
        memory.last_triggered_at = trigger_time

        # 检查层级升级
        self._check_tier_upgrade(memory)

        return memory

    def _check_tier_upgrade(self, memory: MemoryAtom) -> None:
        """检查并执行层级升级

        Args:
            memory: 记忆原子
        """
        current_tier = memory.tier

        if current_tier == MemoryTier.LONG_TERM:
            # 已经是最高层级
            return

        if current_tier == MemoryTier.SHORT_TERM:
            threshold = TIER_UPGRADE_THRESHOLDS[MemoryTier.SHORT_TERM]
            if memory.confidence >= threshold[0] and memory.trigger_count >= threshold[1]:
                memory.tier = MemoryTier.WORKING

        elif current_tier == MemoryTier.WORKING:
            threshold = TIER_UPGRADE_THRESHOLDS[MemoryTier.WORKING]
            if memory.confidence >= threshold[0] and memory.trigger_count >= threshold[1]:
                memory.tier = MemoryTier.LONG_TERM

    def find_pattern_matches(
        self,
        memory: MemoryAtom,
        all_memories: List[MemoryAtom],
        similarity_threshold: float = 0.7,
    ) -> List[MemoryAtom]:
        """查找与给定记忆相似的其他记忆

        简单实现：基于类型和标签匹配

        Args:
            memory: 待匹配的记忆
            all_memories: 所有记忆列表
            similarity_threshold: 相似度阈值

        Returns:
            相似记忆列表
        """
        matches = []

        for other in all_memories:
            if other.id == memory.id:
                continue

            # 类型必须相同
            if other.type != memory.type:
                continue

            # 计算标签重叠度
            if memory.tags and other.tags:
                common_tags = set(memory.tags) & set(other.tags)
                all_tags = set(memory.tags) | set(other.tags)
                if all_tags:
                    tag_similarity = len(common_tags) / len(all_tags)
                    if tag_similarity >= similarity_threshold:
                        matches.append(other)

        return matches

    def strengthen_pattern(
        self,
        memories: List[MemoryAtom],
        trigger_time: Optional[datetime] = None,
    ) -> List[MemoryAtom]:
        """批量强化一组相似记忆

        Args:
            memories: 相似记忆列表
            trigger_time: 触发时间

        Returns:
            更新后的记忆列表
        """
        updated = []
        for memory in memories:
            self.trigger(memory, pattern_matched=True, trigger_time=trigger_time)
            updated.append(memory)
        return updated
