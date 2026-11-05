# Maintaining app installation policies

[中文](../app-install-policy.md) · [Home](../../README.en.md) · [Recovery rules](recovery.md)

This procedure has only been verified on the [60Q5T / V1.50571](device.md). Its purpose is to let one app be installed, run and initiate APK installations. It does not turn a store into a system app or grant root or silent-install privileges.

## What the three lists control

| File | Controls | Yecao Helper case |
| --- | --- | --- |
| `/data/chuserdata/installblacklist` | Target packages blocked from installation | Remove `fun.yecao.helper` |
| `/data/chuserdata/apprunblacklist` | Packages blocked from running | Remove the same package |
| `/data/chuserdata/installdowwhitelist` | Source apps allowed to initiate installation | Append the same package |

There is also a preset source list at `/chperm/preapp/preinstallpermlist`, which was not changed in this case. `killbackground` is a separate background cleanup list. Aerial's background permission is changed through the factory UI; do not mix it with this task.

The firmware installer and framework check these lists by package name. An allowed source does not make every APK it downloads permissible: a target package on a blacklist may still fail. Enabling Android's “unknown sources” setting alone, or running `pm grant INSTALL_PACKAGES` for an ordinary app, is not a complete solution on this device.

## Original file format

All three files in this case contained one package name per line: ASCII bytes, compatible with UTF-8 without a BOM, LF line endings and a final LF. There were no blank lines, comments or surrounding spaces. Ownership was `system:system` (1000:1000), with mode `0664`. The existing duplicate HuanTV Helper entry in the whitelist was preserved.

Read the current files before planning changes. Never overwrite a TV with an example list. A `#` line may cause whitelist parsing to stop early; do not hide entries with comments. Avoid a BOM, unintended encoding conversion, wrong paths and partially written files.

## Risks and execution order

A precise change for one non-system app is expected to have a low startup risk, but the system framework reads these files. Accidentally adding the launcher or Settings to the run blacklist, losing file permissions or overwriting newer vendor configuration may disrupt normal use. The vendor's AppPermission component updates the lists, so a change may later stop working; permanence is not guaranteed.

1. Verify the model, firmware and current root identity, plus the APK's actual package name, version, signature, compatibility and existing installation. Ordinary Termux SSH is not root. Do not uninstall an existing version merely to experiment with a signature mismatch.
2. Back up all three files to the computer as original bytes. Record SHA-256, ownership, mode, size, modification time and readable security context. Check before and after reading so a vendor refresh does not produce a mixed snapshot.
3. Generate a diff on the computer: remove only the target package from both blacklists and append it to the whitelist only if absent. Preserve other entries, order and duplicates. Explain the effects and recovery method, then continue within the user's authorization.
4. Immediately before writing, confirm that the original files have not changed. Validate the bytes and permissions of new files in a separate temporary directory, then replace each file on the same filesystem. A single-file replacement avoids a partial write, but the three replacements are not one atomic transaction. Track completed steps and prepare conditional rollback after partial failure without overwriting external changes.
5. Read all three files back, compare them byte for byte with the planned content, and verify ownership, mode and format. Stop before installation or reboot if they differ.
6. Within the authorized scope, request the factory reload with `am broadcast --user 0 -a com.changhong.listchanged`. A successful broadcast does not verify that the rules took effect.
7. Check actual installation, execution and installation-source authorization. If using a framework interface, call only inspected, named read-only interfaces; do not guess Binder transaction numbers. After installation, recheck file contents and permissions, and existing Aerial behavior.
8. After the user's test succeeds, clean up the original downloaded APK and temporary computer/TV copies as agreed, while retaining the computer backup. Do not delete installed apps under `/data/app/`.

Do not disable AppPermission, lock the files, repeatedly force an old copy back into place or modify system partitions to preserve the result. These are not steps in this case.

## Read-only backup and offline plan

First establish confirmed root using the [connection guide](connection.md). Run these commands from the repository root. `capture` reads the TV without changing it; `plan` is fully offline:

```text
python -B scripts/policy_lists.py capture --ip TV_IP --out .local/policy-before
python -B scripts/policy_lists.py plan --snapshot .local/policy-before --package fun.yecao.helper --out .local/policy-plan
```

The output directories must not already exist. The backup contains raw files and metadata. The plan contains `before/`, `proposed/`, `changes.diff` and `plan.json`. The tool conservatively rejects unrecognized formats for manual analysis; rejection does not necessarily mean that the original file is invalid.

`capture` checks firmware and root when it runs, but `snapshot.json` stores file metadata only, not device identity or user authorization. Record device and connection verification separately in the private [maintenance record](maintenance-record-template.md) to avoid mixing backups from different TVs.

The tool has no write command. It does not install software, request root or send a reload broadcast. An AI taking over must generate and review a write procedure for the current snapshot, rather than reuse a temporary script with old paths or old expected hashes.

After an authorized write, perform a read-only check:

```text
python -B scripts/policy_lists.py verify --ip TV_IP --plan .local/policy-plan
```

This compares raw bytes, UID/GID and mode. It cannot replace checking rules loaded in memory or testing actual installation. Security contexts are captured but are not compared by `verify`. A device with SELinux enabled needs separate context analysis and verification; SELinux was already Disabled in this case.

`verify` does not retain its temporary readback. After writing and again after installation, run `capture` into new directories such as `.local/policy-after-write` and `.local/policy-after-install`, and record verification output in the maintenance record for later conditional recovery.

The new parameterized tool has only been tested offline; the [Yecao Helper case](yecao.md) used individually reviewed commands with time and output limits.

## Recovery

If the current files still match this operation's post-write snapshot, restore the original bytes and permissions, then reload and verify. If the vendor has updated them, back up the current state and merge only the reversal of this operation's package changes; do not overwrite the whole file with an old list. Restoring a package to the run blacklist prevents Yecao Helper from launching. Uninstalling the app does not remove a manually added whitelist entry or uninstall software that it installed.
