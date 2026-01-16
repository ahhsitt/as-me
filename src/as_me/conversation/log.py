"""对话日志追踪

记录已分析的对话会话。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .models import ConversationLog
from ..storage import get_storage_path
from ..storage.json_store import read_json, write_json


class ConversationLogStore:
    """对话日志存储

    负责记录和查询已分析的对话会话。
    """

    LOG_FILE = "logs/analyzed.json"

    def __init__(self):
        """初始化日志存储"""
        self._file_path = get_storage_path(self.LOG_FILE)

    def add(self, log: ConversationLog) -> ConversationLog:
        """添加对话日志

        Args:
            log: 对话日志

        Returns:
            添加后的日志
        """
        logs = self._load_all()

        # 检查是否已存在
        for i, existing in enumerate(logs):
            if existing.get("session_id") == log.session_id:
                # 更新现有记录
                logs[i] = log.model_dump(mode="json")
                self._save_all(logs)
                return log

        # 添加新记录
        logs.append(log.model_dump(mode="json"))
        self._save_all(logs)
        return log

    def get_by_session(self, session_id: str) -> Optional[ConversationLog]:
        """根据会话 ID 获取日志

        Args:
            session_id: 会话 ID

        Returns:
            对话日志，不存在时返回 None
        """
        logs = self._load_all()
        for log in logs:
            if log.get("session_id") == session_id:
                return ConversationLog.model_validate(log)
        return None

    def is_analyzed(self, session_id: str) -> bool:
        """检查会话是否已分析

        Args:
            session_id: 会话 ID

        Returns:
            是否已分析
        """
        return self.get_by_session(session_id) is not None

    def get_all(self) -> List[ConversationLog]:
        """获取所有日志

        Returns:
            所有对话日志列表
        """
        logs = self._load_all()
        return [ConversationLog.model_validate(log) for log in logs]

    def get_analyzed_ids(self) -> set:
        """获取所有已分析的会话 ID

        Returns:
            已分析的会话 ID 集合
        """
        logs = self._load_all()
        return {log.get("session_id") for log in logs if log.get("session_id")}

    def get_recent(self, limit: int = 20) -> List[ConversationLog]:
        """获取最近的日志

        Args:
            limit: 返回数量限制

        Returns:
            最近的对话日志列表
        """
        logs = self.get_all()
        logs.sort(key=lambda x: x.analyzed_at, reverse=True)
        return logs[:limit]

    def count(self) -> int:
        """统计日志数量

        Returns:
            日志数量
        """
        return len(self._load_all())

    def total_extracted(self) -> int:
        """统计总提取数量

        Returns:
            总提取的记忆数量
        """
        logs = self._load_all()
        return sum(log.get("extracted_count", 0) for log in logs)

    def _load_all(self) -> List[dict]:
        """加载所有日志"""
        return read_json(self._file_path) or []

    def _save_all(self, logs: List[dict]) -> None:
        """保存所有日志"""
        write_json(self._file_path, logs)
