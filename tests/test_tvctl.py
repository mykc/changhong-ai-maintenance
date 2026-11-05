"""Offline tests only: the device simulator never invokes adb or contacts a TV."""
import contextlib
import importlib.util
import io
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("tvctl", Path(__file__).resolve().parents[1] / "scripts/tvctl.py")
tvctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tvctl)


class DeviceSimulator:
    def __init__(self):
        self.commands = []
        self.enabled = 0
        self.wss = True
        self.stock = tvctl.STOCK
        self.sdk = "26"
        self.build = "V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30"
        self.root_allowed = True
        self.broken_activity_dump = False
        self.broken_accessibility_read = False
        self.settings = {
            "enabled_accessibility_services": "voice/.A:vendor/.B:voice/.A:app.orchard.tv/.guard.HomeGuardService",
            "accessibility_enabled": "1",
            "enabled_notification_listeners": "keep/.N:app.orchard.tv/app.orchard.tv.guard.RevivalListener",
            "screensaver_components": "clock/.Saver",
        }

    def run(self, argv, timeout=15, limit=262144):
        args = argv[5:] if len(argv) > 3 and argv[3] == "-s" else argv[3:]
        if args[0] != "shell":
            self.commands.append(args)
            if args[0] == "get-state":
                return 0, "device"
            if args[0] == "connect":
                return 0, "connected"
            if args[0] == "root":
                return 0, "adbd is already running as root" if self.root_allowed else "adbd cannot run as root in production builds"
            raise AssertionError(args)
        cmd = shlex.split(args[1])
        self.commands.append(cmd)
        if cmd == ["id"]:
            return 0, "uid=0(root) gid=0(root)"
        if cmd[:1] == ["getprop"]:
            return 0, {"ro.product.name": "full_changhong_mst848", "ro.build.version.sdk": self.sdk,
                       "ro.build.display.id": self.build}[cmd[1]]
        if cmd[:3] == ["cmd", "package", "resolve-activity"]:
            return 0, self.stock
        if cmd == ["cat", "/chperm/preapp/default_launcher"]:
            return 0, "com.changhong.system.launcher.v2;"
        if cmd == ["cat", "/data/chuserdata/killbackground"]:
            return 0, "other.app\napp.orchard.tv"
        if cmd[:2] == ["settings", "get"]:
            if cmd[3] == "enabled_accessibility_services" and self.broken_accessibility_read:
                raise tvctl.CommandError("settings read failed")
            return 0, self.settings.get(cmd[3], "null")
        if cmd[:2] == ["settings", "put"]:
            self.settings[cmd[3]] = cmd[4]
            return 0, ""
        if cmd[:2] == ["settings", "delete"]:
            self.settings.pop(cmd[3], None)
            return 0, "Deleted 1 rows"
        if cmd[:2] == ["dumpsys", "package"]:
            return 0, ("versionName=1.84-guard\n"
                       f"android.permission.WRITE_SECURE_SETTINGS: granted={str(self.wss).lower()}\n"
                       f"User 0: installed=true stopped=false enabled={self.enabled}\n")
        if cmd[:2] == ["dumpsys", "accessibility"]:
            return 0, "Service[label=Aerial 桌面守护]"
        if cmd[:2] == ["dumpsys", "activity"]:
            if self.broken_activity_dump:
                raise tvctl.CommandError("unresponsive application")
            return 0, "Home Guard bound=true"
        if cmd[:2] == ["pm", "path"]:
            return 0, "package:/vendor/app/original/base.apk"
        if cmd[:2] == ["pm", "disable-user"]:
            assert cmd[-1] == tvctl.PKG
            self.enabled = 3
            return 0, "Package app.orchard.tv new state: disabled-user"
        if cmd[:2] == ["pm", "disable"]:
            assert cmd[-1].startswith(tvctl.PKG + "/")
            return 0, "Component new state: disabled"
        if cmd[:2] == ["pm", "revoke"]:
            assert cmd[2] == tvctl.PKG
            self.wss = False
            return 0, ""
        if cmd[:2] == ["am", "force-stop"]:
            assert cmd[-1] == tvctl.PKG
            return 0, ""
        if cmd[:2] == ["am", "start"]:
            return 0, "Status: ok"
        raise AssertionError("Unexpected device command: " + repr(cmd))


