"""记忆存储

实现记忆的持久化存储和查询。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..errors import AsmeError, ErrorCode
from ..storage.base import ensure_storage_dir, get_storage_path
from ..storage.json_store import read_json, write_json
from .models import MemoryAtom, MemoryTier, MemoryType


@dataclass
class QueryOptions:
    """查询选项"""
    limit: int = 100
    offset: int = 0
    min_confidence: float = 0.0
    tier: Optional[MemoryTier] = None
    memory_type: Optional[MemoryType] = None
    sort_by: str = "confidence"  # confidence, created_at, last_triggered_at
    sort_desc: bool = True


class MemoryStore:
    """记忆存储

    按层级存储记忆到不同的 JSON 文件:
    - short-term.json: 短期记忆
    - working.json: 工作记忆
    - long-term.json: 长期记忆
    """

    TIER_FILES = {
        MemoryTier.SHORT_TERM: "short-term.json",
        MemoryTier.WORKING: "working.json",
        MemoryTier.LONG_TERM: "long-term.json",
    }

    def __init__(self, storage_root: Path | None = None):
        """初始化存储

        Args:
            storage_root: 存储根目录，默认 ~/.as-me/
        """
        self.storage_root = storage_root or get_storage_path()
        self.memories_dir = self.storage_root / "memories"
        ensure_storage_dir(self.storage_root)

    def save(self, memory: MemoryAtom) -> MemoryAtom:
        """保存单个记忆

        Args:
            memory: 记忆原子

        Returns:
            保存后的记忆（可能有更新的时间戳）
        """
        memories = self._load_tier(memory.tier)

        # 检查是否已存在
        existing_idx = None
        for i, m in enumerate(memories):
            if m["id"] == memory.id:
                existing_idx = i
                break

        memory_dict = memory.model_dump(mode="json")

        if existing_idx is not None:
            memories[existing_idx] = memory_dict
        else:
            memories.append(memory_dict)

        self._save_tier(memory.tier, memories)
        return memory

    def save_batch(self, memories: List[MemoryAtom]) -> List[MemoryAtom]:
        """批量保存记忆

        按层级分组后批量写入，减少 I/O 操作。

        Args:
            memories: 记忆列表

        Returns:
            保存后的记忆列表
        """
        # 按层级分组
        by_tier: Dict[MemoryTier, List[MemoryAtom]] = {}
        for memory in memories:
            if memory.tier not in by_tier:
                by_tier[memory.tier] = []
            by_tier[memory.tier].append(memory)

        # 每个层级批量保存
        for tier, tier_memories in by_tier.items():
            existing = self._load_tier(tier)
            existing_ids = {m["id"] for m in existing}

            for memory in tier_memories:
                memory_dict = memory.model_dump(mode="json")
                if memory.id in existing_ids:
                    # 更新现有记忆
                    for i, m in enumerate(existing):
                        if m["id"] == memory.id:
                            existing[i] = memory_dict
                            break
                else:
                    existing.append(memory_dict)

            self._save_tier(tier, existing)

        return memories

    def get_by_id(self, memory_id: str) -> Optional[MemoryAtom]:
        """根据 ID 获取记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            记忆原子，不存在时返回 None
        """
        # 遍历所有层级查找
        for tier in MemoryTier:
            memories = self._load_tier(tier)
            for m in memories:
                if m["id"] == memory_id:
                    return MemoryAtom.model_validate(m)
        return None

    def get_all(self, options: QueryOptions | None = None) -> List[MemoryAtom]:
        """获取所有记忆

        Args:
            options: 查询选项

        Returns:
            符合条件的记忆列表
        """
        options = options or QueryOptions()

        # 决定要加载的层级
        tiers_to_load = [options.tier] if options.tier else list(MemoryTier)

        all_memories = []
        for tier in tiers_to_load:
            tier_data = self._load_tier(tier)
            for m in tier_data:
                memory = MemoryAtom.model_validate(m)

                # 应用过滤条件
                if memory.confidence < options.min_confidence:
                    continue
                if options.memory_type and memory.type != options.memory_type:
                    continue

                all_memories.append(memory)

        # 排序
        sort_key_map = {
            "confidence": lambda m: m.confidence,
            "created_at": lambda m: m.created_at,
            "last_triggered_at": lambda m: m.last_triggered_at,
        }
        sort_key = sort_key_map.get(options.sort_by, sort_key_map["confidence"])
        all_memories.sort(key=sort_key, reverse=options.sort_desc)

        # 分页
        start = options.offset
        end = start + options.limit
        return all_memories[start:end]

    def get_by_type(self, memory_type: MemoryType) -> List[MemoryAtom]:
        """按类型获取记忆

        Args:
            memory_type: 记忆类型

        Returns:
            指定类型的记忆列表
        """
        return self.get_all(QueryOptions(memory_type=memory_type))

    def update(self, memory: MemoryAtom) -> MemoryAtom:
        """更新记忆

        Args:
            memory: 更新后的记忆

        Returns:
            更新后的记忆

        Raises:
            AsmeError: 记忆不存在时
        """
        existing = self.get_by_id(memory.id)
        if not existing:
            raise AsmeError(
                ErrorCode.MEMORY_NOT_FOUND,
                f"记忆不存在: {memory.id}"
            )

        # 如果层级变化，需要从旧层级删除
        if existing.tier != memory.tier:
            self._remove_from_tier(existing.id, existing.tier)

        return self.save(memory)

    def delete(self, memory_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            是否成功删除
        """
        for tier in MemoryTier:
            if self._remove_from_tier(memory_id, tier):
                return True
        return False

    def trigger(self, memory_id: str) -> Optional[MemoryAtom]:
        """触发记忆（更新 last_triggered_at 和 trigger_count）

        Args:
            memory_id: 记忆 ID

        Returns:
            更新后的记忆，不存在时返回 None
        """
        memory = self.get_by_id(memory_id)
        if not memory:
            return None

        memory.last_triggered_at = datetime.now()
        memory.trigger_count += 1
        return self.save(memory)

    def count(self, tier: MemoryTier | None = None) -> int:
        """统计记忆数量

        Args:
            tier: 指定层级，为 None 时统计所有

        Returns:
            记忆数量
        """
        if tier:
            return len(self._load_tier(tier))

        total = 0
        for t in MemoryTier:
            total += len(self._load_tier(t))
        return total

    def _load_tier(self, tier: MemoryTier) -> List[Dict]:
        """加载指定层级的记忆"""
        file_path = self.memories_dir / self.TIER_FILES[tier]
        return read_json(file_path) or []

    def _save_tier(self, tier: MemoryTier, memories: List[Dict]) -> None:
        """保存指定层级的记忆"""
        file_path = self.memories_dir / self.TIER_FILES[tier]
        write_json(file_path, memories)

    def _remove_from_tier(self, memory_id: str, tier: MemoryTier) -> bool:
        """从指定层级移除记忆"""
        memories = self._load_tier(tier)
        original_len = len(memories)
        memories = [m for m in memories if m["id"] != memory_id]

        if len(memories) < original_len:
            self._save_tier(tier, memories)
            return True
        return False
