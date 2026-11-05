# 维护连接：Termux、SSH 与原厂 ADB

[English](en/connection.md) · [首页](../README.md)

适用范围见 [设备档案](device.md)。只有本机固件验证过下列服务控制与运行时 root 路径。

## 1. 建立 Termux 通道

电视安装与 Android 8 兼容的 Termux，来源见 [官方安装说明](https://github.com/termux/termux-app#installation)。Termux 只是普通应用；安装它不会自动取得 root。

若只需启动 ADB，在电视 Termux 输入：

```sh
/system/bin/setprop ctl.start adbd
```

**拼写是 `adbd`，不是 `adbb`。** 该命令在本机普通 Termux 身份下有效，不保证其他固件也允许。

如果电视输入不便，可先建立 SSH：

1. 在电脑为本次操作生成一对密钥：`ssh-keygen -t ed25519 -f ./tv_ed25519`。私钥只留在电脑。
2. 将公钥文件 `tv_ed25519.pub` 和 `scripts/termux-ssh.sh` 复制到电视 Download 目录。
3. 电视 Termux 执行 `termux-setup-storage`，允许访问共享存储，然后执行：

```sh
bash /sdcard/Download/termux-ssh.sh /sdcard/Download/tv_ed25519.pub
```

脚本会安装 OpenSSH（首次需联网）、保留已有授权公钥、启动仅公钥认证的 8022 端口，并显示用户名和主机指纹。第一次连接时对照指纹确认；不要关闭主机校验。用户名以脚本实际输出为准。

```text
ssh -i ./tv_ed25519 -p 8022 USER@TV_IP
```

通过 SSH 再执行上述 `setprop` 命令即可。本文不设置 SSH/ADB 开机自启；长虹也可能清理 Termux，不能把 SSH 当作永久在线通道。

## 2. 连接 ADB，先 root，再进入 shell

下面以 **PowerShell** 举例；将变量换成实际值。`TV_IP` 不是可直接连接的地址。

```powershell
$TvIp = 'TV_IP'
$TvSerial = "${TvIp}:5555"
$Adb = 'adb'  # 或下载后 adb.exe 的完整路径
$AdbPort = 5038
```

5038 是**电脑 ADB server 端口**，5555 是**电视 ADB 端口**。只要全程一致，电脑端也可选择其他空闲端口。

**推荐使用有超时和输出上限的工具。** 本机普通身份的 `adb shell` 曾持续输出 `Password:`；工具只在 root 成功后进入 shell，并核对完整固件。下面连接命令必须先成功结束，再单独运行检查：

```powershell
python -B scripts/tvctl.py connect-root --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

出现“root 身份和固件范围已确认”，且退出码为 0 后，才执行：

```powershell
python -B scripts/tvctl.py inspect --ip $TvIp --adb $Adb --server-port $AdbPort
```

除 `inspect` 外的子命令，缺少 `--execute` 时仅显示计划，不连接电视。`inspect` 要求已建立 root 会话；不会自动开启 ADB 或提权。

遇到 `unauthorized`、认证失败、root 被拒或连续密码提示，停止并读 [故障排查](troubleshooting.md)。不要尝试口令爆破或照搬其他机型漏洞。

### 手动排查连接时的成功门槛

以下仅用于理解或分步排查，**不要合并成一键执行块**。命令没有工具的输出保护；任一步报错、超时或状态不符就停止，不能继续到 shell。

1. 执行 `& $Adb -P $AdbPort connect $TvSerial`，再执行 `& $Adb -P $AdbPort -s $TvSerial get-state`；必须返回 `device`。
2. 执行 `& $Adb -P $AdbPort -s $TvSerial root`；必须返回 `restarting adbd as root` 或 `adbd is already running as root`。被拒绝时不执行后续命令。这只重启 adbd 服务，不重启电视。
3. 重新执行连接和 `get-state`，确认再次返回 `device`。
4. 此时才执行 `& $Adb -P $AdbPort -s $TvSerial shell id`，要求包含 `uid=0(root)`；若出现 `Password:` 或 5 秒内不返回，按 Ctrl+C 停止。身份成功后仍需用上述 `inspect` 核对固件，再考虑其他操作。


## 通道状态与退出

开机进入 Aerial 不代表 ADB 或 SSH 已经启动。2026-11-05 的维护开始时，SSH 可用、ADB 端口拒绝连接；再次启动原厂 adbd 并执行 adb root 后维护成功。未配置任何通道的开机自启。

在旧会话中部署过其他 SSH 启动脚本时，先检查它的实际路径与配置，不用本仓库的通用脚本覆盖原有私钥、公钥授权或端口。通过 SSH 调用 Android 工具时可能需要给该次命令设置 `PATH=/system/bin:/system/xbin:$PATH` 并取消 `LD_PRELOAD`、`LD_LIBRARY_PATH`；这不等于修改 Termux 永久配置。

维护结束记录 ADB 是否仍在运行及是否为 root。若用户要求关闭，可通过仍可用的 Termux/SSH 执行 `/system/bin/setprop ctl.stop adbd`，此后 ADB 连接会中断；不要为了测试而主动关闭唯一恢复通道。
