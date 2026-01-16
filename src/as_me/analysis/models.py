"""分析调度数据模型

包含:
- AnalysisStatus: 分析状态枚举
- AnalysisQueueItem: 分析队列项模型
- AutoExtractionSettings: 自动提取配置模型
- AnalysisResult: 分析结果数据类
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    SKIPPED = "skipped"          # 跳过（无可提取内容）


class AnalysisQueueItem(BaseModel):
    """分析队列项

    表示待分析或已分析的会话任务。
    """
    session_id: str                          # 会话 ID
    project_path: str                        # 项目路径
    session_path: str                        # 会话文件路径
    status: AnalysisStatus = AnalysisStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None    # 开始处理时间
    completed_at: Optional[datetime] = None  # 完成时间
    retry_count: int = 0                     # 重试次数
    error_message: Optional[str] = None      # 错误信息
    extracted_count: int = 0                 # 提取的记忆数量


class AutoExtractionSettings(BaseModel):
    """自动提取配置"""
    enabled: bool = True                     # 是否启用
    max_sessions_per_run: int = Field(default=5, ge=1, le=20)
    max_messages_per_session: int = Field(default=100, ge=10, le=500)
    retry_limit: int = Field(default=3, ge=1, le=10)


@dataclass
class AnalysisResult:
    """分析结果

    记录一次分析运行的结果摘要。
    """
    total_sessions: int = 0          # 总会话数
    analyzed_count: int = 0          # 成功分析数
    skipped_count: int = 0           # 跳过数
    failed_count: int = 0            # 失败数
    total_memories: int = 0          # 总提取记忆数
    duration_ms: int = 0             # 总耗时（毫秒）
    errors: list[str] = field(default_factory=list)  # 错误信息列表
