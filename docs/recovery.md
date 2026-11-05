# 恢复规则

[English](en/recovery.md) · [首页](../README.md)

本指南分别说明 Aerial、维护连接和安装策略的恢复。Aerial 恢复的前提是：原长虹桌面仍安装且启用，系统默认 HOME 未修改，只用 Aerial guard 接管。远程恢复需要至少一个可用的维护通道；电视手动卸载则需要系统界面仍能操作。脚本不是刷机救砖工具。电脑命令从仓库根目录执行。

## 一、先区分症状，不要先重启或清数据

| 现象 | 首选处理 |
|---|---|
| Aerial 黑屏、卡顿、反复拉回桌面，ADB 可用 | 应急停用 Aerial，显式打开长虹桌面 |
| ADB 不通但 SSH 可用 | 在 SSH 中启动原厂 adbd，然后先 `adb root` 再 shell |
| 重启后两种连接都没了，但可以操作原桌面 | 打开 Termux，重新运行 SSH 脚本或 `setprop ctl.start adbd` |
| 系统界面不可用且 ADB/SSH 都断了 | 停止命令尝试，按具体症状排查设备/原厂恢复途径；本文无法保证远程恢复 |
| HOME 回长虹，但 Aerial 可手动打开 | 先查后台启动开关与守护绑定；不要禁用原桌面 |

出现异常时先保持网络和当前可用的连接。重启可能同时丢失 root ADB 与 Termux SSH；Aerial 重启后能启动不代表这两个通道也会自启。

## 二、应急恢复：先回到可用桌面

电脑需已有 root ADB；使用实际电视 IPv4 地址：

```text
python -B scripts/tvctl.py emergency-stop --ip TV_IP
python -B scripts/tvctl.py emergency-stop --ip TV_IP --execute
```

第一条只预览，第二条实际执行：

1. 校验当前 root、机型、固件、原 HOME 与 Aerial 安装状态。
2. 把定向快照保存在 `.local/`，不上传。
3. `pm disable-user --user 0 app.orchard.tv`，停用整个 Aerial。
4. 停止其进程，核对包仍安装且处于 disabled-user。
5. 显式启动 `com.changhong.system.launcher.v2/.Launcher`。

这会停止其守护、自启和复活组件，**保留 APK 和应用数据，但 Aerial 暂时打不开**。Android 可能自动移除被停用应用的无障碍服务条目；工具不清空全表，也不手动关闭全局无障碍总开关。

如果工具报告原 HOME 已改变，会停止。不要删除这个检查去强行执行，应重新确认可用的恢复桌面。若操作执行到一半失败，Aerial 可能已经停用；查看日志和当前状态，不要假设事务自动回滚。

原始应急命令如下，仅在已确认当前 root、机型和原桌面存在后使用；沿用 [连接方法](connection.md) 中的 PowerShell 变量：

```powershell
& $Adb -P $AdbPort -s $TvSerial shell pm disable-user --user 0 app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am force-stop --user 0 app.orchard.tv
& $Adb -P $AdbPort -s $TvSerial shell am start -W -n com.changhong.system.launcher.v2/.Launcher
```

## 三、进一步撤销桌面守护

```text
python -B scripts/tvctl.py detach-guard --ip TV_IP
python -B scripts/tvctl.py detach-guard --ip TV_IP --execute
```

工具先停用整包，阻止服务自动复活，再执行以下规则：

- 撤销 Aerial 的 `WRITE_SECURE_SETTINGS` 并复核。只删除守护条目而保留这项权限，应用可能自动加回。
- **读取当前** `enabled_accessibility_services`，只移除 Aerial HomeGuard 的全名或简写形式。其他条目、顺序和重复项保留；不将历史快照的整张表写回。
- 同样只移除 Aerial 的 `RevivalListener` 通知监听条目（如果后来曾启用）。
- 禁用 Aerial 自己的 BootReceiver、RevivalSyncService 和 RevivalListener。
- 打开长虹原桌面，Aerial 整包继续保持停用。

工具不删除同步账号，不改系统同步总开关。Aerial 停用后自身同步组件不可用；保留账号数据不等于守护仍有权限运行。

**该动作不是“还原整台电视到出厂”。** 它不改厂商后台运行开关、系统屏保、其他后来授予的 appops 或其他应用。若用户另行做过这些修改，需要对照自己的基线逐项处理。

## 四、恢复“后台启动”的原限制

