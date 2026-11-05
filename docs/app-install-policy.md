# 应用安装策略维护

[English](en/app-install-policy.md) · [首页](../README.md) · [恢复规则](recovery.md)

本流程只验证于 [60Q5T / V1.50571](device.md)。目标是允许一个应用安装、运行并发起 APK 安装。它不会把商店变成系统应用，也不授予 root 或静默安装特权。

## 三份名单的区别

| 文件 | 控制内容 | 野草助手案例 |
| --- | --- | --- |
| `/data/chuserdata/installblacklist` | 哪些目标包禁止安装 | 删除 `fun.yecao.helper` |
| `/data/chuserdata/apprunblacklist` | 哪些包禁止运行 | 删除同一包名 |
| `/data/chuserdata/installdowwhitelist` | 哪些来源应用可以发起安装 | 追加同一包名 |

另有 `/chperm/preapp/preinstallpermlist` 预置来源名单，本案例没有修改。`killbackground` 是独立的后台清理名单；Aerial 后台许可通过原厂 UI 修改，不与这里混用。

固件安装器及框架按包名检查这些名单。来源获准不代表其下载的所有目标 APK 都被允许；目标若在黑名单中仍可能失败。单开 Android“未知来源”或对普通应用运行 `pm grant INSTALL_PACKAGES`，不是本机完整解决方案。

## 原始格式

本次三份文件都是一行一个包名；ASCII 字节，可按 UTF-8 无 BOM 处理；LF 换行，末行也有 LF；无空行、注释和首尾空格。所有者为 `system:system`（1000:1000），权限 `0664`。白名单原有欢视助手重复项被保留。

必须读取当前文件后再制定改动，不能把示例名单直接覆盖到电视。白名单解析遇到 `#` 行可能提前结束；不要通过加注释隐藏条目。避免 BOM、编码转换、错误路径和写到一半的文件。

## 风险与执行顺序

精确调整单个非系统应用，预计启动风险较低，但这些文件由系统框架读取。误把桌面或设置放入运行黑名单、丢失文件权限、覆盖官方新配置，都可能影响使用。官方 AppPermission 会更新名单，修改可能失效，不承诺永久有效。

1. 核实机型、固件、当前 root，以及 APK 的实际包名、版本、签名、兼容性和现有安装。普通 Termux SSH 不是 root；签名不同不能直接卸载旧版试错。
2. 将三份原文件按原始字节备份到电脑，保存 SHA-256、所有者、权限、大小、修改时间及可读的安全上下文。读取前后核对，避免获取刷新中的混合快照。
3. 在电脑生成差异：仅移除两份黑名单中的目标包，只向白名单追加缺失目标包。保留其他条目、顺序、重复项。说明影响和恢复方法后按用户授权继续。
4. 写入前再次确认原文件未变。独立临时目录中的新文件先验证字节和权限，再在同一文件系统中逐个替换。单文件替换可避免半写，三文件整体不是原子事务；需记录已完成项，失败时条件回退，不覆盖外部新变化。
5. 写后重新读取三份文件，与拟写入内容逐字节比较，复核所有者、权限和格式。不一致时停止安装或重启。
6. 在授权范围内通过原厂通知重载：`am broadcast --user 0 -a com.changhong.listchanged`。广播成功不等于规则已经验证。
7. 检查实际安装、运行、来源授权行为；若使用框架接口，只调用已核查的命名只读接口，不猜 Binder 编号。安装后再次复核文件与权限及已有 Aerial 功能。
8. 用户测试通过后，按约定清理原下载 APK、电脑及电视临时副本，保留电脑备份。不要删除 `/data/app/` 下的已安装应用。

不要为维持效果擅自停用 AppPermission、锁定文件、循环强制覆盖或修改系统分区。这些不是本案例步骤。

## 只读备份与离线计划

先按 [连接方法](connection.md) 确认 root。以下 `capture` 只读连接电视，`plan` 完全离线：

```text
python -B scripts/policy_lists.py capture --ip TV_IP --out .local/policy-before
python -B scripts/policy_lists.py plan --snapshot .local/policy-before --package fun.yecao.helper --out .local/policy-plan
```

输出目录必须不存在。备份包含原始文件和元数据；计划包含 `before/`、`proposed/`、`changes.diff`、`plan.json`。工具保守拒绝不认识的格式，需要人工分析，不代表原文件一定有错。

`capture` 执行时会核对固件和 root，但 `snapshot.json` 只保存文件元数据，不保存设备身份或用户授权。将设备与连接核验结果另记入私有 [维护记录](maintenance-record-template.md)，避免混用不同电视的备份。

工具没有写入命令，不会安装软件、请求 root 或发送重载广播。接手 AI 根据当前快照生成并审阅本次写入脚本，不能重用旧路径或旧校验值的临时脚本。

经授权写入后，可只读复核：

```text
python -B scripts/policy_lists.py verify --ip TV_IP --plan .local/policy-plan
```

该命令比较原始字节、UID/GID 和 mode，不能替代内存规则或实际安装验收；安全上下文虽被采集，但不由 `verify` 比较。若设备启用 SELinux，需另行分析和复核上下文，本案例初始为 Disabled。

`verify` 的临时读取结果不会长期保留。写后及安装后各使用新的目录保存一次 `capture`，例如 `.local/policy-after-write`、`.local/policy-after-install`，并把核验输出记入维护记录，供后续条件恢复使用。

新参数化工具只做离线测试；[野草助手案例](yecao.md) 使用的是当时单独审阅的有界命令。

## 恢复

当前文件仍与本次写入后快照一致时，可以恢复原始字节和权限，再重载、复核。若官方已更新，先备份当前状态，只合并撤销本次条目，不整份写回旧表。重新加入运行黑名单会阻止野草助手启动；卸载应用不会撤销手工白名单，也不会卸载它安装的其他软件。
