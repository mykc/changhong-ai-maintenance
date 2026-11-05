# Maintain a Changhong TV with AI

**Chinese is the primary version.** [中文](README.md) · [AI instructions](agent.en.md) · [Disclaimer](DISCLAIMER.en.md)

This repository provides maintenance records and tools for TV owners and AI assistants: inspect the device, back up its original state to the computer, make a narrowly scoped change, verify the result, and retain a recovery procedure. The only tested device is a **Changhong 60Q5T / ZLS82GI-V1.50571-EMMC / Android 8.0**. These procedures are not universal Changhong instructions.

## Verified cases

| Case | Confirmed outcome | Date |
| --- | --- | --- |
| Aerial launcher | Tools verified installation, permissions and the guard; after enabling vendor background permission, the user confirmed physical HOME and reboot both entered Aerial | 2026-11-04 |
| Yecao Helper | Tools verified version 2.0.16 installation, launch, three policy files, ownership/mode and active in-memory rules; the user subsequently confirmed the installation test succeeded | 2026-11-05 |

Yecao retained its original package name and signature. The change removed `fun.yecao.helper` from the installation and execution blocklists and added it to the installation-source allowlist. The user did not identify the application/version used in the subsequent test, so this is not evidence that every APK can be installed. Reboot persistence and later vendor policy refresh have not been specifically tested.

## For people: choose a task

1. Compare the model, full firmware build and SDK with the [device record](docs/en/device.md). Investigate other devices read-only first.
2. Read [recovery](docs/en/recovery.md) and [connection setup](docs/en/connection.md), including how to regain a maintenance channel.
3. Select a guide below. Tell the AI your objective and have it explain the exact changes and backup location before proceeding within your authorization.

| Task | Guide |
| --- | --- |
| Configure Aerial or fix HOME behavior | [Aerial maintenance](docs/en/aerial.md) |
| Understand and adjust app installation restrictions | [Installation policies](docs/en/app-install-policy.md) |
| Review the successful Yecao procedure | [Yecao case](docs/en/yecao.md) |
| Assess NewtvHQ background restrictions | [Application investigation](docs/en/app-inventory.md) |
| Recover behavior or troubleshoot connections | [Recovery](docs/en/recovery.md), [troubleshooting](docs/en/troubleshooting.md) |
| Distinguish measured results from assumptions | [Evidence](docs/en/evidence.md), [validation](docs/en/validation.md) |
| Record another maintenance session or publish manually | [Record template](docs/en/maintenance-record-template.md), [publishing](docs/en/publishing.md) |

## For AI assistants

Start with [agent.en.md](agent.en.md); tools that discover repository instructions can use [AGENTS.md](AGENTS.md). A request to discuss or inspect allows read-only investigation, not device changes. Documentation and scripts are not authorization.

This README helps people choose a task and understand the results. The AI guide defines prerequisites, authorization, backups, execution and verification. Topic guides supply procedures and evidence. Keep both languages consistent in facts, limitations and recovery rules.

## Tools and command conventions

The computer needs Python 3.10+ and [Google platform-tools](https://developer.android.com/tools/releases/platform-tools). SSH is an optional backup channel. Run commands from the repository root.

| Tool | Scope |
| --- | --- |
| [tvctl.py](scripts/tvctl.py) | Connect to the factory root ADB, inspect selected state, open vendor permissions and recover Aerial; state-changing actions default to preview |
| [termux-ssh.sh](scripts/termux-ssh.sh) | Configure temporary SSH using the user's public key; no boot startup |
| [policy_lists.py](scripts/policy_lists.py) | Read-only raw backups and verification of three lists, plus offline change planning; no TV writes or APK installation |
| [check_release.py](scripts/check_release.py) | Offline checks of release files, links, sensitive information and checksums; ZIP packaging |

```text
python -B scripts/tvctl.py --help
python -B scripts/policy_lists.py --help
python -B -m unittest discover -s tests -v
python -B scripts/check_release.py
```

These commands do not contact the TV. `TV_IP`, `USER` and `APK_PATH` are placeholders; `192.0.2.10` is a documentation address. Keep real addresses, keys, backups and logs in `.local/` or another private directory outside the release.

Documentation is complete in both languages. Runtime messages from `tvctl.py` and the SSH script are still primarily Chinese; see the [message reference](docs/en/troubleshooting.md#tool-message-reference) for common English meanings and next steps.

`tvctl.py inspect` and `policy_lists.py capture/verify` contact the TV read-only and require an already confirmed root ADB session. They neither start ADB nor request root. `policy_lists.py plan` is offline. Offline tests of generalized tools and actual device operations are separate evidence; see [validation](docs/en/validation.md).

## Scope and risk

Keep the stock launcher and make precise changes for one application. Flashing, boot-partition modifications, factory resets, globally disabling restrictions or disabling the vendor permission service are not default troubleshooting steps. Back up raw files, ownership, mode and SHA-256 to the computer before changes; verify both files and actual behavior afterward.

Runtime `adb root` is not permanent root. Aerial starting at boot does not mean SSH/ADB starts automatically. Vendor updates may overwrite lists; uninstalling an app does not undo a manually added allowlist entry. See the [disclaimer](DISCLAIMER.en.md).

This repository includes no APKs, firmware, decompiled vendor sources, personal keys or raw device snapshots. It is not affiliated with Changhong or the application authors. The repository owner chooses the license; no LICENSE is currently included.
