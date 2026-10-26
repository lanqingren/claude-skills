#!/usr/bin/env python3
"""
企业微信 CLI 一键安装脚本
支持 Windows / macOS / Linux

用法:
  python install.py                                       # 基础安装
  python install.py --bot-id ID --secret S               # 安装并显示初始化引导
  python install.py --skip-init                          # 安装，跳过 init 引导
  python install.py --registry https://registry.npmmirror.com  # 指定 npm 镜像
"""
import sys
import subprocess
import os
import argparse
import shutil
import platform

# 确保 UTF-8 输出，避免 Windows GBK 乱码
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ─── 颜色输出 ─────────────────────────────────────────────
def cyan(s):    return f"\033[96m{s}\033[0m"
def green(s):   return f"\033[92m{s}\033[0m"
def red(s):     return f"\033[91m{s}\033[0m"
def yellow(s):  return f"\033[93m{s}\033[0m"
def white(s):   return f"\033[97m{s}\033[0m"
def magenta(s): return f"\033[95m{s}\033[0m"
def bold(s):    return f"\033[1m{s}\033[0m"

def step(msg):  print(f"\n{cyan('[*] ' + msg)}")
def ok(msg):    print(f"    {green('[OK]  ' + msg)}")
def fail(msg):  print(f"    {red('[FAIL] ' + msg)}")
def warn(msg):  print(f"    {yellow('[WARN] ' + msg)}")
def info(msg):  print(f"    {msg}")
def tip(msg):   print(f"    {cyan('→')} {msg}")

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")

def banner():
    print()
    print(magenta("╔══════════════════════════════════════════════════╗"))
    print(magenta("║") + bold("   企业微信 CLI (wecom-cli) 一键安装向导         ") + magenta("║"))
    print(magenta("║") + "   v2.0 · 支持 Windows / macOS / Linux           " + magenta("║"))
    print(magenta("╚══════════════════════════════════════════════════╝"))
    print()

# ─── 环境检测 ─────────────────────────────────────────────
def check_python_version():
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        fail(f"Python {major}.{minor} 版本过低，需要 Python >= 3.7")
        sys.exit(1)

def check_node():
    step("检测 Node.js 环境...")
    r = run("node --version")
    if r.returncode != 0:
        fail("未检测到 Node.js")
        tip("请前往 https://nodejs.org 下载安装 LTS 版本（>= 18）")
        tip("或使用 nvm：nvm install --lts && nvm use --lts")
        sys.exit(1)
    ver = r.stdout.strip()
    try:
        major = int(ver.lstrip("v").split(".")[0])
    except Exception:
        major = 0
    if major >= 18:
        ok(f"Node.js {ver}（满足 >= 18 要求）")
    else:
        fail(f"Node.js {ver} 版本过低，需要 >= 18")
        tip("推荐使用 nvm 升级:")
        info("    nvm install --lts && nvm use --lts")
        tip("或前往官网下载: https://nodejs.org")
        sys.exit(1)

def check_npm():
    step("检测 npm...")
    r = run("npm --version")
    if r.returncode != 0:
        fail("未检测到 npm，请重新安装 Node.js")
        sys.exit(1)
    ok(f"npm {r.stdout.strip()}")

def check_installed():
    step("检测 wecom-cli 是否已安装...")
    r = run("wecom-cli --version")
    if r.returncode == 0:
        ok(f"wecom-cli {r.stdout.strip()} 已安装，跳过安装步骤")
        return True
    info("未检测到 wecom-cli，开始安装...")
    return False

