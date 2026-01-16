"""置信度计算

实现基于证据数量、一致性和时间衰减的复合算法。
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List

from .models import MemoryAtom


def calculate_confidence(
    base_confidence: float,
    matching_evidence_count: int,
    total_evidence_count: int,
    last_triggered_at: datetime,
    half_life_days: int = 30
) -> float:
    """计算综合置信度

    综合考虑：
    1. 基础置信度（初始提取的置信度）
    2. 一致性因子（相同偏好出现次数 / 总样本数）
    3. 时效因子（基于最后触发时间的衰减）

    Args:
        base_confidence: 基础置信度 (0-1)
        matching_evidence_count: 匹配的证据数量
        total_evidence_count: 总证据数量
        last_triggered_at: 最后触发时间
        half_life_days: 半衰期天数

    Returns:
        综合置信度 (0-1)
    """
    # 一致性因子：相同偏好出现次数 / 总样本数
    consistency_factor = matching_evidence_count / max(total_evidence_count, 1)

    # 时效因子：基于最后触发时间的指数衰减
    days_since_last_trigger = (datetime.now() - last_triggered_at).days
    recency_factor = math.exp(-0.693 * days_since_last_trigger / half_life_days)  # ln(2) ≈ 0.693

    return base_confidence * consistency_factor * recency_factor


def apply_time_decay(memory: MemoryAtom, half_life_days: int = 30) -> float:
    """应用时间衰减

    Args:
        memory: 记忆原子
        half_life_days: 半衰期天数

    Returns:
        衰减后的置信度
    """
    days_since_trigger = (datetime.now() - memory.last_triggered_at).days
    decay_factor = math.exp(-0.693 * days_since_trigger / half_life_days)
    return memory.confidence * decay_factor


def calculate_strengthening(
    current_confidence: float,
    repeat_count: int,
    max_confidence: float = 0.95
) -> float:
    """计算记忆强化后的置信度

    当相同偏好被多次观察到时，增强置信度。

    Args:
        current_confidence: 当前置信度
        repeat_count: 重复观察次数
        max_confidence: 最大置信度上限

    Returns:
        强化后的置信度
    """
    # 使用递减增量模型：每次强化的增量递减
    # new = old + (max - old) * factor
    factor = 0.2  # 每次强化增加剩余差距的 20%

    new_confidence = current_confidence
    for _ in range(repeat_count):
        increment = (max_confidence - new_confidence) * factor
        new_confidence = min(max_confidence, new_confidence + increment)

    return new_confidence


def should_delete_memory(memory: MemoryAtom, half_life_days: int = 30) -> bool:
    """判断记忆是否应该被删除

    基于记忆层级的删除阈值：
    - SHORT_TERM: confidence < 0.3
    - WORKING: confidence < 0.2
    - LONG_TERM: confidence < 0.1

    Args:
        memory: 记忆原子
        half_life_days: 半衰期天数

    Returns:
        是否应该删除
    """
    from .models import MemoryTier

    # 计算衰减后的置信度
    decayed_confidence = apply_time_decay(memory, half_life_days)

    # 各层级的删除阈值
    thresholds = {
        MemoryTier.SHORT_TERM: 0.3,
        MemoryTier.WORKING: 0.2,
        MemoryTier.LONG_TERM: 0.1,
    }

    threshold = thresholds.get(memory.tier, 0.3)
    return decayed_confidence < threshold


def find_similar_memories(
    target: MemoryAtom,
    candidates: List[MemoryAtom],
    similarity_threshold: float = 0.8
) -> List[MemoryAtom]:
    """查找相似记忆

    基于简单的文本匹配查找相似记忆。

    Args:
        target: 目标记忆
        candidates: 候选记忆列表
        similarity_threshold: 相似度阈值

    Returns:
        相似记忆列表
    """
    similar = []

    target_words = set(target.content.lower().split())

    for candidate in candidates:
        if candidate.id == target.id:
            continue
        if candidate.type != target.type:
            continue

        # 计算 Jaccard 相似度
        candidate_words = set(candidate.content.lower().split())
        intersection = target_words & candidate_words
        union = target_words | candidate_words

        if union:
            similarity = len(intersection) / len(union)
            if similarity >= similarity_threshold:
                similar.append(candidate)

    return similar
