"""档案管理

管理用户档案和统计信息。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .memory.models import ProfileSettings, Profile
from .storage import get_storage_path
from .storage.json_store import read_json, write_json


class ProfileManager:
    """档案管理器

    负责管理用户档案和统计信息。
    """

    PROFILE_FILE = "profile.json"

    def __init__(self):
        """初始化档案管理器"""
        self._file_path = get_storage_path(self.PROFILE_FILE)

    def get(self) -> Profile:
        """获取用户档案

        如果档案不存在，创建默认档案。

        Returns:
            用户档案
        """
        data = read_json(self._file_path)
        if data:
            return Profile.model_validate(data)

        # 创建默认档案
        profile = Profile()
        self.save(profile)
        return profile

    def save(self, profile: Profile) -> Profile:
        """保存用户档案

        Args:
            profile: 用户档案

        Returns:
            保存后的档案
        """
        profile.updated_at = datetime.now()
        data = profile.model_dump(mode="json")
        write_json(self._file_path, data)
        return profile

    def update_settings(self, **kwargs) -> Profile:
        """更新档案设置

        Args:
            **kwargs: 设置参数

        Returns:
            更新后的档案
        """
        profile = self.get()

        # 更新设置
        for key, value in kwargs.items():
            if hasattr(profile.settings, key):
                setattr(profile.settings, key, value)

        return self.save(profile)

    def increment_memories(self, count: int = 1) -> Profile:
        """增加记忆计数

        Args:
            count: 增加数量

        Returns:
            更新后的档案
        """
        profile = self.get()
        profile.total_memories += count
        return self.save(profile)

    def decrement_memories(self, count: int = 1) -> Profile:
        """减少记忆计数

        Args:
            count: 减少数量

        Returns:
            更新后的档案
        """
        profile = self.get()
        profile.total_memories = max(0, profile.total_memories - count)
        return self.save(profile)

    def increment_principles(self, count: int = 1) -> Profile:
        """增加原则计数

        Args:
            count: 增加数量

        Returns:
            更新后的档案
        """
        profile = self.get()
        profile.total_principles += count
        return self.save(profile)

    def decrement_principles(self, count: int = 1) -> Profile:
        """减少原则计数

        Args:
            count: 减少数量

        Returns:
            更新后的档案
        """
        profile = self.get()
        profile.total_principles = max(0, profile.total_principles - count)
        return self.save(profile)

    def update_last_analyzed(self, session_id: str) -> Profile:
        """更新最后分析的会话

        Args:
            session_id: 会话 ID

        Returns:
            更新后的档案
        """
        profile = self.get()
        profile.last_analyzed_session = session_id
        return self.save(profile)

    def sync_counts(self) -> Profile:
        """同步记忆和原则计数

        从实际存储中重新计算计数。

        Returns:
            更新后的档案
        """
        from .memory.store import MemoryStore
        from .principle.store import PrincipleStore

        profile = self.get()

        # 重新计算记忆数量
        memory_store = MemoryStore()
        profile.total_memories = len(memory_store.get_all())

        # 重新计算原则数量
        principle_store = PrincipleStore()
        profile.total_principles = len(principle_store.get_all())

        return self.save(profile)

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        profile = self.get()
        return {
            "total_memories": profile.total_memories,
            "total_principles": profile.total_principles,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "last_analyzed_session": profile.last_analyzed_session,
            "settings": {
                "extraction_enabled": profile.settings.extraction_enabled,
                "injection_enabled": profile.settings.injection_enabled,
                "max_injected_memories": profile.settings.max_injected_memories,
                "confidence_threshold": profile.settings.confidence_threshold,
                "decay_half_life_days": profile.settings.decay_half_life_days,
            }
        }
