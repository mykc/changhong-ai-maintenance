# Maintenance connection: Termux, SSH and factory ADB

[中文](../connection.md) · [Home](../../README.en.md)

See the [device profile](device.md) for scope. The service control and runtime root procedure below has only been verified on this TV and firmware. Run computer commands from the repository root.

## 1. Establish the Termux channel

Install a Termux version compatible with Android 8 on the TV; see the [official installation instructions](https://github.com/termux/termux-app#installation). Termux is an ordinary app. Installing it does not grant root.

If you only need to start ADB, enter this in Termux on the TV:

```sh
/system/bin/setprop ctl.start adbd
```

**The service name is `adbd`, not `adbb`.** This command worked under the ordinary Termux app identity on this TV; other firmware may not allow it.

If entering commands on the TV is inconvenient, establish SSH first:

1. Generate a key pair on the computer for this work: `ssh-keygen -t ed25519 -f ./tv_ed25519`. Keep the private key on the computer.
2. Copy the public key `tv_ed25519.pub` and `scripts/termux-ssh.sh` to the TV's Download directory.
3. In Termux on the TV, run `termux-setup-storage`, allow shared-storage access, then run:

```sh
bash /sdcard/Download/termux-ssh.sh /sdcard/Download/tv_ed25519.pub
```

The script installs OpenSSH (the first run needs network access), preserves existing authorized public keys, starts SSH on port 8022 with public-key authentication only, and displays the username and host fingerprint. Compare the fingerprint on the first connection; do not disable host verification. Use the username actually printed by the script.

```text
ssh -i ./tv_ed25519 -p 8022 USER@TV_IP
```

Then run the `setprop` command above through SSH. This guide does not configure SSH or ADB to start at boot. Changhong may also terminate Termux, so SSH is not a guaranteed permanent connection.

## 2. Connect ADB: root before shell

The following example uses **PowerShell**. Replace the variables with real values; `TV_IP` is a placeholder, not a usable address.

```powershell
$TvIp = 'TV_IP'
$TvSerial = "${TvIp}:5555"
$Adb = 'adb'  # Or the full path to the downloaded adb.exe
$AdbPort = 5038
```

5038 is the **ADB server port on the computer**; 5555 is the **ADB port on the TV**. Another available computer port is acceptable if used consistently.

**Use the tool with time and output limits as the main path.** On this TV, an ordinary `adb shell` repeatedly printed `Password:`. The tool enters shell only after root succeeds and checks the complete firmware build. Let the connection command finish successfully before running inspection separately:

```powershell
python -B scripts/tvctl.py connect-root --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

Continue only after it prints “root 身份和固件范围已确认” (root identity and firmware confirmed) and exits with code 0:

```powershell
python -B scripts/tvctl.py inspect --ip $TvIp --adb $Adb --server-port $AdbPort
```

Except for `inspect`, subcommands without `--execute` only display a plan and do not connect to the TV. `inspect` requires an established root session; it does not start ADB or elevate privileges automatically.

If the device is `unauthorized`, authentication fails, root is denied, or password prompts repeat, stop and read [troubleshooting](troubleshooting.md). Do not brute-force passwords or copy exploits for other models.

### Success gates for manual connection diagnosis

The following is for understanding or stepwise diagnosis; **do not combine it into an automatically executed block**. These commands lack the tool's output protection. Stop on any error, timeout or unexpected state rather than continuing into shell.

1. Run `& $Adb -P $AdbPort connect $TvSerial`, then `& $Adb -P $AdbPort -s $TvSerial get-state`. Require `device`.
2. Run `& $Adb -P $AdbPort -s $TvSerial root`. Require `restarting adbd as root` or `adbd is already running as root`. If root is refused, do not continue. This restarts only adbd, not the TV.
3. Run the connection and `get-state` commands again and require `device` again.
4. Only then run `& $Adb -P $AdbPort -s $TvSerial shell id` and require `uid=0(root)`. If `Password:` appears or the command does not return within 5 seconds, stop it with Ctrl+C. After confirming identity, still use `inspect` above to check the firmware before considering other operations.

## Channel status and shutdown

Aerial appearing at boot does not mean ADB or SSH has started. At the start of maintenance on 2026-11-05, SSH worked but the ADB port refused connections. Maintenance succeeded after manually starting the factory adbd service and running `adb root` again. No boot startup was configured for either channel.

If an earlier session deployed a different SSH startup script, check its actual path and configuration first. Do not overwrite its private keys, authorized public keys or port with this repository's generic script. Calling Android tools through SSH may require setting `PATH=/system/bin:/system/xbin:$PATH` and unsetting `LD_PRELOAD` and `LD_LIBRARY_PATH` for that command only. This does not require changing the permanent Termux configuration.

At the end of maintenance, record whether ADB is still running and whether it is root. If the user asks to close it, run `/system/bin/setprop ctl.stop adbd` through a still-working Termux or SSH session. This disconnects ADB. Do not close the only recovery channel merely to test shutdown.
