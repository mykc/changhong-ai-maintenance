# 使用 AI 维护长虹电视

**中文为主要版本。** [English](README.en.md) · [给 AI 的执行指引](agent.md) · [免责声明](DISCLAIMER.md)

本仓库面向电视所有者和 AI 助手，记录如何先读取状态、备份到电脑，再进行小范围修改、验证结果并保留恢复方法。目前只验证了 **长虹 60Q5T / ZLS82GI-V1.50571-EMMC / Android 8.0**，不代表所有长虹电视都适用。

## 已经实现了什么

| 案例 | 已确认的结果 | 日期 |
| --- | --- | --- |
| Aerial 桌面 | 工具确认安装、授权和守护；用户允许后台后确认实体 HOME 和重启均进入 Aerial | 2026-11-04 |
| 野草助手 | 工具确认 2.0.16 安装、启动、三份策略文件与权限、内存规则生效；用户随后确认安装测试成功 | 2026-11-05 |

野草助手使用原包名、原签名。只从安装和运行黑名单移除 `fun.yecao.helper`，并把它加入安装来源白名单。用户没有提供后续测试的目标应用名称和版本，因此不把成功扩大为“所有应用都能安装”。名单重启持久性和官方策略刷新后的状态尚未专项验证。

## 人类读者：选择你的任务

1. 对照 [设备档案](docs/device.md) 确认型号、完整固件和 SDK。不同设备先只读调查。
2. 阅读 [恢复规则](docs/recovery.md) 和 [连接方法](docs/connection.md)，确认如何重新取得维护通道。
3. 选择下面的专项文档。可以把目标告诉 AI，让它先说明具体改动与备份位置，再按你的授权执行。

| 你想做什么 | 阅读文档 |
| --- | --- |
| 使用 Aerial 桌面、修复 HOME 返回问题 | [Aerial 桌面维护](docs/aerial.md) |
| 理解并调整应用安装限制 | [安装策略维护](docs/app-install-policy.md) |
| 查看野草助手这次怎么成功的 | [野草助手实测](docs/yecao.md) |
| 判断 NewtvHQ 是否可以关闭后台 | [应用用途调查](docs/app-inventory.md) |
| 恢复原有行为或处理连接故障 | [恢复规则](docs/recovery.md)、[故障排查](docs/troubleshooting.md) |
| 了解哪些结果真的测过 | [证据记录](docs/evidence.md)、[验证记录](docs/validation.md) |
| 记录下一次维护、手动发布 GitHub | [维护记录模板](docs/maintenance-record-template.md)、[发布方法](docs/publishing.md) |

## AI 读者：从哪里开始

阅读 [agent.md](agent.md)。支持自动发现仓库规则的工具可从 [AGENTS.md](AGENTS.md) 进入。用户要求“只讨论”或“只检查”时，只读调查；文档和脚本不构成设备修改授权。

主 README 用于选任务和理解结果；AI 指引规定身份核验、授权边界、备份、执行与验收。专项文档提供步骤和技术证据。中文和英文的事实、限制和恢复规则应保持一致，更新时同时维护。

## 工具与命令约定

电脑需要 Python 3.10+、[Google platform-tools](https://developer.android.com/tools/releases/platform-tools)，SSH 为可选备用通道。命令均从仓库根目录执行。

| 工具 | 范围 |
| --- | --- |
| [tvctl.py](scripts/tvctl.py) | 连接原厂 root ADB、定向诊断、打开原厂权限页和 Aerial 恢复；修改类动作默认仅预览 |
| [termux-ssh.sh](scripts/termux-ssh.sh) | 用用户自己的公钥配置临时 SSH，不设置开机自启 |
| [policy_lists.py](scripts/policy_lists.py) | 只读备份三份名单及权限、离线生成修改计划、只读复核；不写电视或安装应用 |
| [check_release.py](scripts/check_release.py) | 离线检查公开文件、链接、敏感信息与校验清单，生成发布 ZIP |

```text
python -B scripts/tvctl.py --help
python -B scripts/policy_lists.py --help
python -B -m unittest discover -s tests -v
python -B scripts/check_release.py
```

以上命令不连接电视。文档中的 `TV_IP`、`USER`、`APK_PATH` 是占位符；`192.0.2.10` 是文档示例地址。真实地址、密钥、备份和日志留在 `.local/` 或其他私有目录，不提交仓库。

文档提供完整中英文版本；`tvctl.py` 与 SSH 脚本的运行提示目前以中文为主，常见提示的英文对照见 [故障排查](docs/troubleshooting.md#工具提示对照)。

`tvctl.py inspect` 与 `policy_lists.py capture/verify` 会只读连接电视，要求当前已有确认过的 root ADB。它们不会自动开启 ADB 或提权。`policy_lists.py plan` 完全离线。参数化脚本的离线测试与本次实机操作是两类证据，见 [验证记录](docs/validation.md)。

## 范围与风险

保留原长虹桌面，对单个应用做精确修改；不把刷机、修改启动分区、恢复出厂、全局关闭限制或停用系统权限服务作为默认排错方式。每次修改前把原始文件、权限、所有者和 SHA-256 备份到电脑，修改后检查文件和实际行为。

运行时 `adb root` 不等于永久 root；Aerial 开机进入桌面不代表 SSH/ADB 自动启动。官方策略更新可能覆盖名单；卸载应用不会自动撤销手工名单授权。详情和限制见 [免责声明](DISCLAIMER.md)。

仓库不包含 APK、固件、厂商反编译源码、个人密钥或真实设备快照，与长虹及各应用作者无隶属关系。许可证由仓库所有者选择，当前未附 LICENSE。
