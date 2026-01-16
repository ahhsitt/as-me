---
name: principles
description: 查看和管理内核原则
---

# /as-me:principles

查看、确认、修正和管理从记忆中聚合形成的内核原则。

## 原则维度

- **worldview** (世界观): 对事物本质的理解
- **values** (价值观): 重要性和优先级判断
- **decision_pattern** (决策模式): 做决定的方式和逻辑
- **domain_thought** (领域思想): 特定领域的专业认知

## 使用方法

### 列出原则

```
/as-me:principles list
```

选项：
- `--dimension, -d <DIM>`: 按维度过滤
- `--confirmed`: 仅显示已确认的
- `--active`: 仅显示活跃的（默认）
- `--verbose, -v`: 显示详细信息

### 查看原则详情

```
/as-me:principles show <ID>
```

### 确认原则

确认后原则的置信度会提升。

```
/as-me:principles confirm <ID>
```

### 修正原则

修改原则陈述并记录修正原因。

```
/as-me:principles correct <ID> -s "新的陈述" -r "修正原因"
```

### 删除原则

```
/as-me:principles delete <ID>
```

## 示例

列出所有决策模式原则：
```
/as-me:principles list -d decision_pattern
```

列出已确认的原则（详细信息）：
```
/as-me:principles list --confirmed -v
```

确认一个原则：
```
/as-me:principles confirm abc123ef
```

修正一个原则：
```
/as-me:principles correct abc123ef -s "更倾向于实用主义而非完美主义" -r "原描述过于绝对"
```

## 输出格式

列表格式：
```
共 3 条原则

[abc123ef] [决策模式] [✓] 倾向于先验证再实现... (85%)
[def456ab] [价值观] [ ] 注重代码可读性... (70%)
```

详情格式：
```
原则 ID: abc123ef-1234-5678-90ab-cdef12345678
维度: 决策模式
置信度: 85%
用户确认: 是
活跃状态: 是

陈述:
  倾向于先验证再实现，而不是边实现边调试

证据数量: 5
创建时间: 2026-01-15 10:00:00
更新时间: 2026-01-16 15:30:00
```

## 原则形成

原则由系统自动从相似记忆中聚合形成：
1. 当同类型记忆累积到 5 条以上
2. 平均置信度达到 60% 以上
3. 系统会自动概括这些记忆形成一个原则

用户可以确认或修正自动生成的原则，使其更准确。
