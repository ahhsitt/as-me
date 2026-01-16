# As-Me: AI 数字分身

一个 Claude Code 插件，从对话中自动学习用户特征，构建个人化的 AI 数字分身。

## 快速安装

### 方法 1：直接安装（推荐）

```bash
# 在 Claude Code 中运行
/plugin install ahhsitt/as-me
```

### 方法 2：从本地安装（开发用）

```bash
# 克隆仓库
git clone https://github.com/ahhsitt/as-me.git

# 安装 Python 依赖
cd as-me
pip install -e .

# 在 Claude Code 中安装插件
/plugin install /path/to/as-me
```

## 功能特性

- **自动记忆提取**: 每次启动新会话时自动在后台分析上次会话，无需手动操作
- **记忆注入**: 在新对话开始时自动注入相关记忆，让 AI 更好地理解你
- **内核原则**: 从记忆中聚合形成稳定的个人原则（世界观、价值观、决策模式）
- **演化追踪**: 记录原则如何随时间发展和演化
- **隐私优先**: 所有数据本地存储在 `~/.as-me/` 目录

## 使用方法

### 自动记忆提取

从 v0.2.0 开始，记忆提取已完全自动化：

1. **自动触发**: 每次启动新会话时，系统自动在后台分析上次会话
2. **非阻塞**: 后台异步执行，不影响正常对话
3. **智能去重**: 自动跳过已分析的会话
4. **失败重试**: 自动重试失败的分析任务

无需手动执行 `/as-me:analyze` 命令，系统会自动处理一切。

### 斜杠命令

安装后，在 Claude Code 中可以使用以下命令：

| 命令 | 描述 |
|------|------|
| `/as-me:analyze` | 手动分析（已自动化，通常无需使用） |
| `/as-me:memories` | 查看和管理记忆 |
| `/as-me:principles` | 查看和管理原则 |
| `/as-me:evolution` | 查看演化历史 |

### CLI 命令

```bash
# 分析对话
as-me analyze

# 查看记忆
as-me memories list
as-me memories show <ID>
as-me memories delete <ID>

# 查看原则
as-me principles list
as-me principles show <ID>
as-me principles confirm <ID>
as-me principles correct <ID> -s "新陈述" -r "原因"

# 查看演化历史
as-me evolution history
as-me evolution timeline
```

## 工作原理

### 1. 自动记忆提取

每次启动新的 Claude Code 会话时，SessionStart Hook 会自动：
- 检查是否有上次会话需要分析
- 在后台启动独立进程分析上次会话
- 使用 AI 提取技术偏好、思维模式、行为习惯、语言风格等特征
- 将这些特征存储为"记忆原子"

整个过程完全自动化，不阻塞用户的下一次对话。

### 2. 记忆注入

每次启动新的 Claude Code 会话时，SessionStart Hook 会自动：
- 检索与当前上下文相关的记忆
- 将这些记忆注入到对话上下文中
- 让 AI 能够基于你的历史偏好提供更个性化的帮助

### 3. 原则聚合

当同类型的记忆积累到一定数量（≥5条）且置信度足够高（≥60%）时，系统会：
- 自动将这些记忆聚合为更高层次的"原则"
- 原则代表你稳定的价值观、世界观、决策模式

## 记忆类型

- **tech_preference**: 技术偏好（如编程语言、框架、工具）
- **thinking_pattern**: 思维模式（如问题分析方式、决策风格）
- **behavior_habit**: 行为习惯（如工作流程、沟通方式）
- **language_style**: 语言风格（如表达偏好、专业术语）

## 记忆层级

| 层级 | 描述 | 衰减速度 |
|------|------|----------|
| short_term | 短期记忆，新提取的特征 | 快 |
| working | 工作记忆，活跃使用的特征 | 中 |
| long_term | 长期记忆，稳定的特征 | 慢 |

## 原则维度

- **worldview**: 世界观 - 对事物本质的理解
- **values**: 价值观 - 重要性和优先级判断
- **decision_pattern**: 决策模式 - 做决定的方式和逻辑
- **domain_thought**: 领域思想 - 特定领域的专业认知

## 数据存储

所有数据存储在 `~/.as-me/` 目录：

```
~/.as-me/
├── profile.json              # 用户档案
├── memories/
│   ├── short-term.json       # 短期记忆
│   ├── working.json          # 工作记忆
│   └── long-term.json        # 长期记忆
├── principles/
│   └── core.json             # 内核原则
├── evidence/
│   └── index.json            # 证据索引
├── evolution/
│   └── history.json          # 演化历史
└── logs/
    └── analyzed.json         # 分析日志
```

## 配置

编辑 `~/.as-me/profile.json` 修改设置：

```json
{
  "settings": {
    "extraction_enabled": true,
    "injection_enabled": true,
    "max_injected_memories": 10,
    "confidence_threshold": 0.5,
    "decay_half_life_days": 30,
    "auto_extraction": {
      "enabled": true,
      "max_sessions_per_run": 5,
      "max_messages_per_session": 100,
      "retry_limit": 3
    }
  }
}
```

### 自动提取配置项

| 配置项 | 默认值 | 描述 |
|--------|--------|------|
| `auto_extraction.enabled` | true | 是否启用自动提取 |
| `auto_extraction.max_sessions_per_run` | 5 | 每次运行最多分析的会话数 |
| `auto_extraction.max_messages_per_session` | 100 | 每个会话最多分析的消息数 |
| `auto_extraction.retry_limit` | 3 | 失败重试次数上限 |

## 卸载

```bash
# 在 Claude Code 中运行
/plugin uninstall as-me

# 可选：删除数据目录
rm -rf ~/.as-me
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码结构

```
src/as_me/
├── analysis/        # 自动提取调度
├── memory/          # 记忆管理
├── principle/       # 原则管理
├── conversation/    # 对话解析
├── hooks/           # Hook 处理器
├── formatters/      # 输出格式化
├── storage/         # 存储层
└── cli.py           # CLI 入口
```

## 许可证

MIT License
