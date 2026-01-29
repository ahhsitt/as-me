"""As-Me CLI 入口

使用 Click 框架构建命令行界面。
"""

from __future__ import annotations

import click

from . import __version__
from .storage import ensure_storage_dir, get_storage_path


@click.group()
@click.version_option(version=__version__)
def main():
    """As-Me: AI 数字分身 - 从对话中学习并记住你"""
    pass


@main.command("inject-context")
@click.option("--max-memories", "-n", default=10, help="最大注入记忆数量")
@click.option("--min-confidence", "-c", default=0.3, help="最低置信度阈值")
def inject_context(max_memories: int, min_confidence: float):
    """生成记忆上下文供 SessionStart hook 注入

    输出格式遵循 Claude Code Hook 规范。
    """
    from .hooks.session_start import SessionStartHook

    hook = SessionStartHook(
        max_memories=max_memories,
        min_confidence=min_confidence
    )
    output = hook.handle()
    click.echo(output.to_json())


@main.command("analyze")
def analyze():
    """分析当前对话并提取记忆

    注意: 记忆提取现在通过 Claude Code Skill 实现。
    请在 Claude Code 中使用 /as-me:analyze 命令触发分析。

    Skill 会利用 Claude 自身的 LLM 能力分析当前对话，
    无需额外配置 LLM 客户端。
    """
    click.echo("记忆提取现已通过 Claude Code Skill 实现！")
    click.echo("")
    click.echo("请在 Claude Code 中使用以下命令：")
    click.echo("  /as-me:analyze")
    click.echo("")
    click.echo("Skill 会利用 Claude 自身的 LLM 能力分析当前对话，")
    click.echo("无需额外配置，提取质量更高。")
    click.echo("")
    click.echo("查看已提取的记忆：")
    click.echo("  as-me memories list")


@main.command("extract-session")
@click.option("--session-id", required=True, help="会话 ID")
@click.option("--project-path", required=True, help="项目路径")
def extract_session(session_id: str, project_path: str):
    """从会话文件中提取记忆（供 Stop hook 后台调用）"""
    from .extraction import extract_session_background

    extract_session_background(session_id, project_path)


@main.command("stop-hook")
@click.option("--session-id", envvar="CLAUDE_SESSION_ID", help="会话 ID")
@click.option("--project-path", envvar="CLAUDE_CWD", help="项目路径")
def stop_hook(session_id: str | None, project_path: str | None):
    """处理 Stop hook（启动后台提取进程）"""
    from .hooks.stop import StopHook

    hook = StopHook(session_id=session_id, project_path=project_path)
    output = hook.handle()
    click.echo(output.to_json())


@main.group("memories")
def memories():
    """记忆管理命令组"""
    pass


@memories.command("list")
@click.option("--type", "-t", "memory_type", help="按类型过滤 (identity, value, thinking, preference, communication)")
@click.option("--tier", help="按层级过滤 (short_term, working, long_term)")
@click.option("--limit", "-n", default=20, help="显示数量限制")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def memories_list(memory_type: str | None, tier: str | None, limit: int, verbose: bool):
    """列出记忆"""
    from .memory.models import MemoryTier, MemoryType
    from .memory.store import MemoryStore, QueryOptions
    from .formatters.memory_formatter import format_memory_list

    store = MemoryStore()

    # 解析过滤条件
    options = QueryOptions(limit=limit)

    if memory_type:
        try:
            options.memory_type = MemoryType(memory_type)
        except ValueError:
            click.echo(f"错误: 无效的记忆类型 '{memory_type}'", err=True)
            click.echo("有效类型: identity, value, thinking, preference, communication")
            return

    if tier:
        try:
            options.tier = MemoryTier(tier)
        except ValueError:
            click.echo(f"错误: 无效的层级 '{tier}'", err=True)
            click.echo("有效层级: short_term, working, long_term")
            return

    memories = store.get_all(options)
    output = format_memory_list(memories, verbose=verbose)
    click.echo(output)


@memories.command("show")
@click.argument("memory_id")
def memories_show(memory_id: str):
    """显示记忆详情"""
    from .memory.store import MemoryStore
    from .formatters.memory_formatter import format_memory_detail

    store = MemoryStore()

    # 支持短 ID 查找
    memory = store.get_by_id(memory_id)

    if not memory:
        # 尝试前缀匹配
        all_memories = store.get_all()
        matches = [m for m in all_memories if m.id.startswith(memory_id)]
        if len(matches) == 1:
            memory = matches[0]
        elif len(matches) > 1:
            click.echo(f"错误: ID '{memory_id}' 匹配多个记忆:")
            for m in matches[:5]:
                click.echo(f"  - {m.id}")
            return
        else:
            click.echo(f"错误: 未找到记忆 '{memory_id}'", err=True)
            return

    output = format_memory_detail(memory)
    click.echo(output)


