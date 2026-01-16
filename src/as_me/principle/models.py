"""原则数据模型

包含:
- PrincipleDimension: 原则维度枚举
- Principle: 内核原则模型
- Evidence: 证据模型
- EvolutionTrigger: 演化触发类型枚举
- EvolutionEvent: 演化事件模型
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


class PrincipleDimension(str, Enum):
    """原则维度"""
    WORLDVIEW = "worldview"                  # 世界观
    VALUES = "values"                        # 价值观
    DECISION_PATTERN = "decision_pattern"    # 决策模式
    DOMAIN_THOUGHT = "domain_thought"        # 领域思想


class Principle(BaseModel):
    """内核原则

    从记忆原子中聚合出的稳定特征。
    evidence_count >= 3 才能创建原则。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dimension: PrincipleDimension
    statement: str = Field(max_length=200)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    confirmed_by_user: bool = False
    active: bool = True


class Evidence(BaseModel):
    """证据

    支撑记忆或原则的具体对话引用。
    memory_id 或 principle_id 至少有一个。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: Optional[str] = None
    principle_id: Optional[str] = None
    source_session_id: str
    quote: str = Field(max_length=1000)
    weight: float = Field(ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    context: Optional[str] = None

    @model_validator(mode='after')
    def check_reference(self) -> 'Evidence':
        if not self.memory_id and not self.principle_id:
            raise ValueError('memory_id 或 principle_id 必须至少设置一个')
        return self


class EvolutionTrigger(str, Enum):
    """演化触发类型"""
    NEW_EVIDENCE = "new_evidence"           # 新证据
    CONFLICTING_EVIDENCE = "conflict"       # 冲突证据
    USER_CONFIRMATION = "user_confirm"      # 用户确认
    USER_CORRECTION = "user_correct"        # 用户修正
    TIME_DECAY = "time_decay"               # 时间衰减
    AGGREGATION = "aggregation"             # 记忆聚合


class EvolutionEvent(BaseModel):
    """演化事件

    记录原则的变化历史。
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    principle_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    previous_confidence: float = Field(ge=0, le=1)
    new_confidence: float = Field(ge=0, le=1)
    trigger: EvolutionTrigger
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
