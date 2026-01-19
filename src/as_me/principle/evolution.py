"""演化追踪器

记录和查询原则的演化历史。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..storage import get_storage_path
from ..storage.json_store import read_json_gz, write_json_gz
from .models import EvolutionEvent, EvolutionTrigger


class EvolutionTracker:
    """演化追踪器

    负责记录和查询原则的演化历史。
    """

    EVOLUTION_FILE = "evolution/history.json"

    def __init__(self):
        """初始化演化追踪器"""
        self._file_path = get_storage_path(self.EVOLUTION_FILE)

    def record_event(
        self,
        principle_id: str,
        previous_confidence: float,
        new_confidence: float,
        trigger: EvolutionTrigger,
        reason: str,
        evidence_ids: Optional[List[str]] = None,
    ) -> EvolutionEvent:
        """记录演化事件

        Args:
            principle_id: 原则 ID
            previous_confidence: 之前的置信度
            new_confidence: 新的置信度
            trigger: 触发类型
            reason: 变化原因
            evidence_ids: 相关证据 ID 列表

        Returns:
            创建的演化事件
        """
        event = EvolutionEvent(
            principle_id=principle_id,
            previous_confidence=previous_confidence,
            new_confidence=new_confidence,
            trigger=trigger,
            reason=reason,
            evidence_ids=evidence_ids or [],
        )

        # 读取现有事件
        events = self._load_events()

        # 添加新事件
        events.append(event)

        # 保存
        self._save_events(events)

        return event

    def get_history(self, principle_id: str) -> List[EvolutionEvent]:
        """获取指定原则的演化历史

        Args:
            principle_id: 原则 ID

        Returns:
            演化事件列表（按时间正序）
        """
        events = self._load_events()
        principle_events = [e for e in events if e.principle_id == principle_id]
        return sorted(principle_events, key=lambda e: e.timestamp)

    def get_timeline(
        self,
        principle_id: Optional[str] = None,
        trigger: Optional[EvolutionTrigger] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[EvolutionEvent]:
        """获取演化时间线

        支持多种过滤条件。

        Args:
            principle_id: 可选，按原则 ID 过滤
            trigger: 可选，按触发类型过滤
            start_time: 可选，开始时间
            end_time: 可选，结束时间
            limit: 返回数量限制

        Returns:
            演化事件列表（按时间倒序）
        """
        events = self._load_events()

        # 应用过滤条件
        if principle_id:
            events = [e for e in events if e.principle_id == principle_id]

        if trigger:
            events = [e for e in events if e.trigger == trigger]

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        # 按时间倒序排序
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        # 限制数量
        return events[:limit]

    def get_all(self) -> List[EvolutionEvent]:
        """获取所有演化事件

        Returns:
            所有演化事件列表
        """
        return self._load_events()

    def _load_events(self) -> List[EvolutionEvent]:
        """加载演化事件"""
        data = read_json_gz(self._file_path)
        if not data:
            return []
        return [EvolutionEvent.model_validate(item) for item in data]

    def _save_events(self, events: List[EvolutionEvent]) -> None:
        """保存演化事件"""
        data = [event.model_dump(mode="json") for event in events]
        write_json_gz(self._file_path, data)
