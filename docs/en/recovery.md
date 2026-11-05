# Recovery rules

[中文](../recovery.md) · [Home](../../README.en.md)

This guide covers recovery for Aerial, maintenance connections and installation policies separately. Aerial recovery assumes that the original Changhong launcher remains installed and enabled, the system default HOME is unchanged, and only Aerial guard handles HOME. Remote recovery needs at least one working maintenance channel; manual uninstallation on the TV needs a usable system interface. These scripts are not firmware flashing or unbricking tools. Run computer commands from the repository root.

## 1. Identify the symptom before rebooting or clearing data

| Symptom | First response |
| --- | --- |
| Aerial shows a black screen, hangs or repeatedly returns to its launcher; ADB works | Disable Aerial with the emergency action and explicitly open the Changhong launcher |
| ADB is unavailable but SSH works | Start the factory adbd service over SSH, then run `adb root` before opening a shell |
| Both connections disappeared after reboot, but the original launcher works | Open Termux and rerun the SSH script or `setprop ctl.start adbd` |
| System UI is unusable and both ADB and SSH are disconnected | Stop command attempts and investigate device-specific or factory recovery options; this guide cannot guarantee remote recovery |
| HOME returns to Changhong, but Aerial can be opened manually | Check background startup permission and guard binding; do not disable the original launcher |

Preserve the network and any working connection when a problem occurs. A reboot may lose both root ADB and Termux SSH. Aerial starting after reboot does not prove that these channels also start automatically.

## 2. Emergency recovery: return to a working launcher

The computer must already have root ADB. Substitute the TV's actual IPv4 address:

```text
python -B scripts/tvctl.py emergency-stop --ip TV_IP
python -B scripts/tvctl.py emergency-stop --ip TV_IP --execute
```

The first command previews only. The second performs these actions:

1. Verifies current root, model, firmware, original HOME and Aerial installation state.
2. Saves a targeted snapshot under `.local/` without uploading it.
3. Disables the entire Aerial package using `pm disable-user --user 0 app.orchard.tv`.
4. Stops its process and checks that the package remains installed with the disabled-user state.
5. Explicitly starts `com.changhong.system.launcher.v2/.Launcher`.

This stops its guard, boot and revival components. **The APK and app data remain, but Aerial cannot be opened while disabled.** Android may automatically remove accessibility entries for the disabled app. The tool neither clears the whole list nor manually turns off the global accessibility switch.

The tool stops if the original HOME has changed. Do not remove this check to force execution; establish which recovery launcher is actually usable. If an operation fails midway, Aerial may already be disabled. Inspect the logs and current state; do not assume automatic transactional rollback.