# ─── 安装步骤 ─────────────────────────────────────────────
def install_cli(registry: str = ""):
    step("安装 @wecom/cli（全局）...")
    reg_flag = f" --registry {registry}" if registry else ""
    cmd = f"npm install -g @wecom/cli{reg_flag}"
    info(f"执行: {cmd}")
    r = subprocess.run(cmd, shell=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail("安装失败")
        if not registry:
            warn("检测到安装失败，尝试使用淘宝镜像重试...")
            return install_cli(registry="https://registry.npmmirror.com")
        tip("仍然失败，请检查网络后手动执行:")
        info(f"    npm install -g @wecom/cli --registry https://registry.npmmirror.com")
        sys.exit(1)
    ok("@wecom/cli 安装完成")
    return True

def install_skills():
    step("安装 wecom-cli Skills（Agent 技能包）...")
    cmd = "npx skills add WeComTeam/wecom-cli -y -g"
    info(f"执行: {cmd}")
    r = subprocess.run(cmd, shell=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        warn("Skills 安装失败（不影响基本命令行使用，可后续手动安装）")
        tip("手动安装命令: npx skills add WeComTeam/wecom-cli -y -g")
    else:
        ok("Skills 安装完成")

def verify_install():
    step("验证安装...")
    r = run("wecom-cli --version")
    if r.returncode == 0:
        ok(f"验证通过: wecom-cli {r.stdout.strip()}")
    else:
        fail("安装后无法调用 wecom-cli")
        warn("可能原因：npm 全局 bin 路径不在 PATH 环境变量中")
        npm_r = run("npm config get prefix")
        if npm_r.returncode == 0:
            prefix = npm_r.stdout.strip()
            if platform.system() == "Windows":
                tip(f"请将以下路径加入系统 PATH: {prefix}")
                tip("PowerShell 临时生效: $env:PATH += ';' + (npm config get prefix)")
            else:
                tip(f"请将以下路径加入 PATH: {prefix}/bin")
                tip(f"bash: export PATH=\"$PATH:{prefix}/bin\"")
        tip("添加 PATH 后重新打开终端即可")
        sys.exit(1)

# ─── 配置引导 ─────────────────────────────────────────────
def config_exists():
    home = os.path.expanduser("~")
    return os.path.exists(os.path.join(home, ".config", "wecom", "bot.enc"))

def guide_init(bot_id: str = "", secret: str = ""):
    step("初始化配置引导...")
    if config_exists():
        ok("已检测到配置文件（~/.config/wecom/bot.enc），无需重新初始化")
        tip("如需重新配置，请在真实终端中执行: wecom-cli init")
        return

    print()
    print(f"    {bold('需要 Bot ID 和 Secret 才能连接企业微信')}")
    print()
    info("获取 Bot ID 和 Secret 步骤:")
    info("  1. 打开企业微信客户端")
    info("  2. 工作台 → 智能机器人 → 手动创建")
    info("  3. 选择「API 模式创建」→ 连接方式选「使用长连接」")
    info("  4. 保存页面上的 Bot ID 和 Secret")
    info("  5. 配置「可见成员」（添加需要使用 CLI 的账号）")
    info("  6. 在「授权」中开启所需权限（通讯录 / 消息 / 文档等）")
    print()

    if bot_id and secret:
        print(f"    {green('✓')} 您的凭证如下（在 wecom-cli init 时输入）:")
        print(f"      Bot ID : {white(bot_id)}")
        print(f"      Secret : {white(secret)}")
        print()

    print(f"    {yellow('⚠')}  {bold('wecom-cli init 必须在真实交互式终端（TTY）中运行')}")
    info("       不支持管道 / 脚本自动化传参")
    print()
    info("请在 Windows Terminal / CMD / PowerShell 窗口中执行:")
    print(f"      {yellow('wecom-cli init')}")
    print()
    info("初始化步骤:")
    info("  1. 方向键选「手动输入 Bot ID 和 Secret」→ 回车")
    info("  2. 输入 Bot ID → 回车")
    info("  3. 输入 Secret → 回车")
    info("  4. 看到「初始化完成 ✅」即可")

# ─── 完成摘要 ─────────────────────────────────────────────
def print_summary():
    print()
    print(magenta("╔══════════════════════════════════════════════════╗"))
    print(magenta("║") + green("   🎉 安装完成！wecom-cli 已就绪                  ") + magenta("║"))
    print(magenta("╚══════════════════════════════════════════════════╝"))
    print()
    print(cyan("快速测试命令:"))
    print("  wecom-cli --version")
    print("  chcp 65001  # Windows 编码设置（PowerShell）")
    print("  wecom-cli contact get_userlist '{}'")
    print()
    print(cyan("支持能力:"))
    print("  contact   通讯录查询与搜索")
    print("  doc       文档 / 智能表格")
    print("  meeting   视频会议管理")
    print("  msg       聊天消息收发")
    print("  schedule  日程增删改查")
    print("  todo      待办事项管理")
    print()
    print(cyan("参考文档:"))
    print("  GitHub : https://github.com/WecomTeam/wecom-cli")
    print("  官方文档: https://open.work.weixin.qq.com/help2/pc/21676")
    print()

# ─── 主入口 ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="企业微信 CLI 一键安装向导",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python install.py
  python install.py --bot-id YOUR_ID --secret YOUR_SECRET
  python install.py --skip-init
  python install.py --registry https://registry.npmmirror.com
        """
    )
    parser.add_argument("--bot-id",    default="", metavar="BOT_ID",
                        help="Bot ID（用于初始化引导提示）")
    parser.add_argument("--secret",    default="", metavar="SECRET",
                        help="Bot Secret（用于初始化引导提示）")
    parser.add_argument("--skip-init", action="store_true",
                        help="跳过 init 引导（已配置过的用户）")
    parser.add_argument("--registry",  default="", metavar="URL",
                        help="指定 npm 镜像源（如: https://registry.npmmirror.com）")
    args = parser.parse_args()

    banner()
    check_python_version()
    check_node()
    check_npm()

    already = check_installed()
    if not already:
        install_cli(registry=args.registry)
        install_skills()
        verify_install()

    if not args.skip_init:
        guide_init(args.bot_id, args.secret)

    print_summary()


if __name__ == "__main__":
    main()
