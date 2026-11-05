# Evidence and limits

[中文](../evidence.md) · [Home](../../README.en.md)

Verification dates: 2026-11-04 through 2026-11-05, covering one 60Q5T / V1.50571 only.

## How each result was established

| Conclusion | Evidence |
| --- | --- |
| Ordinary Termux can start the factory adbd service | Network ADB became reachable after executing `/system/bin/setprop ctl.start adbd` |
| The current session can obtain root | `adb root` succeeded and `shell id` returned `uid=0(root)` |
| Aerial installed, launched and compiled successfully | Installation `Success`, launch `Status: ok`, and dexopt mode `speed` |
| The guard bound and existing accessibility entries were preserved | Targeted before/after readings and `Home Guard bound=true` |
| Aerial was terminated after entering the background | Its PID disappeared 1–2 seconds after a controlled launch of Termux, before HOME was pressed |
| The background cleanup mechanism matched the symptom | The local list contained Aerial, and the firmware implementation can terminate listed processes after app switching/stopping |
| Aerial was allowed to run in the background | The user first changed the setting manually; tools later confirmed on 2026-11-05 that Aerial was absent from the background cleanup list |
| Normal operation, physical HOME and boot into Aerial worked | Final user report; not an automated cold-boot acceptance test |
| ADB/root/SSH automatically return at boot | Neither configured nor verified; on 2026-11-05 SSH was available, then ADB was manually restarted and root confirmed |

Early failed experiments and the later success report after the user changed background permission belong to different stages. An old list snapshot is not tool verification of the final setting.

## APK

```text
Package: app.orchard.tv
Version: 1.84-guard / 114
minSdk: 21
ABI: includes arm64-v8a
APK SHA-256:
189026ef636f39b716fc7778669bb590607fcf5f19d79da6800d70db043dd71d
Signing certificate SHA-256:
e08962dceaab534210f4725ecb71e3d0906d60dc9da9f2c5fa3b1759874d6685
```

APK v1/v2 signature verification passed, and the certificate fingerprint matched the upstream record at the time. The certificate subject contains Android Debug, which does not by itself mean the APK is a development build with the debuggable flag; the observed package flags did not show debuggable. These hashes apply only to that file. The repository does not distribute the binary.

## ADB findings

Initially, properties indicated port 5555 and enabled ADB, but no adbd process existed and the port refused connections. `/init.usb.rc` defined a service named `adbd` marked disabled; one relevant USB configuration branch had `start adbd` commented out. The hidden AdbEnable handler in the device's factory program also sets `ctl.start=adbd`.

An ordinary shell test repeatedly printed `Password:`. Running the factory `adb root` before opening the shell succeeded. The password was neither cracked nor changed.

The first connection experienced authentication failure and later entered state `device`; the cause was not fully established. `ro.adb.secure=1`, so this observation must not be presented as a general way to bypass authorization.

`ChSystemService` was absent from this device's service list; Binder methods for other models are not part of this procedure. The factory DEBUG item controls logging level. ATCMD services can change network addresses and perform factory operations, so they should not be started to enable ADB.

## Background failure and the key fix

```text
0.0 s  Aerial foreground; process present
10.3 s Requested launch of Termux
11.5 s Termux foreground; Aerial process still present
12.8 s Aerial process disappeared
40.2 s After the user pressed HOME, Changhong launcher was foreground; Aerial still had no process
```

`/data/chuserdata/killbackground` is this vendor's third-party background cleanup list, not a standard Android configuration file. The system implementation includes a cleanup path delayed by about 1000 ms and checks the list in paths such as Activity stopping. The factory Background Startup switch adds or removes the package name, then sets `killapplistchanged` to `true`; the system reads the list again and resets it to `false`.

The factory UI writes a set back to the file and may reorder entries. Acceptance should compare whether other packages remain, rather than require an unchanged file hash.

The firmware handles HOME keycodes 3 and 4124, while the current Aerial version recognizes standard HOME. Physical keycode capture did not yield valid events. Because the user reported success after allowing background activity, modifying keycodes, system keylayout or compiling a custom APK is not recommended.

## System configuration preserved

Original HOME: `com.changhong.system.launcher.v2/.Launcher`. The original file `/chperm/preapp/default_launcher` contained `com.changhong.system.launcher.v2;` and was not changed.

Five accessibility components already existed: iFlytek voice, Changhong AIOS Niubility/SceneId/AI assistance services, and Changhong TaskMonitorService. Each was compared and preserved during guard configuration. The public guide provides no command that hard-overwrites the entire list, because other TVs and later states may differ.

This case did not configure Aerial as the system screensaver or grant notification-listener, overlay, location or usage-access permission. Aerial's own in-app screensaver is separate from system screensaver configuration.

## Later Yecao Helper case

Tools verified on 2026-11-05 that the original lists were backed up to the computer; only `fun.yecao.helper` was changed in the three files; bytes, UID/GID and mode matched after writing and again after installation; the framework rules in memory allowed the package to install, run and initiate installation; and version 2.0.16 installed and launched successfully. The original launcher and Aerial configuration were preserved. See the [Yecao case study](yecao.md).

The user then reported “测试成功” (“test successful”), recorded as user evidence of a subsequent successful installation test. The target app's name and version were not supplied. Reboot persistence and long-term policy refresh were not tested. These list samples must not be described as fixed rules for every model from the manufacturer.

## Read-only NewtvHQ analysis

APK interfaces showed account synchronization, entitlement synchronization, playback authorization and event reporting capabilities. No disabling or background-restriction test was performed. The impact assessment is based on code inspection, not a reproduced failure. See [app-purpose investigation](app-inventory.md).
