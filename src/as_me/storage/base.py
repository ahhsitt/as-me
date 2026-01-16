"""存储基础工具

确保存储目录存在，提供路径获取功能。
"""

from __future__ import annotations

from pathlib import Path


# 默认存储根目录
DEFAULT_STORAGE_ROOT = Path.home() / ".as-me"


def get_storage_path(subpath: str = "", root: Path | None = None) -> Path:
    """获取存储路径

    Args:
        subpath: 子路径（如 "memories/working.json"）
        root: 存储根目录，默认 ~/.as-me/

    Returns:
        完整的存储路径
    """
    base = root or DEFAULT_STORAGE_ROOT
    if subpath:
        return base / subpath
    return base


def ensure_storage_dir(root: Path | None = None) -> Path:
    """确保存储目录结构存在

    创建以下目录结构:
    ~/.as-me/
    ├── memories/
    ├── principles/
    ├── evidence/
    ├── evolution/
    ├── archive/
    └── logs/

    Args:
        root: 存储根目录，默认 ~/.as-me/

    Returns:
        存储根目录路径
    """
    base = root or DEFAULT_STORAGE_ROOT

    # 创建所有子目录
    subdirs = [
        "memories",
        "principles",
        "evidence",
        "evolution",
        "archive",
        "logs",
    ]

    for subdir in subdirs:
        (base / subdir).mkdir(parents=True, exist_ok=True)

    return base
