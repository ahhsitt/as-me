"""轻量级索引管理

构建和维护索引文件，加速检索。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .json_store import read_json, write_json
from ..memory.models import MemoryType, MemoryTier


INDEX_FILE = "index.json"
TOP_CONFIDENCE_LIMIT = 100  # 保存前 100 个高置信度记忆 ID


class IndexManager:
    """轻量级索引管理器"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.index_path = base_path / INDEX_FILE

    def build_index(
        self,
        memory_ids_by_type: Dict[MemoryType, Set[str]] | None = None,
        memory_ids_by_tier: Dict[MemoryTier, Set[str]] | None = None,
        top_confidence_ids: List[str] | None = None,
        memory_count: int = 0,
        principle_count: int = 0,
    ) -> Dict:
        """构建索引结构

        Args:
            memory_ids_by_type: 按类型分组的记忆 ID
            memory_ids_by_tier: 按层级分组的记忆 ID
            top_confidence_ids: 高置信度记忆 ID 列表
            memory_count: 记忆总数
            principle_count: 原则总数

        Returns:
            索引字典
        """
        # 转换 Set 为 List 以便 JSON 序列化
        type_index = {}
        if memory_ids_by_type:
            for mem_type, ids in memory_ids_by_type.items():
                type_index[mem_type.value] = list(ids)

        tier_index = {}
        if memory_ids_by_tier:
            for tier, ids in memory_ids_by_tier.items():
                tier_index[tier.value] = list(ids)

        return {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "memory_count": memory_count,
            "principle_count": principle_count,
            "memory_ids_by_type": type_index,
            "memory_ids_by_tier": tier_index,
            "top_confidence_ids": (top_confidence_ids or [])[:TOP_CONFIDENCE_LIMIT],
        }

    def save_index(self, index: Dict) -> None:
        """保存索引"""
        write_json(self.index_path, index)

    def load_index(self) -> Optional[Dict]:
        """加载索引"""
        return read_json(self.index_path)

    def update_counts(self, memory_count: int, principle_count: int) -> None:
        """更新计数

        Args:
            memory_count: 记忆总数
            principle_count: 原则总数
        """
        index = self.load_index()
        if index is None:
            index = self.build_index(
                memory_count=memory_count,
                principle_count=principle_count,
            )
        else:
            index["memory_count"] = memory_count
            index["principle_count"] = principle_count
            index["updated_at"] = datetime.now().isoformat()

        self.save_index(index)

    def get_memory_count(self) -> int:
        """获取记忆总数"""
        index = self.load_index()
        return index.get("memory_count", 0) if index else 0

    def get_principle_count(self) -> int:
        """获取原则总数"""
        index = self.load_index()
        return index.get("principle_count", 0) if index else 0
