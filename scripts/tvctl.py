#!/usr/bin/env python3
"""Narrow helper for the documented 60Q5T firmware. Python 3.10+, standard library."""
from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time

PKG = "app.orchard.tv"
STOCK = "com.changhong.system.launcher.v2/.Launcher"
VERIFIED_BUILD = "V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30"
GUARD_NAMES = {PKG + "/" + PKG + ".guard.HomeGuardService", PKG + "/.guard.HomeGuardService"}
LISTENER_NAMES = {PKG + "/" + PKG + ".guard.RevivalListener", PKG + "/.guard.RevivalListener"}
LOCAL = Path(__file__).resolve().parent.parent / ".local"
PLANS = {
    "connect-root": "连接 ADB，切换原厂 adbd 为 root，核对机型；不重启电视。",
    "inspect": "在已有 root 会话中定向读取状态，保存私有本地快照。",
    "open-background": "保存快照，打开原厂权限管理页；请用遥控器只设置 Aerial。",
    "emergency-stop": "保存快照，仅停用 Aerial 整包并停止它，打开长虹原桌面；保留数据。",
    "detach-guard": "保存快照，停用 Aerial，撤销其守护权限和服务，打开原桌面；包仍禁用、数据保留。",
}


class CommandError(RuntimeError):
    pass


def bounded_run(argv: list[str], timeout: float = 15, limit: int = 256 * 1024) -> tuple[int, str]:
    """A vendor shell can flood Password forever: bound runtime and captured bytes."""
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    buf = bytearray()
    overflow = threading.Event()

    def reader() -> None:
        assert proc.stdout is not None
        while True:
            part = proc.stdout.read(1024)
            if not part:
                break
            left = max(0, limit - len(buf))
            buf.extend(part[:left])
            if len(part) > left:
                overflow.set()
                try:
                    proc.kill()
                except OSError:
                    pass
                break

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    expired = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        proc.kill()
        proc.wait()
    thread.join(timeout=2)
    assert proc.stdout is not None
    if not thread.is_alive():
        proc.stdout.close()
    if expired or overflow.is_set() or thread.is_alive():
        raise CommandError("命令超时或输出过多，已停止；不要反复尝试普通 shell。")
    text = buf.decode("utf-8", "replace").replace("\r", "").replace("\x00", "").strip()
    return proc.returncode, text


def without_components(value: str, removed: set[str]) -> str:
    if value in ("", "null"):
        return ""
    # Preserve order, duplicates, and every unrelated component; never restore an old full list.
    return ":".join(item for item in value.split(":") if item not in removed)


def user_zero(package: str) -> str:
    match = re.search(r"^\s*User 0:.*$", package, re.MULTILINE)
    if not match:
        raise CommandError("无法识别 User 0 的包状态。")
    return match.group(0)


