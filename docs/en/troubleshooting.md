# Troubleshooting

[中文](../troubleshooting.md) · [Home](../../README.en.md)

## Connection to port 5555 is refused

An enabled ADB setting does not prove that adbd is running. First confirm the IP address and network, then run `/system/bin/setprop ctl.start adbd` in Termux. This service name worked on this TV; do not spell it `adbb`. Do not start ATCMD services or open factory menus for this purpose.

If this command is denied, the environment differs from the verified device. Stop: this guide does not provide a universal privilege-escalation method for Changhong firmware.

## `unauthorized` or authentication failure

Continue only when the device state is `device`. If a debugging authorization prompt appears, the user should verify the connection source before allowing it. An early authentication failure in this case later changed to `device`, but the cause was not fully established. This is not an authentication-bypass procedure. Stop if the failure persists.

## The shell repeatedly prints `Password:`

Stop that client command. Run `adb root` first, reconnect, then run `id`. `tvctl.py` limits continuous output and execution time. It neither guesses passwords nor changes the system password.

## Installation fails or signatures conflict

Require an actual `Success` result, not merely a zero process exit code. Check the Android SDK, APK source and package name. Do not automatically uninstall an existing app after a signature mismatch, because that loses app data. The guard and standard builds share a package name; do not treat them as independent apps that can be freely installed over each other.

## Aerial works in the foreground, but HOME returns to Changhong after opening another app

First check the factory Background Startup setting, then the PID and guard binding. An entry in accessibility settings does not prove that the process is alive. Without background permission on this TV, Aerial was terminated about 1–2 seconds after entering the background.

The acceptance test is to keep another app in the foreground, confirm Aerial survives in the background, then press physical HOME. Pressing HOME only while in Aerial, or merely running `am start`, is insufficient.

If background permission is on and the process is alive but HOME still fails, record the current `Home Guard` diagnostic line and existing services, then investigate one cause at a time. Do not arbitrarily disable Changhong TaskMonitorService, voice services or all accessibility services.

## Are `filterHomeAlways` or custom keycodes needed?

They were not needed in this case. The Android 8 guard already requests key filtering. This option mainly addresses other system behavior and may affect long-press volume handling. Custom HOME handling in the firmware does not establish a need to modify system keycodes. The user reported that HOME worked after allowing background activity, so preserve that successful configuration first.

## Permission is granted, but the guard is not bound

First confirm `WRITE_SECURE_SETTINGS: granted=true` and check that the entire Aerial package is not still disabled. You can stop and reopen Aerial. In this case, bringing an old task to the foreground did not perform full initialization; restarting the app bound the guard successfully. Do not repeatedly clear or overwrite the entire accessibility list.

## SSH disappears

The vendor may terminate Termux, or it may not start after a reboot. Open Termux and rerun your own SSH initialization script, then recheck the username, port and host fingerprint. Do not allow every app to run in the background just to preserve SSH, and do not mistake ordinary SSH for root.

The Aerial case authorized background permission only for Aerial; Termux was not automatically allowed. Persistent background permission for Termux requires explaining its effects and obtaining separate authorization.

## It stops working after an upgrade

The installation handling in this firmware includes logic that adds third-party apps to the background cleanup list. Installing over an existing app follows that path too. After an upgrade, recheck:

1. Aerial's factory Background Startup setting.
2. WSS permission and actual HomeGuard binding.
3. Whether Aerial's BootReceiver is restricted.
4. Physical HOME from another app, sound, standby and functions important to the user.

Do not begin every upgrade by resetting all permissions. Read the current state first. Before a reboot test, confirm authorization and prepare a recovery channel.

## Which logs should remain private?

Read only known setting keys. Do not run `settings list secure` and paste the complete output into GitHub: historical configuration on this TV may contain network credentials. Keep raw screenshots, device lists, complete app logs, SSH known_hosts and keys locally. Publish only the necessary sanitized excerpts.

## A store is installed, but will not open or cannot install other apps

The installation blacklist, run blacklist and installation-source whitelist are three independent checks. Read the current three lists and relevant switches, confirm the store's actual package name, then check whether the target APK it is installing is restricted. Changing only one list may be insufficient. ADB installation does not guarantee bypassing framework checks. See [installation-policy maintenance](app-install-policy.md).

## Policy changes do not take effect, or stop working later

Recheck file bytes, permissions and the actual system rules. Distinguish an incorrect write from a framework reload that has not happened or a vendor refresh that overwrote the files. Read only relevant setting keys and necessary logs. Vendor updates can rewrite lists; do not blindly restore old files repeatedly or disable the entire permission service.

## Only SSH works, and pm reports that app_process cannot be found

This reflects differences between the Termux command environment and Android system tools. For that command only, set `PATH=/system/bin:/system/xbin:$PATH` and unset `LD_PRELOAD` and `LD_LIBRARY_PATH`, then call the system tool. This does not grant root. `dumpsys` may still be denied for lack of the DUMP permission. Do not automatically elevate privileges merely because one diagnostic item is unreadable.

## Tool message reference

`tvctl.py` and the SSH script currently print primarily Chinese messages and have no language switch. Common messages are translated below; read the complete actual output for the full failure reason.

| Output fragment | Meaning and next step |
| --- | --- |
| `仅预览，未连接电视` | Preview only; no TV connection or operation. Add `--execute` only within existing authorization. |
| `root 身份和固件范围已确认` | Current root identity and complete build passed checks. This does not establish automatic startup after reboot. |
| `操作未全部完成` / `命令超时或输出过多` | Incomplete operation / timeout or excessive output. Changes may be partial; preserve logs and inspect current state instead of blindly repeating. |
| `超出本指南实测固件范围` | Firmware does not match the verified build. Stop changes; do not remove the check. |
| `未确认 SSH 已启动` | SSH startup was not confirmed. Check this script's log and port 8022 usage; do not terminate an unidentified SSH service. |
| `主机公钥指纹` | Host public-key fingerprint. Compare it with the computer's prompt before first connection; do not disable host verification. |
