# -*- coding: utf-8 -*-
"""
功能契約測試 (tests/test_capabilities.py)

本測試檔案的目的是確保所有在 `README.md` 中聲明的能力都處於可執行狀態。
它會動態地從 `README.md` 的「系統能力清單」表格中解析出命令，
並為每一個命令創建一個自動化測試，以驗證其存在性與基本可執行性。

這是「記憶聖約」原則的程式碼體現：任何被寫入文件的能力，都必須被自動化測試所驗證。
"""

import subprocess
import re
import pytest
from pathlib import Path

# --- 常數定義 ---
ROOT_DIR = Path(__file__).parent.parent
README_PATH = ROOT_DIR / "README.md"

# --- 輔助函式 ---

def get_shell_commands_from_readme():
    """
    從 README.md 的 Markdown 表格中解析出所有 shell 指令。

    Returns:
        list[tuple[str, str]]: 一個包含 (能力名稱, 執行命令) 的元組列表。
    """
    if not README_PATH.is_file():
        raise FileNotFoundError("找不到 README.md，無法讀取能力清單。")

    content = README_PATH.read_text(encoding="utf-8")

    # 使用正則表達式尋找 Markdown 表格中的命令
    # 匹配 `|` 開頭，後面跟著一些文字，然後是 `|`，再跟著一些文字，
    # 最後是 `|` 和一個包含 `<code>` 標籤的儲存格
    pattern = re.compile(r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*`([^`]+)`\s*\|")

    matches = pattern.findall(content)

    # 提取能力名稱和命令
    # (能力名稱, 執行命令)
    commands = [(match[0].strip(), match[2].strip()) for match in matches if '執行命令' not in match[1]]
    return commands

# --- 動態測試生成 ---

# 獲取所有待測試的命令
try:
    COMMANDS_TO_TEST = get_shell_commands_from_readme()
except FileNotFoundError as e:
    print(f"錯誤: {e}")
    COMMANDS_TO_TEST = []

# 使用 pytest.mark.parametrize 來為每個命令動態創建一個測試案例
@pytest.mark.parametrize("capability_name, command", COMMANDS_TO_TEST)
def test_capability_contract(capability_name, command):
    """
    驗證單一能力的契約。

    Args:
        capability_name (str): 能力的描述性名稱。
        command (str): 要執行的 shell 命令。
    """
    # 對於需要 --help 標誌的命令
    if "python" in command or "bash" in command:
        if "run.py" in command:
            # run.py 使用 click，子命令的 help 需要特殊處理
            command_parts = command.split()
            executable = command_parts[:3] # poetry run python
            script = command_parts[3]
            subcommand = command_parts[4]
            test_command = executable + [script, subcommand, "--help"]
        else:
            test_command = command.split() + ["--help"]
    else:
        # 對於像 `bash preflight-check.sh` 這樣的命令，我們檢查檔案是否存在且可執行
        script_path = Path(command.split()[1])
        assert script_path.is_file(), f"腳本檔案不存在: {script_path}"
        assert script_path.stat().st_mode & 0o111, f"腳本檔案不可執行: {script_path}"
        # 對於 shell 腳本，我們不實際執行它，只驗證其存在性和權限
        return


    try:
        # 執行命令 (例如：`poetry run python commander_console.py build-feature-store --help`)
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )

        # 驗證成功
        # 成功的 --help 命令應該返回 0
        assert result.returncode == 0, f"命令 '{command}' 的 --help 測試返回非零退出碼。"
        # 並且 stdout 不應為空
        assert result.stdout.strip(), f"命令 '{command}' 的 --help 測試沒有任何輸出。"

    except FileNotFoundError:
        pytest.fail(f"命令 '{' '.join(test_command)}' 找不到。請檢查路徑和環境。")
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"命令 '{' '.join(test_command)}' 執行失敗。\n"
            f"返回碼: {e.returncode}\n"
            f"輸出: \n{e.stdout}\n"
            f"錯誤: \n{e.stderr}"
        )
