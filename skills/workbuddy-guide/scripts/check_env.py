#!/usr/bin/env python3
"""
WorkBuddy 环境一键诊断脚本
用法：python check_env.py
功能：检查代理状态、连接器配置、专家注册、最近错误日志
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# 使用纯 ASCII 符号，避免 Windows GBK 编码问题
OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"

HOME = Path.home()
WORKBUDDY_DIR = HOME / ".workbuddy"
CONNECTORS_DIR = WORKBUDDY_DIR / "connectors"
EXPERTS_DIR = WORKBUDDY_DIR / "plugins" / "marketplaces" / "my-experts" / "plugins"
LOGS_DIR = WORKBUDDY_DIR / "logs"

def green(s):
    return f"\033[92m{s}\033[0m"

def red(s):
    return f"\033[91m{s}\033[0m"

def yellow(s):
    return f"\033[93m{s}\033[0m"

def check_proxy():
    """检查代理是否运行"""
    print("\n" + "=" * 50)
    print("1. 代理状态检查")
    print("=" * 50)
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "3",
             "http://127.0.0.1:51103/health"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip() == "200":
            print(green(f"{OK} 代理正常运行 (端口 51103)"))
            return True
        else:
            print(red(f"{FAIL} 代理无响应 (HTTP {result.stdout.strip()})"))
            print(yellow(f"   → 建议：重启 WorkBuddy"))
            return False
    except Exception:
        print(red(f"{FAIL} 无法连接代理 (端口 51103)"))
        print(yellow(f"   → 建议：确认 WorkBuddy 是否正在运行"))
        return False

def check_connectors():
    """检查连接器配置"""
    print("\n" + "=" * 50)
    print("2. 连接器配置检查")
    print("=" * 50)

    sessions = [d for d in CONNECTORS_DIR.iterdir()
                if d.is_dir() and d.name not in ("default", "skills")]

    if not sessions:
        print(red(f"{FAIL} 未找到连接器会话目录"))
        return

    for session in sorted(sessions):
        print(f"\n--- Session: {session.name} ---")

        # 检查 connector-states.json
        states_file = session / "connector-states.json"
        if states_file.exists():
            try:
                states = json.loads(states_file.read_text(encoding='utf-8'))
                enabled = states.get("enabled", [])
                header_overrides = states.get("headerOverrides", {})
                print(f"  已启用连接器: {len(enabled)} 个")
                if enabled:
                    print(f"  列表: {', '.join(enabled)}")
                if header_overrides:
                    print(f"  有 headerOverrides: {', '.join(header_overrides.keys())}")
            except json.JSONDecodeError:
                print(red(f"  {FAIL} connector-states.json 格式错误"))
        else:
            print(yellow(f"  {WARN} 无 connector-states.json"))

        # 检查 mcp.json
        mcp_file = session / "mcp.json"
        if mcp_file.exists():
            try:
                config = json.loads(mcp_file.read_text(encoding='utf-8'))
                connectors = [k for k in config if k.startswith("connector:")]
                disabled = [k for k, v in config.items() if k.startswith("connector:") and v.get("disabled")]
                print(f"  配置的连接器: {len(connectors)} 个")
                if disabled:
                    print(yellow(f"  已禁用: {', '.join(disabled)}"))
            except json.JSONDecodeError:
                print(red(f"  {FAIL} mcp.json 格式错误"))
        else:
            print(yellow(f"  {WARN} 无 mcp.json"))

def check_experts():
    """检查专家注册"""
    print("\n" + "=" * 50)
    print("3. 专家注册检查")
    print("=" * 50)

    if not EXPERTS_DIR.exists():
        print(yellow(f"{WARN} 无自定义专家目录"))
        return

    experts = [d for d in EXPERTS_DIR.iterdir() if d.is_dir()]
    if not experts:
        print(yellow(f"{WARN} 无自定义专家"))
        return

    for expert in experts:
        print(f"\n--- {expert.name} ---")
        # plugin.json 可能在 .codebuddy-plugin/ 或 .workbuddy-plugin/ 子目录
        plugin_file = None
        for subdir in ("plugin.json", ".codebuddy-plugin/plugin.json", ".workbuddy-plugin/plugin.json"):
            candidate = expert / subdir
            if candidate.exists():
                plugin_file = candidate
                break
        agent_dir = expert / "agents"

        if plugin_file:
            try:
                plugin = json.loads(plugin_file.read_text(encoding='utf-8'))
                print(f"  名称: {plugin.get('displayName', 'N/A')}")
                print(f"  类型: {plugin.get('expertType', 'N/A')}")
                print(f"  插件位置: {plugin_file.relative_to(expert)}")
                agent_name = plugin.get('agentName', '')
            except json.JSONDecodeError:
                print(red(f"  {FAIL} plugin.json 格式错误"))
                continue
        else:
            print(red(f"  {FAIL} 缺少 plugin.json（已检查 expert/、.codebuddy-plugin/、.workbuddy-plugin/）"))
            continue

        if agent_dir.exists():
            md_file = agent_dir / f"{agent_name}.md"
            if md_file.exists():
                size = md_file.stat().st_size
                print(f"  Agent文件: {agent_name}.md ({size} 字节)")
                if size < 100:
                    print(yellow(f"  {WARN} Prompt 太短，可能缺少必要信息"))
                elif size > 5000:
                    print(yellow(f"  {WARN} Prompt 太长，可能导致模型遗忘"))
            else:
                print(red(f"  {FAIL} 缺少 agents/{agent_name}.md"))
        else:
            print(red(f"  {FAIL} 缺少 agents/ 目录"))

def check_logs():
    """检查最近错误日志"""
    print("\n" + "=" * 50)
    print("4. 最近错误日志")
    print("=" * 50)

    if not LOGS_DIR.exists():
        print(yellow(f"{WARN} 无日志目录"))
        return

    log_files = sorted(LOGS_DIR.glob("*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        print("无日志文件")
        return

    for log_file in log_files[:3]:  # 只检查最近3个日志
        try:
            content = log_file.read_text(encoding='utf-8', errors='ignore')
            errors = [l for l in content.split('\n') if 'error' in l.lower() or 'fail' in l.lower()]
            if errors:
                print(f"\n{log_file.name} ({len(errors)} 条错误):")
                for e in errors[-5:]:  # 只显示最近5条
                    print(f"  {e[:120]}...")
            else:
                print(f"\n{log_file.name}: 无错误")
        except Exception:
            print(f"\n{log_file.name}: 无法读取")

def check_config_files():
    """检查配置文件完整性"""
    print("\n" + "=" * 50)
    print("5. 配置文件完整性")
    print("=" * 50)

    checks = {
        "~/.workbuddy/mcp.json": WORKBUDDY_DIR / "mcp.json",
        "~/.workbuddy/connectors/default/mcp.json": CONNECTORS_DIR / "default" / "mcp.json",
    }

    for name, path in checks.items():
        if path.exists():
            try:
                json.loads(path.read_text(encoding='utf-8'))
                print(green(f"{OK} {name} — 格式正确"))
            except json.JSONDecodeError:
                print(red(f"{FAIL} {name} — JSON格式错误"))
        else:
            print(yellow(f"{WARN} {name} — 文件不存在（可能使用默认配置）"))

def summary():
    """输出诊断摘要"""
    print("\n" + "=" * 50)
    print("诊断完成")
    print("=" * 50)
    print("""
常见问题快速修复：
  - 所有连接器down → 重启 WorkBuddy
  - 单个连接器disconnected → 重新登录
  - 专家不生效 → 执行 validate + register
  - 自动化不执行 → 检查 status 是否 ACTIVE
  - 配置JSON错误 → 用 jsonlint 检查
""")

if __name__ == "__main__":
    print("WorkBuddy 环境诊断工具 v1.0")
    print(f"检测时间: {Path(sys.argv[0]).name}")

    check_proxy()
    check_connectors()
    check_experts()
    check_logs()
    check_config_files()
    summary()
