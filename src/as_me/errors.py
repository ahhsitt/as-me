"""As-Me 错误定义

包含:
- ErrorCode: 错误码枚举
- AsmeError: 自定义异常基类
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """错误码"""
    # 存储相关 (1xx)
    STORAGE_READ_ERROR = "E101"
    STORAGE_WRITE_ERROR = "E102"
    STORAGE_NOT_FOUND = "E103"
    STORAGE_CORRUPTED = "E104"

    # 记忆相关 (2xx)
    MEMORY_NOT_FOUND = "E201"
    MEMORY_INVALID = "E202"
    MEMORY_DUPLICATE = "E203"

    # 原则相关 (3xx)
    PRINCIPLE_NOT_FOUND = "E301"
    PRINCIPLE_INVALID = "E302"
    PRINCIPLE_INSUFFICIENT_EVIDENCE = "E303"

    # 对话相关 (4xx)
    CONVERSATION_NOT_FOUND = "E401"
    CONVERSATION_PARSE_ERROR = "E402"
    CONVERSATION_ALREADY_ANALYZED = "E403"

    # 提取相关 (5xx)
    EXTRACTION_FAILED = "E501"
    EXTRACTION_NO_FEATURES = "E502"

    # 分析调度相关 (7xx)
    ANALYSIS_ALREADY_RUNNING = "E701"
    ANALYSIS_SESSION_NOT_FOUND = "E702"
    ANALYSIS_PARSE_ERROR = "E703"
    ANALYSIS_EXTRACTION_FAILED = "E704"
    ANALYSIS_STORAGE_ERROR = "E705"

    # 验证相关 (6xx)
    VALIDATION_ERROR = "E601"


class AsmeError(Exception):
    """As-Me 自定义异常基类"""

    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
