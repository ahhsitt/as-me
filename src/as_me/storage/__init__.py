"""As-Me 存储模块

分层存储架构:
- 热层 (Hot): 内存缓存 + JSON 文件
- 温层 (Warm): JSON 文件
- 冷层 (Cold): gzip 压缩归档
"""

from .base import get_storage_path, ensure_storage_dir
from .json_store import read_json, write_json
from .cache import MemoryCache
from .index import IndexManager
from .cold_storage import ColdStorageManager

__all__ = [
    "get_storage_path",
    "ensure_storage_dir",
    "read_json",
    "write_json",
    "MemoryCache",
    "IndexManager",
    "ColdStorageManager",
]
