# Aerial 桌面维护

[English](en/aerial.md) · [首页](../README.md) · [恢复规则](recovery.md)

本任务适用于 [实测设备](device.md)，使用 Aerial 1.84-guard，保留原长虹桌面。用户在原厂 UI 允许 Aerial 后台后，确认实体 HOME 和重启均进入 Aerial。2026-11-05 后续维护时再次确认后台允许与原无障碍条目，但没有证明调试通道自动开机。

## 前置条件

先按 [连接方法](connection.md) 建立原厂 root ADB，再保存相关基线。以下 PowerShell 变量需要替换为自己的值；不要把 `TV_IP` 原样执行。所有命令从仓库根目录运行。

```powershell
$TvIp = 'TV_IP'
$TvSerial = "${TvIp}:5555"
$Adb = 'adb'
$AdbPort = 5038
```

安装前核对用户指定 APK 的来源、包名、版本和签名；[本次指纹](evidence.md#安装包) 只对应当时版本。了解守护权限的副作用和恢复方法，再按已授权范围操作。

## 1. 记录基线，安装 guard 版试用

运行 `inspect`，将输出保存在本地 `.local/`。它定向保存当前默认桌面、Aerial 权限、无障碍服务、屏保、后台名单和守护诊断；这些文件不应发布。

从 [Aerial 官方 Releases](https://github.com/pengchujin/aerial-tv/releases) 下载 `aerial-guard.apk`。本次使用 1.84-guard；将来的版本可能改变行为。Android 8 使用完整版，不用 Android 4.x 的 Lite。

guard 不声明标准 HOME 候选，通过无障碍守护接管主页键；原长虹桌面保留。APK 的 [本次哈希与签名](evidence.md#安装包) 仅对应本次版本，不可套用其他版本。

先确认没有同包名旧安装：

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm path app.orchard.tv
```

无输出时按首次安装处理；已有安装则先备份并检查版本/签名/权限，**不要自动卸载，也不要以为覆盖安装会清掉旧权限**。

首次安装及试用：

```powershell
& $Adb -P $AdbPort -s $TvSerial install ./aerial-guard.apk
# 必须看到 Success。
& $Adb -P $AdbPort -s $TvSerial shell pm disable --user 0 app.orchard.tv/.guard.BootReceiver
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n app.orchard.tv/.MainActivity
# 等待应用界面出现，再为 Android 8 生成应用编译缓存。
& $Adb -P $AdbPort -s $TvSerial shell cmd package compile -m speed -f app.orchard.tv
```

Android 8 直接安装 APK；Aerial 的 `.dm` 安装优化是 Android 9+ 路径。这里不使用 `install -g` 自动授权。

先测试画面、方向键、确认、返回和打开应用。此阶段尚未开守护，HOME 回长虹是预期行为。暂时关闭自身 BootReceiver 是为了限制试用阶段的开机行为；之后授予守护权限时，Aerial 会自动恢复它。

## 2. 允许 Aerial 在后台运行：本机的关键步骤

进入长虹原厂 **电视管家 → 应用管理 → 权限管理 → 后台启动**，找到 **Aerial**，将状态设为 **开启**。仅更改 Aerial，不必放开所有应用。

也可在确认操作范围后，通过电脑打开对应页面：

```powershell
python -B scripts/tvctl.py open-background --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

工具只打开页面，不会代点开关。看到页面后用实体遥控器确认焦点再操作。正确 action 是 `com.changhong.tvmanager.authManager`；**不要用 `background_run` action**，它在这版电视管家的实际路由中可能落到卸载页。

本次先开守护再试验时，Aerial 切后台约 1–2 秒就消失，导致 HOME 回长虹。诊断发现它在厂商后台清理名单 `/data/chuserdata/killbackground` 中。用户在上述原厂页面允许后台后，报告问题解决。因此复现流程建议先允许后台，再启用守护。

“允许后台启动”会增加 Aerial 的后台内存占用；不会使它成为系统应用，也不保证在内存极低时永不被回收。Aerial 后台权限通过原厂 UI 调整；这里不直接编辑后台清理名单。安装策略的三份名单属于另一项维护任务。

## 3. 开启桌面守护

先明确接受影响：授予 `WRITE_SECURE_SETTINGS` 后，Aerial 会自动追加 HomeGuard、恢复自身 BootReceiver，并配置自身的同步恢复机制。以后开机可能主动进入 Aerial；这不是单纯的显示权限。

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm grant app.orchard.tv android.permission.WRITE_SECURE_SETTINGS
& $Adb -P $AdbPort -s $TvSerial shell am force-stop app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n app.orchard.tv/.MainActivity
python -B scripts/tvctl.py inspect --ip $TvIp --adb $Adb --server-port $AdbPort
```

本次重新启动 Aerial 后守护才绑定。原无障碍服务应完整保留，只增加：

```text
app.orchard.tv/app.orchard.tv.guard.HomeGuardService
```

本机没有额外授权悬浮窗、用量统计或通知监听。不要无差别执行所有品牌的授权脚本；确需补充权限时先查原因并说明用途。

## 4. 验收与日常使用

1. `dumpsys accessibility` 中出现已绑定的 Aerial 桌面守护；Aerial 诊断应有 `Home Guard bound=true`。
2. **从 Aerial 打开另一个普通应用**，停留至少 15 秒，确认 Aerial PID 和守护仍在。
3. 用实体遥控器按 HOME，确认回 Aerial。只在 Aerial 内按 HOME 留在 Aerial，不算跨应用通过；ADB 模拟键也不能替代实体测试。
4. 测方向键、确认/返回、音量和常用应用。系统 HOME 解析仍是长虹，符合 guard 方案。
5. 重启前确认已有对应授权、恢复通道和风险，再测试开机结果。**本次用户自行重启后确认进入 Aerial**；ADB、SSH 和 root 是否重启后仍可用未知。

若需查看状态：

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pidof app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell dumpsys accessibility
& $Adb -P $AdbPort -s $TvSerial shell dumpsys activity app.orchard.tv/.MainActivity
```

HDMI、语音、长时间待机、所有输入设备没有逐项专项验证，不承诺全部兼容。成功后无需继续改键码、刷系统或替换原厂默认桌面文件。

## 异常时恢复

电视仍开机且 ADB 可用时，先执行预览：

```powershell
python -B scripts/tvctl.py emergency-stop --ip $TvIp --adb $Adb --server-port $AdbPort
# 确认后实际执行：仅停用 Aerial，保留数据，打开原长虹桌面。
python -B scripts/tvctl.py emergency-stop --ip $TvIp --adb $Adb --server-port $AdbPort --execute
```

如果要进一步撤销守护权限和自身服务，使用 `detach-guard`，详见 [完整恢复规则](recovery.md)。不要直接清空无障碍总表，也不要盲目重新启用有问题的 Aerial。

## 升级后的必查项

本固件的成功安装/覆盖安装路径可能将第三方应用重新加入后台清理名单。**每次升级 Aerial 后，重新检查“后台启动”、BootReceiver、守护绑定与跨应用 HOME**。先检查再修改，保留用户数据；不要为解决签名冲突直接卸载。

工具验证边界见 [验证记录](validation.md)，下载来源见 [参考资料](references.md)。
