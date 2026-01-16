"""冷数据压缩管理

实现 gzip 压缩归档功能。
"""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .json_store import read_json, write_json


class ColdStorageManager:
    """冷数据压缩管理器

    负责将旧数据归档到压缩文件。
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.archive_path = base_path / "archive"

    def archive_old_evidence(self, cutoff_days: int = 90) -> int:
        """归档旧证据到压缩文件

        Args:
            cutoff_days: 超过此天数的证据将被归档

        Returns:
            归档的证据数量
        """
        cutoff = datetime.now() - timedelta(days=cutoff_days)
        evidence_file = self.base_path / "evidence" / "index.json"

        all_evidence = read_json(evidence_file)
        if not all_evidence:
            return 0

        # 分离新旧数据
        recent = []
        archive = []
        for e in all_evidence:
            timestamp_str = e.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp.replace(tzinfo=None) > cutoff:
                    recent.append(e)
                else:
                    archive.append(e)
            except (ValueError, TypeError):
                # 无法解析时间戳，保留在 recent
                recent.append(e)

        if not archive:
            return 0

        # 压缩归档
        year_month = cutoff.strftime("%Y-%m")
        archive_file = self.archive_path / f"evidence-{year_month}.json.gz"
        self._write_gzip(archive_file, archive)

        # 更新原文件
        write_json(evidence_file, recent)

        return len(archive)

    def archive_old_memories(self, memories: List[Dict], cutoff_days: int = 90) -> tuple[List[Dict], int]:
        """归档旧记忆

        Args:
            memories: 记忆列表
            cutoff_days: 超过此天数且置信度低的记忆将被归档

        Returns:
            (保留的记忆列表, 归档数量)
        """
        cutoff = datetime.now() - timedelta(days=cutoff_days)

        recent = []
        archive = []
        for m in memories:
            timestamp_str = m.get("last_triggered_at", m.get("created_at", ""))
            confidence = m.get("confidence", 1.0)

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # 低置信度且过期的记忆归档
                if timestamp.replace(tzinfo=None) < cutoff and confidence < 0.3:
                    archive.append(m)
                else:
                    recent.append(m)
            except (ValueError, TypeError):
                recent.append(m)

        if archive:
            year_month = datetime.now().strftime("%Y-%m")
            archive_file = self.archive_path / f"memories-{year_month}.json.gz"
            self._append_to_archive(archive_file, archive)

        return recent, len(archive)

    def load_archived_evidence(self, year_month: str) -> List[Dict]:
        """按需加载归档证据

        Args:
            year_month: 年月字符串，如 "2026-01"

        Returns:
            证据列表
        """
        archive_file = self.archive_path / f"evidence-{year_month}.json.gz"
        return self._read_gzip(archive_file)

    def load_archived_memories(self, year_month: str) -> List[Dict]:
        """按需加载归档记忆

        Args:
            year_month: 年月字符串，如 "2026-01"

        Returns:
            记忆列表
        """
        archive_file = self.archive_path / f"memories-{year_month}.json.gz"
        return self._read_gzip(archive_file)

    def list_archives(self, prefix: str = "") -> List[str]:
        """列出所有归档文件

        Args:
            prefix: 文件名前缀过滤

        Returns:
            归档文件名列表
        """
        if not self.archive_path.exists():
            return []

        archives = []
        for f in self.archive_path.glob("*.json.gz"):
            if not prefix or f.name.startswith(prefix):
                archives.append(f.name)
        return sorted(archives)

    def _write_gzip(self, path: Path, data: Any) -> None:
        """写入 gzip 压缩文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def _read_gzip(self, path: Path) -> List[Dict]:
        """读取 gzip 压缩文件"""
        if not path.exists():
            return []

        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)

    def _append_to_archive(self, path: Path, new_data: List[Dict]) -> None:
        """追加数据到归档文件"""
        existing = self._read_gzip(path)
        existing.extend(new_data)
        self._write_gzip(path, existing)
