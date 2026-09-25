<p align="center">
  <img src="apps/desktop/public/tino-agent-mark.png" alt="TinoAgent 标识" width="112">
</p>

<h1 align="center">TinoAgent</h1>

<p align="center">独立的开源 AI Agent 桌面应用与运行时 · 当前为开发者预览版</p>

<p align="center">
  <a href="https://github.com/xiaoxuanoos/tino-agent/releases">版本发布</a> ·
  <a href="docs/tino-automation.md">更新与自动提交</a> ·
  <a href="docs/tino-cloud-deployment.md">部署与安全边界</a> ·
  <a href="LICENSE">MIT 许可</a>
</p>

TinoAgent 是基于 [Nous Research 的 Hermes Agent](https://github.com/NousResearch/hermes-agent)
继续开发的独立项目。桌面应用使用 Tino Agent 品牌，代码发布在本仓库；它不是 Nous Research
的官方服务，也不要求通过 Nous Portal 充值。原项目的版权和 MIT 许可保留在
[LICENSE](LICENSE)，原版说明保存在 [README.hermes-upstream.md](README.hermes-upstream.md)。

## 当前状态

- 桌面应用和后端源码位于同一仓库；可配置第三方模型服务商或兼容接口。
- 本地桌面数据与其他项目分开存放。更新器会检查 Git 分支关系，并在无法安全证明可快进时保留本地改动。
- GitHub 发布目前只提供**源码预览版**。本机 macOS 构建尚无 Developer ID 签名与 Apple 公证，不能当作可直接安装的公众正式版。
- 公开注册、多租户隔离及云端正式部署尚未完成。不要把当前单用户后端直接暴露到公网；具体边界见[部署说明](docs/tino-cloud-deployment.md)。

## 获取源码

```bash
git clone --branch custom/tino-agent https://github.com/xiaoxuanoos/tino-agent.git
cd tino-agent
```

源码预览版的构建与测试需要 Python、Node.js 和项目依赖；桌面端脚本位于
[`apps/desktop/package.json`](apps/desktop/package.json)。不要使用上游 Hermes 官网的一键安装命令来安装 TinoAgent，
那会安装另一个项目。自动提交与更新的适用范围见 [Tino 文档](docs/tino-automation.md)。

## 上游与许可

本项目保留 Hermes Agent 的 MIT 许可及 Nous Research 版权声明。TinoAgent 的名称、界面和本仓库的发布
由此独立项目维护；上游资料仅用于说明代码来源，不代表上游对 TinoAgent 的认可或支持。
