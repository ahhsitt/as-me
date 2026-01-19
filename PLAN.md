# as-me 重构计划

## 目标

将 as-me 从"后台 Python 进程 + 外部 LLM 客户端"架构重构为"Claude Code Skill 驱动"架构，利用 Claude Code 自身的 LLM 能力进行记忆提取。

## 核心变更

### 架构对比

| 方面 | 当前架构 | 目标架构 |
|------|---------|---------|
| 记忆提取 | 后台 Python 进程 + 启发式/外部 LLM | Claude Code Skill（利用 Claude 自身） |
| 触发时机 | SessionStart 触发后台进程 | Skill 手动/自动调用 |
| 分析对象 | 历史 JSONL 文件 | 当前对话上下文 |
| 依赖 | 需配置 LLM 客户端或用正则 | 零配置，直接利用 Claude |

### 保留的功能

- 记忆存储层（MemoryStore, 三层结构）
- 原则系统（PrincipleStore, aggregation, evolution）
- 记忆注入（SessionStart Hook 注入 user-profile）
- 记忆衰减和强化机制
- 命令：/as-me-memories, /as-me-principles, /as-me-evolution

### 移除/简化的功能

- 后台分析进程（BackgroundRunner）
- 分析队列（AnalysisQueue）
- 分析调度器（AnalysisScheduler）
- 对话解析器（ConversationParser）- 简化为仅保留日志记录
- 启发式提取器（MemoryExtractor._heuristic_extract）

---

## 实施步骤

### Phase 1: 创建核心 Skill [重要]

**目标**: 创建 `/as-me:analyze` skill，让 Claude 在当前对话中提取记忆

#### Step 1.1: 重新设计 analyze skill

- [ ] 更新 `skills/analyze/SKILL.md`
- [ ] 定义清晰的提取流程和输出格式
- [ ] 添加去重检查指引
- [ ] 添加写入记忆的具体步骤

**文件**: `skills/analyze/SKILL.md`

#### Step 1.2: 确保 skill 正确注册

- [ ] 检查 Claude Code 的 skill 发现机制
- [ ] 确认 `as-me:analyze` 能正确加载（而非命令）
- [ ] 测试 skill 调用

**验证**: 运行 `/as-me:analyze` 应加载 skill 而非 command

---

### Phase 2: 简化分析模块

**目标**: 移除不再需要的后台分析逻辑

#### Step 2.1: 清理 analysis 模块

- [ ] 删除 `src/as_me/analysis/runner.py`（后台进程管理）
- [ ] 删除 `src/as_me/analysis/scheduler.py`（调度器）
- [ ] 删除 `src/as_me/analysis/queue.py`（队列管理）
- [ ] 保留 `src/as_me/analysis/models.py`（如有其他模块依赖）或删除

**文件变更**:
- 删除: `runner.py`, `scheduler.py`, `queue.py`
- 更新: `__init__.py`

#### Step 2.2: 简化 conversation 模块

- [ ] 删除 `src/as_me/conversation/parser.py`（不再解析历史 JSONL）
- [ ] 保留 `src/as_me/conversation/log.py`（记录已分析会话）
- [ ] 保留 `src/as_me/conversation/models.py`（数据模型）

**文件变更**:
- 删除: `parser.py`
- 更新: `__init__.py`

#### Step 2.3: 简化 memory/extractor

- [ ] 移除 `MemoryExtractor` 类（不再需要 Python 层提取）
- [ ] 移除 `prompts.py`（提取 prompt 移到 skill 中）
- [ ] 保留记忆模型和存储逻辑

**文件变更**:
- 删除: `extractor.py`, `prompts.py`
- 更新: `__init__.py`

---

### Phase 3: 更新 SessionStart Hook

**目标**: 简化 hook，移除后台分析触发

#### Step 3.1: 重构 session_start.py

- [ ] 移除 `trigger_background_analysis()` 调用
- [ ] 保留记忆注入逻辑
- [ ] 保留衰减应用逻辑
- [ ] 更新日志输出

**文件**: `src/as_me/hooks/session_start.py`

