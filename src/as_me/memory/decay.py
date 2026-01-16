"""记忆淡化机制

基于时间的置信度衰减，让长期未使用的记忆逐渐淡化。
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import List, Optional

from .models import MemoryAtom, MemoryTier


# 默认半衰期（天）
DEFAULT_HALF_LIFE_DAYS = 30

# 各层级的衰减系数（越高层级衰减越慢）
TIER_DECAY_FACTORS = {
    MemoryTier.SHORT_TERM: 1.0,   # 正常衰减
    MemoryTier.WORKING: 0.5,      # 衰减减半
    MemoryTier.LONG_TERM: 0.25,   # 衰减四分之一
}

# 置信度阈值（低于此值的记忆会被标记删除）
MIN_CONFIDENCE_THRESHOLDS = {
    MemoryTier.SHORT_TERM: 0.3,
    MemoryTier.WORKING: 0.2,
    MemoryTier.LONG_TERM: 0.1,
}


class MemoryDecay:
    """记忆淡化器

    根据时间计算记忆的置信度衰减。
    """

    def __init__(self, half_life_days: int = DEFAULT_HALF_LIFE_DAYS):
        """初始化淡化器

        Args:
            half_life_days: 半衰期天数
        """
        self.half_life_days = half_life_days

    def calculate_decay(
        self,
        memory: MemoryAtom,
        reference_time: Optional[datetime] = None,
    ) -> float:
        """计算记忆的衰减后置信度

        使用指数衰减公式: C(t) = C₀ * (1/2)^(t/T)
        其中 t 是距上次触发的时间，T 是半衰期

        Args:
            memory: 记忆原子
            reference_time: 参考时间，默认为当前时间

        Returns:
            衰减后的置信度
        """
        if reference_time is None:
            reference_time = datetime.now()

        # 计算时间差（天）
        time_diff = reference_time - memory.last_triggered_at
        days_elapsed = time_diff.total_seconds() / (24 * 3600)

        if days_elapsed <= 0:
            return memory.confidence

        # 获取层级衰减系数
        decay_factor = TIER_DECAY_FACTORS.get(memory.tier, 1.0)

        # 应用层级调整的半衰期
        adjusted_half_life = self.half_life_days / decay_factor

        # 指数衰减
        decay_ratio = math.pow(0.5, days_elapsed / adjusted_half_life)
        new_confidence = memory.confidence * decay_ratio

        return max(0.0, min(1.0, new_confidence))

    def apply_decay(
        self,
        memory: MemoryAtom,
        reference_time: Optional[datetime] = None,
    ) -> MemoryAtom:
        """应用衰减到记忆

        Args:
            memory: 记忆原子
            reference_time: 参考时间

        Returns:
            更新后的记忆（原对象被修改）
        """
        memory.confidence = self.calculate_decay(memory, reference_time)
        return memory

    def should_remove(self, memory: MemoryAtom) -> bool:
        """判断记忆是否应该被移除

        Args:
            memory: 记忆原子

        Returns:
            是否应该移除
        """
        threshold = MIN_CONFIDENCE_THRESHOLDS.get(memory.tier, 0.1)
        return memory.confidence < threshold

    def process_batch(
        self,
        memories: List[MemoryAtom],
        reference_time: Optional[datetime] = None,
    ) -> tuple[List[MemoryAtom], List[MemoryAtom]]:
        """批量处理记忆衰减

        Args:
            memories: 记忆列表
            reference_time: 参考时间

        Returns:
            (保留的记忆列表, 应删除的记忆列表)
        """
        to_keep = []
        to_remove = []

        for memory in memories:
            self.apply_decay(memory, reference_time)
            if self.should_remove(memory):
                to_remove.append(memory)
            else:
                to_keep.append(memory)

        return to_keep, to_remove

    def estimate_removal_date(
        self,
        memory: MemoryAtom,
        reference_time: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """估计记忆被移除的日期

        Args:
            memory: 记忆原子
            reference_time: 参考时间

        Returns:
            预计移除日期，如果记忆已被用户确认则返回 None
        """
        if reference_time is None:
            reference_time = datetime.now()

        threshold = MIN_CONFIDENCE_THRESHOLDS.get(memory.tier, 0.1)
        decay_factor = TIER_DECAY_FACTORS.get(memory.tier, 1.0)
        adjusted_half_life = self.half_life_days / decay_factor

        # 计算达到阈值需要的时间
        # threshold = confidence * (0.5)^(t/T)
        # t = T * log(threshold/confidence) / log(0.5)
        if memory.confidence <= threshold:
            return reference_time

        ratio = threshold / memory.confidence
        days_to_removal = adjusted_half_life * math.log(ratio) / math.log(0.5)

        return memory.last_triggered_at + timedelta(days=days_to_removal)
