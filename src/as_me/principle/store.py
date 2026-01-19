"""原则存储

实现原则的持久化存储和查询。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..errors import AsmeError, ErrorCode
from ..storage.base import ensure_storage_dir, get_storage_path
from ..storage.json_store import read_json_gz, write_json_gz
from .models import EvolutionTrigger, Principle, PrincipleDimension


class PrincipleStore:
    """原则存储

    存储和管理内核原则。
    """

    PRINCIPLES_FILE = "principles/core.json"

    def __init__(self, storage_root: Path | None = None):
        """初始化存储

        Args:
            storage_root: 存储根目录，默认 ~/.as-me/
        """
        self.storage_root = storage_root or get_storage_path()
        self.principles_file = self.storage_root / self.PRINCIPLES_FILE
        ensure_storage_dir(self.storage_root)

    def save(self, principle: Principle) -> Principle:
        """保存原则

        Args:
            principle: 原则对象

        Returns:
            保存后的原则
        """
        principles = self._load_all()

        # 检查是否已存在
        existing_idx = None
        for i, p in enumerate(principles):
            if p["id"] == principle.id:
                existing_idx = i
                break

        principle_dict = principle.model_dump(mode="json")

        if existing_idx is not None:
            principles[existing_idx] = principle_dict
        else:
            principles.append(principle_dict)

        self._save_all(principles)
        return principle

    def get_by_id(self, principle_id: str) -> Optional[Principle]:
        """根据 ID 获取原则

        Args:
            principle_id: 原则 ID

        Returns:
            原则对象，不存在时返回 None
        """
        principles = self._load_all()
        for p in principles:
            if p["id"] == principle_id:
                return Principle.model_validate(p)
        return None

    def get_by_dimension(self, dimension: PrincipleDimension) -> List[Principle]:
        """按维度获取原则

        Args:
            dimension: 原则维度

        Returns:
            指定维度的原则列表
        """
        principles = self._load_all()
        result = []
        for p in principles:
            if p["dimension"] == dimension.value:
                result.append(Principle.model_validate(p))
        return result

    def get_active(self) -> List[Principle]:
        """获取所有活跃原则

        Returns:
            活跃原则列表（按置信度排序）
        """
        principles = self._load_all()
        result = []
        for p in principles:
            principle = Principle.model_validate(p)
            if principle.active:
                result.append(principle)

        # 按置信度排序
        result.sort(key=lambda p: p.confidence, reverse=True)
        return result

    def get_all(self) -> List[Principle]:
        """获取所有原则

        Returns:
            所有原则列表
        """
        principles = self._load_all()
        return [Principle.model_validate(p) for p in principles]

    def update(self, principle: Principle) -> Principle:
        """更新原则

        Args:
            principle: 更新后的原则

        Returns:
            更新后的原则

        Raises:
            AsmeError: 原则不存在时
        """
        existing = self.get_by_id(principle.id)
        if not existing:
            raise AsmeError(
                ErrorCode.PRINCIPLE_NOT_FOUND,
                f"原则不存在: {principle.id}"
            )

        principle.updated_at = datetime.now()
        return self.save(principle)

    def confirm(self, principle_id: str) -> Principle:
        """确认原则

        用户确认后，原则的置信度会提升。

        Args:
            principle_id: 原则 ID

        Returns:
            确认后的原则

        Raises:
            AsmeError: 原则不存在时
        """
        principle = self.get_by_id(principle_id)
        if not principle:
            raise AsmeError(
                ErrorCode.PRINCIPLE_NOT_FOUND,
                f"原则不存在: {principle_id}"
            )

        previous_confidence = principle.confidence
        principle.confirmed_by_user = True
        principle.confidence = min(1.0, principle.confidence + 0.2)  # 确认后提升置信度
        principle.updated_at = datetime.now()

        # 记录演化事件
        self._record_evolution(
            principle_id=principle.id,
            previous_confidence=previous_confidence,
            new_confidence=principle.confidence,
            trigger=EvolutionTrigger.USER_CONFIRMATION,
            reason="用户确认原则",
        )

        return self.save(principle)

    def correct(self, principle_id: str, new_statement: str, reason: str) -> Principle:
        """修正原则

        用户修正原则内容，并记录修正原因。

        Args:
            principle_id: 原则 ID
            new_statement: 新的原则陈述
            reason: 修正原因

        Returns:
            修正后的原则

        Raises:
            AsmeError: 原则不存在时
        """
        principle = self.get_by_id(principle_id)
        if not principle:
            raise AsmeError(
                ErrorCode.PRINCIPLE_NOT_FOUND,
                f"原则不存在: {principle_id}"
            )

        previous_confidence = principle.confidence
        principle.statement = new_statement
        principle.confirmed_by_user = True  # 用户修正也视为确认
        principle.updated_at = datetime.now()

        # 记录演化事件
        self._record_evolution(
            principle_id=principle.id,
            previous_confidence=previous_confidence,
            new_confidence=principle.confidence,
            trigger=EvolutionTrigger.USER_CORRECTION,
            reason=reason,
        )

        return self.save(principle)

    def delete(self, principle_id: str) -> bool:
        """删除原则

        Args:
            principle_id: 原则 ID

        Returns:
            是否成功删除
        """
        principles = self._load_all()
        original_len = len(principles)
        principles = [p for p in principles if p["id"] != principle_id]

        if len(principles) < original_len:
            self._save_all(principles)
            return True
        return False

    def deactivate(self, principle_id: str) -> Principle:
        """停用原则

        Args:
            principle_id: 原则 ID

        Returns:
            停用后的原则
        """
        principle = self.get_by_id(principle_id)
        if not principle:
            raise AsmeError(
                ErrorCode.PRINCIPLE_NOT_FOUND,
                f"原则不存在: {principle_id}"
            )

        principle.active = False
        principle.updated_at = datetime.now()
        return self.save(principle)

    def count(self, active_only: bool = False) -> int:
        """统计原则数量

        Args:
            active_only: 是否只统计活跃原则

        Returns:
            原则数量
        """
        if active_only:
            return len(self.get_active())
        return len(self._load_all())

    def _load_all(self) -> List[Dict]:
        """加载所有原则"""
        return read_json_gz(self.principles_file) or []

    def _save_all(self, principles: List[Dict]) -> None:
        """保存所有原则"""
        write_json_gz(self.principles_file, principles)

    def _record_evolution(
        self,
        principle_id: str,
        previous_confidence: float,
        new_confidence: float,
        trigger: EvolutionTrigger,
        reason: str,
        evidence_ids: Optional[List[str]] = None,
    ) -> None:
        """记录演化事件

        Args:
            principle_id: 原则 ID
            previous_confidence: 之前的置信度
            new_confidence: 新的置信度
            trigger: 触发类型
            reason: 变化原因
            evidence_ids: 相关证据 ID 列表
        """
        from .evolution import EvolutionTracker

        tracker = EvolutionTracker()
        tracker.record_event(
            principle_id=principle_id,
            previous_confidence=previous_confidence,
            new_confidence=new_confidence,
            trigger=trigger,
            reason=reason,
            evidence_ids=evidence_ids,
        )
