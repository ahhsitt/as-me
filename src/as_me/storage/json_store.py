"""JSON 文件读写辅助函数

支持普通 JSON 和 gzip 压缩 JSON 两种格式。
"""

import gzip
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, compressed: bool = False) -> Any:
    """读取 JSON 文件

    Args:
        path: JSON 文件路径
        compressed: 是否为压缩文件

    Returns:
        解析后的 JSON 数据，文件不存在时返回 None
    """
    if compressed:
        return read_json_gz(path)

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any, indent: int | None = None, compressed: bool = False) -> None:
    """写入 JSON 文件

    Args:
        path: JSON 文件路径
        data: 要写入的数据
        indent: 缩进空格数，默认 None（紧凑格式）
        compressed: 是否压缩存储
    """
    if compressed:
        write_json_gz(path, data)
        return

    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=indent, default=str),
        encoding="utf-8"
    )


def read_json_gz(path: Path) -> Any:
    """读取 gzip 压缩的 JSON 文件

    自动兼容：先尝试 .json.gz，不存在则尝试 .json

    Args:
        path: 文件路径（可以是 .json 或 .json.gz）

    Returns:
        解析后的 JSON 数据，文件不存在时返回 None
    """
    # 标准化路径：确保使用 .json.gz 后缀
    gz_path = _ensure_gz_suffix(path)
    json_path = Path(str(gz_path).replace('.json.gz', '.json'))

    # 优先读取压缩文件
    if gz_path.exists():
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            return json.load(f)

    # 回退到未压缩文件（兼容旧数据）
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))

    return None


def write_json_gz(path: Path, data: Any) -> None:
    """写入 gzip 压缩的 JSON 文件

    Args:
        path: 文件路径（自动添加 .gz 后缀）
        data: 要写入的数据
    """
    gz_path = _ensure_gz_suffix(path)

    # 确保父目录存在
    gz_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str)


def migrate_to_compressed(path: Path) -> bool:
    """将未压缩的 JSON 文件迁移为压缩格式

    Args:
        path: 原 JSON 文件路径

    Returns:
        是否执行了迁移
    """
    json_path = Path(str(path).replace('.json.gz', '.json'))
    gz_path = _ensure_gz_suffix(path)

    # 如果压缩文件已存在，不需要迁移
    if gz_path.exists():
        return False

    # 如果原文件不存在，不需要迁移
    if not json_path.exists():
        return False

    # 读取原数据
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # 写入压缩文件
    write_json_gz(gz_path, data)

    # 删除原文件
    json_path.unlink()

    return True


def _ensure_gz_suffix(path: Path) -> Path:
    """确保路径以 .json.gz 结尾"""
    path_str = str(path)
    if path_str.endswith('.json.gz'):
        return path
    if path_str.endswith('.json'):
        return Path(path_str + '.gz')
    return Path(path_str + '.json.gz')
