"""原则聚合器

从记忆原子中聚合形成内核原则。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from string import Template
from typing import List, Optional

from ..memory.models import MemoryAtom, MemoryType
from ..memory.store import MemoryStore
from .evidence_store import EvidenceStore
from .models import Evidence, Principle, PrincipleDimension
from .store import PrincipleStore


# 聚合阈值
AGGREGATION_THRESHOLD = 5  # 同类记忆数量
MIN_CONFIDENCE = 0.6       # 最低平均置信度


# 记忆类型到原则维度的映射
TYPE_TO_DIMENSION = {
    MemoryType.TECH_PREFERENCE: PrincipleDimension.DOMAIN_THOUGHT,
    MemoryType.THINKING_PATTERN: PrincipleDimension.DECISION_PATTERN,
    MemoryType.BEHAVIOR_HABIT: PrincipleDimension.VALUES,
    MemoryType.LANGUAGE_STYLE: PrincipleDimension.WORLDVIEW,
}


AGGREGATION_PROMPT = Template("""分析以下相似的记忆，提取一个统一的原则陈述。

## 相似记忆
$memories

## 要求
1. 原则陈述应概括这些记忆的共同特征
2. 使用简洁、抽象的语言（不超过 100 字）
3. 避免具体的技术细节，关注更高层次的偏好或模式
4. 置信度基于记忆的一致性程度

## 输出格式
```json
{
  "statement": "原则陈述",
  "confidence": 0.0-1.0,
  "reasoning": "聚合推理说明"
}
```
""")


@dataclass
class AggregationCandidate:
    """聚合候选"""
    memories: List[MemoryAtom]
    dimension: PrincipleDimension
    avg_confidence: float


class PrincipleAggregator:
    """原则聚合器

    负责从相似记忆中聚合形成原则。
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        principle_store: PrincipleStore,
        evidence_store: EvidenceStore,
        llm_client=None
    ):
        """初始化聚合器

        Args:
            memory_store: 记忆存储
            principle_store: 原则存储
            evidence_store: 证据存储
            llm_client: LLM 客户端（可选）
        """
        self.memory_store = memory_store
        self.principle_store = principle_store
        self.evidence_store = evidence_store
        self.llm_client = llm_client

    def find_aggregation_candidates(self) -> List[AggregationCandidate]:
        """查找可聚合的记忆组

        Returns:
            聚合候选列表
        """
        candidates = []

        # 按类型分组记忆
        for memory_type in MemoryType:
            memories = self.memory_store.get_by_type(memory_type)

            if len(memories) < AGGREGATION_THRESHOLD:
                continue

            avg_confidence = sum(m.confidence for m in memories) / len(memories)
            if avg_confidence < MIN_CONFIDENCE:
                continue

            # 进一步按相似性分组
            groups = self._group_similar_memories(memories)

            for group in groups:
                if len(group) >= AGGREGATION_THRESHOLD:
                    group_avg = sum(m.confidence for m in group) / len(group)
                    if group_avg >= MIN_CONFIDENCE:
                        dimension = TYPE_TO_DIMENSION.get(
                            memory_type,
                            PrincipleDimension.DOMAIN_THOUGHT
                        )
                        candidates.append(AggregationCandidate(
                            memories=group,
                            dimension=dimension,
                            avg_confidence=group_avg,
                        ))

        return candidates

    def aggregate(self, candidate: AggregationCandidate) -> Optional[Principle]:
        """聚合记忆形成原则

        Args:
            candidate: 聚合候选

        Returns:
            生成的原则，失败时返回 None
        """
        if self.llm_client:
            return self._llm_aggregate(candidate)
        else:
            return self._heuristic_aggregate(candidate)

    def update_with_evidence(
        self,
        principle: Principle,
        memories: List[MemoryAtom]
    ) -> Principle:
        """用记忆更新原则的证据

        Args:
            principle: 原则
            memories: 相关记忆列表

        Returns:
            更新后的原则
        """
        # 为每个记忆创建证据
        for memory in memories:
            evidence = Evidence(
                principle_id=principle.id,
                source_session_id=memory.source_session_id,
                quote=memory.content,
                weight=memory.confidence,
            )
            self.evidence_store.save(evidence)

            # 更新记忆的关联原则
            memory.related_principle_id = principle.id
            self.memory_store.save(memory)

        # 更新原则的证据计数
        principle.evidence_count = len(memories)
        return self.principle_store.save(principle)

    def process_all_candidates(self) -> List[Principle]:
        """处理所有聚合候选

        Returns:
            新创建的原则列表
        """
        candidates = self.find_aggregation_candidates()
        new_principles = []

        for candidate in candidates:
            principle = self.aggregate(candidate)
            if principle:
                # 保存原则
                self.principle_store.save(principle)

                # 添加证据
                self.update_with_evidence(principle, candidate.memories)

                new_principles.append(principle)

        return new_principles

    def _group_similar_memories(
        self,
        memories: List[MemoryAtom]
    ) -> List[List[MemoryAtom]]:
        """将记忆按相似性分组

        简单实现：基于关键词重叠

        Args:
            memories: 记忆列表

        Returns:
            分组后的记忆列表
        """
        if len(memories) <= AGGREGATION_THRESHOLD:
            return [memories]

        # 简单实现：基于 tags 分组
        groups: dict[str, List[MemoryAtom]] = {}

        for memory in memories:
            # 使用第一个 tag 或 "default" 作为分组键
            key = memory.tags[0] if memory.tags else "default"
            if key not in groups:
                groups[key] = []
            groups[key].append(memory)

        # 过滤太小的组
        return [g for g in groups.values() if len(g) >= 2]

    def _llm_aggregate(self, candidate: AggregationCandidate) -> Optional[Principle]:
        """使用 LLM 聚合"""
        memories_text = "\n".join([
            f"- {m.content} (置信度: {m.confidence:.0%})"
            for m in candidate.memories
        ])

        prompt = AGGREGATION_PROMPT.substitute(memories=memories_text)

        try:
            response = self.llm_client.complete(prompt)
            result = self._parse_json_response(response)

            return Principle(
                dimension=candidate.dimension,
                statement=result.get("statement", "")[:200],
                confidence=float(result.get("confidence", candidate.avg_confidence)),
                evidence_count=len(candidate.memories),
            )
        except Exception:
            return self._heuristic_aggregate(candidate)

    def _heuristic_aggregate(self, candidate: AggregationCandidate) -> Optional[Principle]:
        """启发式聚合（模拟模式）"""
        # 选择置信度最高的记忆作为基础
        best_memory = max(candidate.memories, key=lambda m: m.confidence)

        # 简单概括
        statement = f"倾向于 {best_memory.content[:100]}"

        return Principle(
            dimension=candidate.dimension,
            statement=statement,
            confidence=candidate.avg_confidence,
            evidence_count=len(candidate.memories),
        )

    def _parse_json_response(self, response: str) -> dict:
        """解析 JSON 响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}
