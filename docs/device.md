# 已验证设备

[English](en/device.md) · [首页](../README.md)

| 项目 | 实测值 |
| --- | --- |
| 型号 | 长虹 60Q5T |
| 固件标识 | ZLS82GI-V1.50571-EMMC |
| 完整 build | V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30 |
| Android / SDK | 8.0.0 / 26 |
| product / board / platform | full_changhong_mst848 / mst848 / m7221 |
| ABI | arm64-v8a |
| build type / ro.debuggable | userdebug / 1 |
| SELinux | 初始为 Disabled，维护时未修改 |
| 原桌面 | com.changhong.system.launcher.v2/.Launcher |
| 默认桌面文件 | /chperm/preapp/default_launcher，保留原内容 |

普通 Termux 可启动原厂 `adbd`，电脑 `adb root` 后取得当前会话的 root shell。没有刷机、安装持久化 root 或破解 shell 密码。

Aerial guard 1.84（versionCode 114）经用户确认 HOME 和重启成功。野草助手 2.0.16（versionCode 23）经工具确认安装、启动、名单内容和权限；用户随后确认安装测试成功。

只有一台实机样本。没有跨机型刷机、长期待机、全部 HDMI/语音组合或野草助手名单重启持久性测试。2026-11-05 再次使用 SSH 并手动启动 ADB 后取得 root，不证明这些通道会随开机自动恢复。
