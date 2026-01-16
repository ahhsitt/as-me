"""记忆提取器

从对话中提取用户特征。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from ..errors import AsmeError, ErrorCode
from .models import MemoryAtom, MemoryType
from .prompts import (
    EXTRACTION_PROMPT,
    FEATURE_CHECK_PROMPT,
    format_conversation_for_extraction,
)


@dataclass
class ExtractionResult:
    """提取结果"""
    memories: List[MemoryAtom]
    analysis_notes: str = ""


class MemoryExtractor:
    """记忆提取器

    使用 LLM 从对话中提取用户特征。
    """

    TYPE_MAP = {
        "tech_preference": MemoryType.TECH_PREFERENCE,
        "thinking_pattern": MemoryType.THINKING_PATTERN,
        "language_style": MemoryType.LANGUAGE_STYLE,
        "behavior_habit": MemoryType.BEHAVIOR_HABIT,
    }

    def __init__(self, llm_client=None):
        """初始化提取器

        Args:
            llm_client: LLM 客户端（用于调用 Claude API）
                       如果为 None，使用模拟模式
        """
        self.llm_client = llm_client

    def has_extractable_features(self, messages: List[str]) -> bool:
        """快速判断对话是否包含可提取特征

        Args:
            messages: 用户消息列表

        Returns:
            是否包含可提取特征
        """
        if not messages:
            return False

        # 合并所有消息
        combined = " ".join(messages)

        # 关键词启发式检查（快速过滤）
        feature_indicators = [
            # 偏好表达
            "我喜欢", "我偏好", "我习惯", "我倾向", "我更喜欢",
            "prefer", "like to", "usually",
            # 技术偏好
            "用 ", "使用 ", "选择 ", "而不是",
            # 行为习惯
            "我通常", "我一般", "我总是", "我从不",
            # 思维模式
            "我认为", "我觉得", "在我看来", "我的理解",
        ]

        for indicator in feature_indicators:
            if indicator in combined:
                return True

        # 如果有 LLM 客户端，使用 LLM 进行更准确的判断
        if self.llm_client:
            return self._llm_check_features(messages)

        return False

    def extract(self, messages: List[str], session_id: str) -> ExtractionResult:
        """从对话中提取记忆

        Args:
            messages: 用户消息列表
            session_id: 会话 ID

        Returns:
            提取结果

        Raises:
            AsmeError: 提取失败时
        """
        if not messages:
            return ExtractionResult(memories=[], analysis_notes="无消息可分析")

        # 格式化对话
        conversation = format_conversation_for_extraction(messages)

        # 使用 LLM 提取
        if self.llm_client:
            return self._llm_extract(conversation, session_id)

        # 模拟模式：基于关键词的简单提取
        return self._heuristic_extract(messages, session_id)

    def _llm_check_features(self, messages: List[str]) -> bool:
        """使用 LLM 检查是否有可提取特征"""
        conversation = format_conversation_for_extraction(messages, max_length=2000)
        prompt = FEATURE_CHECK_PROMPT.substitute(conversation=conversation)

        try:
            response = self._call_llm(prompt)
            result = self._parse_json_response(response)
            return result.get("has_features", False)
        except Exception:
            # 出错时保守返回 True，让后续提取阶段处理
            return True

    def _llm_extract(self, conversation: str, session_id: str) -> ExtractionResult:
        """使用 LLM 提取记忆"""
        prompt = EXTRACTION_PROMPT.substitute(conversation=conversation)

        try:
            response = self._call_llm(prompt)
            result = self._parse_json_response(response)
        except Exception as e:
            raise AsmeError(
                ErrorCode.EXTRACTION_FAILED,
                f"LLM 提取失败: {e}"
            )

        memories = []
        for item in result.get("memories", []):
            memory = self._create_memory_from_dict(item, session_id)
            if memory:
                memories.append(memory)

        return ExtractionResult(
            memories=memories,
            analysis_notes=result.get("analysis_notes", "")
        )

    def _heuristic_extract(self, messages: List[str], session_id: str) -> ExtractionResult:
        """启发式提取（模拟模式）

        基于关键词匹配的简单提取逻辑。
        """
        memories = []
        combined = " ".join(messages)

        # 技术偏好模式
        tech_patterns = [
            (r"我(喜欢|偏好|习惯)用?\s*(\w+)", 0.7),
            (r"(TypeScript|Python|Go|Rust|Java)\s*比\s*(\w+)\s*好", 0.6),
            (r"我用\s*(\w+)\s*而不是\s*(\w+)", 0.65),
        ]

        for pattern, confidence in tech_patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                content = f"偏好使用 {match[-1] if isinstance(match, tuple) else match}"
                memory = MemoryAtom(
                    type=MemoryType.TECH_PREFERENCE,
                    content=content[:500],
                    confidence=confidence,
                    source_session_id=session_id,
                    tags=["auto_extracted", "heuristic"],
                )
                memories.append(memory)

        # 行为习惯模式
        habit_patterns = [
            (r"我(通常|一般|总是|习惯)\s*(.{5,50})", 0.6),
        ]

        for pattern, confidence in habit_patterns:
            matches = re.findall(pattern, combined)
            for match in matches[:3]:  # 限制数量
                content = f"{match[0]}{match[1]}"
                memory = MemoryAtom(
                    type=MemoryType.BEHAVIOR_HABIT,
                    content=content[:500],
                    confidence=confidence,
                    source_session_id=session_id,
                    tags=["auto_extracted", "heuristic"],
                )
                memories.append(memory)

        return ExtractionResult(
            memories=memories,
            analysis_notes="启发式提取（模拟模式）"
        )

    def _call_llm(self, prompt: str) -> str:
        """调用 LLM

        Args:
            prompt: 提示词

        Returns:
            LLM 响应文本
        """
        if not self.llm_client:
            raise AsmeError(
                ErrorCode.EXTRACTION_FAILED,
                "LLM 客户端未配置"
            )

        # 调用 LLM 客户端
        # 这里假设 llm_client 有一个 complete 方法
        response = self.llm_client.complete(prompt)
        return response

    def _parse_json_response(self, response: str) -> dict:
        """解析 LLM 的 JSON 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典
        """
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { } 块
        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise AsmeError(
            ErrorCode.EXTRACTION_FAILED,
            "无法解析 LLM 响应为 JSON"
        )

    def _create_memory_from_dict(
        self,
        item: dict,
        session_id: str
    ) -> Optional[MemoryAtom]:
        """从字典创建记忆原子

        Args:
            item: 提取的记忆字典
            session_id: 会话 ID

        Returns:
            记忆原子，无效时返回 None
        """
        type_str = item.get("type", "")
        memory_type = self.TYPE_MAP.get(type_str)
        if not memory_type:
            return None

        content = item.get("content", "")
        if not content or len(content) > 500:
            return None

        confidence = item.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0, min(1, confidence))

        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        tags = [str(t) for t in tags if t]
        tags.append("llm_extracted")

        return MemoryAtom(
            type=memory_type,
            content=content,
            confidence=confidence,
            source_session_id=session_id,
            tags=tags,
        )
