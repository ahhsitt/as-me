"""证据存储

实现证据的持久化存储和查询。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..storage.base import ensure_storage_dir, get_storage_path
from ..storage.json_store import read_json, write_json
from .models import Evidence


class EvidenceStore:
    """证据存储

    存储支撑记忆和原则的证据。
    """

    EVIDENCE_FILE = "evidence/index.json"

    def __init__(self, storage_root: Path | None = None):
        """初始化存储

        Args:
            storage_root: 存储根目录，默认 ~/.as-me/
        """
        self.storage_root = storage_root or get_storage_path()
        self.evidence_file = self.storage_root / self.EVIDENCE_FILE
        ensure_storage_dir(self.storage_root)

    def save(self, evidence: Evidence) -> Evidence:
        """保存证据

        Args:
            evidence: 证据对象

        Returns:
            保存后的证据
        """
        all_evidence = self._load_all()

        # 检查是否已存在
        existing_idx = None
        for i, e in enumerate(all_evidence):
            if e["id"] == evidence.id:
                existing_idx = i
                break

        evidence_dict = evidence.model_dump(mode="json")

        if existing_idx is not None:
            all_evidence[existing_idx] = evidence_dict
        else:
            all_evidence.append(evidence_dict)

        self._save_all(all_evidence)
        return evidence

    def save_batch(self, evidences: List[Evidence]) -> List[Evidence]:
        """批量保存证据

        Args:
            evidences: 证据列表

        Returns:
            保存后的证据列表
        """
        all_evidence = self._load_all()
        existing_ids = {e["id"] for e in all_evidence}

        for evidence in evidences:
            evidence_dict = evidence.model_dump(mode="json")
            if evidence.id in existing_ids:
                for i, e in enumerate(all_evidence):
                    if e["id"] == evidence.id:
                        all_evidence[i] = evidence_dict
                        break
            else:
                all_evidence.append(evidence_dict)

        self._save_all(all_evidence)
        return evidences

    def get_by_id(self, evidence_id: str) -> Optional[Evidence]:
        """根据 ID 获取证据

        Args:
            evidence_id: 证据 ID

        Returns:
            证据对象，不存在时返回 None
        """
        all_evidence = self._load_all()
        for e in all_evidence:
            if e["id"] == evidence_id:
                return Evidence.model_validate(e)
        return None

    def get_by_memory(self, memory_id: str) -> List[Evidence]:
        """获取记忆的所有证据

        Args:
            memory_id: 记忆 ID

        Returns:
            证据列表
        """
        all_evidence = self._load_all()
        result = []
        for e in all_evidence:
            if e.get("memory_id") == memory_id:
                result.append(Evidence.model_validate(e))
        return result

    def get_by_principle(self, principle_id: str) -> List[Evidence]:
        """获取原则的所有证据

        Args:
            principle_id: 原则 ID

        Returns:
            证据列表
        """
        all_evidence = self._load_all()
        result = []
        for e in all_evidence:
            if e.get("principle_id") == principle_id:
                result.append(Evidence.model_validate(e))
        return result

    def get_by_session(self, session_id: str) -> List[Evidence]:
        """获取会话的所有证据

        Args:
            session_id: 会话 ID

        Returns:
            证据列表
        """
        all_evidence = self._load_all()
        result = []
        for e in all_evidence:
            if e.get("source_session_id") == session_id:
                result.append(Evidence.model_validate(e))
        return result

    def delete(self, evidence_id: str) -> bool:
        """删除证据

        Args:
            evidence_id: 证据 ID

        Returns:
            是否成功删除
        """
        all_evidence = self._load_all()
        original_len = len(all_evidence)
        all_evidence = [e for e in all_evidence if e["id"] != evidence_id]

        if len(all_evidence) < original_len:
            self._save_all(all_evidence)
            return True
        return False

    def delete_by_memory(self, memory_id: str) -> int:
        """删除记忆的所有证据

        Args:
            memory_id: 记忆 ID

        Returns:
            删除的证据数量
        """
        all_evidence = self._load_all()
        original_len = len(all_evidence)
        all_evidence = [e for e in all_evidence if e.get("memory_id") != memory_id]

        deleted = original_len - len(all_evidence)
        if deleted > 0:
            self._save_all(all_evidence)
        return deleted

    def delete_by_principle(self, principle_id: str) -> int:
        """删除原则的所有证据

        Args:
            principle_id: 原则 ID

        Returns:
            删除的证据数量
        """
        all_evidence = self._load_all()
        original_len = len(all_evidence)
        all_evidence = [e for e in all_evidence if e.get("principle_id") != principle_id]

        deleted = original_len - len(all_evidence)
        if deleted > 0:
            self._save_all(all_evidence)
        return deleted

    def count(self) -> int:
        """统计证据数量

        Returns:
            证据数量
        """
        return len(self._load_all())

    def _load_all(self) -> List[Dict]:
        """加载所有证据"""
        return read_json(self.evidence_file) or []

    def _save_all(self, evidences: List[Dict]) -> None:
        """保存所有证据"""
        write_json(self.evidence_file, evidences)