#### Step 3.2: 更新 shell 脚本

- [ ] 简化 `hooks/session-start.sh`
- [ ] 移除后台进程启动逻辑

**文件**: `hooks/session-start.sh`

---

### Phase 4: 更新 CLI

**目标**: 移除不再使用的命令

#### Step 4.1: 清理 CLI 命令

- [ ] 移除 `analyze-background` 命令
- [ ] 更新 `inject-context` 命令（如需要）
- [ ] 保留其他命令（memories, principles, evolution）

**文件**: `src/as_me/cli.py`

#### Step 4.2: 更新 command 文档

- [ ] 重写 `commands/analyze.md`，指向 skill
- [ ] 添加说明：推荐使用 `/as-me:analyze` skill

**文件**: `commands/analyze.md`

---

### Phase 5: 清理存储和配置

**目标**: 移除不再需要的配置和存储

#### Step 5.1: 简化 profile 配置

- [ ] 移除 `auto_extraction` 配置段
- [ ] 保留 `injection_enabled`, `confidence_threshold` 等
- [ ] 更新 `ProfileSettings` 模型

**文件**: `src/as_me/memory/models.py`

#### Step 5.2: 清理存储目录

- [ ] 移除 `~/.as-me/analysis/` 目录使用
- [ ] 更新 `storage/base.py` 的目录结构

**文件**: `src/as_me/storage/base.py`

---

### Phase 6: 测试和文档

#### Step 6.1: 更新测试

- [ ] 移除与 analysis 相关的测试
- [ ] 添加新 skill 的集成测试说明

#### Step 6.2: 更新文档

- [ ] 更新 `CLAUDE.md`
- [ ] 更新 `README.md`（如有）
- [ ] 更新 skill 和 command 的使用说明

---

## 文件变更清单

### 删除的文件

```
src/as_me/analysis/runner.py
src/as_me/analysis/scheduler.py
src/as_me/analysis/queue.py
src/as_me/conversation/parser.py
src/as_me/memory/extractor.py
src/as_me/memory/prompts.py
```

### 修改的文件

```
src/as_me/analysis/__init__.py     # 清理导出
src/as_me/conversation/__init__.py # 清理导出
src/as_me/memory/__init__.py       # 清理导出
src/as_me/memory/models.py         # 移除 AutoExtractionSettings
src/as_me/hooks/session_start.py   # 移除后台分析触发
src/as_me/cli.py                   # 移除 analyze-background 命令
src/as_me/storage/base.py          # 更新目录结构
hooks/session-start.sh             # 简化脚本
commands/analyze.md                # 重写，指向 skill
skills/analyze/SKILL.md            # 完善 skill 定义
```

### 新增的文件

无（skill 已创建）

---

## 验收标准

1. **功能验证**
   - [ ] `/as-me:analyze` 能正确加载 skill
   - [ ] Claude 能按照 skill 指引提取记忆并写入文件
   - [ ] SessionStart 仍能正确注入记忆上下文
   - [ ] 记忆衰减和强化机制正常工作

2. **代码质量**
   - [ ] 无废弃代码残留
   - [ ] 模块导入无错误
   - [ ] 类型检查通过（mypy）

3. **用户体验**
   - [ ] 零配置即可使用
   - [ ] 提取质量优于启发式方法
   - [ ] 命令/skill 文档清晰

---

## 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Skill 加载机制不明确 | 高 | 先测试 skill 注册机制再大规模重构 |
| 遗漏依赖导致运行时错误 | 中 | 逐步删除，每步验证 |
| 用户已有配置不兼容 | 低 | 不考虑 breaking change，直接重构 |

---

## 执行顺序

1. **先验证 skill 机制** (Phase 1) - 确认方案可行
2. **简化分析模块** (Phase 2) - 核心重构
3. **更新 Hook** (Phase 3) - 移除触发逻辑
4. **更新 CLI** (Phase 4) - 清理命令
5. **清理配置** (Phase 5) - 收尾
6. **测试文档** (Phase 6) - 完善

预计工作量：每个 Phase 独立可测试，整体重构可在 1-2 个会话内完成。
