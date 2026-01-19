---
name: as-me-principles
description: 查看和管理从记忆聚合形成的内核原则
---

# View and Manage Principles

查看、确认、修正和管理从记忆中聚合形成的内核原则。

## 原则维度

- **worldview** (世界观): 对事物本质的理解
- **values** (价值观): 重要性和优先级判断
- **decision_pattern** (决策模式): 做决定的方式和逻辑
- **domain_thought** (领域思想): 特定领域的专业认知

## 原则形成机制

原则由系统自动从相似记忆中聚合形成：
1. 当同类型记忆累积到 5 条以上
2. 平均置信度达到 60% 以上
3. 系统会自动概括这些记忆形成一个原则

## 执行步骤

### Step 1: 读取原则

```bash
if [ -f ~/.as-me/principles/active.json.gz ]; then
  gzip -dc ~/.as-me/principles/active.json.gz
elif [ -f ~/.as-me/principles/active.json ]; then
  cat ~/.as-me/principles/active.json
else
  echo "[]"
fi
```

### Step 2: 展示原则列表

以清晰的格式展示原则：

```
共 N 条原则

[ID前8位] [维度] [✓/空] 原则陈述摘要... (置信度%)
```

其中 ✓ 表示用户已确认。

### Step 3: 支持的操作

**列出原则**
- 默认显示所有活跃原则
- 支持按维度过滤：`--dimension decision_pattern`
- 支持只显示已确认：`--confirmed`

**查看详情**
- 显示完整信息：维度、陈述、置信度、证据数量、确认状态等

**确认原则**
- 用户确认原则正确
- 提升置信度 20%（上限 100%）
- 记录确认事件到演化历史

**修正原则**
- 修改原则陈述
- 记录修正原因
- 记录修正事件到演化历史

**删除原则**
- 删除指定原则
- 删除前询问用户确认

### Step 4: 写回更新

如果有修改操作，更新原则文件并记录演化事件：

```bash
python3 << 'EOF'
import gzip
import json
from pathlib import Path
from datetime import datetime
import uuid

principles_dir = Path.home() / ".as-me" / "principles"
principles_dir.mkdir(parents=True, exist_ok=True)
gz_path = principles_dir / "active.json.gz"

# principles 变量包含更新后的原则列表
principles = []  # 替换为实际数据

with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
    json.dump(principles, f, ensure_ascii=False)
EOF
```

## 输出格式示例

**列表格式：**
```
共 3 条原则

[abc123ef] [决策模式] [✓] 倾向于先验证再实现，而不是边实现边调试 (100%)
[def456ab] [价值观] [ ] 注重代码可读性胜过性能优化 (70%)
[ghi789cd] [世界观] [✓] 相信简洁是终极的复杂 (95%)
```

**详情格式：**
```
原则 ID: abc123ef-1234-5678-90ab-cdef12345678
维度: 决策模式 (decision_pattern)
置信度: 100%
用户确认: 是
活跃状态: 是

陈述:
  倾向于先验证再实现，而不是边实现边调试

证据数量: 5
创建时间: 2026-01-15 10:00:00
更新时间: 2026-01-19 15:30:00
```
