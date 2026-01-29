"""会话记忆提取器

从 Claude Code 会话文件中提取用户消息，分析并存储记忆。
"""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from ..memory.models import MemoryAtom, MemoryTier, MemoryType
from ..memory.store import MemoryStore
from ..storage.base import get_storage_path
from ..storage.json_store import read_json_gz, write_json_gz


@dataclass
class ExtractionResult:
    """提取结果"""
    session_id: str
    extracted_count: int
    skipped_duplicate: int
    error: Optional[str] = None


class SessionExtractor:
    """会话记忆提取器

    从 Claude Code 的 .jsonl 会话文件中提取用户消息，
    调用 LLM 分析并存储记忆。
    """

    CLAUDE_DATA_DIR = Path.home() / ".claude"
    PROJECTS_DIR = CLAUDE_DATA_DIR / "projects"
    ANALYZED_LOG = "analyzed_sessions.json"

    def __init__(self, storage_root: Path | None = None):
        """初始化提取器

        Args:
            storage_root: 存储根目录
        """
        self.storage_root = storage_root or get_storage_path()
        self.memory_store = MemoryStore(storage_root)

    def extract_session(self, session_id: str, project_path: str) -> ExtractionResult:
        """提取单个会话的记忆

        Args:
            session_id: 会话 ID
            project_path: 项目路径（用于定位会话文件）

        Returns:
            提取结果
        """
        try:
            # 检查是否已分析过
            if self._is_analyzed(session_id):
                return ExtractionResult(
                    session_id=session_id,
                    extracted_count=0,
                    skipped_duplicate=0,
                    error="already analyzed"
                )

            # 读取会话文件
            session_file = self._find_session_file(session_id, project_path)
            if not session_file:
                return ExtractionResult(
                    session_id=session_id,
                    extracted_count=0,
                    skipped_duplicate=0,
                    error="session file not found"
                )

            # 提取用户消息
            user_messages = self._extract_user_messages(session_file)
            if not user_messages:
                self._mark_analyzed(session_id)
                return ExtractionResult(
                    session_id=session_id,
                    extracted_count=0,
                    skipped_duplicate=0,
                )

            # 分析并提取记忆
            memories = self._analyze_messages(user_messages, session_id)

            # 去重并保存
            saved, skipped = self._save_with_dedup(memories)

            # 标记已分析
            self._mark_analyzed(session_id, len(saved))

            return ExtractionResult(
                session_id=session_id,
                extracted_count=len(saved),
                skipped_duplicate=skipped,
            )

        except Exception as e:
            return ExtractionResult(
                session_id=session_id,
                extracted_count=0,
                skipped_duplicate=0,
                error=str(e)
            )

    def _find_session_file(self, session_id: str, project_path: str) -> Optional[Path]:
        """查找会话文件

        Claude Code 会话文件存储在:
        ~/.claude/projects/<encoded-project-path>/<session-id>.jsonl
        """
        # 将项目路径编码为目录名
        # Claude Code 的编码规则：把 / 替换为 -，. 也替换为 -
        encoded_path = project_path.replace("/", "-").replace(".", "-")
        project_dir = self.PROJECTS_DIR / encoded_path

        if not project_dir.exists():
            # 尝试匹配（可能有细微差异）
            if self.PROJECTS_DIR.exists():
                for d in self.PROJECTS_DIR.iterdir():
                    if d.is_dir() and project_path.replace("/", "-") in d.name:
                        project_dir = d
                        break

        if not project_dir.exists():
            return None

        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists():
            return session_file

        return None

    def _extract_user_messages(self, session_file: Path) -> List[str]:
        """从会话文件中提取用户消息"""
        messages = []

        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    # 只处理用户消息
                    if entry.get("type") != "user":
                        continue

                    # 跳过元消息（如 skill 注入）
                    if entry.get("isMeta"):
                        continue

                    message = entry.get("message", {})
                    content = message.get("content")

                    if isinstance(content, str):
                        # 过滤掉命令（如 /commit, /exit 等）
                        if not content.startswith("/"):
                            messages.append(content)
                    elif isinstance(content, list):
                        # 多模态消息，提取文本部分
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                if text and not text.startswith("/"):
                                    messages.append(text)

                except json.JSONDecodeError:
                    continue

        return messages

    def _analyze_messages(self, messages: List[str], session_id: str) -> List[MemoryAtom]:
        """分析消息并提取记忆

        使用简单的规则匹配提取明显的用户特征。
        复杂分析交给 Claude（通过 skill）处理。
        """
        memories = []

        # 合并所有消息
        full_text = "\n".join(messages)

        # 规则 1: 明确的身份表达
        identity_patterns = [
            (r"我是(?:一[个名位])?(.{2,30}?)(?:[，。,.]|$)", 0.7),
            (r"作为(?:一[个名位])?(.{2,30}?)(?:[，。,.]|$)", 0.6),
            (r"我的(?:工作|职业|角色)是(.{2,30}?)(?:[，。,.]|$)", 0.7),
        ]

        for pattern, confidence in identity_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches[:2]:  # 每个模式最多 2 条
                memories.append(MemoryAtom(
                    id=str(uuid.uuid4()),
                    type=MemoryType.IDENTITY,
                    content=f"用户自述: {match.strip()}",
                    confidence=confidence,
                    tier=MemoryTier.SHORT_TERM,
                    source_session_id=session_id,
                    tags=["auto_extracted", "rule_based"],
                ))

        # 规则 2: 偏好表达
        preference_patterns = [
            (r"我(?:喜欢|偏好|习惯)(.{5,50}?)(?:[，。,.]|$)", 0.6),
            (r"我(?:不喜欢|讨厌|不习惯)(.{5,50}?)(?:[，。,.]|$)", 0.6),
        ]

        for pattern, confidence in preference_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches[:2]:
                memories.append(MemoryAtom(
                    id=str(uuid.uuid4()),
                    type=MemoryType.PREFERENCE,
                    content=match.strip(),
                    confidence=confidence,
                    tier=MemoryTier.SHORT_TERM,
                    source_session_id=session_id,
                    tags=["auto_extracted", "rule_based"],
                ))

        # 规则 3: 价值/信念表达
        value_patterns = [
            (r"我(?:认为|觉得|相信)(.{5,80}?)(?:[，。,.]|$)", 0.5),
            (r"我的原则是(.{5,50}?)(?:[，。,.]|$)", 0.7),
        ]

        for pattern, confidence in value_patterns:
            matches = re.findall(pattern, full_text)
            for match in matches[:2]:
                memories.append(MemoryAtom(
                    id=str(uuid.uuid4()),
                    type=MemoryType.VALUE,
                    content=match.strip(),
                    confidence=confidence,
                    tier=MemoryTier.SHORT_TERM,
                    source_session_id=session_id,
                    tags=["auto_extracted", "rule_based"],
                ))

        return memories

    def _save_with_dedup(self, memories: List[MemoryAtom]) -> tuple[List[MemoryAtom], int]:
        """保存记忆并去重

        Returns:
            (保存的记忆, 跳过的重复数)
        """
        if not memories:
            return [], 0

        # 获取现有记忆
        existing = self.memory_store.get_all()
        existing_contents = {m.content.lower() for m in existing}

        # 过滤重复
        to_save = []
        skipped = 0

        for memory in memories:
            if memory.content.lower() in existing_contents:
                skipped += 1
            else:
                to_save.append(memory)
                existing_contents.add(memory.content.lower())

        # 批量保存
        if to_save:
            self.memory_store.save_batch(to_save)

        return to_save, skipped

    def _is_analyzed(self, session_id: str) -> bool:
        """检查会话是否已分析"""
        log_path = self.storage_root / self.ANALYZED_LOG
        log = read_json_gz(log_path) or {}
        return session_id in log.get("sessions", {})

    def _mark_analyzed(self, session_id: str, extracted_count: int = 0) -> None:
        """标记会话已分析"""
        log_path = self.storage_root / self.ANALYZED_LOG
        log = read_json_gz(log_path) or {"sessions": {}}

        log["sessions"][session_id] = {
            "analyzed_at": datetime.now().isoformat(),
            "extracted_count": extracted_count,
        }

        write_json_gz(log_path, log)


def extract_session_background(session_id: str, project_path: str) -> None:
    """后台提取会话记忆（供 CLI 调用）"""
    extractor = SessionExtractor()
    result = extractor.extract_session(session_id, project_path)

    # 可选：写入日志
    if result.extracted_count > 0:
        log_file = get_storage_path() / "extraction.log"
        with open(log_file, "a") as f:
            f.write(
                f"{datetime.now().isoformat()} | "
                f"session={session_id[:8]} | "
                f"extracted={result.extracted_count} | "
                f"skipped={result.skipped_duplicate}\n"
            )
