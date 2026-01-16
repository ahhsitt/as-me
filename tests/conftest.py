"""Pytest 配置和共享 fixtures"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_storage_dir():
    """创建临时存储目录用于测试"""
    temp_dir = Path(tempfile.mkdtemp(prefix="as-me-test-"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_conversation_data():
    """示例对话数据"""
    return [
        {
            "uuid": "msg-001",
            "parentUuid": "",
            "timestamp": "2026-01-16T10:00:00Z",
            "type": "user",
            "sessionId": "session-001",
            "cwd": "/Users/test/project",
            "gitBranch": "main",
            "message": {
                "role": "user",
                "content": "我更喜欢使用 TypeScript 而不是 JavaScript"
            },
            "isSidechain": False
        },
        {
            "uuid": "msg-002",
            "parentUuid": "msg-001",
            "timestamp": "2026-01-16T10:00:30Z",
            "type": "assistant",
            "sessionId": "session-001",
            "cwd": "/Users/test/project",
            "gitBranch": "main",
            "message": {
                "role": "assistant",
                "content": "好的，我会使用 TypeScript 来实现这个功能。"
            },
            "isSidechain": False
        }
    ]


@pytest.fixture
def sample_memory_atom():
    """示例记忆原子数据"""
    return {
        "id": "mem-001",
        "type": "tech_preference",
        "content": "偏好使用 TypeScript 而不是 JavaScript",
        "confidence": 0.8,
        "tier": "short_term",
        "source_session_id": "session-001",
        "tags": ["language", "typescript"]
    }
