# Verified device

[中文](../device.md) · [Home](../../README.en.md)

| Item | Observed value |
| --- | --- |
| Model | Changhong 60Q5T |
| Firmware identifier | ZLS82GI-V1.50571-EMMC |
| Full build | V1.50571-ZLS82Gi-BuildTime.2025.06.12,12.16.30 |
| Android / SDK | 8.0.0 / 26 |
| product / board / platform | full_changhong_mst848 / mst848 / m7221 |
| ABI | arm64-v8a |
| build type / ro.debuggable | userdebug / 1 |
| SELinux | Initially Disabled; not changed during maintenance |
| Original launcher | com.changhong.system.launcher.v2/.Launcher |
| Default launcher file | /chperm/preapp/default_launcher; original content preserved |

Ordinary Termux could start the factory `adbd` service. Running `adb root` from the computer then provided a root shell for the current session. No firmware was flashed, no persistent root was installed, and no shell password was cracked.

For Aerial guard 1.84 (versionCode 114), the user confirmed that physical HOME and reboot behavior worked. For Yecao Helper 2.0.16 (versionCode 23), tools verified installation, launch, policy file contents and permissions; the user subsequently reported that the installation test succeeded.

The evidence covers one physical TV. It does not include flashing across models, long standby, every HDMI/voice combination, or reboot persistence of the Yecao policy changes. On 2026-11-05, SSH was available and ADB was manually started again before obtaining root. This does not prove that either channel starts automatically at boot.
