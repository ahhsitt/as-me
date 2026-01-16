"""JSON 文件读写辅助函数"""

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """读取 JSON 文件

    Args:
        path: JSON 文件路径

    Returns:
        解析后的 JSON 数据，文件不存在时返回 None
    """
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any, indent: int = 2) -> None:
    """写入 JSON 文件

    Args:
        path: JSON 文件路径
        data: 要写入的数据
        indent: 缩进空格数，默认 2
    """
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent, default=str),
        encoding="utf-8"
    )
