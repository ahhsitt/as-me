"""记忆层级管理

实现记忆层级升级逻辑（短期 → 工作 → 长期）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple

from .confidence import apply_time_decay, should_delete_memory
from .models import MemoryAtom, MemoryTier
from .store import MemoryStore


@dataclass
class TierTransition:
    """层级转换记录"""
    memory_id: str
    from_tier: MemoryTier
    to_tier: MemoryTier | None  # None 表示删除
    reason: str


class TierManager:
    """记忆层级管理器

    负责记忆的层级升级和淡化删除。

    升级条件：
    - SHORT_TERM → WORKING: 3天内触发次数 >= 2 且 confidence >= 0.5
    - WORKING → LONG_TERM: 30天内触发次数 >= 5 且 confidence >= 0.7

    删除条件：
    - SHORT_TERM: confidence < 0.3 且超过 3 天未触发
    - WORKING: confidence < 0.2 且超过 14 天未触发
    - LONG_TERM: confidence < 0.1 且超过 90 天未触发
    """

    # 升级阈值
    UPGRADE_THRESHOLDS = {
        MemoryTier.SHORT_TERM: {
            "min_triggers": 2,
            "min_confidence": 0.5,
            "min_days": 3,
            "next_tier": MemoryTier.WORKING,
        },
        MemoryTier.WORKING: {
            "min_triggers": 5,
            "min_confidence": 0.7,
            "min_days": 30,
            "next_tier": MemoryTier.LONG_TERM,
        },
    }

    # 删除阈值
    DELETE_THRESHOLDS = {
        MemoryTier.SHORT_TERM: {
            "max_confidence": 0.3,
            "inactive_days": 3,
        },
        MemoryTier.WORKING: {
            "max_confidence": 0.2,
            "inactive_days": 14,
        },
        MemoryTier.LONG_TERM: {
            "max_confidence": 0.1,
            "inactive_days": 90,
        },
    }

    def __init__(self, store: MemoryStore, half_life_days: int = 30):
        """初始化管理器

        Args:
            store: 记忆存储
            half_life_days: 置信度衰减半衰期
        """
        self.store = store
        self.half_life_days = half_life_days

    def process_all(self) -> List[TierTransition]:
        """处理所有记忆的层级变化

        Returns:
            层级变化记录列表
        """
        transitions = []

        # 处理每个层级
        for tier in MemoryTier:
            tier_transitions = self._process_tier(tier)
            transitions.extend(tier_transitions)

        return transitions

    def check_upgrade(self, memory: MemoryAtom) -> MemoryTier | None:
        """检查记忆是否可以升级

        Args:
            memory: 记忆原子

        Returns:
            目标层级，不升级时返回 None
        """
        threshold = self.UPGRADE_THRESHOLDS.get(memory.tier)
        if not threshold:
            # LONG_TERM 不能再升级
            return None

        # 检查时间条件
        days_since_creation = (datetime.now() - memory.created_at).days
        if days_since_creation < threshold["min_days"]:
            return None

        # 检查触发次数
        if memory.trigger_count < threshold["min_triggers"]:
            return None

        # 检查置信度（应用衰减后）
        decayed_confidence = apply_time_decay(memory, self.half_life_days)
        if decayed_confidence < threshold["min_confidence"]:
            return None

        return threshold["next_tier"]

    def check_delete(self, memory: MemoryAtom) -> bool:
        """检查记忆是否应该删除

        Args:
            memory: 记忆原子

        Returns:
            是否应该删除
        """
        threshold = self.DELETE_THRESHOLDS.get(memory.tier)
        if not threshold:
            return False

        # 检查置信度
        decayed_confidence = apply_time_decay(memory, self.half_life_days)
        if decayed_confidence >= threshold["max_confidence"]:
            return False

        # 检查不活跃时间
        days_inactive = (datetime.now() - memory.last_triggered_at).days
        if days_inactive < threshold["inactive_days"]:
            return False

        return True

    def upgrade(self, memory: MemoryAtom, target_tier: MemoryTier) -> MemoryAtom:
        """升级记忆层级

        Args:
            memory: 记忆原子
            target_tier: 目标层级

        Returns:
            升级后的记忆
        """
        old_tier = memory.tier
        memory.tier = target_tier

        # 更新存储（会自动处理跨层级移动）
        return self.store.update(memory)

    def _process_tier(self, tier: MemoryTier) -> List[TierTransition]:
        """处理指定层级的记忆

        Args:
            tier: 记忆层级

        Returns:
            层级变化记录列表
        """
        transitions = []
        memories = self.store.get_all().copy()

        # 过滤当前层级
        tier_memories = [m for m in memories if m.tier == tier]

        for memory in tier_memories:
            # 检查删除
            if self.check_delete(memory):
                self.store.delete(memory.id)
                transitions.append(TierTransition(
                    memory_id=memory.id,
                    from_tier=tier,
                    to_tier=None,
                    reason=f"置信度过低且超过 {self.DELETE_THRESHOLDS[tier]['inactive_days']} 天未触发"
                ))
                continue

            # 检查升级
            target_tier = self.check_upgrade(memory)
            if target_tier:
                self.upgrade(memory, target_tier)
                transitions.append(TierTransition(
                    memory_id=memory.id,
                    from_tier=tier,
                    to_tier=target_tier,
                    reason=f"满足升级条件：触发次数 {memory.trigger_count}，置信度 {memory.confidence:.2f}"
                ))

        return transitions


def batch_update_tiers(store: MemoryStore, half_life_days: int = 30) -> List[TierTransition]:
    """批量更新记忆层级

    便捷函数，用于定期任务。

    Args:
        store: 记忆存储
        half_life_days: 置信度衰减半衰期

    Returns:
        层级变化记录列表
    """
    manager = TierManager(store, half_life_days)
    return manager.process_all()
