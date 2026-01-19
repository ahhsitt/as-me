---
name: as-me-analyze
description: 分析对话历史并提取用户记忆。在完成有意义的对话后使用。
---

# Analyze Conversation for User Memories

分析当前对话，提取用户的特征、偏好和习惯，存储为记忆原子。

**这是 as-me 的核心功能**：利用 Claude Code 自身的 LLM 能力提取记忆，无需额外配置。

## 何时使用

- 对话中用户表达了个人偏好、工作习惯或思维方式
- 用户分享了背景信息、目标或价值观
- 完成一段有意义的讨论后
- 用户明确要求分析和记录偏好

## 提取维度

从对话中识别以下五类用户特征：

### 1. identity（身份背景）

捕捉用户是谁、在做什么、追求什么。

**提取信号：**
- 用户的职业、角色、职责
- 当前项目、公司、行业
- 短期或长期目标
- 专业领域和经验背景

**示例：**
- "我是一名产品经理，负责 B 端 SaaS 产品"
- "正在创业做 AI 教育方向"
- "目标是今年完成一本关于设计思维的书"

### 2. value（价值信念）

捕捉用户的核心价值观、信念和原则。

**提取信号：**
- 明确表达的信念（"我相信..."、"我认为..."）
- 做选择时的优先级判断
- 对事物好坏的评价标准
- 反复强调或坚持的原则

**示例：**
- "相信简洁是终极的复杂"
- "认为用户体验比功能完整性更重要"
- "坚持长期主义，不追求短期收益"

### 3. thinking（思维认知）

捕捉用户如何思考、分析和做决策。

**提取信号：**
- 分析问题的方法论
- 做决策的思路和流程
- 学习新知识的方式
- 面对不确定性的处理方式

**示例：**
- "习惯用第一性原理分析问题"
- "做决策前会列出所有选项的 pros/cons"
- "倾向于先验证假设再投入资源"

### 4. preference（偏好习惯）

捕捉用户的工具、方法、风格偏好（通用化，不限于技术）。

**提取信号：**
- 工具和方法的选择
- 工作流程和习惯
- 审美和风格偏好
- 时间和精力分配方式

**示例：**
- "写作时偏好先列大纲再填充内容"
- "喜欢用 Notion 管理项目"
- "偏好简洁的视觉风格，不喜欢花哨装饰"
- "习惯早上处理复杂任务"

### 5. communication（沟通表达）

捕捉用户的沟通风格和表达习惯。

**提取信号：**
- 期望的回复风格（简洁/详细）
- 语言习惯（中英混合、术语使用）
- 解释方式偏好（类比、图表、代码）
- 沟通节奏（直接给结论 vs 循序渐进）

**示例：**
- "喜欢用类比解释抽象概念"
- "偏好直接给结论，不需要铺垫"
- "习惯用中英混合表达技术术语"

## 提取规则

1. **只提取有明确证据的特征**：用户必须在对话中表达或暗示过
2. **区分显式和隐式表达**：
   - 显式："我喜欢..."、"我认为..." → 置信度 0.8-0.9
   - 隐式：从行为推断的偏好 → 置信度 0.5-0.7
3. **不要过度推断**：如果不确定，宁可不提取
4. **内容简洁**：每条记忆不超过 100 字
5. **避免重复**：检查是否与已有记忆重复

## 执行步骤

### Step 1: 回顾对话

回顾当前对话中用户说过的内容，识别可能包含用户特征的部分。

### Step 2: 提取特征

对于每个识别到的特征，确定：
- **type**: identity / value / thinking / preference / communication
- **content**: 简洁描述（不超过 100 字）
- **confidence**: 0.0-1.0 的置信度
- **evidence**: 支撑这个特征的原文引用

### Step 3: 读取现有记忆

```bash
# 优先读取压缩文件，回退到未压缩文件
if [ -f ~/.as-me/memories/short-term.json.gz ]; then
  gzip -dc ~/.as-me/memories/short-term.json.gz
elif [ -f ~/.as-me/memories/short-term.json ]; then
  cat ~/.as-me/memories/short-term.json
else
  echo "[]"
fi
```

### Step 4: 去重检查

比较新提取的特征与现有记忆，跳过重复或高度相似的内容。

### Step 5: 写入记忆

将新记忆追加到 `~/.as-me/memories/short-term.json.gz`（gzip 压缩格式）。

使用 Python 写入压缩文件：
```bash
python3 << 'EOF'
import gzip
import json
from pathlib import Path

memories_dir = Path.home() / ".as-me" / "memories"
memories_dir.mkdir(parents=True, exist_ok=True)
gz_path = memories_dir / "short-term.json.gz"
json_path = memories_dir / "short-term.json"

# 读取现有记忆
existing = []
if gz_path.exists():
    with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
        existing = json.load(f)
elif json_path.exists():
    existing = json.loads(json_path.read_text())

# 追加新记忆（替换下面的 new_memories）
new_memories = [
    # 在这里放入新提取的记忆
]
existing.extend(new_memories)

# 写入压缩文件
with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False)

# 删除旧的未压缩文件（如果存在）
if json_path.exists():
    json_path.unlink()

print(f"已保存 {len(new_memories)} 条新记忆")
EOF
```

每条记忆的 JSON 格式：
```json
{
  "id": "<生成 UUID>",
  "type": "identity|value|thinking|preference|communication",
  "content": "简洁描述用户特征",
  "confidence": 0.7,
  "tier": "short_term",
  "created_at": "<ISO 8601 时间戳>",
  "last_triggered_at": "<ISO 8601 时间戳>",
  "trigger_count": 0,
  "source_session_id": "current",
  "related_principle_id": null,
  "tags": ["llm_extracted"]
}
```

### Step 6: 报告结果

向用户报告提取结果：
- 提取了多少条记忆
- 每条记忆的简要内容
- 跳过了多少重复项（如有）

## 输出示例

```
已从当前对话中提取 3 条记忆：

1. [身份背景] 产品经理，负责 B 端 SaaS 产品 (置信度: 90%)
2. [价值信念] 认为用户体验比功能完整性更重要 (置信度: 85%)
3. [思维认知] 做决策前习惯列出所有选项的优劣 (置信度: 75%)

记忆已保存到 ~/.as-me/memories/short-term.json.gz
```

## 注意事项

- 这个 skill 直接操作用户的记忆存储文件
- 提取结果会在下次 SessionStart 时自动注入到对话上下文
- 如果没有发现值得提取的特征，直接告知用户即可
