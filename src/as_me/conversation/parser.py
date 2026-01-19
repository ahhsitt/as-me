"""对话解析器

解析 Claude Code 的 JSONL 对话历史文件。

Claude Code 对话历史存储位置:
~/.claude/projects/{PROJECT_PATH_ENCODED}/{SESSION_UUID}.jsonl
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Literal, Optional, Union

from pydantic import BaseModel

from ..errors import AsmeError, ErrorCode


class MessageContent(BaseModel):
    """消息内容"""
    role: str
    content: Union[str, list]


class ConversationEntry(BaseModel):
    """对话条目"""
    uuid: str                    # 消息唯一 ID
    parentUuid: Optional[str] = None  # 父消息 ID（线程），根消息时为 None
    timestamp: str               # ISO 8601
    type: Literal['user', 'assistant', 'system']
    sessionId: str
    cwd: str
    gitBranch: Optional[str] = None
    message: Optional[MessageContent] = None  # 消息内容，某些条目可能没有
    isSidechain: bool = False    # 是否为子代理对话


# Claude Code 对话历史根目录
CLAUDE_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


class ConversationParser:
    """对话解析器

    解析 Claude Code 的 JSONL 对话历史。
    """

    def __init__(self, projects_root: Path | None = None):
        """初始化解析器

        Args:
            projects_root: Claude 项目根目录，默认 ~/.claude/projects/
        """
        self.projects_root = projects_root or CLAUDE_PROJECTS_ROOT

    def parse(self, session_path: Path) -> List[ConversationEntry]:
        """解析单个对话会话

        Args:
            session_path: JSONL 文件路径

        Returns:
            对话条目列表

        Raises:
            AsmeError: 解析失败时
        """
        if not session_path.exists():
            raise AsmeError(
                ErrorCode.CONVERSATION_NOT_FOUND,
                f"对话文件不存在: {session_path}"
            )

        entries = []
        try:
            for entry in self._iter_jsonl(session_path):
                # 跳过非对话条目（summary, file-history-snapshot 等）
                entry_type = entry.get("type")
                if entry_type not in ("user", "assistant", "system"):
                    continue
                entries.append(ConversationEntry.model_validate(entry))
        except json.JSONDecodeError as e:
            raise AsmeError(
                ErrorCode.CONVERSATION_PARSE_ERROR,
                f"JSON 解析失败: {e}",
                {"path": str(session_path)}
            )
        except Exception as e:
            raise AsmeError(
                ErrorCode.CONVERSATION_PARSE_ERROR,
                f"对话解析失败: {e}",
                {"path": str(session_path)}
            )

        return entries

    def get_recent_sessions(
        self,
        project_path: str | None = None,
        limit: int = 10
    ) -> List[Path]:
        """获取最近的会话文件

        Args:
            project_path: 项目路径（编码后），为 None 时返回所有项目的会话
            limit: 返回数量上限

        Returns:
            会话文件路径列表（按修改时间降序）
        """
        if project_path:
            search_paths = [self.projects_root / project_path]
        else:
            search_paths = list(self.projects_root.iterdir()) if self.projects_root.exists() else []

        sessions = []
        for project_dir in search_paths:
            if not project_dir.is_dir():
                continue
            for jsonl_file in project_dir.glob("*.jsonl"):
                # 排除 history.jsonl（仅包含摘要）
                if jsonl_file.name == "history.jsonl":
                    continue
                sessions.append(jsonl_file)

        # 按修改时间排序
        sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return sessions[:limit]

    def get_unanalyzed_sessions(
        self,
        analyzed_session_ids: set[str],
        project_path: str | None = None,
        limit: int = 10
    ) -> List[Path]:
        """获取未分析的会话文件

        Args:
            analyzed_session_ids: 已分析的会话 ID 集合
            project_path: 项目路径（编码后）
            limit: 返回数量上限

        Returns:
            未分析的会话文件路径列表
        """
        recent_sessions = self.get_recent_sessions(project_path, limit=limit * 2)

        unanalyzed = []
        for session_path in recent_sessions:
            # 从文件名提取 session ID（去除 .jsonl 后缀）
            session_id = session_path.stem
            if session_id not in analyzed_session_ids:
                unanalyzed.append(session_path)
            if len(unanalyzed) >= limit:
                break

        return unanalyzed

    def get_session_summary(self, session_path: Path) -> dict:
        """获取会话摘要信息

        Args:
            session_path: 会话文件路径

        Returns:
            包含消息数、时间范围等的摘要字典
        """
        entries = self.parse(session_path)
        if not entries:
            return {
                "message_count": 0,
                "user_message_count": 0,
                "assistant_message_count": 0,
                "start_time": None,
                "end_time": None,
                "cwd": None,
            }

        user_messages = [e for e in entries if e.type == "user"]
        assistant_messages = [e for e in entries if e.type == "assistant"]

        return {
            "message_count": len(entries),
            "user_message_count": len(user_messages),
            "assistant_message_count": len(assistant_messages),
            "start_time": entries[0].timestamp,
            "end_time": entries[-1].timestamp,
            "cwd": entries[0].cwd,
        }

    def extract_user_messages(self, entries: List[ConversationEntry]) -> List[str]:
        """提取用户消息文本

        Args:
            entries: 对话条目列表

        Returns:
            用户消息文本列表
        """
        messages = []
        for entry in entries:
            if entry.type != "user":
                continue
            if entry.isSidechain:
                continue  # 跳过子代理对话
            if entry.message is None:
                continue  # 跳过没有消息内容的条目

            content = entry.message.content
            if isinstance(content, str):
                messages.append(content)
            elif isinstance(content, list):
                # 处理多部分消息
                text_parts = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                if text_parts:
                    messages.append("\n".join(text_parts))

        return messages

    def _iter_jsonl(self, path: Path) -> Iterator[dict]:
        """迭代 JSONL 文件

        Args:
            path: JSONL 文件路径

        Yields:
            解析后的 JSON 对象
        """
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
