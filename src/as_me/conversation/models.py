"""对话数据模型

包含:
- ConversationLog: 对话日志模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ..analysis.models import AnalysisStatus


class ConversationLog(BaseModel):
    """对话日志

    记录已分析的对话会话。
    """
    session_id: str
    project_path: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    extracted_count: int = 0
    message_count: int = 0
    # 新增字段
    status: AnalysisStatus = AnalysisStatus.COMPLETED
    error_message: Optional[str] = None
    analysis_duration_ms: Optional[int] = None  # 分析耗时（毫秒）