@memories.command("delete")
@click.argument("memory_id")
@click.confirmation_option(prompt="确认删除此记忆?")
def memories_delete(memory_id: str):
    """删除记忆"""
    from .memory.store import MemoryStore

    store = MemoryStore()

    # 支持短 ID 查找
    memory = store.get_by_id(memory_id)

    if not memory:
        # 尝试前缀匹配
        all_memories = store.get_all()
        matches = [m for m in all_memories if m.id.startswith(memory_id)]
        if len(matches) == 1:
            memory = matches[0]
        elif len(matches) > 1:
            click.echo(f"错误: ID '{memory_id}' 匹配多个记忆，请使用更长的 ID")
            return
        else:
            click.echo(f"错误: 未找到记忆 '{memory_id}'", err=True)
            return

    if store.delete(memory.id):
        click.echo(f"已删除记忆: {memory.id}")
    else:
        click.echo(f"删除失败: {memory.id}", err=True)


@main.group("principles")
def principles():
    """原则管理命令组"""
    pass


@principles.command("list")
@click.option("--dimension", "-d", help="按维度过滤 (worldview, values, decision_pattern, domain_thought)")
@click.option("--confirmed", is_flag=True, help="仅显示已确认的")
@click.option("--active", is_flag=True, default=True, help="仅显示活跃的")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def principles_list(dimension: str | None, confirmed: bool, active: bool, verbose: bool):
    """列出原则"""
    from .principle.models import PrincipleDimension
    from .principle.store import PrincipleStore
    from .formatters.principle_formatter import format_principle_list

    store = PrincipleStore()

    if dimension:
        try:
            dim = PrincipleDimension(dimension)
            principles = store.get_by_dimension(dim)
        except ValueError:
            click.echo(f"错误: 无效的维度 '{dimension}'", err=True)
            click.echo("有效维度: worldview, values, decision_pattern, domain_thought")
            return
    elif active:
        principles = store.get_active()
    else:
        principles = store.get_all()

    if confirmed:
        principles = [p for p in principles if p.confirmed_by_user]

    output = format_principle_list(principles, verbose=verbose)
    click.echo(output)


@principles.command("show")
@click.argument("principle_id")
def principles_show(principle_id: str):
    """显示原则详情"""
    from .principle.store import PrincipleStore
    from .formatters.principle_formatter import format_principle_detail

    store = PrincipleStore()

    # 支持短 ID 查找
    principle = store.get_by_id(principle_id)

    if not principle:
        all_principles = store.get_all()
        matches = [p for p in all_principles if p.id.startswith(principle_id)]
        if len(matches) == 1:
            principle = matches[0]
        elif len(matches) > 1:
            click.echo(f"错误: ID '{principle_id}' 匹配多个原则:")
            for p in matches[:5]:
                click.echo(f"  - {p.id}")
            return
        else:
            click.echo(f"错误: 未找到原则 '{principle_id}'", err=True)
            return

    output = format_principle_detail(principle)
    click.echo(output)


@principles.command("confirm")
@click.argument("principle_id")
def principles_confirm(principle_id: str):
    """确认原则"""
    from .principle.store import PrincipleStore

    store = PrincipleStore()

    # 支持短 ID 查找
    principle = store.get_by_id(principle_id)
    if not principle:
        all_principles = store.get_all()
        matches = [p for p in all_principles if p.id.startswith(principle_id)]
        if len(matches) == 1:
            principle = matches[0]
        else:
            click.echo(f"错误: 未找到原则 '{principle_id}'", err=True)
            return

    updated = store.confirm(principle.id)
    click.echo(f"已确认原则: {updated.statement[:50]}...")
    click.echo(f"新置信度: {int(updated.confidence * 100)}%")


@principles.command("correct")
@click.argument("principle_id")
@click.option("--statement", "-s", prompt="新的原则陈述", help="修正后的陈述")
@click.option("--reason", "-r", prompt="修正原因", help="修正原因")
def principles_correct(principle_id: str, statement: str, reason: str):
    """修正原则"""
    from .principle.store import PrincipleStore

    store = PrincipleStore()

    # 支持短 ID 查找
    principle = store.get_by_id(principle_id)
    if not principle:
        all_principles = store.get_all()
        matches = [p for p in all_principles if p.id.startswith(principle_id)]
        if len(matches) == 1:
            principle = matches[0]
        else:
            click.echo(f"错误: 未找到原则 '{principle_id}'", err=True)
            return

    updated = store.correct(principle.id, statement, reason)
    click.echo(f"已修正原则: {updated.id}")
    click.echo(f"新陈述: {updated.statement}")


