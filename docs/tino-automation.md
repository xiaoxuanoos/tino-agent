# Tino Agent 自动提交与升级（独立仓库 / 单用户灰度）

Tino 源码已隔离在公开仓库 `xiaoxuanoos/tino-agent` 的 `custom/tino-agent` 分支，
本地 `origin` 指向该仓库；原 Hermes 仓库只保留为不可推送的上游参考。
自动提交脚本仍需逐次指定文件和测试，并不会监视任意聊天或自动推送未经审查的改动。
下方云端示例只用于 SSH 隧道访问的单用户灰度，**不支持公众注册**。

## 自动提交

在 Tino 专属 GitHub 仓库的干净检出中，任务完成后显式提供改动文件及测试文件：

```bash
python3 scripts/tino_auto_commit.py \
  --repo /absolute/path/to/tino-agent \
  --repository OWNER/tino-agent \
  --path scripts/example.py \
  --test-path tests/scripts/test_example.py \
  --message 'Improve example' --push
```

工具验证 Git origin 与指定仓库完全匹配、拒绝原 Hermes 仓库、已有暂存项、
未列出的改动、密钥/生成文件及符号链接，调用项目的 `scripts/run_tests.sh`，
测试成功且工作树没有变化才提交。省略 `--push` 时只在本地提交；推送从不强制。
没有配置后台监视器，也不会定时把任意对话或工作区文件提交上网。

## 镜像发布与云端自动升级

1. 建立**独立** Tino 仓库，并在该仓库设置 Actions 变量
   `TINO_RELEASE_REPOSITORY=OWNER/tino-agent`。仅这个仓库的 `main` 推送会触发
   `.github/workflows/tino-staging-image.yml`；构建后进行镜像来源及启动验证，
   才用仓库的 `GITHUB_TOKEN` 发布 `ghcr.io/OWNER/tino-agent:stable` 和 SHA 标签。
   不要把现有脏目录直接推送到新仓库，应先审查内容与凭据。
2. 在独立的、受控的灰度主机上设置 `TINO_RELEASE_REPOSITORY` 和 `TINO_IMAGE`，
   例如 `TINO_IMAGE=ghcr.io/owner/tino-agent:stable`。若镜像是私有的，需在主机
   自行配置只读 GHCR 凭据；不要提交凭据，也不要在聊天里发送密钥。第一次部署
   由管理员核对镜像后运行 `docker compose -f deploy/tino-staging.compose.yml up -d`。
   这只会暴露主机回环地址的 9119 端口，需用 SSH 隧道访问。
3. 首次部署健康且备份已安排之后，可以由管理员在该主机的定时任务中运行
   `python3 deploy/tino_auto_upgrade.py`（例如每天低峰时段）。脚本用文件锁避免
   并发，只拉取与专属仓库匹配的 `:stable` 标签，仅更新 `agent` 服务；若新镜像
   健康检查失败，恢复上一个镜像并以失败状态退出。

自动回退**只恢复程序镜像**，不会反向迁移数据卷。涉及数据库/状态格式变更时，
必须提前备份并单独做迁移演练。若服务器没有 Docker、专属仓库及定时任务，
此流程仍是“已准备、未启用”，不是已经完成的云部署或桌面应用静默升级。
桌面端使用 `custom/tino-agent` 检查并手动应用更新；完整的无人值守桌面自动升级
仍需要专属发行签名与发布流程。切勿将桌面更新分支改回原 Hermes 仓库的 `main`。

## macOS 本地桌面更新

如果检出位于会给 `.app` 附加 Finder 元数据的同步目录，macOS 严格签名校验可能失败。
可将生成的 `apps/desktop/release` 放到 Tino 专用的非同步目录，并让检出中的同名路径
指向它；更新器会在真实 `release` 目录旁暂存新包，签名验证通过后才替换旧包。
操作前必须退出 Tino、确认没有正在运行的会话，并保留原 `release` 目录作回退。

外置 `release` 目录需要一个不含密钥的 `.tino-checkout.json`，格式为
`{"root":"/absolute/path/to/tino-checkout"}`。从外置应用启动时，Tino 只有在该路径下
确实存在源码、虚拟环境及 `.tino-runtime/home` 时才继续使用原隔离聊天与设置；
不要单独把 `.app` 复制到其他位置后启动。切换后检查 Git 工作树是否干净、
`codesign --verify --deep --strict` 是否通过、后端是否仍打开原 `.tino-runtime/home/state.db`。

## GitHub 源码预发布

预发布标签应指向 `custom/tino-agent`，而不是尚未切换的默认 `main` 分支。
当前 macOS 本地构建只有 ad-hoc 签名、尚未经过 Apple 公证；GitHub 的源码归档可供开发者检出，
但不要把本机 `.app` 宣称为公众可直接安装的正式桌面包。正式二进制发行需先配置 Developer ID、
完成公证并在干净机器上验证安装与首次启动。
