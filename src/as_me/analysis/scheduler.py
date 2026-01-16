"""分析调度器

协调后台分析任务的执行。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..conversation.log import ConversationLogStore
from ..conversation.parser import ConversationParser
from ..errors import AsmeError, ErrorCode
from ..memory.extractor import MemoryExtractor
from ..memory.store import MemoryStore
from ..storage import get_storage_path
from ..storage.json_store import read_json
from .models import AnalysisQueueItem, AnalysisResult, AnalysisStatus
from .queue import AnalysisQueue

logger = logging.getLogger(__name__)


class AnalysisScheduler:
    """分析调度器

    负责协调后台分析任务，包括：
    - 检查是否应该运行分析
    - 获取待分析的会话
    - 执行分析并保存结果
    """

    def __init__(self, storage_root: Path | None = None):
        """初始化调度器

        Args:
            storage_root: 存储根目录，默认 ~/.as-me/
        """
        self.storage_root = storage_root or get_storage_path()
        self.queue = AnalysisQueue(self.storage_root)
        self.parser = ConversationParser()
        self.memory_store = MemoryStore(self.storage_root)
        self.log_store = ConversationLogStore()
        self.extractor = MemoryExtractor()

    def should_run_analysis(self) -> bool:
        """检查是否应该运行分析

        检查条件：
        1. auto_extraction.enabled 为 True
        2. extraction_enabled 为 True
        3. 存在未分析的会话

        Returns:
            是否应该运行分析
        """
        # 检查配置
        config = self._get_config()
        if not config.get("extraction_enabled", True):
            return False

        auto_config = config.get("auto_extraction", {})
        if not auto_config.get("enabled", True):
            return False

        # 检查是否有待分析的会话
        pending = self.get_pending_sessions()
        return len(pending) > 0

    def get_pending_sessions(self) -> list[AnalysisQueueItem]:
        """获取待分析的会话列表

        首先扫描新的未分析会话并添加到队列，
        然后返回待处理的队列项。

        Returns:
            待分析的会话队列项列表，按优先级排序
        """
        config = self._get_config()
        auto_config = config.get("auto_extraction", {})
        max_sessions = auto_config.get("max_sessions_per_run", 5)

        # 扫描新会话
        self._scan_new_sessions()

        # 获取待处理项
        return self.queue.get_pending(limit=max_sessions)

    def run_analysis(self) -> AnalysisResult:
        """执行分析任务

        1. 获取待分析会话
        2. 依次处理每个会话
        3. 更新状态和日志
        4. 返回分析结果

        Returns:
            分析结果摘要
        """
        start_time = time.time()
        result = AnalysisResult()

        pending = self.get_pending_sessions()
        result.total_sessions = len(pending)

        for item in pending:
            try:
                extracted = self._analyze_session(item)
                if extracted > 0:
                    result.analyzed_count += 1
                    result.total_memories += extracted
                else:
                    result.skipped_count += 1
            except Exception as e:
                result.failed_count += 1
                result.errors.append(f"{item.session_id}: {str(e)}")

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    def _analyze_session(self, item: AnalysisQueueItem) -> int:
        """分析单个会话

        Args:
            item: 队列项

        Returns:
            提取的记忆数量

        Raises:
            AsmeError: 分析失败时
        """
        start_time = time.time()

        # 更新状态为处理中
        self.queue.update_status(item.session_id, AnalysisStatus.PROCESSING)

        try:
            # 检查会话文件是否存在
            session_path = Path(item.session_path)
            if not session_path.exists():
                raise AsmeError(
                    ErrorCode.ANALYSIS_SESSION_NOT_FOUND,
                    f"会话文件不存在: {session_path}"
                )

            # 解析对话
            entries = self.parser.parse(session_path)
            if not entries:
                self.queue.update_status(
                    item.session_id,
                    AnalysisStatus.SKIPPED
                )
                self._log_analysis(item, 0, start_time, AnalysisStatus.SKIPPED)
                return 0

            # 提取用户消息
            messages = self.parser.extract_user_messages(entries)

            # 检查是否有可提取特征
            if not self.extractor.has_extractable_features(messages):
                self.queue.update_status(
                    item.session_id,
                    AnalysisStatus.SKIPPED
                )
                self._log_analysis(item, 0, start_time, AnalysisStatus.SKIPPED)
                return 0

            # 执行提取
            config = self._get_config()
            auto_config = config.get("auto_extraction", {})
            max_messages = auto_config.get("max_messages_per_session", 100)

            # 截断消息
            if len(messages) > max_messages:
                messages = messages[-max_messages:]

            extraction_result = self.extractor.extract(messages, item.session_id)

            # 保存记忆
            extracted_count = 0
            for memory in extraction_result.memories:
                self.memory_store.save(memory)
                extracted_count += 1

            # 更新状态
            self.queue.update_status(
                item.session_id,
                AnalysisStatus.COMPLETED,
                extracted_count=extracted_count
            )
            self._log_analysis(
                item,
                extracted_count,
                start_time,
                AnalysisStatus.COMPLETED,
                len(entries)
            )

            return extracted_count

        except AsmeError as e:
            self._handle_analysis_error(item, e, start_time)
            raise

        except Exception as e:
            error = AsmeError(
                ErrorCode.ANALYSIS_EXTRACTION_FAILED,
                str(e)
            )
            self._handle_analysis_error(item, error, start_time)
            raise error

    def _scan_new_sessions(self) -> None:
        """扫描新的未分析会话并添加到队列"""
        # 获取已分析的会话 ID
        analyzed_ids = self.log_store.get_analyzed_ids()

        # 获取队列中的会话 ID
        queue_data = self.queue._load()
        queue_ids = {
            item.get("session_id")
            for item in queue_data.get("items", [])
        }

        # 获取最近的会话
        recent_sessions = self.parser.get_recent_sessions(limit=20)

        for session_path in recent_sessions:
            session_id = session_path.stem

            # 跳过已分析或已在队列中的会话
            if session_id in analyzed_ids or session_id in queue_ids:
                continue

            # 获取项目路径
            project_path = session_path.parent.name

            # 添加到队列
            item = AnalysisQueueItem(
                session_id=session_id,
                project_path=project_path,
                session_path=str(session_path),
            )
            self.queue.add(item)

    def _handle_analysis_error(
        self,
        item: AnalysisQueueItem,
        error: AsmeError,
        start_time: float
    ) -> None:
        """处理分析错误

        Args:
            item: 队列项
            error: 错误
            start_time: 开始时间
        """
        config = self._get_config()
        auto_config = config.get("auto_extraction", {})
        retry_limit = auto_config.get("retry_limit", 3)

        # 更新状态为失败
        self.queue.update_status(
            item.session_id,
            AnalysisStatus.FAILED,
            error_message=str(error)
        )

        # 记录日志
        self._log_analysis(
            item,
            0,
            start_time,
            AnalysisStatus.FAILED,
            error_message=str(error)
        )

        # 检查是否可以重试
        current_item = self.queue.get_by_session_id(item.session_id)
        if current_item and current_item.retry_count < retry_limit:
            self.queue.mark_for_retry(item.session_id)

    def _log_analysis(
        self,
        item: AnalysisQueueItem,
        extracted_count: int,
        start_time: float,
        status: AnalysisStatus,
        message_count: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """记录分析日志

        Args:
            item: 队列项
            extracted_count: 提取数量
            start_time: 开始时间
            status: 状态
            message_count: 消息数量
            error_message: 错误信息
        """
        from ..conversation.models import ConversationLog

        duration_ms = int((time.time() - start_time) * 1000)

        log = ConversationLog(
            session_id=item.session_id,
            project_path=item.project_path,
            extracted_count=extracted_count,
            message_count=message_count,
            status=status,
            error_message=error_message,
            analysis_duration_ms=duration_ms,
        )

        self.log_store.add(log)

    def _get_config(self) -> dict:
        """获取配置

        Returns:
            配置字典
        """
        profile_path = self.storage_root / "profile.json"
        profile = read_json(profile_path)

        if not profile:
            return {"extraction_enabled": True, "auto_extraction": {"enabled": True}}

        return profile.get("settings", {})
