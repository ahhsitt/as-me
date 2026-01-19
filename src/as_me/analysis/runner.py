"""后台任务运行器

负责启动和管理后台分析进程。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from ..storage import get_storage_path

logger = logging.getLogger(__name__)


class BackgroundRunner:
    """后台任务启动器

    使用 subprocess.Popen 启动独立的后台分析进程，
    确保进程在父进程退出后继续运行。
    """

    PID_FILE = "analysis/.pid"

    @staticmethod
    def spawn_analysis(
        storage_root: Path | None = None,
        log_file: Path | None = None
    ) -> int | None:
        """启动后台分析进程

        使用 subprocess.Popen 启动独立进程。
        进程在父进程退出后继续运行。

        Args:
            storage_root: 存储根目录
            log_file: 日志文件路径

        Returns:
            进程 PID，启动失败时返回 None
        """
        storage_root = storage_root or get_storage_path()
        pid_path = storage_root / BackgroundRunner.PID_FILE

        # 确保目录存在
        pid_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否已有进程运行
        if BackgroundRunner.is_analysis_running(storage_root):
            return None

        # 构建命令
        cmd = [sys.executable, "-m", "as_me.cli", "analyze-background"]

        # 配置日志文件
        if log_file:
            cmd.extend(["--log-file", str(log_file)])

        # 配置进程参数
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "close_fds": True,
        }

        # 设置输出
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_file, "a")
            kwargs["stdout"] = log_handle
            kwargs["stderr"] = log_handle
        else:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL

        # 平台特定的脱离设置
        if os.name == "posix":  # Linux/macOS
            kwargs["start_new_session"] = True
        elif os.name == "nt":  # Windows
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS |
                subprocess.CREATE_NEW_PROCESS_GROUP
            )

        try:
            proc = subprocess.Popen(cmd, **kwargs)
            # 注意：不在这里写 PID 文件，让子进程自己写
            # 避免竞态条件：子进程检查时会发现自己的 PID 已存在
            return proc.pid
        except Exception:
            return None

    @staticmethod
    def is_analysis_running(storage_root: Path | None = None) -> bool:
        """检查是否有分析进程正在运行

        通过检查 PID 文件和进程状态判断。
        如果 PID 文件存在但进程已不存在，会自动清理 PID 文件。

        Args:
            storage_root: 存储根目录

        Returns:
            是否有分析进程运行中
        """
        pid = BackgroundRunner.get_running_pid(storage_root)
        if pid is None:
            return False

        is_running = BackgroundRunner._is_process_running(pid)

        # 如果进程不存在，清理 stale PID 文件
        if not is_running:
            BackgroundRunner.cleanup_pid(storage_root)
            return False

        return True

    @staticmethod
    def get_running_pid(storage_root: Path | None = None) -> int | None:
        """获取运行中的分析进程 PID

        Args:
            storage_root: 存储根目录

        Returns:
            PID，无运行进程时返回 None
        """
        storage_root = storage_root or get_storage_path()
        pid_path = storage_root / BackgroundRunner.PID_FILE

        if not pid_path.exists():
            return None

        try:
            with open(pid_path, "r") as f:
                pid_str = f.read().strip()
                if pid_str:
                    return int(pid_str)
        except (ValueError, IOError):
            pass

        return None

    @staticmethod
    def cleanup_pid(storage_root: Path | None = None) -> None:
        """清理 PID 文件

        Args:
            storage_root: 存储根目录
        """
        storage_root = storage_root or get_storage_path()
        pid_path = storage_root / BackgroundRunner.PID_FILE

        if pid_path.exists():
            try:
                pid_path.unlink()
            except IOError:
                pass

    @staticmethod
    def _write_pid(pid_path: Path, pid: int) -> None:
        """写入 PID 文件

        Args:
            pid_path: PID 文件路径
            pid: 进程 ID
        """
        with open(pid_path, "w") as f:
            f.write(str(pid))

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """检查进程是否仍在运行

        Args:
            pid: 进程 ID

        Returns:
            进程是否在运行
        """
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
