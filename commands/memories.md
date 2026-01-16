---
name: memories
description: 查看和管理存储的记忆
---

# /as-me:memories

查看、管理和删除已存储的记忆原子。

## 使用方法

### 列出记忆

```
/as-me:memories list
```

选项：
- `--type, -t <TYPE>`: 按类型过滤
  - `tech_preference`: 技术偏好
  - `thinking_pattern`: 思维模式
  - `behavior_habit`: 行为习惯
  - `language_style`: 语言风格
- `--tier <TIER>`: 按层级过滤
  - `short_term`: 短期记忆
  - `working`: 工作记忆
  - `long_term`: 长期记忆
- `--limit, -n <N>`: 显示数量限制（默认 20）
- `--verbose, -v`: 显示详细信息

### 查看记忆详情

```
/as-me:memories show <ID>
```

支持使用记忆 ID 的前缀（至少 8 位）。

### 删除记忆

```
/as-me:memories delete <ID>
```

删除前会要求确认。

## 示例

列出所有技术偏好：
```
/as-me:memories list -t tech_preference
```

列出长期记忆（详细信息）：
```
/as-me:memories list --tier long_term -v
```

查看特定记忆：
```
/as-me:memories show abc123ef
```

删除记忆：
```
/as-me:memories delete abc123ef
```

## 输出格式

列表格式：
```
共 5 条记忆

[abc123ef] [技术偏好] [工作] 偏好使用 TypeScript... (85%)
[def456ab] [行为习惯] [短期] 通常先写测试再实现... (75%)
```

详情格式：
```
记忆 ID: abc123ef-1234-5678-90ab-cdef12345678
类型: 技术偏好
层级: 工作
置信度: 85%

内容:
  偏好使用 TypeScript 而不是 JavaScript

来源会话: session-123
创建时间: 2026-01-16 10:00:00
最后触发: 2026-01-16 15:30:00
触发次数: 3
标签: typescript, language
```
