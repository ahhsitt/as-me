---
name: as-me-analyze
description: 分析对话历史并提取用户记忆（已自动化，通常无需手动执行）
---

# /as-me-analyze

> **注意**: 记忆提取已自动化！每次启动新会话时，系统会自动在后台分析上次会话并提取记忆。通常不需要手动执行此命令。

分析 Claude Code 对话历史，自动提取用户特征并存储为记忆原子。

## 自动提取机制

从 v0.2.0 开始，记忆提取已完全自动化：

1. **SessionStart Hook**: 每次启动新会话时自动触发
2. **后台异步处理**: 不阻塞用户的下一次对话
3. **智能去重**: 自动跳过已分析的会话
4. **失败重试**: 自动重试失败的分析任务

## 何时需要手动分析

通常情况下，你不需要手动执行此命令。以下场景可能需要：

- 首次安装后，需要分析历史会话
- 自动分析被禁用时
- 需要重新分析特定会话

## 使用方法

由于记忆提取已自动化，直接运行命令会显示提示信息：

```
/as-me-analyze
```

如需强制手动分析，请使用 `--force` 选项：

```
/as-me-analyze --force
```

### 选项

- `--force` 或 `-f`: 强制执行手动分析
- `--session <ID>` 或 `-s <ID>`: 分析指定会话
- `--all`: 分析所有未分析的会话
- `--limit <N>` 或 `-n <N>`: 限制分析会话数量（默认 5）

## 提取的记忆类型

1. **技术偏好 (tech_preference)**: 编程语言、框架、工具偏好
2. **思维模式 (thinking_pattern)**: 决策方式、推理风格
3. **语言风格 (language_style)**: 表达习惯、常用词汇
4. **行为习惯 (behavior_habit)**: 工作流程、操作习惯

## 示例

查看自动化提示：
```
/as-me-analyze
```

强制分析最近一个对话：
```
/as-me-analyze --force
```

分析最近 10 个未分析的对话：
```
/as-me-analyze --force --all -n 10
```

分析指定会话：
```
/as-me-analyze -s abc123ef-...
```

## 查看分析结果

```
/as-me-memories list
```

提取的记忆存储在 `~/.as-me/memories/` 目录下。

## 配置自动提取

可以在 `~/.as-me/profile.json` 中配置自动提取行为：

```json
{
  "settings": {
    "auto_extraction": {
      "enabled": true,
      "max_sessions_per_run": 5,
      "max_messages_per_session": 100,
      "retry_limit": 3
    }
  }
}
```
