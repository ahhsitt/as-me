"""记忆数据模型

包含:
- MemoryType: 记忆类型枚举
- MemoryTier: 记忆层级枚举
- MemoryAtom: 记忆原子模型
- ProfileSettings: 档案设置模型
- Profile: 用户档案模型
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型

    五大维度，覆盖身份层、认知层、偏好层：
    - 身份层：identity, value
    - 认知层：thinking
    - 偏好层：preference, communication
    """
    IDENTITY = "identity"           # 身份背景：角色、目标、专业领域
    VALUE = "value"                 # 价值信念：信念、原则、优先级
    THINKING = "thinking"           # 思维认知：分析方法、决策风格
    PREFERENCE = "preference"       # 偏好习惯：工具、方法、风格偏好
    COMMUNICATION = "communication" # 沟通表达：沟通风格、表达习惯


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


class ProfileSettings(BaseModel):
    """档案设置"""
    injection_enabled: bool = True        # 是否启用记忆注入
    max_injected_memories: int = Field(default=10, ge=1, le=50)
    confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    decay_half_life_days: int = Field(default=30, ge=7, le=365)


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