@principles.command("delete")
@click.argument("principle_id")
@click.confirmation_option(prompt="确认删除此原则?")
def principles_delete(principle_id: str):
    """删除原则"""
    from .principle.store import PrincipleStore

    store = PrincipleStore()

    # 支持短 ID 查找
    principle = store.get_by_id(principle_id)
    if not principle:
        all_principles = store.get_all()
        matches = [p for p in all_principles if p.id.startswith(principle_id)]
        if len(matches) == 1:
            principle = matches[0]
        else:
            click.echo(f"错误: 未找到原则 '{principle_id}'", err=True)
            return

    if store.delete(principle.id):
        click.echo(f"已删除原则: {principle.id}")
    else:
        click.echo(f"删除失败: {principle.id}", err=True)


@main.group("evolution")
def evolution():
    """演化追踪命令组"""
    pass


@evolution.command("history")
@click.option("--principle", "-p", help="指定原则 ID")
@click.option("--limit", "-n", default=20, help="显示数量限制")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def evolution_history(principle: str | None, limit: int, verbose: bool):
    """查看演化历史"""
    from .principle.evolution import EvolutionTracker
    from .principle.store import PrincipleStore
    from .formatters.evolution_formatter import format_evolution_list, format_evolution_timeline

    tracker = EvolutionTracker()

    if principle:
        # 支持短 ID 查找
        store = PrincipleStore()
        full_principle = store.get_by_id(principle)
        if not full_principle:
            all_principles = store.get_all()
            matches = [p for p in all_principles if p.id.startswith(principle)]
            if len(matches) == 1:
                full_principle = matches[0]
            elif len(matches) > 1:
                click.echo(f"错误: ID '{principle}' 匹配多个原则:")
                for p in matches[:5]:
                    click.echo(f"  - {p.id}")
                return
            else:
                click.echo(f"错误: 未找到原则 '{principle}'", err=True)
                return

        events = tracker.get_history(full_principle.id)
        if events:
            output = format_evolution_timeline(events, full_principle.id)
        else:
            output = f"原则 {full_principle.id[:8]} 暂无演化历史"
    else:
        events = tracker.get_timeline(limit=limit)
        output = format_evolution_list(events, verbose=verbose)

    click.echo(output)


@evolution.command("timeline")
@click.option("--trigger", "-t", help="按触发类型过滤 (new_evidence, conflict, user_confirm, user_correct, time_decay, aggregation)")
@click.option("--limit", "-n", default=30, help="显示数量限制")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def evolution_timeline(trigger: str | None, limit: int, verbose: bool):
    """查看演化时间线"""
    from .principle.evolution import EvolutionTracker
    from .principle.models import EvolutionTrigger
    from .formatters.evolution_formatter import format_evolution_list

    tracker = EvolutionTracker()

    trigger_filter = None
    if trigger:
        try:
            trigger_filter = EvolutionTrigger(trigger)
        except ValueError:
            click.echo(f"错误: 无效的触发类型 '{trigger}'", err=True)
            click.echo("有效类型: new_evidence, conflict, user_confirm, user_correct, time_decay, aggregation")
            return

    events = tracker.get_timeline(trigger=trigger_filter, limit=limit)
    output = format_evolution_list(events, verbose=verbose)
    click.echo(output)


@evolution.command("show")
@click.argument("event_id")
def evolution_show(event_id: str):
    """显示演化事件详情"""
    from .principle.evolution import EvolutionTracker
    from .formatters.evolution_formatter import format_evolution_detail

    tracker = EvolutionTracker()
    events = tracker.get_all()

    # 支持短 ID 查找
    event = None
    for e in events:
        if e.id == event_id:
            event = e
            break

    if not event:
        matches = [e for e in events if e.id.startswith(event_id)]
        if len(matches) == 1:
            event = matches[0]
        elif len(matches) > 1:
            click.echo(f"错误: ID '{event_id}' 匹配多个事件:")
            for e in matches[:5]:
                click.echo(f"  - {e.id}")
            return
        else:
            click.echo(f"错误: 未找到演化事件 '{event_id}'", err=True)
            return

    output = format_evolution_detail(event)
    click.echo(output)


if __name__ == "__main__":
    main()
