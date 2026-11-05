# 手动发布与后续维护

[English](en/publishing.md) · [首页](../README.md)

发布目录名称为 `changhong-ai-maintenance`，可作为建议仓库名。只上传这个目录内的公开文件，不上传旁边的私有现场备份、旧工作目录或原始日志。目录不依赖此前的本机路径。

## 发布前检查

- 中文为主要版本，英文为完整配套；人类入口为 `README.md` / `README.en.md`，AI 入口为 `agent.md` / `agent.en.md` 与 `AGENTS.md`。
- 阅读 [免责声明](../DISCLAIMER.md)，自行决定开源许可证。免责声明不是 LICENSE；没有 LICENSE 不表示任意复用已获授权。
- 确认不含真实 IP、个人路径、Termux 实际 UID、私钥、公钥、known_hosts、Wi-Fi 密码、令牌、原始截图/日志、固件或 APK。
- `.gitignore` 只阻止未来误加入，不清除已经跟踪或进入历史的秘密；必要时检查 `git ls-files` 和历史。
- 第三方工具与 APK 由使用者从可信来源准备。本仓库的指纹仅对应案例版本，不替代来源核验。

## 离线验证和打包

从仓库根目录运行，下面命令不会连接电视：

```text
python -B -m unittest discover -s tests -v
python -B scripts/tvctl.py --help
python -B scripts/policy_lists.py --help
python -B scripts/tvctl.py emergency-stop --ip 192.0.2.10
python -B scripts/check_release.py
python -B scripts/check_release.py --check --zip
```

示例 IP 属于文档专用地址；预览没有 `--execute`。`-B` 防止 Python 生成含本机路径的字节码缓存；它不会清除以前的缓存。有 Bash 时再运行 `bash -n scripts/termux-ssh.sh`。

`check_release.py` 只收录明确列出的公开文件，检查双语文件存在、本地文件链接、常见敏感信息模式及 UTF-8 无 BOM / LF 格式，然后刷新 `SHA256SUMS`。`.gitattributes` 固定 LF，避免不同系统克隆后文件字节改变。`--check` 只比对已有清单；`--zip` 在目录旁生成 ZIP。新增公开文档或工具时，审阅后同步更新脚本的文件清单。忽略的 `.local/`、缓存和工作目录不会打包，未知其他文件使检查失败。

自动扫描不能保证检出全部秘密，仍需人工审阅暂存内容。离线测试不能代替真机验收，见 [验证记录](validation.md)。

## 手动推送到 GitHub

先在 GitHub 手动创建仓库，再在发布目录执行；把远端 URL 替换为自己的值：

```text
git init
git add README.md README.en.md agent.md agent.en.md AGENTS.md DISCLAIMER.md DISCLAIMER.en.md docs scripts tests .gitignore .gitattributes SHA256SUMS
git diff --cached --stat
git diff --cached
git commit -m "Document AI-assisted Changhong TV maintenance"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

这只是步骤，本次没有创建远端、提交或推送。也可用网页上传：将已通过检查的发布 ZIP 解压到新目录，只上传解压后的公开内容，注意 `.gitignore` 和 `.gitattributes` 两个隐藏文件。GitHub 网页上传不执行 `.gitignore`，不要直接拖入运行过脚本的工作目录，以免上传缓存、`.local/` 备份或密钥。若添加 LICENSE，需同步更新发布检查脚本的允许清单。

## 接受新案例

收集型号、完整固件、SDK、应用版本和签名、用户目标、最小复现、具体改动、备份、恢复方法，以及每项结果的证据来源。未知结果写明未测；其他机型单列，不覆盖已有案例边界。

修改中文后同步英文，尤其是授权、恢复、参数和未验证事项。让独立审阅者在没有原会话上下文的情况下，只阅读仓库检查完整性；修复问题后重跑相关离线检查并重新生成校验值。不要为了检查文档而连接用户电视。
