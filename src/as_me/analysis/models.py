"""分析模块数据模型

简化版本 - 只保留状态枚举和结果数据类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    SKIPPED = "skipped"          # 跳过（无可提取内容）


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
