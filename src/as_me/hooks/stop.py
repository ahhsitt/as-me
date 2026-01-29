"""Stop Hook 处理器

在 Claude 停止响应时，启动后台进程提取当前会话的用户记忆。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class StopHookOutput:
    """Stop Hook 输出"""
    success: bool = True
    error: Optional[str] = None

    def to_json(self) -> str:
        """转换为 JSON 输出"""
        output = {"success": self.success}
        if self.error:
            output["error"] = self.error
        return json.dumps(output, ensure_ascii=False)


class StopHook:
    """Stop Hook 处理器

    在 Claude 停止响应时触发，启动后台进程分析当前会话并提取记忆。
    """

    def __init__(self, session_id: Optional[str] = None, project_path: Optional[str] = None):
        """初始化处理器

        Args:
            session_id: 当前会话 ID
            project_path: 当前项目路径
        """
        self.session_id = session_id
        self.project_path = project_path

    def handle(self) -> StopHookOutput:
        """处理 Stop 事件

        启动后台进程分析当前会话，提取用户记忆。
        Hook 立即返回，分析在后台异步执行。

        Returns:
            Hook 输出
        """
        try:
            if not self.session_id or not self.project_path:
                return StopHookOutput(success=True)  # 静默跳过

            # 启动后台分析进程
            self._spawn_background_analysis()

            return StopHookOutput(success=True)

        except Exception as e:
            # 错误不应阻止会话结束
            return StopHookOutput(success=False, error=str(e))

    def _spawn_background_analysis(self) -> None:
        """启动后台分析进程"""
        cmd = [
            sys.executable,
            "-m",
            "as_me.cli",
            "extract-session",
            "--session-id",
            self.session_id,
            "--project-path",
            self.project_path,
        ]

        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }

        if os.name == "posix":  # Linux/macOS
            kwargs["start_new_session"] = True

        subprocess.Popen(cmd, **kwargs)
