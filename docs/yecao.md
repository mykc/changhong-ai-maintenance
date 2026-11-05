# 实测：野草助手 2.0.16

[English](en/yecao.md) · [安装策略](app-install-policy.md) · [首页](../README.md)

2026-11-05，用户授权安装提供的 APK、修改三份名单、先备份到电脑、写后复查文件和权限，并在成功后清理无用安装包。设备为 [60Q5T / V1.50571](device.md)。

## 结果与证据边界

保留原包名和原签名，安装成功并打开到应用列表。工具确认三份名单内容、权限、系统内存规则符合预期；Aerial 原有无障碍条目与后台许可、长虹默认桌面保持。

用户随后反馈“测试成功”，确认后续安装测试成功。目标应用名称、版本和全过程日志未提供，不能扩大为所有应用都可安装。没有重启或长期策略刷新测试。

## APK 信息

| 项目 | 值 |
| --- | --- |
| 包名 | fun.yecao.helper |
| versionName / versionCode | 2.0.16 / 23 |
| minSdk / targetSdk | 17 / 22 |
| ABI | arm64-v8a、armeabi-v7a |
| 大小 | 16,287,650 字节 |
| APK SHA-256 | b0531b022e454fb7c1c7e2fa2c4dece2558ed2077d4541d4643c3a95234155d6 |
| 签名证书 SHA-256 | 22aa481788a5591cf874b115c286fc4ae5170bf755b8e8f062e4c86396dc4661 |

v1/v2 签名校验通过，已安装 `base.apk` 的校验值一致。签名完整性不等于独立核实发行方或软件安全。本仓库不分发 APK。

## 三份名单的变化

原文件均为 `system:system / 0664`、无 BOM、LF 换行且末行有 LF；无空行、注释和多余空格。唯一修改是两份黑名单各删除 `fun.yecao.helper`，来源白名单末尾追加它。

| 文件 | 修改前 | 修改后 |
| --- | --- | --- |
| installblacklist | 171 字节、8 行 | 154 字节、7 行 |
| apprunblacklist | 171 字节、8 行 | 154 字节、7 行 |
| installdowwhitelist | 161 字节、8 行、7 个不同包名 | 178 字节、9 行、8 个不同包名 |

以下是当时策略样本，不能当作其他设备的恢复模板。

两份黑名单原本相同：

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

可更新安装来源白名单原始顺序：

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

欢视助手重复项保留。预置来源名单只有 `com.egame.tv`、`tv.huan.tvhelper`，未修改。

## 验证过程

1. 用 SSH 将三份原文件备份到电脑，记录元数据和 SHA-256，核对原始字节。
2. 当时 SSH 可用但 ADB 未运行；启动原厂 adbd，执行 `adb root`，确认身份和固件。
3. 生成精确差异，设置原权限，在同一文件系统内逐个替换，使用原厂广播重载。
4. 写后与安装后各重新读取文件，比较字节并复核 `1000:1000 / 0664`。
5. 临时只读 Java 探针通过 `AppGlobals.getPackageManager()` 调用已核查的命名接口。`isAppInBlackList` 的提示参数为 false，结果为：

```text
fun.yecao.helper installBlocked=false runBlocked=false installSourceAllowed=true
com.shafa.market installBlocked=true runBlocked=true installSourceAllowed=false
com.changhong.mmp.fileexplorer installBlocked=false runBlocked=false installSourceAllowed=true
```

6. 安装返回 `Success`，启动返回 `Status: ok`，观察到应用列表。用户随后确认测试成功。
7. 复核原桌面和 Aerial 状态；删除原下载 APK、电脑临时副本及电视 APK/探针暂存文件，保留电脑备份和已安装应用。

公开仓库只包含脱敏事实与流程，不含个人路径、原始日志、真实截图和二进制备份。恢复时需重新读取当前名单，详见 [恢复规则](recovery.md)。

## 经验

这次成功依赖三项独立放行。ADB 安装仍可能受框架黑名单限制；Aerial 可安装不证明所有商店都可安装。改包名会引入重签名、升级与组件兼容问题，本次没有采用。官方策略可能恢复限制，不能为此擅自禁用系统服务。
