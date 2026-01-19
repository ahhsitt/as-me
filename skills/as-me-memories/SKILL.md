---
name: as-me-memories
description: 查看和管理存储的记忆原子
---

# View and Manage Memories

查看、管理和删除已存储的记忆原子。

## 记忆类型

- **identity** (身份背景): 用户的职业、角色、目标
- **value** (价值信念): 核心价值观和原则
- **thinking** (思维认知): 思考和决策方式
- **preference** (偏好习惯): 工具、方法、风格偏好
- **communication** (沟通表达): 沟通风格和表达习惯

## 记忆层级

- **short_term**: 短期记忆，新提取的特征
- **working**: 工作记忆，被多次触发的特征
- **long_term**: 长期记忆，高置信度的稳定特征

## 执行步骤

### Step 1: 读取记忆

```bash
if [ -f ~/.as-me/memories/short-term.json.gz ]; then
  gzip -dc ~/.as-me/memories/short-term.json.gz
elif [ -f ~/.as-me/memories/short-term.json ]; then
  cat ~/.as-me/memories/short-term.json
else
  echo "[]"
fi
```

### Step 2: 展示记忆列表

以清晰的格式展示记忆：

```
共 N 条记忆

[ID前8位] [类型] [层级] 内容摘要... (置信度%)
```

### Step 3: 支持的操作

根据用户请求执行：

**列出记忆**
- 默认显示所有记忆
- 支持按类型过滤：`--type identity`
- 支持按层级过滤：`--tier long_term`
- 支持限制数量：`--limit 10`

**查看详情**
- 根据 ID 前缀查找记忆
- 显示完整信息：类型、内容、置信度、创建时间、触发次数等

**删除记忆**
- 根据 ID 删除指定记忆
- 删除前询问用户确认

### Step 4: 写回更新

如果有删除操作，更新记忆文件：

```bash
python3 << 'EOF'
import gzip
import json
from pathlib import Path

memories_dir = Path.home() / ".as-me" / "memories"
gz_path = memories_dir / "short-term.json.gz"

# memories 变量包含更新后的记忆列表
memories = []  # 替换为实际数据

with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
    json.dump(memories, f, ensure_ascii=False)
EOF
```

## 输出格式示例

**列表格式：**
```
共 5 条记忆

[abc123ef] [身份背景] [工作] 产品经理，负责 B 端 SaaS 产品 (85%)
[def456ab] [偏好习惯] [短期] 偏好使用 TypeScript (75%)
[ghi789cd] [思维认知] [长期] 习惯用第一性原理分析问题 (90%)
```

**详情格式：**
```
记忆 ID: abc123ef-1234-5678-90ab-cdef12345678
类型: 身份背景 (identity)
层级: 工作记忆 (working)
置信度: 85%

内容:
  产品经理，负责 B 端 SaaS 产品

创建时间: 2026-01-16 10:00:00
最后触发: 2026-01-19 15:30:00
触发次数: 3
标签: llm_extracted
```
