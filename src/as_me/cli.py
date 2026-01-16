"""As-Me CLI 入口

使用 Click 框架构建命令行界面。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

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


@main.command("analyze-background")
@click.option("--log-file", type=click.Path(), help="日志文件路径")
@click.option("--max-sessions", "-n", default=5, help="最大分析会话数量")
def analyze_background(log_file: str | None, max_sessions: int):
    """后台分析命令（由 SessionStart Hook 自动调用）

    此命令用于在后台执行会话分析，提取记忆原子。
    通常不需要手动调用，由 SessionStart Hook 自动触发。

    退出码:
      0 - 成功
      1 - 错误
      2 - 已有分析进程运行
    """
    import logging
    import sys

    from .analysis.runner import BackgroundRunner
    from .analysis.scheduler import AnalysisScheduler

    # 配置日志
    if log_file:
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    logger = logging.getLogger("as_me.analyze_background")
    storage_root = get_storage_path()

    try:
        # 检查是否已有进程运行
        if BackgroundRunner.is_analysis_running(storage_root):
            logger.warning("分析进程已在运行")
            sys.exit(2)

        # 写入 PID 文件
        pid_path = storage_root / BackgroundRunner.PID_FILE
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pid_path, "w") as f:
            import os
            f.write(str(os.getpid()))

        logger.info("开始后台分析...")

        # 执行分析
        scheduler = AnalysisScheduler(storage_root)

        if not scheduler.should_run_analysis():
            logger.info("没有待分析的会话")
            BackgroundRunner.cleanup_pid(storage_root)
            sys.exit(0)

        result = scheduler.run_analysis()

        logger.info(
            f"分析完成: 共 {result.total_sessions} 个会话, "
            f"成功 {result.analyzed_count}, "
            f"跳过 {result.skipped_count}, "
            f"失败 {result.failed_count}, "
            f"提取 {result.total_memories} 条记忆, "
            f"耗时 {result.duration_ms}ms"
        )

        if result.errors:
            for error in result.errors:
                logger.error(f"错误: {error}")

        # 清理 PID 文件
        BackgroundRunner.cleanup_pid(storage_root)
        sys.exit(0)

    except Exception as e:
        logger.error(f"分析失败: {e}")
        BackgroundRunner.cleanup_pid(storage_root)
        sys.exit(1)


@main.command("analyze")
@click.option("--session", "-s", help="指定会话 ID")
@click.option("--all", "analyze_all", is_flag=True, help="分析所有未分析的会话")
@click.option("--limit", "-n", default=5, help="分析会话数量上限")
@click.option("--force", "-f", is_flag=True, help="强制执行手动分析（记忆提取已自动化，通常无需手动执行）")
def analyze(session: str | None, analyze_all: bool, limit: int, force: bool):
    """分析对话并提取记忆

    从 Claude Code 对话历史中提取用户特征。

    注意: 记忆提取已自动化，每次启动新会话时会自动在后台分析上次会话。
    通常不需要手动执行此命令。如确需手动分析，请使用 --force 选项。
    """
    # 检查是否需要显示自动化提示
    if not force and not session:
        click.echo("提示: 记忆提取已自动化！")
        click.echo("")
        click.echo("每次启动新会话时，系统会自动在后台分析上次会话并提取记忆。")
        click.echo("通常不需要手动执行此命令。")
        click.echo("")
        click.echo("如果确需手动分析，请使用以下选项:")
        click.echo("  as-me analyze --force        # 强制手动分析")
        click.echo("  as-me analyze -s <会话ID>    # 分析指定会话")
        click.echo("")
        click.echo("查看分析状态:")
        click.echo("  as-me memories list          # 查看已提取的记忆")
        return

    from .conversation.parser import ConversationParser
    from .memory.extractor import MemoryExtractor
    from .memory.store import MemoryStore
    from .storage.json_store import read_json

    # 确保存储目录存在
    ensure_storage_dir()

    store = MemoryStore()
    parser = ConversationParser()
    extractor = MemoryExtractor()

    # 获取已分析的会话
    logs_file = get_storage_path("logs/analyzed.json")
    analyzed_logs = read_json(logs_file) or []
    analyzed_ids = {log["session_id"] for log in analyzed_logs}

    if session:
        # 分析指定会话
        sessions_to_analyze = []
        for s in parser.get_recent_sessions(limit=50):
            if s.stem == session:
                sessions_to_analyze = [s]
                break
        if not sessions_to_analyze:
            click.echo(f"错误: 未找到会话 {session}", err=True)
            return
    elif analyze_all:
        # 分析所有未分析的会话
        sessions_to_analyze = parser.get_unanalyzed_sessions(analyzed_ids, limit=limit)
    else:
        # 默认分析最近一个未分析的会话
        sessions_to_analyze = parser.get_unanalyzed_sessions(analyzed_ids, limit=1)

    if not sessions_to_analyze:
        click.echo("没有待分析的会话")
        return

    total_extracted = 0
    for session_path in sessions_to_analyze:
        session_id = session_path.stem
        click.echo(f"分析会话: {session_id[:8]}...")

        try:
            entries = parser.parse(session_path)
            messages = parser.extract_user_messages(entries)

            if not messages:
                click.echo(f"  跳过: 无用户消息")
                continue

            # 检查是否有可提取特征
            if not extractor.has_extractable_features(messages):
                click.echo(f"  跳过: 无可提取特征")
                continue

            # 提取记忆
            result = extractor.extract(messages, session_id)

            if result.memories:
                store.save_batch(result.memories)
                total_extracted += len(result.memories)
                click.echo(f"  提取: {len(result.memories)} 条记忆")
                for mem in result.memories:
                    click.echo(f"    - [{mem.type.value}] {mem.content[:50]}...")
            else:
                click.echo(f"  结果: 无记忆提取")

            # 记录已分析
            analyzed_logs.append({
                "session_id": session_id,
                "project_path": str(session_path.parent),
                "analyzed_at": datetime.now().isoformat(),
                "extracted_count": len(result.memories),
                "message_count": len(messages),
            })

        except Exception as e:
            click.echo(f"  错误: {e}", err=True)

    # 保存分析日志
    from .storage.json_store import write_json
    write_json(logs_file, analyzed_logs)

    click.echo(f"\n完成! 共提取 {total_extracted} 条记忆")


@main.group("memories")
def memories():
    """记忆管理命令组"""
    pass


@memories.command("list")
@click.option("--type", "-t", "memory_type", help="按类型过滤 (tech_preference, thinking_pattern, behavior_habit, language_style)")
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
            click.echo("有效类型: tech_preference, thinking_pattern, behavior_habit, language_style")
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