The underlying emergency commands are below. Use them only after confirming current root, the model and the presence of the original launcher. Use the PowerShell variables from the [connection guide](connection.md):

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm disable-user --user 0 app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am force-stop --user 0 app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n com.changhong.system.launcher.v2/.Launcher
```

## 3. Remove the launcher guard further

```text
python -B scripts/tvctl.py detach-guard --ip TV_IP
python -B scripts/tvctl.py detach-guard --ip TV_IP --execute
```

The tool first disables the entire package to prevent automatic revival, then:

- Revokes Aerial's `WRITE_SECURE_SETTINGS` and verifies the result. If this permission remains, the app may add guard entries back after they are removed.
- **Reads the current** `enabled_accessibility_services` value and removes only the full or shortened Aerial HomeGuard component name. It preserves other entries, order and duplicates; it does not restore an entire historical list.
- Similarly removes only Aerial's `RevivalListener` notification-listener entry, if it was enabled later.
- Disables Aerial's own BootReceiver, RevivalSyncService and RevivalListener.
- Opens the original Changhong launcher and leaves the entire Aerial package disabled.

The tool does not delete synchronization accounts or change the global synchronization switch. Aerial's own sync components are unavailable while the package is disabled; retained account data does not mean the guard still has permission to run.

**This does not reset the entire TV to factory settings.** It does not change the vendor background permission, system screensaver, other appops granted later or other apps. Address any such separate changes individually against your own baseline.

## 4. Restore the original background restriction

In the factory **电视管家 → 应用管理 → 权限管理 → 后台启动** (TV Manager → App Management → Permission Management → Background Startup), set **Aerial** back to **关闭** (Off) to reverse this case's background allowance.

Change only Aerial. Do not overwrite the current `/data/chuserdata/killbackground` with a complete old snapshot, which would erase the user's later choices for other apps. The factory UI may reorder the list; verify that other apps' permissions are preserved.

The scripts do not write this list directly. ADB can open the permission page:

```text
python -B scripts/tvctl.py open-background --ip TV_IP --execute
```

Inspect the page and selected app before acting. Do not blindly select uninstall, data clearing or “开机直达” (direct launch at boot).

## 5. Try Aerial again

Resolve the cause of the problem first. After detaching the guard, use this trial order:

1. Confirm that `WRITE_SECURE_SETTINGS` is not granted, HomeGuard has been removed and Aerial's BootReceiver remains disabled.
2. Re-enable the entire package with `pm enable --user 0 app.orchard.tv`.
3. Explicitly open Aerial and test only its UI. Do not copy a script that grants every permission at once.
4. Before enabling HOME takeover again, explain and confirm the effects of background permission and the guard, then follow the [Aerial guide](aerial.md) for setup and acceptance checks.

If `detach-guard` was previously run, it also disabled Aerial's RevivalSyncService and RevivalListener. When intentionally restoring the guard later, restore these components to their default state as needed. Aerial itself automatically restores only BootReceiver and ConfigReceiver. Enabling the whole package does not automatically reset every component.

Uninstalling Aerial deletes its own settings, photos and other app data. It needs separate confirmation and is not the first recovery step. Uninstalling system apps, modifying the default-launcher file or keylayout, flashing partitions and clearing user data are outside this procedure's authorization.

## 6. Restore connections and finish

In ordinary Termux or an existing SSH session, run:

```sh
/system/bin/setprop ctl.start adbd
```

Then run `connect-root --execute` on the computer using the [connection guide](connection.md). Switching adbd to root briefly disconnects ADB; it does not reboot the TV. Stop if the device is `unauthorized` or root is unsupported. Do not retry through the ordinary shell's password prompt.

Before ending debugging, confirm that the connection is no longer needed for recovery. Then, in Termux/SSH:

```sh
/system/bin/setprop ctl.stop adbd
bash /sdcard/Download/termux-ssh.sh stop
```

`adb disconnect` disconnects only this computer's client; it does not stop the TV's listener. Stopping the SSH listener neither removes authorized public keys nor necessarily ends existing sessions. To revoke access, verify the fingerprint and remove only the public key you added, preserving other users' authorization.

The generic recovery scripts have only been tested offline. No destructive recovery drill was performed on the final working TV state. Every real recovery requires checking command output and the TV screen.

## 7. Uninstall Aerial from the TV UI

When the original Changhong launcher is retained and default HOME is unchanged, uninstalling Aerial through the TV's app manager would normally remove its guard and boot components and restore the original launcher behavior. It also deletes Aerial's own data. This UI-based uninstall recovery was not rehearsed, so it cannot be promised to work in every failure state. Prefer turning off the guard while the UI is still usable and confirming that the original launcher works. Uninstalling Aerial does not uninstall Termux or close ADB/SSH.

## 8. Reverse installation-policy changes

This section concerns the [Yecao Helper case](yecao.md). It does not use Aerial's `emergency-stop` or `detach-guard` commands.

1. Preserve the network and current maintenance channel, then make a fresh backup of all three current lists. Read access through ordinary SSH does not imply permission to write them; confirmed maintenance privileges are required.
2. If current hashes still match this operation's post-write snapshot, the original files can be restored. If the vendor or user has changed them, merge only the reversal of this package's changes while retaining other changes.
3. Reversing the Yecao allowance restores its entries in the installation and run blacklists and removes the source-whitelist entry added in this operation. Restoring the run restriction prevents the still-installed Yecao app from launching normally.
4. After writing, verify raw bytes, ownership and mode, request reload with `com.changhong.listchanged`, and verify the actual rules. The broadcast return code alone is not completion evidence.
5. Uninstalling Yecao does not automatically restore the lists or uninstall other apps it installed. Restoring these policies does not affect Aerial's launcher guard.

The three files initially had `system:system / 0664` on this device. Other maintenance sessions must use their actual recorded metadata. Do not globally disable blacklists, lock files or disable vendor management services as a recovery action.