class TV:
    def __init__(self, adb: str, ip: str, server_port: int, port: int):
        self.adb = adb
        self.serial = f"{ip}:{port}"
        self.base = [adb, "-P", str(server_port)]
        self.history: list[dict] = []

    def run(self, *args: str, checked: bool = True, device: bool = True, timeout: float = 15) -> str:
        cmd = self.base + (["-s", self.serial] if device else []) + list(args)
        code, output = bounded_run(cmd, timeout)
        self.history.append({"args": list(args), "exit": code, "output": output})
        if checked and code != 0:
            raise CommandError(f"命令失败（{code}）：{' '.join(args)}\n{output}")
        return output

    def shell(self, *args: str, **kwargs) -> str:
        # subprocess list escaping protects the local shell; quote separately for Android's shell.
        return self.run("shell", " ".join(shlex.quote(arg) for arg in args), **kwargs)

    def connect(self) -> bool:
        self.run("connect", self.serial, device=False, checked=False)
        return self.run("get-state", checked=False) == "device"

    def connect_root(self) -> None:
        if not self.connect():
            raise CommandError("ADB 未处于 device；先在 Termux 启动 adbd 并解决认证/网络问题。")
        result = self.run("root")
        print(result)
        if not any(x in result.lower() for x in ("already running as root", "restarting adbd as root")):
            raise CommandError("未确认原厂 adb root 成功；不会进入普通 shell。")
        for _ in range(5):
            if self.connect():
                break
            time.sleep(1)
        else:
            raise CommandError("adbd 切换 root 后没有重新连接。")
        self.check_identity()

    def check_identity(self) -> None:
        if self.run("get-state", checked=False) != "device":
            raise CommandError("ADB 不在线。先执行 connect-root；必要时通过 Termux 恢复。")
        if "uid=0(root)" not in self.shell("id", timeout=5):
            raise CommandError("当前不是 root。先执行 connect-root，不继续修改。")
        product = self.shell("getprop", "ro.product.name")
        sdk = self.shell("getprop", "ro.build.version.sdk")
        build = self.shell("getprop", "ro.build.display.id")
        if (product != "full_changhong_mst848" or sdk != "26"
                or build != VERIFIED_BUILD):
            raise CommandError(f"超出本指南实测固件范围，停止：{product} / SDK {sdk} / {build}")

    def snapshot(self, recovery: bool = False) -> dict[str, str]:
        commands = {
            "home": ("cmd", "package", "resolve-activity", "--brief", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME", "-c", "android.intent.category.DEFAULT"),
            "default_launcher": ("cat", "/chperm/preapp/default_launcher"),
            "accessibility_services": ("settings", "get", "secure", "enabled_accessibility_services"),
            "accessibility_enabled": ("settings", "get", "secure", "accessibility_enabled"),
            "notification_listeners": ("settings", "get", "secure", "enabled_notification_listeners"),
            "screensaver_components": ("settings", "get", "secure", "screensaver_components"),
            "background_kill_list": ("cat", "/data/chuserdata/killbackground"),
            "package": ("dumpsys", "package", PKG),
            "accessibility": ("dumpsys", "accessibility"),
            "aerial_activity": ("dumpsys", "activity", PKG + "/.MainActivity"),
        }
        result = {}
        for key, cmd in commands.items():
            # An unresponsive Aerial must not block its own emergency shutdown.
            if recovery and key == "aerial_activity":
                result[key] = "[skipped during recovery: may call the unresponsive application]"
                continue
            try:
                result[key] = self.shell(*cmd, timeout=10 if recovery else 20)
            except CommandError as exc:
                if not recovery or key in ("home", "package"):
                    raise
                result[key] = "[diagnostic unavailable] " + str(exc)
        return result

    def assert_stock_home(self, state: dict[str, str]) -> None:
        if STOCK not in state["home"]:
            raise CommandError("HOME 已不是本方案保留的长虹桌面；停止，避免停用唯一默认桌面。")
        if not self.shell("pm", "path", STOCK.split("/")[0]).startswith("package:"):
            raise CommandError("找不到长虹原桌面。")
        if "installed=true" not in user_zero(state["package"]):
            raise CommandError("未查到用户 0 的 Aerial 安装。")

    def disable_aerial(self) -> None:
        result = self.shell("pm", "disable-user", "--user", "0", PKG)
        if "disabled-user" not in result:
            raise CommandError("停用未确认：" + result)
        self.shell("am", "force-stop", "--user", "0", PKG)
        status = user_zero(self.shell("dumpsys", "package", PKG))
        if "installed=true" not in status or not re.search(r"\benabled=3\b", status):
            raise CommandError("无法核实 Aerial 已停用且数据保留。")

    def detach(self) -> None:
        # Caller disables the entire package first, preventing all its revival paths from racing.
        self.shell("pm", "revoke", PKG, "android.permission.WRITE_SECURE_SETTINGS")
        state = self.shell("dumpsys", "package", PKG)
        if "android.permission.WRITE_SECURE_SETTINGS: granted=true" in state:
            raise CommandError("撤销 WRITE_SECURE_SETTINGS 未生效；Aerial 保持停用。")
        for setting, names in (("enabled_accessibility_services", GUARD_NAMES),
                               ("enabled_notification_listeners", LISTENER_NAMES)):
            current = self.shell("settings", "get", "secure", setting)
            remaining = without_components(current, names)
            if current not in ("", "null") and remaining != current:
                if remaining:
                    self.shell("settings", "put", "secure", setting, remaining)
                else:
                    self.shell("settings", "delete", "secure", setting)
                actual = self.shell("settings", "get", "secure", setting)
                if without_components(actual, set()) != remaining:
                    raise CommandError(f"{setting} 复核不一致，停止并保留现场。")
        for name in ("BootReceiver", "RevivalSyncService", "RevivalListener"):
            result = self.shell("pm", "disable", "--user", "0", PKG + "/.guard." + name)
            if "disabled" not in result:
                raise CommandError("关闭 Aerial 组件未确认：" + name)

    def show_stock(self) -> None:
        result = self.shell("am", "start", "-W", "--user", "0", "-n", STOCK, timeout=25)
        print(result)
        if "Status: ok" not in result:
            raise CommandError("Aerial 已停用，但原桌面启动结果未确认。")
        print("原桌面启动命令成功，请在电视确认画面。Aerial 保持停用、数据保留。")


def save_private(name: str, data) -> Path:
    LOCAL.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = LOCAL / f"{stamp}-{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=PLANS)
    parser.add_argument("--ip", required=True, help="电视当前 IPv4 地址；无内置地址")
    parser.add_argument("--adb", default="adb", help="adb 可执行文件或其完整路径")
    parser.add_argument("--server-port", type=int, default=5038, help="电脑 ADB server 端口")
    parser.add_argument("--port", type=int, default=5555, help="电视 ADB 端口")
    parser.add_argument("--execute", action="store_true", help="执行会改变状态的动作；否则仅预览")
    args = parser.parse_args(argv)
    try:
        ipaddress.IPv4Address(args.ip)
    except ValueError:
        parser.error("--ip 必须是实际 IPv4 地址")
    if not all(1 <= p <= 65535 for p in (args.port, args.server_port)):
        parser.error("端口必须在 1..65535")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    print(PLANS[args.action])
    if args.action != "inspect" and not args.execute:
        print("仅预览，未连接电视。确认影响后加 --execute。")
        return 0
    adb = shutil.which(args.adb)
    if not adb:
        print("找不到 adb。安装 Google platform-tools，并使用 --adb 指定路径。", file=sys.stderr)
        return 1
    tv = TV(adb, args.ip, args.server_port, args.port)
    try:
        if args.action == "connect-root":
            tv.connect_root()
            print("root 身份和固件范围已确认；这是当前会话状态。")
            return 0
        tv.check_identity()
        recovery = args.action in ("emergency-stop", "detach-guard")
        before = tv.snapshot(recovery=recovery)
        print("私有快照：", save_private("before-" + args.action, before))
        if args.action == "inspect":
            for key in ("home", "accessibility_services", "screensaver_components"):
                print(f"[{key}]\n{before[key]}")
            print("Aerial 在后台清理名单中：", PKG in before["background_kill_list"].splitlines())
            for line in before["aerial_activity"].splitlines():
                if "Home Guard" in line:
                    print(line)
            return 0
        if args.action == "open-background":
            result = tv.shell("am", "start", "-W", "-a", "com.changhong.tvmanager.authManager",
                              "-n", "com.changhong.tvmanager/.appmanager.ui.ActivityAppManagerHelp", timeout=25)
            print(result)
            if "Status: ok" not in result:
                raise CommandError("权限管理页面启动未确认。")
            print("请看清后台启动页面和 Aerial 焦点，再用遥控器操作。工具没有切换任何开关。")
            return 0
        tv.assert_stock_home(before)
        tv.disable_aerial()
        if args.action == "detach-guard":
            tv.detach()
        tv.show_stock()
        after = tv.snapshot(recovery=True)
        print("恢复后快照：", save_private("after-" + args.action, after))
        original_others = without_components(before["accessibility_services"], GUARD_NAMES)
        final_others = without_components(after["accessibility_services"], GUARD_NAMES)
        if any(state["accessibility_services"].startswith("[diagnostic unavailable]") for state in (before, after)):
            print("恢复已执行，但未能读取完整无障碍状态；请保留日志后续核查。")
        elif original_others != final_others:
            raise CommandError("其他无障碍条目出现变化；没有用旧表覆盖，请人工核查快照。")
        print("未改后台运行开关/系统屏保/默认桌面文件，未卸载、清数据或重启。")
        return 0
    except (CommandError, OSError) as exc:
        print(f"操作未全部完成：{exc}\n请保留日志，勿盲目重复或恢复出厂。", file=sys.stderr)
        return 1
    finally:
        if tv.history:
            print("私有命令记录：", save_private("commands-" + args.action, tv.history))


if __name__ == "__main__":
    raise SystemExit(main())
