#!/usr/bin/env bash
# Stop hook: Claude 停止响应时启动后台进程提取记忆
# 环境变量: CLAUDE_SESSION_ID, CLAUDE_CWD

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PLUGIN_ROOT}/.venv"

# 查找 Python 3.11+
find_python() {
    for py in python3.12 python3.11; do
        if command -v "$py" &>/dev/null; then
            echo "$py"
            return
        fi
    done
    echo "python3"
}

SYSTEM_PYTHON=$(find_python)

# 创建 venv（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    "$SYSTEM_PYTHON" -m venv "$VENV_DIR" >/dev/null 2>&1
fi

# 使用 venv 中的 Python
PYTHON="${VENV_DIR}/bin/python"

# 检查 as_me 模块是否已安装
if ! "$PYTHON" -c "import as_me" 2>/dev/null; then
    "$PYTHON" -m pip install -q git+https://github.com/ahhsitt/as-me.git >/dev/null 2>&1
fi

# 调用 stop-hook 命令（它会启动后台进程）
"$PYTHON" -m as_me.cli stop-hook
