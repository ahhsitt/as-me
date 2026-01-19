---
name: as-me-analyze
description: 分析当前对话并提取用户记忆
---

# /as-me-analyze

> **推荐**: 请使用 `/as-me:analyze` skill，它能利用 Claude 自身的 LLM 能力进行更精准的记忆提取。

分析当前对话，提取用户的特征、偏好和习惯。

## 使用方法

直接运行命令即可触发记忆分析：

```
/as-me-analyze
```

此命令会调用 `/as-me:analyze` skill 执行分析。

## 提取的记忆类型

1. **技术偏好 (tech_preference)**: 编程语言、框架、工具、架构偏好
2. **思维模式 (thinking_pattern)**: 决策方式、推理风格、问题分析方法
3. **行为习惯 (behavior_habit)**: 工作流程、操作习惯
4. **语言风格 (language_style)**: 表达习惯、沟通偏好

## 查看分析结果

```
/as-me-memories list
```

提取的记忆存储在 `~/.as-me/memories/` 目录下。

## 相关命令

- `/as-me-memories` - 查看和管理记忆
- `/as-me-principles` - 查看和管理原则
- `/as-me-evolution` - 查看演化历史
