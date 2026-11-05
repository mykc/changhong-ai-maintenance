# Maintaining the Aerial launcher

[中文](../aerial.md) · [Home](../../README.en.md) · [Recovery rules](recovery.md)

This task applies to the [verified device](device.md), uses Aerial 1.84-guard and preserves the original Changhong launcher. After allowing Aerial to run in the background through the factory UI, the user confirmed that physical HOME and reboot both opened Aerial. Follow-up maintenance on 2026-11-05 again verified background permission and the original accessibility entries. It did not establish automatic startup of the debugging channels.

## Prerequisites

Establish factory root ADB using the [connection guide](connection.md), then save the relevant baseline. Replace these PowerShell variables with your own values; do not use `TV_IP` literally. Run all commands from the repository root.

```powershell
$TvIp = 'TV_IP'
$TvSerial = "${TvIp}:5555"
$Adb = 'adb'
$AdbPort = 5038
```

Before installation, check the source, package name, version and signature of the user-selected APK. The [recorded fingerprints](evidence.md#apk) apply only to the version used in this case. Understand the effects of guard permissions and the recovery method, then operate within the authorized scope.

## 1. Record the baseline and try the guard build

Run `inspect` and keep its output locally under `.local/`. It captures selected information about the current default launcher, Aerial permissions, accessibility services, screensaver, background list and guard diagnostics. These files should not be published.

Download `aerial-guard.apk` from the [official Aerial Releases](https://github.com/pengchujin/aerial-tv/releases). This case used 1.84-guard; future releases may behave differently. Use the full build for Android 8, rather than the Lite build for Android 4.x.

The guard build does not declare itself as a standard HOME candidate. It uses an accessibility guard to handle HOME while retaining the original Changhong launcher. The [APK hash and signature](evidence.md#apk) recorded for this case must not be applied to other versions.

First check for an existing installation with the same package name:

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm path app.orchard.tv
```

No output indicates a first installation. If the app is already installed, back it up and check its version, signature and permissions first. **Do not automatically uninstall it or assume that installing over it clears old permissions.**

For a first installation and trial:

```powershell
& $Adb -P $AdbPort -s $TvSerial install ./aerial-guard.apk
# Require Success in the output.
& $Adb -P $AdbPort -s $TvSerial shell pm disable --user 0 app.orchard.tv/.guard.BootReceiver
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n app.orchard.tv/.MainActivity
# Wait for the app UI, then generate the app compilation cache for Android 8.
& $Adb -P $AdbPort -s $TvSerial shell cmd package compile -m speed -f app.orchard.tv
```

Install the APK directly on Android 8. Aerial's `.dm` installation optimization is for Android 9+. This procedure does not use `install -g` to grant permissions automatically.

First test the display, directional keys, OK, Back and opening apps. The guard is not enabled at this stage, so HOME returning to Changhong is expected. Temporarily disabling Aerial's BootReceiver limits boot behavior during the trial; Aerial automatically restores it when guard permissions are granted later.

## 2. Allow Aerial to run in the background: the key step on this TV

In the factory UI, open **电视管家 → 应用管理 → 权限管理 → 后台启动** (TV Manager → App Management → Permission Management → Background Startup). Find **Aerial** and set it to **开启** (On). Change only Aerial; other apps do not need to be allowed.

After confirming the operation's scope, you can open the page from the computer:

```powershell
python -B scripts/tvctl.py open-background --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

The tool opens the page but does not toggle the setting. Inspect the page and confirm focus with the physical remote before acting. The correct action is `com.changhong.tvmanager.authManager`. **Do not use the `background_run` action**: this version of TV Manager may route it to the uninstall page.

During the original test, the guard was enabled first, but Aerial disappeared about 1–2 seconds after entering the background, so HOME returned to Changhong. Diagnostics found it in the vendor's background cleanup list, `/data/chuserdata/killbackground`. The user reported that allowing background activity on the factory page resolved the problem. The repeatable procedure therefore allows background activity before enabling the guard.

Allowing background startup increases Aerial's background memory use. It does not turn Aerial into a system app or guarantee survival under extreme memory pressure. Change this permission through the factory UI; this procedure does not edit the background cleanup file directly. The three installation-policy lists belong to a separate maintenance task.

## 3. Enable the launcher guard

Understand and accept the effects first: after receiving `WRITE_SECURE_SETTINGS`, Aerial automatically adds HomeGuard, restores its own BootReceiver and configures its own synchronization-based recovery mechanism. It may open Aerial at later boots. This permission affects more than the display.

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm grant app.orchard.tv android.permission.WRITE_SECURE_SETTINGS
& $Adb -P $AdbPort -s $TvSerial shell am force-stop app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n app.orchard.tv/.MainActivity
python -B scripts/tvctl.py inspect --ip $TvIp --adb $Adb --server-port $AdbPort
```

In this case the guard bound only after Aerial was restarted. Preserve every original accessibility service and add only:

```text
app.orchard.tv/app.orchard.tv.guard.HomeGuardService
```

This TV did not receive additional overlay, usage-access or notification-listener permissions. Do not indiscriminately run every brand-specific permission script. Investigate and explain any additional permission before granting it.

## 4. Acceptance checks and everyday use

1. Confirm that `dumpsys accessibility` shows Aerial's launcher guard as bound, and that Aerial's diagnostics contain `Home Guard bound=true`.
2. **Open another ordinary app from Aerial**, remain there for at least 15 seconds, and confirm that the Aerial PID and guard still exist.
3. Press HOME on the physical remote and confirm that Aerial opens. Pressing HOME while already inside Aerial is not a cross-app test, and an ADB-generated key event does not replace the physical test.
4. Test directional keys, OK/Back, volume and frequently used apps. The system still resolving HOME to Changhong is expected with the guard approach.
5. Before testing a reboot, confirm that it is authorized, that a recovery route is available and that the risks are understood. **In this case, the user independently rebooted and confirmed that Aerial opened.** Whether ADB, SSH and root remain available after reboot was not verified.

To inspect status:

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pidof app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell dumpsys accessibility
& $Adb -P $AdbPort -s $TvSerial shell dumpsys activity app.orchard.tv/.MainActivity
```

HDMI, voice, long standby and every input device were not separately tested. Full compatibility is not guaranteed. After success, further keycode changes, firmware flashing or replacement of the factory default-launcher file are unnecessary.

## Recovery after a problem

If the TV is still running and ADB is available, preview the emergency action first:

```powershell
python -B scripts/tvctl.py emergency-stop --ip $TvIp --adb $Adb --server-port $AdbPort
# Once authorized: disable only Aerial, retain its data and open the original Changhong launcher.
python -B scripts/tvctl.py emergency-stop --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

To remove guard permissions and disable its own services further, use `detach-guard` as described in the [full recovery rules](recovery.md). Do not clear the whole accessibility list or blindly re-enable a malfunctioning Aerial installation.

## Checks after upgrading

On this firmware, a successful installation or installation over an existing app may add third-party apps back to the background cleanup list. **After every Aerial upgrade, recheck Background Startup, BootReceiver, guard binding and physical HOME from another app.** Inspect before changing anything and preserve user data. Do not uninstall simply to resolve a signature conflict.

See [validation](validation.md) for the tool's verification limits and [references](references.md) for download sources.