在长虹原厂 **电视管家 → 应用管理 → 权限管理 → 后台启动**，把 **Aerial** 设回“关闭”，就是撤销本次允许后台的设置。

只更改 Aerial。不要用旧的 `/data/chuserdata/killbackground` 整份快照覆盖当前文件，否则会覆盖用户后来对其他应用的选择。原厂 UI 可能重排列表顺序，验收比较其他应用的权限是否相同。

本文的脚本不直接写这个名单。ADB 可打开权限管理页：

```text
python -B scripts/tvctl.py open-background --ip TV_IP --execute
```

先看清页面与选中的应用，不能盲点卸载、数据清理或“开机直达”。

## 五、再次试用 Aerial

先解决导致异常的问题。撤销守护后的安全试用顺序是：

1. 确认 `WRITE_SECURE_SETTINGS` 未授予，HomeGuard 已移除，自身 BootReceiver 保持禁用。
2. `pm enable --user 0 app.orchard.tv` 恢复整包。
3. 显式打开 Aerial，仅测试界面。不要直接照抄一键全授权脚本。
4. 需要重新接管时，重新说明并确认后台权限和守护影响，再按照 [Aerial 专项文档](aerial.md) 配置与验收。

若之前运行了 `detach-guard`，它还禁用了 Aerial 自身的 RevivalSyncService 和 RevivalListener。后续真正恢复守护时可按需要恢复这两个组件的默认状态；Aerial 本身只自动恢复 BootReceiver 和 ConfigReceiver。不要把“整包 enable”误认为所有组件都会自动恢复。

卸载 Aerial 会删除它自己的设置、照片等数据，必须另行确认；不是第一恢复步骤。任何系统应用卸载、默认桌面文件修改、keylayout 修改、刷分区、清空用户数据，均不在本方案授权范围内。

## 六、连接恢复与收尾

普通 Termux 或已有 SSH 会话中：

```sh
/system/bin/setprop ctl.start adbd
```

然后电脑 `connect-root --execute`。切换 adbd 为 root 会短暂断连，不重启电视。若 `unauthorized` 或 root 不支持，停止；不要在普通 shell 的密码提示中重试。

结束调试前，确认不再依赖该连接恢复，再在 Termux/SSH 执行：

```sh
/system/bin/setprop ctl.stop adbd
bash /sdcard/Download/termux-ssh.sh stop
```

`adb disconnect` 只断开本电脑客户端，不等于关闭电视端监听。停止 SSH 监听也不等于删除公钥授权或结束所有已建立会话；需要撤销访问时，核对指纹后只移除自己添加的那一条公钥，保留别人的授权。

通用恢复脚本仅做了离线测试，未在最终正常状态的电视上执行破坏性恢复演练。每次真实恢复都必须观察输出和电视画面。

## 七、从电视界面卸载 Aerial

原长虹桌面保留且默认 HOME 未修改时，用户从电视应用管理卸载 Aerial，通常会移除其守护和开机组件，恢复原桌面行为。它也会删除 Aerial 自身数据；电视上的卸载恢复没有实际演练，不能承诺所有异常状态都能这样恢复。优先在仍可操作时关闭守护并确认原桌面可用。卸载 Aerial 不会卸载 Termux 或关闭 ADB/SSH。

## 八、撤销应用安装策略变更

本项对应 [野草助手案例](yecao.md)，不使用 Aerial 的 `emergency-stop` 或 `detach-guard`。

1. 先保持网络和当前维护通道，重新备份当前三份名单。普通 SSH 可读取不代表能写回，需要已确认的维护权限。
2. 当前哈希仍等于本次写后快照时，可恢复修改前文件。若官方或用户已改变名单，必须合并撤销本次包名，保留其他变化。
3. 撤销野草助手放行意味着恢复它在安装、运行黑名单中的条目，并删除本次追加的来源白名单条目。恢复运行限制会使仍安装的野草助手无法正常启动。
4. 写回后核验原始字节、所有者和权限，再通过 `com.changhong.listchanged` 通知重载，验证实际规则。不要仅靠广播返回码判断完成。
5. 卸载野草助手不会自动恢复名单，也不会卸载它安装的其他应用。恢复策略不涉及 Aerial 的桌面守护。

本机三份名单初始权限为 `system:system / 0664`；其他维护记录以其实际备份为准。不要以全局关黑名单、锁文件或停用厂商管理服务作为恢复动作。
