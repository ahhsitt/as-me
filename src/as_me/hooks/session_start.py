"""SessionStart Hook 处理器

处理 Claude Code 的 SessionStart 事件，注入用户记忆上下文。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..memory.decay import MemoryDecay
from ..memory.retriever import MemoryRetriever
from ..memory.store import MemoryStore
from ..storage import ensure_storage_dir, get_storage_path, ColdStorageManager


@dataclass
class HookOutput:
    """Hook 输出"""
    additional_context: str = ""
    error: Optional[str] = None

    def to_json(self) -> str:
        """转换为 Claude Code Hook 规范的 JSON 输出"""
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": self.additional_context
            }
        }

        if self.error:
            output["error"] = self.error

        return json.dumps(output, ensure_ascii=False)


class SessionStartHook:
    """SessionStart Hook 处理器

    在新对话开始时，检索相关记忆并注入到上下文中。
    同时执行记忆淡化和强化机制。
    """

    def __init__(
        self,
        storage_root: Path | None = None,
        max_memories: int = 10,
        min_confidence: float = 0.3,
        max_context_length: int = 2000,
        apply_decay: bool = True,
    ):
        """初始化处理器

        Args:
            storage_root: 存储根目录
            max_memories: 最大注入记忆数量
            min_confidence: 最低置信度阈值
            max_context_length: 最大上下文长度
            apply_decay: 是否应用记忆衰减
        """
        self.storage_root = storage_root or get_storage_path()
        self.max_memories = max_memories
        self.min_confidence = min_confidence
        self.max_context_length = max_context_length
        self.apply_decay = apply_decay

    def handle(self, event_type: str = "startup") -> HookOutput:
        """处理 SessionStart 事件

        行为：
        1. 检查记忆注入是否启用
        2. 应用记忆衰减（如果启用）
        3. 检索相关记忆并强化
        4. 格式化并返回注入内容

        Args:
            event_type: 事件类型（startup 或 resume）

        Returns:
            Hook 输出
        """
        try:
            # 确保存储目录存在
            ensure_storage_dir(self.storage_root)

            # 检查是否启用记忆注入
            if not self._is_injection_enabled():
                return HookOutput()

            store = MemoryStore(self.storage_root)

            # 应用记忆衰减（如果启用）
            if self.apply_decay:
                self._apply_memory_decay(store)

            # 执行冷存储归档（归档旧数据）
            self._archive_cold_data()

            # 检索相关记忆
            retriever = MemoryRetriever(store)

            memories = retriever.retrieve_relevant(
                limit=self.max_memories,
                min_confidence=self.min_confidence
            )

            if not memories:
                return HookOutput()

            # 触发记忆强化（被检索的记忆会被强化）
            self._strengthen_triggered_memories(store, memories)

            # 格式化注入内容
            context = retriever.format_for_injection(
                memories,
                max_length=self.max_context_length
            )

            return HookOutput(additional_context=context)

        except Exception as e:
            # 错误不应阻止会话启动，仅记录
            return HookOutput(error=str(e))

    def _is_injection_enabled(self) -> bool:
        """检查记忆注入是否启用"""
        from ..storage.json_store import read_json

        profile_path = self.storage_root / "profile.json"
        profile = read_json(profile_path)

        if not profile:
            return True  # 默认启用

        settings = profile.get("settings", {})
        return settings.get("injection_enabled", True)

    def _apply_memory_decay(self, store: MemoryStore) -> None:
        """应用记忆衰减

        Args:
            store: 记忆存储
        """
        decay = MemoryDecay(half_life_days=self._get_decay_half_life())

        # 获取所有记忆
        all_memories = store.get_all()

        # 应用衰减
        to_keep, to_remove = decay.process_batch(all_memories)

        # 更新保留的记忆
        for memory in to_keep:
            store.save(memory)

        # 删除低置信度记忆
        for memory in to_remove:
            store.delete(memory.id)

    def _get_decay_half_life(self) -> int:
        """获取衰减半衰期配置"""
        from ..storage.json_store import read_json

        profile_path = self.storage_root / "profile.json"
        profile = read_json(profile_path)

        if not profile:
            return 30  # 默认 30 天

        settings = profile.get("settings", {})
        return settings.get("decay_half_life_days", 30)

    def _strengthen_triggered_memories(
        self,
        store: MemoryStore,
        memories: list,
    ) -> None:
        """强化被触发的记忆

        Args:
            store: 记忆存储
            memories: 被触发的记忆列表 (ScoredMemory 对象)
        """
        for scored_memory in memories:
            # ScoredMemory 包装了实际的 MemoryAtom
            store.trigger(scored_memory.memory.id)

    def _archive_cold_data(self) -> None:
        """归档冷数据

        将超过 90 天的旧证据归档到压缩文件。
        """
        try:
            cold_storage = ColdStorageManager(self.storage_root)
            cold_storage.archive_old_evidence(cutoff_days=90)
        except Exception:
            # 归档失败不应影响主流程，静默忽略
            pass


def generate_context() -> str:
    """生成记忆上下文的便捷函数

    供 CLI 命令调用。

    Returns:
        JSON 格式的 Hook 输出
    """
    hook = SessionStartHook()
    output = hook.handle()
    return output.to_json()
