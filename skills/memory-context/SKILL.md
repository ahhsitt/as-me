---
name: memory-context
description: 为当前对话注入用户记忆上下文
---

# Memory Context Skill

此 skill 在对话开始时自动激活，注入用户的已知特征和偏好。

## 功能

当检测到以下情况时激活：
1. 新对话开始 (SessionStart)
2. 会话恢复 (resume)

## 注入内容

注入的上下文包含用户的：

- **技术偏好**: 编程语言、框架、工具偏好
- **思维模式**: 决策方式、推理风格
- **行为习惯**: 工作流程、操作习惯
- **语言风格**: 表达习惯、常用词汇

## 配置

可在 `~/.as-me/profile.json` 中配置：

```json
{
  "settings": {
    "injection_enabled": true,
    "max_injected_memories": 10,
    "confidence_threshold": 0.5
  }
}
```

## 使用说明

此 skill 通过 SessionStart hook 自动工作，无需手动调用。

如需手动查看当前会注入的内容，可运行：

```bash
as-me inject-context
```

## 注入格式示例

```xml
<user-profile>
以下是用户的已知特征和偏好：

## 技术偏好
- 偏好使用 TypeScript 而不是 JavaScript (高置信度)
- 喜欢函数式编程风格 (中等置信度)

## 行为习惯
- 通常先写测试再实现功能 (高置信度)

</user-profile>
```
