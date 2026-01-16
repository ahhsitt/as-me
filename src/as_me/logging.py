"""日志配置

为 As-Me 插件配置 Python logging。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from .storage import get_storage_path


# 默认日志级别
DEFAULT_LOG_LEVEL = logging.INFO

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_SIMPLE = "%(levelname)s: %(message)s"

# 日志文件名
LOG_FILE = "logs/as-me.log"


def setup_logging(
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = False,
) -> logging.Logger:
    """配置日志

    Args:
        level: 日志级别
        log_file: 日志文件路径，默认为 ~/.as-me/logs/as-me.log
        console: 是否输出到控制台

    Returns:
        根日志记录器
    """
    # 获取根日志记录器
    logger = logging.getLogger("as_me")
    logger.setLevel(level)

    # 清除现有处理器
    logger.handlers.clear()

    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT)
    simple_formatter = logging.Formatter(LOG_FORMAT_SIMPLE)

    # 添加文件处理器
    if log_file is None:
        log_file = get_storage_path(LOG_FILE)

    # 确保日志目录存在
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 添加控制台处理器（如果需要）
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取模块日志记录器

    Args:
        name: 模块名称

    Returns:
        日志记录器
    """
    return logging.getLogger(f"as_me.{name}")


# 初始化日志
_logger = None


def init_logging(level: int = DEFAULT_LOG_LEVEL, console: bool = False) -> None:
    """初始化日志系统

    Args:
        level: 日志级别
        console: 是否输出到控制台
    """
    global _logger
    if _logger is None:
        _logger = setup_logging(level=level, console=console)


def log_info(message: str, module: str = "core") -> None:
    """记录信息日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    get_logger(module).info(message)


def log_warning(message: str, module: str = "core") -> None:
    """记录警告日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    get_logger(module).warning(message)


def log_error(message: str, module: str = "core", exc_info: bool = False) -> None:
    """记录错误日志

    Args:
        message: 日志消息
        module: 模块名称
        exc_info: 是否包含异常信息
    """
    get_logger(module).error(message, exc_info=exc_info)


def log_debug(message: str, module: str = "core") -> None:
    """记录调试日志

    Args:
        message: 日志消息
        module: 模块名称
    """
    get_logger(module).debug(message)
