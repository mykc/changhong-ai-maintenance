#!/usr/bin/env python3
"""Read-only policy capture/verification and offline single-package planning.

Python 3.10+, standard library. Capture and verify contact the TV through an
already connected, authorized root ADB session; plan is entirely offline.
No command runs adb connect, requests root, or writes to the TV.
Hashes detect inconsistency; these local artifacts are not signed evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

import tvctl

NAMES = ("installblacklist", "apprunblacklist", "installdowwhitelist")
REMOTE = {name: "/data/chuserdata/" + name for name in NAMES}
MAX_FILE = 1024 * 1024
MAX_JSON = 64 * 1024
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")
CRITICAL = {"android", "com.termux", tvctl.PKG, tvctl.STOCK.split("/")[0]}
META_KEYS = {"remote_path", "sha256", "uid", "gid", "mode", "size", "mtime", "inode", "device", "selinux"}
CONTEXT = re.compile(r"[A-Za-z0-9_]+:[A-Za-z0-9_]+:[A-Za-z0-9_]+:s[0-9]+(?::c[0-9,.-]+)?")


class PolicyError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def exact_keys(value, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise PolicyError(f"Unexpected {label} schema; manual review required.")


def valid_time(value) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise PolicyError("Invalid artifact timestamp.")
    try:
        dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PolicyError("Invalid artifact timestamp.") from exc


def integer(value, maximum: int, label: str) -> None:
    if type(value) is not int or not 0 <= value <= maximum:
        raise PolicyError(f"Invalid {label} metadata.")


def valid_hash(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def local_path(path: Path) -> Path:
    """Do not resolve away symlinks (including Windows directory junctions)."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PolicyError(f"Local symlinks/reparse points are not accepted: {part}")
    return path


