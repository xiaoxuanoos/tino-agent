# Tino Agent 自动提交与升级（独立仓库 / 单用户灰度）

此目录的 `origin` 指向 `xiaoxuanoos/tino-agent`，原 Hermes 项目仅保留只读同步来源。
自动提交工具不会作为后台监视器自行运行；GitHub Actions 当前也暂时关闭，
要在品牌、测试与发布流程审查完成后才能启用。云端示例只用于 SSH 隧道访问的
单用户灰度，**不支持公众注册**。

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

1. 在独立 Tino 仓库设置 Actions 变量
   `TINO_RELEASE_REPOSITORY=xiaoxuanoos/tino-agent`，并在发布测试通过后重新启用 Actions。
   启用后，仅这个仓库的 `main` 推送会触发
   `.github/workflows/tino-staging-image.yml`；构建后进行镜像来源及启动验证，
   才用仓库的 `GITHUB_TOKEN` 发布 `ghcr.io/OWNER/tino-agent:stable` 和 SHA 标签。
   不要把旧工作目录的未审查改动直接推送到新仓库，应先审查内容与凭据。
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
桌面端当前保留现有的更新提示及手动应用机制；独立签名、发布和安全自动安装
还需要独立签名、发布和安全自动安装机制，不能让桌面应用直接拉取原 Hermes 更新。
