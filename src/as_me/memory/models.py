"""记忆数据模型

包含:
- MemoryType: 记忆类型枚举
- MemoryTier: 记忆层级枚举
- MemoryAtom: 记忆原子模型
- AutoExtractionSettings: 自动提取配置（从 analysis.models 导入）
- ProfileSettings: 档案设置模型
- Profile: 用户档案模型
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
import uuid

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..analysis.models import AutoExtractionSettings as _AutoExtractionSettings


class MemoryType(str, Enum):
    """记忆类型"""
    TECH_PREFERENCE = "tech_preference"      # 技术偏好
    THINKING_PATTERN = "thinking_pattern"    # 思维模式
    LANGUAGE_STYLE = "language_style"        # 语言风格
    BEHAVIOR_HABIT = "behavior_habit"        # 行为习惯


class MemoryTier(str, Enum):
    """记忆层级

    状态转换:
    SHORT_TERM → WORKING → LONG_TERM

    淡化删除条件:
    - SHORT_TERM: confidence < 0.3
    - WORKING: confidence < 0.2
    - LONG_TERM: confidence < 0.1
    """
    SHORT_TERM = "short_term"    # 短期记忆（< 3天）
    WORKING = "working"          # 工作记忆（活跃的）
    LONG_TERM = "long_term"      # 长期记忆（稳定的）


class MemoryAtom(BaseModel):
    """记忆原子 - 最小记忆单元

    存储从对话中提取的单个特征。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    content: str = Field(max_length=500)
    confidence: float = Field(ge=0, le=1)
    tier: MemoryTier = MemoryTier.SHORT_TERM
    created_at: datetime = Field(default_factory=datetime.now)
    last_triggered_at: datetime = Field(default_factory=datetime.now)
    trigger_count: int = Field(default=0, ge=0)
    source_session_id: str
    related_principle_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# 内联定义 AutoExtractionSettings 以避免循环导入
class AutoExtractionSettings(BaseModel):
    """自动提取配置"""
    enabled: bool = True                     # 是否启用
    max_sessions_per_run: int = Field(default=5, ge=1, le=20)
    max_messages_per_session: int = Field(default=100, ge=10, le=500)
    retry_limit: int = Field(default=3, ge=1, le=10)


class ProfileSettings(BaseModel):
    """档案设置"""
    extraction_enabled: bool = True       # 是否启用自动提取
    injection_enabled: bool = True        # 是否启用记忆注入
    max_injected_memories: int = Field(default=10, ge=1, le=50)
    confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    decay_half_life_days: int = Field(default=30, ge=7, le=365)
    # 新增: 自动提取配置
    auto_extraction: AutoExtractionSettings = Field(
        default_factory=AutoExtractionSettings
    )


class Profile(BaseModel):
    """用户档案

    汇总所有记忆和原则的元数据。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    total_memories: int = 0
    total_principles: int = 0
    last_analyzed_session: Optional[str] = None
    settings: ProfileSettings = Field(default_factory=ProfileSettings)