def read_file(path: Path, limit: int = MAX_FILE) -> bytes:
    path = local_path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise PolicyError(f"Expected a bounded regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise PolicyError(f"Local file changed while opening: {path}")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PolicyError(f"File exceeds the size limit: {path}")
    return data


def directory(path: Path, expected: set[str]) -> Path:
    path = local_path(path)
    if not path.is_dir() or {entry.name for entry in path.iterdir()} != expected:
        raise PolicyError(f"Unexpected file set: {path}")
    for name in expected:
        local_path(path / name)
    return path


def new_output(path: Path, create: bool = True) -> Path:
    path = local_path(path)
    if path.exists():
        raise PolicyError(f"Output already exists; choose a new directory: {path}")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def write_file(path: Path, data: bytes) -> None:
    local_path(path)
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(0o600)


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def read_json(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PolicyError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(read_file(path, MAX_JSON), object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PolicyError(f"Invalid JSON: {path}") from exc


def validate_metadata(name: str, meta) -> None:
    exact_keys(meta, META_KEYS, name)
    if meta["remote_path"] != REMOTE[name] or not valid_hash(meta["sha256"]):
        raise PolicyError(f"Invalid path or hash metadata: {name}")
    for key in ("uid", "gid"):
        integer(meta[key], 2**32 - 1, key)
    for key in ("mtime", "inode", "device"):
        integer(meta[key], 2**63 - 1, key)
    integer(meta["size"], MAX_FILE, "size")
    if not isinstance(meta["mode"], str) or not re.fullmatch(r"[0-7]{4}", meta["mode"]):
        raise PolicyError(f"Invalid mode metadata: {name}")
    if meta["selinux"] is not None and (not isinstance(meta["selinux"], str) or not CONTEXT.fullmatch(meta["selinux"])):
        raise PolicyError(f"Invalid SELinux metadata: {name}")


def load_snapshot(path: Path) -> tuple[dict, dict[str, bytes]]:
    path = directory(path, set(NAMES) | {"snapshot.json"})
    manifest = read_json(path / "snapshot.json")
    exact_keys(manifest, {"schema_version", "kind", "captured_utc", "files"}, "snapshot")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["kind"] != "policy-list-snapshot":
        raise PolicyError("Unsupported snapshot schema.")
    valid_time(manifest["captured_utc"])
    exact_keys(manifest["files"], set(NAMES), "snapshot files")
    content = {}
    for name in NAMES:
        meta = manifest["files"][name]
        validate_metadata(name, meta)
        data = read_file(path / name)
        if len(data) != meta["size"] or digest(data) != meta["sha256"]:
            raise PolicyError(f"Snapshot bytes do not match metadata: {name}")
        content[name] = data
    return manifest, content


def validate_package(package: str) -> str:
    if not isinstance(package, str) or len(package) > 255 or not PACKAGE.fullmatch(package):
        raise PolicyError("Target must be one valid dotted Android package name.")
    if package in CRITICAL or package.startswith(("android.", "com.android.", "com.changhong.", "com.termux.")):
        raise PolicyError("Critical/platform packages are outside this third-party helper's scope.")
    return package


def package_lines(data: bytes, name: str) -> list[bytes]:
    # This tool supports only the observed grammar, not every possible vendor format.
    if not data or not data.endswith(b"\n"):
        raise PolicyError(f"Unproven format in {name} (empty or missing final LF); manual review required, not proof of a corrupt TV file.")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise PolicyError(f"Unproven non-ASCII format in {name}; manual review required.") from exc
    lines = text[:-1].split("\n")
    if any(len(line) > 255 or (line != "android" and not PACKAGE.fullmatch(line)) for line in lines):
        raise PolicyError(f"Unproven line format in {name}; manual review required (no blank/comment/whitespace/BOM/CR lines supported).")
    return data.splitlines(keepends=True)


def derive(before: dict[str, bytes], package: str) -> dict[str, bytes]:
    validate_package(package)
    target = package.encode("ascii") + b"\n"
    proposed = {}
    for name in NAMES:
        lines = package_lines(before[name], name)
        if name == "installdowwhitelist":
            proposed[name] = before[name] if target in lines else before[name] + target
        else:
            proposed[name] = b"".join(line for line in lines if line != target)
        if len(proposed[name]) > MAX_FILE:
            raise PolicyError(f"Proposed file exceeds size limit: {name}")
    return proposed


def make_diff(before: dict[str, bytes], proposed: dict[str, bytes]) -> bytes:
    return "".join(
        line
        for name in NAMES
        for line in difflib.unified_diff(before[name].decode("ascii").splitlines(keepends=True),
                                         proposed[name].decode("ascii").splitlines(keepends=True),
                                         fromfile="before/" + name, tofile="proposed/" + name)
    ).encode("ascii")


def plan(snapshot: Path, package: str, output: Path) -> Path:
    validate_package(package)
    output = new_output(output, create=False)
    manifest, before = load_snapshot(snapshot)
    proposed = derive(before, package)
    difference = make_diff(before, proposed)
    # Use the validated in-memory manifest, never paths supplied inside it.
    manifest_bytes = json_bytes(manifest)
    result = {"schema_version": 1, "kind": "policy-list-plan", "created_utc": timestamp(),
              "package": package, "before_manifest_sha256": digest(manifest_bytes),
              "proposed": {name: {"sha256": digest(proposed[name]), "size": len(proposed[name])} for name in NAMES}}
    new_output(output)
    for folder in ("before", "proposed"):
        (output / folder).mkdir(mode=0o700)
    for name in NAMES:
        write_file(output / "before" / name, before[name])
        write_file(output / "proposed" / name, proposed[name])
    write_file(output / "before" / "snapshot.json", manifest_bytes)
    write_file(output / "changes.diff", difference)
    write_file(output / "plan.json", json_bytes(result))
    return output


def load_plan(path: Path) -> tuple[dict, dict, dict[str, bytes]]:
    path = directory(path, {"before", "proposed", "changes.diff", "plan.json"})
    result = read_json(path / "plan.json")
    exact_keys(result, {"schema_version", "kind", "created_utc", "package", "before_manifest_sha256", "proposed"}, "plan")
    if type(result["schema_version"]) is not int or result["schema_version"] != 1 or result["kind"] != "policy-list-plan":
        raise PolicyError("Unsupported plan schema.")
    valid_time(result["created_utc"])
    validate_package(result["package"])
    before_manifest, before = load_snapshot(path / "before")
    if not valid_hash(result["before_manifest_sha256"]) or digest(read_file(path / "before" / "snapshot.json", MAX_JSON)) != result["before_manifest_sha256"]:
        raise PolicyError("Before metadata does not match the plan.")
    expected = derive(before, result["package"])
    directory(path / "proposed", set(NAMES))
    exact_keys(result["proposed"], set(NAMES), "proposed files")
    for name in NAMES:
        meta = result["proposed"][name]
        exact_keys(meta, {"sha256", "size"}, "proposed metadata")
        integer(meta["size"], MAX_FILE, "proposed size")
        data = read_file(path / "proposed" / name)
        if not valid_hash(meta["sha256"]) or digest(data) != meta["sha256"] or len(data) != meta["size"] or data != expected[name]:
            raise PolicyError(f"Proposed file is not the exact single-package change: {name}")
    if read_file(path / "changes.diff", 8 * MAX_FILE) != make_diff(before, expected):
        raise PolicyError("Review diff does not match the plan.")
    return result, before_manifest, expected


def remote_stat(tv: tvctl.TV, name: str) -> dict:
    # stat without -L rejects a symlink itself, rather than following its target.
    output = tv.shell("stat", "-c", "%f %u %g %s %Y %i %d", REMOTE[name], timeout=10)
    fields = output.split()
    if len(fields) != 7 or not re.fullmatch(r"[0-9a-fA-F]+", fields[0]) or any(not re.fullmatch(r"[0-9]+", item) for item in fields[1:]):
        raise PolicyError(f"Unrecognized remote stat output: {name}")
    raw_mode = int(fields[0], 16)
    if not stat.S_ISREG(raw_mode):
        raise PolicyError(f"Remote source must be a regular file, never a symlink: {name}")
    uid, gid, size, mtime, inode, device = map(int, fields[1:])
    result = {"uid": uid, "gid": gid, "size": size, "mtime": mtime, "inode": inode,
              "device": device, "mode": f"{stat.S_IMODE(raw_mode):04o}"}
    # Validate bounds before pull or hash reads.
    validate_metadata(name, dict(result, remote_path=REMOTE[name], sha256="0" * 64, selinux=None))
    return result


def remote_state(tv: tvctl.TV, name: str) -> dict:
    before = remote_stat(tv, name)
    output = tv.shell("sha256sum", REMOTE[name], timeout=10)
    match = re.fullmatch(r"([0-9a-f]{64})\s+" + re.escape(REMOTE[name]), output)
    if not match:
        raise PolicyError(f"Unrecognized remote SHA-256 output: {name}")
    # SELinux context is optional; absence is recorded explicitly, never invented.
    context_output = tv.shell("ls", "-Zd", REMOTE[name], checked=False, timeout=10)
    context = context_output.removesuffix(" " + REMOTE[name]).strip()
    context = context if CONTEXT.fullmatch(context) else None
    if before != remote_stat(tv, name):
        raise PolicyError(f"Remote file changed during metadata read: {name}")
    return dict(before, remote_path=REMOTE[name], sha256=match.group(1), selinux=context)


def capture(tv: tvctl.TV, output: Path) -> Path:
    output = new_output(output, create=False)
    tv.check_identity()
    # Refuse indirect parent paths too; all remote operands remain constants.
    parent_modes = tv.shell("stat", "-c", "%f", "/data", "/data/chuserdata", timeout=10).split()
    if len(parent_modes) != 2 or any(not re.fullmatch(r"[0-9a-fA-F]+", mode) or not stat.S_ISDIR(int(mode, 16)) for mode in parent_modes):
        raise PolicyError("Remote policy directories must be real directories, not symlinks.")
    new_output(output)
    states = {name: remote_state(tv, name) for name in NAMES}
    for name in NAMES:
        target = output / name
        tv.run("pull", REMOTE[name], str(target), timeout=15)
        data = read_file(target)
        target.chmod(0o600)
        after = remote_state(tv, name)
        if after != states[name] or digest(data) != states[name]["sha256"] or len(data) != states[name]["size"]:
            raise PolicyError(f"Remote file changed during capture: {name}; incomplete directory has no trusted snapshot manifest.")
    # A later file may have changed an earlier one. Do not publish a mixed snapshot.
    for name in NAMES:
        if remote_state(tv, name) != states[name]:
            raise PolicyError(f"Remote files changed before capture completed: {name}; no trusted snapshot manifest written.")
    write_file(output / "snapshot.json", json_bytes({"schema_version": 1, "kind": "policy-list-snapshot",
                                                    "captured_utc": timestamp(), "files": states}))
    return output


def verify(tv: tvctl.TV, validated: tuple[dict, dict, dict[str, bytes]]) -> None:
    _, before_manifest, proposed = validated
    with tempfile.TemporaryDirectory(prefix="policy-verify-") as temporary:
        current_path = capture(tv, Path(temporary) / "current")
        current_manifest, current = load_snapshot(current_path)
        for name in NAMES:
            if current[name] != proposed[name]:
                raise PolicyError(f"Current TV bytes differ from the reviewed proposal: {name}")
            for key in ("uid", "gid", "mode"):
                if current_manifest["files"][name][key] != before_manifest["files"][name][key]:
                    raise PolicyError(f"Current TV {key} differs from captured metadata: {name}")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    capture_parser = commands.add_parser("capture", help="Read raw policy files from an existing root session")
    capture_parser.add_argument("--out", required=True, type=Path, help="New private directory, preferably under .local/")
    plan_parser = commands.add_parser("plan", help="Generate a single-package plan entirely offline")
    plan_parser.add_argument("--snapshot", required=True, type=Path)
    plan_parser.add_argument("--package", required=True)
    plan_parser.add_argument("--out", required=True, type=Path, help="New private directory, preferably under .local/")
    verify_parser = commands.add_parser("verify", help="Read-only comparison against the proposed bytes and original UID/GID/mode")
    verify_parser.add_argument("--plan", required=True, type=Path)
    for command in (capture_parser, verify_parser):
        command.add_argument("--ip", required=True, help="Current TV IPv4 address; no saved default")
        command.add_argument("--adb", default="adb")
        command.add_argument("--server-port", type=int, default=5038)
        command.add_argument("--port", type=int, default=5555)
    args = parser.parse_args(argv)
    if args.action != "plan":
        try:
            ipaddress.IPv4Address(args.ip)
        except ValueError:
            parser.error("--ip must be an IPv4 address")
        if not all(1 <= port <= 65535 for port in (args.server_port, args.port)):
            parser.error("Ports must be in 1..65535")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "plan":
            output = plan(args.snapshot, args.package, args.out)
            print(f"Offline plan: {output}\nReview changes.diff and metadata before any separately authorized write.")
            return 0
        # Fail local validation before even locating adb.
        validated = load_plan(args.plan) if args.action == "verify" else None
        if args.action == "capture":
            new_output(args.out, create=False)
        adb = shutil.which(args.adb)
        if not adb:
            raise PolicyError("adb not found; specify Google platform-tools with --adb.")
        tv = tvctl.TV(adb, args.ip, args.server_port, args.port)
        if args.action == "capture":
            print(f"Read-only raw snapshot: {capture(tv, args.out)}")
        else:
            assert validated is not None
            verify(tv, validated)
            print("Verified current raw bytes and UID/GID/mode against the plan. Runtime policy, reload, installation, and launch behavior were not checked.")
        return 0
    except (PolicyError, tvctl.CommandError, OSError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
