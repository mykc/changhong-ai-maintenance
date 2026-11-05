# Case study: Yecao Helper 2.0.16

[中文](../yecao.md) · [Installation policies](app-install-policy.md) · [Home](../../README.en.md)

On 2026-11-05, the user authorized installation of a supplied APK, changes to three policy lists, a computer backup before writing, file and permission checks afterward, and removal of unneeded installation packages after success. The device was the [60Q5T / V1.50571](device.md).

## Result and evidence limits

The original package name and signature were retained. Installation succeeded, and the app opened to its app list. Tools verified that the three policy files, their permissions and the framework's rules in memory matched the intended changes. The existing Aerial accessibility entry, its background permission and the Changhong default launcher were preserved.

The user subsequently reported “测试成功” (“test successful”), confirming that the later installation test succeeded. The target app's name, version and full execution log were not provided. This does not establish that all apps can be installed. Reboot persistence and long-term policy refresh behavior were not tested.

## APK details

| Item | Value |
| --- | --- |
| Package | fun.yecao.helper |
| versionName / versionCode | 2.0.16 / 23 |
| minSdk / targetSdk | 17 / 22 |
| ABI | arm64-v8a, armeabi-v7a |
| Size | 16,287,650 bytes |
| APK SHA-256 | b0531b022e454fb7c1c7e2fa2c4dece2558ed2077d4541d4643c3a95234155d6 |
| Signing certificate SHA-256 | 22aa481788a5591cf874b115c286fc4ae5170bf755b8e8f062e4c86396dc4661 |

The v1/v2 signatures passed verification, and the installed `base.apk` had the same checksum. Signature integrity does not independently establish the publisher's identity or software safety. This repository does not distribute the APK.

## Changes to the three lists

The original files all had ownership/mode `system:system / 0664`, no BOM, LF line endings and a final LF, with no blank lines, comments or extra spaces. The only changes were removing `fun.yecao.helper` from each blacklist and appending it to the installation-source whitelist.

| File | Before | After |
| --- | --- | --- |
| installblacklist | 171 bytes, 8 lines | 154 bytes, 7 lines |
| apprunblacklist | 171 bytes, 8 lines | 154 bytes, 7 lines |
| installdowwhitelist | 161 bytes, 8 lines, 7 distinct packages | 178 bytes, 9 lines, 8 distinct packages |

The following lists are historical policy samples, not recovery templates for other devices.

The two blacklists initially contained the same entries:

```text
com.shafa.market
fun.yecao.helper
com.changhong.dangbeimarket
com.coocaa.dangbeimarket
com.dangbei1.tvlauncher
com.ant.store.appstore
com.shafa.launcher
com.dangbeimarket
```

The original order of the updateable installation-source whitelist was:

```text
com.egame.tv
tv.huan.tvhelper
com.fengmizhibo.live
com.jiajia.v6.changhong2
com.tencent.gamestick
com.zte9.funny
com.changhong.mmp.fileexplorer
tv.huan.tvhelper
```

The duplicate HuanTV Helper entry was preserved. The preset source list contained only `com.egame.tv` and `tv.huan.tvhelper` and was not changed.

## Verification process

1. Backed up the three original files to the computer through SSH, recorded metadata and SHA-256, and checked the raw bytes.
2. SSH was available but ADB was not running. Started the factory adbd service, ran `adb root`, and verified identity and firmware.
3. Generated the exact diff, applied the original permissions, replaced files individually on the same filesystem, and sent the factory reload broadcast.
4. Read the files again both after writing and after installation, compared bytes, and verified `1000:1000 / 0664`.
5. A temporary read-only Java probe called inspected, named interfaces through `AppGlobals.getPackageManager()`. The prompt argument to `isAppInBlackList` was false. Results were:

```text
fun.yecao.helper installBlocked=false runBlocked=false installSourceAllowed=true
com.shafa.market installBlocked=true runBlocked=true installSourceAllowed=false
com.changhong.mmp.fileexplorer installBlocked=false runBlocked=false installSourceAllowed=true
```

6. Installation returned `Success`, launch returned `Status: ok`, and the app list was visible. The user later confirmed that testing succeeded.
7. Rechecked the original launcher and Aerial state. Removed the original downloaded APK, temporary computer copies, and temporary APK/probe files on the TV, while retaining the computer backups and installed app.

The public repository contains sanitized facts and procedures only, without personal paths, raw logs, actual screenshots or binary backups. Recovery requires reading the current lists again; see [recovery rules](recovery.md).

## Lessons

Success in this case required three independent policy allowances. ADB installation can still be subject to framework blacklists; the ability to install Aerial does not prove that every store can be installed. Renaming a package introduces signing, update and component compatibility issues, so this case did not use that approach. Vendor policy may reinstate restrictions; that does not authorize disabling system services.
