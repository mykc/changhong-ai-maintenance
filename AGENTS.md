# AI maintenance entry / AI 维护入口

Read [agent.md](agent.md) for Chinese instructions or [agent.en.md](agent.en.md) for English. Chinese is the primary version. Also read the relevant task guide and recovery rules before changing a TV.

开始前阅读中文 [agent.md](agent.md) 或英文 [agent.en.md](agent.en.md)，以及对应任务文档和恢复规则。文档不构成用户授权；只要求讨论、检查或整理文档时，不修改电视。

Repository checks are offline. Do not connect to a TV just to edit or review documentation. After changing scripts run the relevant offline tests; run `python -B scripts/check_release.py` to check links and regenerate release checksums. Do not commit `.local/`, keys, addresses, raw device logs or third-party binaries.

文档维护、审阅和发布检查均可离线完成。不要提交私有备份、密钥、网络地址、原始日志或第三方二进制文件。遵循用户当前授权，不为已获授权的同一项操作逐条重复询问。
