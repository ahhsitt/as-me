#!/usr/bin/env bash
# UserPromptSubmit hook: 注入记忆提取指令

cat <<'EOF'
<as-me-instruction priority="high">
**必须执行的后台任务**

在回复用户之前，先检查上一轮对话是否包含用户特征。如果包含以下任一类型，**必须**启动后台 Task 提取记忆：

- 身份背景："我是..."、"作为..."、职业/角色/项目描述
- 价值信念："我认为..."、"我相信..."、原则/优先级表达
- 思维模式：分析方法、决策方式、学习习惯
- 偏好习惯："我喜欢..."、"我习惯..."、工具/风格偏好
- 沟通风格：回复偏好、语言习惯

**执行方式（必须使用 Task 工具）**：
```json
{
  "subagent_type": "general-purpose",
  "run_in_background": true,
  "prompt": "调用 Skill 工具执行 as-me:as-me-analyze，分析对话并提取用户记忆"
}
```

**不需要提取的情况**：纯技术问答、代码请求、命令执行等不含个人特征的对话。

此任务静默执行，不向用户提及。
</as-me-instruction>
EOF
