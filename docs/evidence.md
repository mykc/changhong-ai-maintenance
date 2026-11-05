# 证据与适用边界

[English](en/evidence.md) · [首页](../README.md)

验证日期：2026-11-04 至 2026-11-05，仅针对一台 60Q5T / V1.50571。

## 哪些结果如何确认

| 结论 | 证据 |
|---|---|
| 普通 Termux 可启动原厂 adbd | 实际执行 `/system/bin/setprop ctl.start adbd` 后，网络 ADB 可连接 |
| 当前会话可 root | `adb root` 成功，`shell id` 返回 `uid=0(root)` |
| Aerial 安装、启动、编译成功 | 安装 `Success`，启动 `Status: ok`，dexopt 为 `speed` |
| 守护曾绑定，原有无障碍保留 | 前后定向读取及 `Home Guard bound=true` |
| 切后台后被结束 | 受控打开 Termux 后 1–2 秒 Aerial PID 消失，之后才按 HOME |
| 后台清理机制匹配 | 本机名单有 Aerial，固件实现可在应用切换/停止后结束名单内进程 |
| 已允许 Aerial 后台运行 | 用户先手动设置；2026-11-05 后续维护时工具确认 Aerial 不在后台清理名单中 |
| 运行、主页键、重启进 Aerial 正常 | 用户最终反馈；不是脚本自动完成的冷启动验收 |
| ADB/root/SSH 自动随开机恢复 | 未验证且未配置；2026-11-05 是 SSH 可用后手动重新启动 ADB，再确认 root |

早期失败的试验记录与后来用户完成后台设置后的成功反馈属于不同阶段。旧名单快照不能冒充最终设置的工具验证。

## 安装包

```text
包名: app.orchard.tv
版本: 1.84-guard / 114
minSdk: 21
ABI: 包含 arm64-v8a
APK SHA-256:
189026ef636f39b716fc7778669bb590607fcf5f19d79da6800d70db043dd71d
签名证书 SHA-256:
e08962dceaab534210f4725ecb71e3d0906d60dc9da9f2c5fa3b1759874d6685
```

APK v1/v2 签名验证通过，证书指纹与当时上游记录一致。证书主体名包含 Android Debug，不等于此 APK 是带 debuggable 标志的开发构建；实际包标志未显示 debuggable。哈希仅针对本次文件，仓库不分发该二进制。

## ADB 发现

初始有 5555 和 ADB 开启属性，但 adbd 进程不存在，端口连接被拒。`/init.usb.rc` 中存在名为 `adbd` 的服务，标记为 disabled；对应的一条 USB 配置分支注释了 `start adbd`。本机工厂程序中的隐藏 AdbEnable 处理也是设置 `ctl.start=adbd`。

普通 shell 测试曾反复输出 `Password:`；改为先执行原厂 `adb root` 再开 shell 才成功。没有破解或修改该密码。

第一次连接出现过认证失败，后来设备进入 `device`；原因未完全确认。`ro.adb.secure=1`，不能将本次现象写成普遍绕过授权的方法。

`ChSystemService` 不在本机服务列表；其他机型的 Binder 方法不作为本机方案。工厂 DEBUG 项是日志等级；ATCMD 服务会改网络地址并有工厂操作，不应为开启 ADB 而启动它。

## 后台问题与关键修复

```text
0.0 s  Aerial 前台，进程存在
10.3 s 发起打开 Termux
11.5 s Termux 前台，Aerial 进程仍在
12.8 s Aerial 进程消失
40.2 s 用户按 HOME 后长虹桌面在前台，Aerial 仍无进程
```

`/data/chuserdata/killbackground` 是本机厂商第三方后台清理名单，不是 Android 的通用配置文件。系统实现包含延迟约 1000 ms 的清理路径，也会在 Activity 停止等路径检查名单。原厂“后台启动”开关增删对应包名，然后将 `killapplistchanged` 设为 `true`；系统重新读取后写回 `false`。

原厂 UI 使用集合写回，可能重排顺序。验收应比较其他包名是否保持，而非要求文件哈希不变。

固件包含 HOME 键码 3 和 4124 的处理，Aerial 当前识别标准 HOME。但实际实体键码采集未得到有效事件；用户允许后台后报告正常，因此不建议修改键码、系统 keylayout 或编译定制 APK。

## 保留的系统配置

原 HOME：`com.changhong.system.launcher.v2/.Launcher`；原默认文件 `/chperm/preapp/default_launcher` 的内容为 `com.changhong.system.launcher.v2;`，未修改。

当时已有 5 个无障碍组件：讯飞语音、长虹 AIOS 的 Niubility/SceneId/AI 辅助服务、长虹 TaskMonitorService。配置守护时逐项比对保留；公开指南不提供一条硬覆盖全表的命令，因为其他电视和未来状态可能不同。

本次未设置 Aerial 系统屏保、通知监听、悬浮窗、定位或用量统计授权。Aerial 自带应用内屏保与系统屏保配置是两回事。

## 野草助手后续案例

2026-11-05 工具确认：原始名单已在电脑备份；只对 `fun.yecao.helper` 修改三份文件；写后与安装后字节、UID/GID、mode 均一致；系统内存规则允许该包安装、运行和发起安装；2.0.16 安装、启动成功。原桌面与 Aerial 相关配置保持。详情见 [野草助手实测](yecao.md)。

用户随后反馈“测试成功”，作为后续实际安装测试成功的用户证据记录。目标应用名称与版本未提供，没有重启持久性或长期策略刷新测试。不能把此次名单样本写成厂商所有机型的固定规则。

## NewtvHQ 只读分析

APK 接口显示账号同步、权益同步、播放鉴权和事件上报能力；没有执行停用或后台限制测试。影响判断属于基于代码的评估，不能标为实际故障复现。见 [应用用途调查](app-inventory.md)。
