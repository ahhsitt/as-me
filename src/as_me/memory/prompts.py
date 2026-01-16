"""记忆提取提示词模板

定义用于 LLM 分析对话并提取记忆的提示词。
"""

from __future__ import annotations

from string import Template


EXTRACTION_PROMPT = Template("""分析以下对话，提取用户的特征信息。

## 对话内容
$conversation

## 提取维度
1. **技术偏好 (tech_preference)**: 编程语言、框架、工具、代码风格偏好
2. **思维模式 (thinking_pattern)**: 决策方式、推理风格、问题分析方法
3. **语言风格 (language_style)**: 表达习惯、常用词汇、沟通方式
4. **行为习惯 (behavior_habit)**: 工作流程、关注领域、操作习惯

## 提取规则
1. 只提取有明确证据支持的特征
2. 每个特征需要有具体的对话引用作为证据
3. 置信度基于证据的明确程度：
   - 0.8-1.0: 用户明确表达的偏好
   - 0.6-0.8: 从用户行为推断的偏好
   - 0.4-0.6: 可能的偏好，需要更多证据
4. 不要推断用户没有表达或暗示的内容
5. 标签应使用小写英文，多个单词用下划线连接

## 输出格式
请以 JSON 格式输出，结构如下：
```json
{
  "memories": [
    {
      "type": "tech_preference|thinking_pattern|language_style|behavior_habit",
      "content": "具体内容（简洁描述，不超过100字）",
      "confidence": 0.0-1.0,
      "evidence": "支撑引用（原文摘录）",
      "tags": ["tag1", "tag2"]
    }
  ],
  "analysis_notes": "分析过程的简要说明（可选）"
}
```

如果对话中没有可提取的特征，返回空列表：
```json
{
  "memories": [],
  "analysis_notes": "未发现明确的用户特征"
}
```
""")


FEATURE_CHECK_PROMPT = Template("""快速判断以下对话是否包含可提取的用户特征。

## 对话内容
$conversation

## 判断标准
以下情况认为有可提取特征：
1. 用户表达了技术偏好（如"我喜欢用 TypeScript"、"我习惯用 vim"）
2. 用户展示了思维模式（如决策过程、问题分析方法）
3. 用户有独特的语言风格（如常用词汇、表达习惯）
4. 用户提及了工作习惯（如"我通常先写测试"）

以下情况认为无可提取特征：
1. 纯技术问答（如"Python 怎么读文件"）
2. 通用对话（如问候、感谢）
3. 仅包含代码输出或错误信息

## 输出格式
```json
{
  "has_features": true|false,
  "reason": "简要说明判断理由"
}
```
""")


MERGE_PROMPT = Template("""判断以下两个记忆是否表达相同或相似的用户特征，如果是则合并。

## 记忆 A
- 类型: $type_a
- 内容: $content_a
- 置信度: $confidence_a

## 记忆 B
- 类型: $type_b
- 内容: $content_b
- 置信度: $confidence_b

## 判断标准
1. 类型必须相同才能合并
2. 内容语义相近（如"偏好 TypeScript" 和 "喜欢静态类型语言"）
3. 合并后的内容应该更加准确和全面
4. 合并后的置信度取两者中较高的值

## 输出格式
```json
{
  "should_merge": true|false,
  "merged_content": "合并后的内容（如果 should_merge 为 true）",
  "merged_confidence": 0.0-1.0,
  "reason": "合并或不合并的理由"
}
```
""")


def format_conversation_for_extraction(messages: list[str], max_length: int = 4000) -> str:
    """格式化对话内容用于提取

    Args:
        messages: 用户消息列表
        max_length: 最大字符数

    Returns:
        格式化后的对话文本
    """
    formatted = []
    total_length = 0

    for i, msg in enumerate(messages, 1):
        line = f"[用户消息 {i}]\n{msg}\n"
        if total_length + len(line) > max_length:
            # 截断最后一条消息
            remaining = max_length - total_length - 50
            if remaining > 100:
                line = f"[用户消息 {i}]\n{msg[:remaining]}...\n"
                formatted.append(line)
            break
        formatted.append(line)
        total_length += len(line)

    return "\n".join(formatted)
