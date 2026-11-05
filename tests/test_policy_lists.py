"""Offline policy tests. All device operations use an in-memory ADB simulator."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    spec = importlib.util.spec_from_file_location("policy_lists", SCRIPTS / "policy_lists.py")
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
finally:
    sys.path.remove(str(SCRIPTS))

TARGET = "fun.yecao.helper"
BEFORE = {
    "installblacklist": b"other.app\nfun.yecao.helper\nother.app\nfun.yecao.helper.extra\nfun.yecao.helper\n",
    "apprunblacklist": b"fun.yecao.helper\nkeep.app\nkeep.app\n",
    "installdowwhitelist": b"source.app\nsource.app\n",
}


class DeviceSimulator:
    def __init__(self):
        self.content = dict(BEFORE)
        self.meta = {name: {"uid": 1000, "gid": 1000, "mode": 0o664, "mtime": 1234567890,
                            "inode": index + 1, "device": 42, "filetype": stat.S_IFREG}
                     for index, name in enumerate(policy.NAMES)}
        self.commands = []
        self.state = "device"
        self.root = True
        self.sdk = "26"
        self.parent_symlink = False
        self.context_available = True
        self.fail_pull = None
        self.after_pull = None
        self.stat_hook = None
        self.stat_count = {name: 0 for name in policy.NAMES}

    def run(self, argv, timeout=15, limit=262144):
        if argv[:5] != ["adb", "-P", "5038", "-s", "192.0.2.10:5555"]:
            raise AssertionError("Missing explicit device/server selection: " + repr(argv))
        if not 0 < timeout <= 15:
            raise AssertionError("Unbounded read")
        args = argv[5:]
        if args[0] == "shell":
            args = shlex.split(args[1])
        self.commands.append(args)
        if args == ["get-state"]:
            return 0, self.state
        if args == ["id"]:
            return 0, "uid=0(root) gid=0(root)" if self.root else "uid=2000(shell)"
        if args[:1] == ["getprop"]:
            return 0, {"ro.product.name": "full_changhong_mst848", "ro.build.version.sdk": self.sdk,
                       "ro.build.display.id": "V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30"}[args[1]]
        if args == ["stat", "-c", "%f", "/data", "/data/chuserdata"]:
            return 0, "41ed\n" + ("a1ff" if self.parent_symlink else "41ed")
        if args[0] == "pull":
            name = Path(args[1]).name
            if args[1] != policy.REMOTE[name]:
                raise AssertionError("Unexpected remote source")
            if self.fail_pull == name:
                return 1, "simulated pull failure"
            Path(args[2]).write_bytes(self.content[name])
            if self.after_pull:
                self.after_pull(name)
            return 0, "1 file pulled"
        if args[:2] == ["stat", "-c"]:
            if args[2] != "%f %u %g %s %Y %i %d":
                raise AssertionError(args)
            name = Path(args[3]).name
            if args[3] != policy.REMOTE[name]:
                raise AssertionError("Unexpected remote source")
            self.stat_count[name] += 1
            if self.stat_hook:
                self.stat_hook(name, self.stat_count[name])
            meta = self.meta[name]
            return 0, f"{meta['filetype'] | meta['mode']:x} {meta['uid']} {meta['gid']} {len(self.content[name])} {meta['mtime']} {meta['inode']} {meta['device']}"
        if args[0] == "sha256sum":
            name = Path(args[1]).name
            return 0, policy.digest(self.content[name]) + "  " + args[1]
        if args[:2] == ["ls", "-Zd"]:
            if self.context_available:
                return 0, "u:object_r:system_data_file:s0 " + args[2]
            return 1, "context unavailable"
        raise AssertionError("Unexpected command (including any device write): " + repr(args))


class Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.device = DeviceSimulator()

    def tearDown(self):
        self.temporary.cleanup()

    def tv(self):
        return policy.tvctl.TV("adb", "192.0.2.10", 5038, 5555)

    def capture(self, name="snapshot"):
        with mock.patch.object(policy.tvctl, "bounded_run", side_effect=self.device.run):
            return policy.capture(self.tv(), self.root / name)

    def create_plan(self):
        snapshot = self.capture()
        with self.offline():
            return policy.plan(snapshot, TARGET, self.root / "plan")

    @contextlib.contextmanager
    def offline(self):
        with mock.patch.object(policy.shutil, "which", side_effect=AssertionError("No adb discovery offline")), mock.patch.object(policy.tvctl, "bounded_run", side_effect=AssertionError("No network/device invocation offline")):
            yield

    def invoke(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as error:
            result = policy.main(args)
        return result, output.getvalue(), error.getvalue()

    def edit_json(self, path, update):
        value = json.loads(path.read_bytes())
        update(value)
        path.write_bytes(policy.json_bytes(value))

    def test_capture_preserves_all_raw_bytes_without_format_conversion(self):
        raw = b"\xef\xbb\xbfentry.one\r\n\x00\xff trailing  "
        self.device.content["installblacklist"] = raw
        snapshot = self.capture()
        manifest, content = policy.load_snapshot(snapshot)
        self.assertEqual(content["installblacklist"], raw)
        self.assertEqual(manifest["files"]["installblacklist"]["sha256"], policy.digest(raw))
        self.assertEqual(manifest["files"]["installblacklist"]["mode"], "0664")
        self.assertEqual(manifest["files"]["installblacklist"]["selinux"], "u:object_r:system_data_file:s0")
        self.assertEqual(sum(command[0] == "pull" for command in self.device.commands), 3)
        self.assertNotIn("cat", [command[0] for command in self.device.commands])

    def test_identity_precedes_every_policy_file_read(self):
        self.capture()
        identity_end = self.device.commands.index(["getprop", "ro.build.display.id"])
        first_file = next(index for index, command in enumerate(self.device.commands) if command[0] == "stat")
        self.assertLess(identity_end, first_file)
        self.assertEqual(self.device.commands[:2], [["get-state"], ["id"]])
        self.assertFalse(any(command[0] in {"connect", "root", "push", "install", "reboot", "am"} for command in self.device.commands))

    def test_auth_root_and_firmware_failures_never_read_policy_files(self):
        for field, value in (("state", "unauthorized"), ("root", False), ("sdk", "27")):
            with self.subTest(field=field):
                self.device = DeviceSimulator()
                setattr(self.device, field, value)
                with self.assertRaises(policy.tvctl.CommandError):
                    self.capture(field)
                self.assertFalse(any(command[0] in {"stat", "sha256sum", "pull", "root", "connect"} for command in self.device.commands))
                self.assertFalse((self.root / field).exists())

    def test_capture_records_actual_mode_owner_and_missing_context(self):
        self.device.meta["installblacklist"].update(uid=123, gid=456, mode=0o600)
        self.device.context_available = False
        snapshot = self.capture()
        manifest, _ = policy.load_snapshot(snapshot)
        meta = manifest["files"]["installblacklist"]
        self.assertEqual((meta["uid"], meta["gid"], meta["mode"], meta["selinux"]), (123, 456, "0600", None))

    def test_target_exactness_order_and_duplicates(self):
        path = self.create_plan()
        _, manifest, proposed = policy.load_plan(path)
        self.assertEqual(proposed["installblacklist"], b"other.app\nother.app\nfun.yecao.helper.extra\n")
        self.assertEqual(proposed["apprunblacklist"], b"keep.app\nkeep.app\n")
        self.assertEqual(proposed["installdowwhitelist"], BEFORE["installdowwhitelist"] + b"fun.yecao.helper\n")
        for name in policy.NAMES:
            self.assertEqual((path / "before" / name).read_bytes(), BEFORE[name])
            self.assertEqual(manifest["files"][name]["mode"], "0664")
        difference = (path / "changes.diff").read_text(encoding="ascii")
        self.assertIn("-fun.yecao.helper\n", difference)
        self.assertIn("+fun.yecao.helper\n", difference)

    def test_existing_whitelist_target_duplicates_are_not_appended_or_removed(self):
        self.device.content["installdowwhitelist"] = b"fun.yecao.helper\nsource.app\nfun.yecao.helper\n"
        path = self.create_plan()
        self.assertEqual((path / "proposed" / "installdowwhitelist").read_bytes(), self.device.content["installdowwhitelist"])

    def test_blacklist_containing_only_target_can_become_empty(self):
        self.device.content["installblacklist"] = b"fun.yecao.helper\nfun.yecao.helper\n"
        path = self.create_plan()
        self.assertEqual(policy.load_plan(path)[2]["installblacklist"], b"")

    def test_unknown_format_is_refused_for_manual_review_before_creating_plan(self):
        for index, raw in enumerate((b"", b"other.app", b"other.app\r\n", b"\xef\xbb\xbfother.app\n", b"other.app\n\n", b"#comment\n", b" other.app\n", b"other.app \n", b"other.app\x00\n", b"other.\xff\n")):
            with self.subTest(raw=raw):
                self.device.content["installblacklist"] = raw
                snapshot = self.capture(f"snapshot{index}")
                output = self.root / f"plan{index}"
                with self.offline(), self.assertRaisesRegex(policy.PolicyError, "manual review"):
                    policy.plan(snapshot, TARGET, output)
                self.assertFalse(output.exists())

    def test_dangerous_and_critical_targets_are_refused_offline(self):
        for target in ("fun.yecao.helper;reboot", "foo.$(id)", "foo.`id`", "foo.'x'", "foo/bar", "foo\\bar", "foo..bar", "foo.123", "foo.app\n", "foo.app\x00", "android", "com.android.settings", "com.termux", "app.orchard.tv", "com.changhong.system.launcher.v2"):
            with self.subTest(target=target), self.offline():
                code, _, _ = self.invoke(["plan", "--snapshot", str(self.root / "missing"), "--package", target, "--out", str(self.root / "new")])
                self.assertEqual(code, 1)
        self.assertFalse((self.root / "new").exists())

    def test_help_errors_and_plan_never_discover_or_run_adb(self):
        snapshot = self.capture()
        with self.offline():
            code, _, _ = self.invoke(["plan", "--snapshot", str(snapshot), "--package", TARGET, "--out", str(self.root / "plan")])
            self.assertEqual(code, 0)
            for args, expected in ((["--help"], 0), (["plan", "--help"], 0), (["capture", "--ip", "x;reboot", "--out", "unused"], 2), (["capture", "--ip", "192.0.2.10", "--port", "0", "--out", "unused"], 2), (["apply"], 2), (["plan"], 2)):
                with self.subTest(args=args), self.assertRaises(SystemExit) as caught:
                    self.invoke(args)
                self.assertEqual(caught.exception.code, expected)

    def test_output_directory_is_never_overwritten(self):
        snapshot = self.capture()
        before = (snapshot / "installblacklist").read_bytes()
        with self.offline():
            code, _, _ = self.invoke(["capture", "--ip", "192.0.2.10", "--out", str(snapshot)])
            self.assertEqual(code, 1)
            with self.assertRaises(policy.PolicyError):
                policy.plan(snapshot, TARGET, snapshot)
        self.assertEqual((snapshot / "installblacklist").read_bytes(), before)

    def test_partial_capture_has_no_trusted_manifest(self):
        self.device.fail_pull = "apprunblacklist"
        with self.assertRaises(policy.tvctl.CommandError):
            self.capture()
        self.assertTrue((self.root / "snapshot" / "installblacklist").exists())
        self.assertFalse((self.root / "snapshot" / "snapshot.json").exists())
        with self.assertRaises(policy.PolicyError):
            policy.load_snapshot(self.root / "snapshot")

    def test_change_during_pull_is_rejected(self):
        def change(name):
            self.device.content[name] += b"new.entry\n"
        self.device.after_pull = change
        with self.assertRaisesRegex(policy.PolicyError, "changed during capture"):
            self.capture()
        self.assertFalse((self.root / "snapshot" / "snapshot.json").exists())

    def test_final_all_file_recheck_catches_an_earlier_file_update(self):
        def change(name):
            if name == "installdowwhitelist":
                self.device.content["installblacklist"] += b"official.update\n"
        self.device.after_pull = change
        with self.assertRaisesRegex(policy.PolicyError, "before capture completed"):
            self.capture()
        self.assertFalse((self.root / "snapshot" / "snapshot.json").exists())

    def test_remote_metadata_change_is_rejected_even_if_bytes_match(self):
        def change(name):
            self.device.meta[name]["mode"] = 0o600
        self.device.after_pull = change
        with self.assertRaisesRegex(policy.PolicyError, "changed during capture"):
            self.capture()
        self.assertFalse((self.root / "snapshot" / "snapshot.json").exists())

    def test_remote_symlinks_and_parent_symlinks_are_rejected_before_pull(self):
        self.device.meta["installblacklist"]["filetype"] = stat.S_IFLNK
        with self.assertRaisesRegex(policy.PolicyError, "symlink"):
            self.capture("filelink")
        self.assertFalse(any(command[0] == "pull" for command in self.device.commands))
        self.device = DeviceSimulator()
        self.device.parent_symlink = True
        with self.assertRaisesRegex(policy.PolicyError, "symlink"):
            self.capture("parentlink")
        self.assertFalse(any(command[0] == "pull" for command in self.device.commands))

    def test_remote_size_limit_is_enforced_before_hash_or_pull(self):
        self.device.content["installblacklist"] = b"a" * (policy.MAX_FILE + 1)
        with self.assertRaisesRegex(policy.PolicyError, "size"):
            self.capture()
        self.assertFalse(any(command[0] in {"pull", "sha256sum"} for command in self.device.commands))

    def test_snapshot_bytes_file_set_paths_and_metadata_are_validated_offline(self):
        snapshot = self.capture()
        manifest_path = snapshot / "snapshot.json"
        original = manifest_path.read_bytes()
        for key, value in (("remote_path", "/data/chuserdata/../system/evil;reboot"), ("uid", -1), ("gid", True), ("mode", "0664;reboot"), ("size", 999), ("sha256", "0" * 64), ("mtime", "123"), ("selinux", "wrong context")):
            with self.subTest(key=key), self.offline():
                manifest_path.write_bytes(original)
                self.edit_json(manifest_path, lambda data: data["files"]["installblacklist"].update({key: value}))
                with self.assertRaises(policy.PolicyError):
                    policy.plan(snapshot, TARGET, self.root / "never")
        manifest_path.write_bytes(original)
        (snapshot / "installblacklist").write_bytes(b"changed.file\n")
        with self.offline(), self.assertRaises(policy.PolicyError):
            policy.load_snapshot(snapshot)
        (snapshot / "installblacklist").write_bytes(BEFORE["installblacklist"])
        (snapshot / "extra").write_bytes(b"unexpected")
        with self.offline(), self.assertRaisesRegex(policy.PolicyError, "file set"):
            policy.load_snapshot(snapshot)

    def test_unknown_schema_and_duplicate_json_keys_are_rejected(self):
        snapshot = self.capture()
        path = snapshot / "snapshot.json"
        original = path.read_bytes()
        for change in (lambda data: data.update(schema_version=True), lambda data: data.update(schema_version=2), lambda data: data.update(extra=True), lambda data: data["files"].pop("apprunblacklist")):
            path.write_bytes(original)
            self.edit_json(path, change)
            with self.assertRaises(policy.PolicyError):
                policy.load_snapshot(snapshot)
        path.write_bytes(b'{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(policy.PolicyError, "Duplicate"):
            policy.load_snapshot(snapshot)

    def test_deeply_nested_json_stops_cleanly_offline(self):
        snapshot = self.capture()
        # JSON recursion limits vary across Python versions. A valid nested
        # array must still fail the snapshot schema if the parser accepts it.
        for payload in (b"[" * 2000 + b"]" * 2000, b"[" * 2000):
            with self.subTest(well_formed=payload.endswith(b"]")):
                (snapshot / "snapshot.json").write_bytes(payload)
                with self.offline():
                    code, _, error = self.invoke(["plan", "--snapshot", str(snapshot), "--package", TARGET, "--out", str(self.root / "plan")])
                self.assertEqual(code, 1)
                self.assertRegex(error, r"Invalid JSON|Unexpected snapshot schema")
                self.assertFalse((self.root / "plan").exists())

    def test_tampered_proposal_with_updated_hash_is_still_rejected_before_adb(self):
        path = self.create_plan()
        changed = b"unrelated.new\n"
        (path / "proposed" / "apprunblacklist").write_bytes(changed)
        self.edit_json(path / "plan.json", lambda data: data["proposed"]["apprunblacklist"].update(sha256=policy.digest(changed), size=len(changed)))
        with self.offline():
            code, _, error = self.invoke(["verify", "--ip", "192.0.2.10", "--plan", str(path)])
        self.assertEqual(code, 1)
        self.assertIn("exact single-package", error)

    def test_tampered_before_metadata_diff_and_package_are_rejected_offline(self):
        path = self.create_plan()
        plan_original = (path / "plan.json").read_bytes()
        meta_original = (path / "before" / "snapshot.json").read_bytes()
        diff_original = (path / "changes.diff").read_bytes()
        changes = (
            lambda: self.edit_json(path / "before" / "snapshot.json", lambda data: data["files"]["apprunblacklist"].update(mode="0600")),
            lambda: (path / "changes.diff").write_bytes(b"misleading review\n"),
            lambda: self.edit_json(path / "plan.json", lambda data: data.update(package="other.application")),
        )
        for change in changes:
            (path / "plan.json").write_bytes(plan_original)
            (path / "before" / "snapshot.json").write_bytes(meta_original)
            (path / "changes.diff").write_bytes(diff_original)
            change()
            with self.offline():
                code, _, _ = self.invoke(["verify", "--ip", "192.0.2.10", "--plan", str(path)])
                self.assertEqual(code, 1)

    def test_local_file_and_directory_symlinks_are_rejected(self):
        snapshot = self.capture()
        real = self.root / "real"
        real.write_bytes(BEFORE["installblacklist"])
        target = snapshot / "installblacklist"
        target.unlink()
        try:
            target.symlink_to(real)
        except OSError:
            self.skipTest("OS does not allow creating test symlinks")
        with self.offline(), self.assertRaisesRegex(policy.PolicyError, "symlinks"):
            policy.load_snapshot(snapshot)
        directory_link = self.root / "directory-link"
        directory_link.symlink_to(snapshot, target_is_directory=True)
        with self.offline(), self.assertRaisesRegex(policy.PolicyError, "symlinks"):
            policy.load_snapshot(directory_link)

    def test_local_symlink_detection_without_os_symlink_privileges(self):
        path = self.root / "source"
        with mock.patch.object(Path, "lstat", return_value=os.stat_result((stat.S_IFLNK | 0o777,) + (0,) * 9)), self.assertRaisesRegex(policy.PolicyError, "symlinks"):
            policy.read_file(path)

    def test_verify_matches_raw_bytes_owner_and_mode_without_runtime_claim(self):
        path = self.create_plan()
        self.device.content = policy.load_plan(path)[2]
        self.device.commands.clear()
        with mock.patch.object(policy.shutil, "which", return_value="adb"), mock.patch.object(policy.tvctl, "bounded_run", side_effect=self.device.run):
            code, output, error = self.invoke(["verify", "--ip", "192.0.2.10", "--plan", str(path)])
        self.assertEqual(code, 0, error)
        self.assertIn("Runtime policy, reload, installation, and launch behavior were not checked", output)
        self.assertFalse(any(command[0] in {"connect", "root", "push", "am", "install"} for command in self.device.commands))

    def test_verify_rejects_postwrite_metadata_mismatch_and_raw_byte_mismatch(self):
        path = self.create_plan()
        validated = policy.load_plan(path)
        expected_meta = copy.deepcopy(self.device.meta)
        for field, value in (("mode", 0o600), ("uid", 0), ("gid", 0), ("bytes", b"keep.app\r\nkeep.app\r\n")):
            with self.subTest(field=field):
                self.device.content = dict(validated[2])
                self.device.meta = copy.deepcopy(expected_meta)
                if field == "bytes":
                    self.device.content["apprunblacklist"] = value
                else:
                    self.device.meta["apprunblacklist"][field] = value
                with mock.patch.object(policy.tvctl, "bounded_run", side_effect=self.device.run), self.assertRaisesRegex(policy.PolicyError, "differ"):
                    policy.verify(self.tv(), validated)


if __name__ == "__main__":
    unittest.main()
