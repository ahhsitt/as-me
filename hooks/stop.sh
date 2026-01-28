#!/usr/bin/env bash
# Stop hook: 每次 Claude 回复后注入提示，让 Claude 判断是否需要提取用户记忆

set -euo pipefail

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "<as-me-memory-extraction>\n你刚刚完成了一轮回复。请判断当前对话是否包含值得提取的用户特征（身份背景、价值信念、思维模式、偏好习惯、沟通风格）。\n\n**判断标准：**\n- 用户是否表达了个人偏好、习惯或价值观？\n- 用户是否分享了背景信息、目标或专业领域？\n- 对话是否揭示了用户的思维方式或决策模式？\n\n**如果有值得提取的特征：**\n使用 Task 工具在后台调用 as-me:as-me-analyze skill 进行分析：\n```\nTask tool with:\n- subagent_type: \"general-purpose\"\n- run_in_background: true\n- prompt: \"调用 Skill 工具执行 as-me:as-me-analyze，分析当前对话并提取用户记忆\"\n```\n\n**如果没有值得提取的特征：**\n直接跳过，不需要任何操作。\n\n注意：不要向用户提及这个检查过程，静默执行即可。\n</as-me-memory-extraction>"
  }
}
EOF
