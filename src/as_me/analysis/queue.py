"""分析队列管理器

管理待分析的会话队列。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..storage import get_storage_path
from ..storage.json_store import read_json, write_json
from .models import AnalysisQueueItem, AnalysisStatus

logger = logging.getLogger(__name__)


class AnalysisQueue:
    """分析队列管理器

    负责管理待分析会话的队列，支持添加、查询、状态更新等操作。
    """

    QUEUE_FILE = "analysis/queue.json"

    def __init__(self, storage_root: Path | None = None):
        """初始化队列管理器

        Args:
            storage_root: 存储根目录，默认 ~/.as-me/
        """
        self.storage_root = storage_root or get_storage_path()
        self._file_path = self.storage_root / self.QUEUE_FILE
        # 确保目录存在
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, item: AnalysisQueueItem) -> AnalysisQueueItem:
        """添加队列项

        如果 session_id 已存在，更新现有项。

        Args:
            item: 队列项

        Returns:
            添加/更新后的队列项
        """
        data = self._load()
        items = data.get("items", [])

        # 检查是否已存在
        for i, existing in enumerate(items):
            if existing.get("session_id") == item.session_id:
                # 更新现有项
                items[i] = item.model_dump(mode="json")
                data["items"] = items
                data["last_updated"] = datetime.now().isoformat()
                self._save(data)
                return item

        # 添加新项
        items.append(item.model_dump(mode="json"))
        data["items"] = items
        data["last_updated"] = datetime.now().isoformat()
        self._save(data)
        return item

    def get_pending(self, limit: int = 5) -> list[AnalysisQueueItem]:
        """获取待处理的队列项

        Args:
            limit: 返回数量限制

        Returns:
            待处理的队列项列表
        """
        data = self._load()
        items = data.get("items", [])

        pending = []
        for item_data in items:
            if item_data.get("status") == AnalysisStatus.PENDING.value:
                pending.append(AnalysisQueueItem.model_validate(item_data))
                if len(pending) >= limit:
                    break

        return pending

    def get_by_session_id(self, session_id: str) -> Optional[AnalysisQueueItem]:
        """根据会话 ID 获取队列项

        Args:
            session_id: 会话 ID

        Returns:
            队列项，不存在时返回 None
        """
        data = self._load()
        items = data.get("items", [])

        for item_data in items:
            if item_data.get("session_id") == session_id:
                return AnalysisQueueItem.model_validate(item_data)

        return None

    def update_status(
        self,
        session_id: str,
        status: AnalysisStatus,
        error_message: str | None = None,
        extracted_count: int = 0
    ) -> Optional[AnalysisQueueItem]:
        """更新队列项状态

        Args:
            session_id: 会话 ID
            status: 新状态
            error_message: 错误信息（失败时）
            extracted_count: 提取的记忆数量

        Returns:
            更新后的队列项，不存在时返回 None
        """
        data = self._load()
        items = data.get("items", [])

        for i, item_data in enumerate(items):
            if item_data.get("session_id") == session_id:
                item = AnalysisQueueItem.model_validate(item_data)

                # 更新状态
                item.status = status

                # 更新时间戳
                now = datetime.now()
                if status == AnalysisStatus.PROCESSING:
                    item.started_at = now
                elif status in (
                    AnalysisStatus.COMPLETED,
                    AnalysisStatus.FAILED,
                    AnalysisStatus.SKIPPED
                ):
                    item.completed_at = now

                # 更新其他字段
                if error_message:
                    item.error_message = error_message
                if extracted_count > 0:
                    item.extracted_count = extracted_count

                items[i] = item.model_dump(mode="json")
                data["items"] = items
                data["last_updated"] = now.isoformat()
                self._save(data)
                return item

        return None

    def mark_for_retry(self, session_id: str) -> bool:
        """标记为重试

        Args:
            session_id: 会话 ID

        Returns:
            是否成功标记（未超过重试限制）
        """
        data = self._load()
        items = data.get("items", [])

        for i, item_data in enumerate(items):
            if item_data.get("session_id") == session_id:
                item = AnalysisQueueItem.model_validate(item_data)

                # 增加重试计数
                item.retry_count += 1

                # 重置状态为 PENDING
                item.status = AnalysisStatus.PENDING
                item.started_at = None
                item.completed_at = None
                item.error_message = None

                items[i] = item.model_dump(mode="json")
                data["items"] = items
                data["last_updated"] = datetime.now().isoformat()
                self._save(data)
                return True

        return False

    def cleanup_completed(self, older_than_days: int = 7) -> int:
        """清理已完成的队列项

        Args:
            older_than_days: 清理 N 天前的已完成项

        Returns:
            清理的数量
        """
        data = self._load()
        items = data.get("items", [])
        cutoff = datetime.now() - timedelta(days=older_than_days)

        cleaned = 0
        remaining = []

        for item_data in items:
            status = item_data.get("status")
            completed_at = item_data.get("completed_at")

            # 保留非终态项
            if status not in (
                AnalysisStatus.COMPLETED.value,
                AnalysisStatus.FAILED.value,
                AnalysisStatus.SKIPPED.value
            ):
                remaining.append(item_data)
                continue

            # 检查完成时间
            if completed_at:
                try:
                    completed_time = datetime.fromisoformat(completed_at)
                    if completed_time > cutoff:
                        remaining.append(item_data)
                        continue
                except ValueError:
                    remaining.append(item_data)
                    continue

            cleaned += 1

        data["items"] = remaining
        data["last_updated"] = datetime.now().isoformat()
        self._save(data)
        return cleaned

    def _load(self) -> dict:
        """加载队列数据"""
        data = read_json(self._file_path)
        if not data:
            return {"items": [], "last_updated": None}
        return data

    def _save(self, data: dict) -> None:
        """保存队列数据"""
        write_json(self._file_path, data)