class Tests(unittest.TestCase):
    def invoke(self, device, action, execute=True):
        argv = [action, "--ip", "192.0.2.10"] + (["--execute"] if execute else [])
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(tvctl, "LOCAL", Path(directory)), mock.patch.object(tvctl.shutil, "which", return_value="adb"), mock.patch.object(tvctl, "bounded_run", side_effect=device.run), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return tvctl.main(argv)

    def test_mutation_preview_never_resolves_or_invokes_adb(self):
        for action in ("connect-root", "open-background", "emergency-stop", "detach-guard"):
            with self.subTest(action=action), mock.patch.object(tvctl.shutil, "which", side_effect=AssertionError("must not find adb")), mock.patch.object(tvctl, "bounded_run", side_effect=AssertionError("must not execute")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tvctl.main([action, "--ip", "192.0.2.10"]), 0)

    def test_invalid_ip_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            tvctl.parse_args(["inspect", "--ip", "x;reboot"])

    def test_root_precedes_any_shell(self):
        device = DeviceSimulator()
        self.assertEqual(self.invoke(device, "connect-root"), 0)
        self.assertLess(device.commands.index(["root"]), device.commands.index(["id"]))

    def test_root_refusal_never_opens_shell(self):
        device = DeviceSimulator()
        device.root_allowed = False
        self.assertEqual(self.invoke(device, "connect-root"), 1)
        self.assertNotIn(["id"], device.commands)

    def test_inspect_reads_without_grant_root_or_device_writes(self):
        device = DeviceSimulator()
        self.assertEqual(self.invoke(device, "inspect", execute=False), 0)
        self.assertNotIn(["root"], device.commands)
        self.assertFalse(any(c[:2] in (["settings", "put"], ["pm", "disable-user"], ["pm", "grant"]) for c in device.commands))

    def test_emergency_preserves_data_and_settings(self):
        device = DeviceSimulator()
        previous = dict(device.settings)
        self.assertEqual(self.invoke(device, "emergency-stop"), 0)
        self.assertEqual(device.enabled, 3)
        self.assertEqual(device.settings, previous)
        self.assertTrue(any(c[:2] == ["am", "start"] and c[-1] == tvctl.STOCK for c in device.commands))
        self.assertFalse(any("uninstall" in c or "reboot" in c or "remount" in c for c in device.commands))

    def test_emergency_does_not_wait_for_unresponsive_app_dump(self):
        device = DeviceSimulator()
        device.broken_activity_dump = True
        self.assertEqual(self.invoke(device, "emergency-stop"), 0)
        self.assertEqual(device.enabled, 3)
        self.assertFalse(any(c[:2] == ["dumpsys", "activity"] for c in device.commands))

    def test_detach_preserves_other_services_and_disables_before_revoke(self):
        device = DeviceSimulator()
        self.assertEqual(self.invoke(device, "detach-guard"), 0)
        self.assertFalse(device.wss)
        self.assertEqual(device.enabled, 3)
        self.assertEqual(device.settings["enabled_accessibility_services"], "voice/.A:vendor/.B:voice/.A")
        self.assertEqual(device.settings["enabled_notification_listeners"], "keep/.N")
        self.assertEqual(device.settings["accessibility_enabled"], "1")
        self.assertEqual(device.settings["screensaver_components"], "clock/.Saver")
        disable = next(i for i, c in enumerate(device.commands) if c[:2] == ["pm", "disable-user"])
        revoke = next(i for i, c in enumerate(device.commands) if c[:2] == ["pm", "revoke"])
        self.assertLess(disable, revoke)

    def test_emergency_survives_noncritical_settings_read_failure(self):
        device = DeviceSimulator()
        device.broken_accessibility_read = True
        self.assertEqual(self.invoke(device, "emergency-stop"), 0)
        self.assertEqual(device.enabled, 3)

    def test_wrong_home_or_firmware_blocks_mutation(self):
        for field, value in (("stock", "different/.Home"), ("sdk", "27")):
            device = DeviceSimulator()
            setattr(device, field, value)
            self.assertEqual(self.invoke(device, "emergency-stop"), 1)
            self.assertEqual(device.enabled, 0)

    def test_component_filter_is_exact_and_preserves_duplicates(self):
        value = "x/.A:app.orchard.tv/.guard.HomeGuardServiceExtra:x/.A:app.orchard.tv/.guard.HomeGuardService"
        self.assertEqual(tvctl.without_components(value, tvctl.GUARD_NAMES), "x/.A:app.orchard.tv/.guard.HomeGuardServiceExtra:x/.A")

    def test_similar_or_rebuilt_firmware_is_rejected_before_mutation(self):
        for build in ("V1.505710-ZLS82Gi-BuildTime.2025.06.12,12.16.30",
                      "V1.50571-ZLS82Gi-BuildTime.2025.06.13,12.16.30",
                      "V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30-custom"):
            with self.subTest(build=build):
                device = DeviceSimulator()
                device.build = build
                self.assertEqual(self.invoke(device, "emergency-stop"), 1)
                self.assertEqual(device.enabled, 0)
                self.assertFalse(any(cmd[:1] in (["pm"], ["am"], ["settings"]) for cmd in device.commands))

    def test_remote_shell_quotes_metacharacters_as_single_argument(self):
        with mock.patch.object(tvctl, "bounded_run", return_value=(0, "")) as run:
            tv = tvctl.TV("adb", "192.0.2.10", 5038, 5555)
            payload = "keep/.A:odd'/$value;$(echo no)"
            tv.shell("settings", "put", "secure", "example", payload)
            self.assertEqual(shlex.split(run.call_args.args[0][-1])[-1], payload)

    def test_output_flood_is_bounded(self):
        with self.assertRaises(tvctl.CommandError):
            tvctl.bounded_run([sys.executable, "-c", "import sys; sys.stdout.write('Password:'*20000)"], timeout=5, limit=4096)

    def test_silent_command_timeout(self):
        with self.assertRaises(tvctl.CommandError):
            tvctl.bounded_run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.1)


if __name__ == "__main__":
    unittest.main()
