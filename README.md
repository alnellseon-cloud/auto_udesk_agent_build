# UAgent 智能工作流搭建工具

这是一个面向 UAgent/Dify 派生平台的工作流编排工具。它提供 Python API 封装、节点工厂、YAML/JSON Builder、任务模板和测试样例，可由 Codex、Claude Code 或人工脚本调用。

仓库不包含真实平台地址、账号、密码、Token、客户 App ID、历史任务、原始材料或运行日志。

## 快速开始

```bash
git clone https://github.com/alnellseon-cloud/auto_udesk_agent_build.git
cd auto_udesk_agent_build
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，至少配置平台地址和一种认证方式：

```dotenv
UAGENT_BASE_URL=https://your-uagent-host.example.com
UAGENT_TOKEN=Bearer your_token_here
```

也可配置 `UAGENT_EMAIL`、`UAGENT_PASSWORD_MD5` 和 `UC_BASE_URL` 使用自动登录。`.env` 已被 Git 忽略，请勿提交真实值。

## 主要目录

- `uagent/`：平台 API 与节点工厂封装。
- `builder/`：从 YAML/JSON 规范生成并部署工作流。
- `examples/`：不含真实资源 ID 的基础样例。
- `tasks/_template/`：新任务目录模板和同会话测试脚本。
- `docs/`：节点支持范围与可复用搭建经验。
- `tests/`：节点工厂回归测试。

## 常用命令

```bash
.venv/bin/python main.py list
.venv/bin/python main.py build examples/simple_qa.yaml
.venv/bin/python main.py test <app_id> "你好"
.venv/bin/python -m unittest discover -s tests -v
```

所有平台写操作都应先读取当前设计；更新已有工作流时，保存完整的 `nodes + edges` 并携带当前 `uuid`，再按需发布。

## 安全边界

- 不提交 `.env`、Bearer Token、账号、密码哈希或真实平台域名。
- 不提交 `tasks/<customer>/`、日志、原始文档、治理后文档或具体 App/Dataset ID。
- 新增示例时只使用虚构域名与占位 ID。
- 发布前运行仓库敏感信息检查，确认历史任务未进入待提交文件。

更多说明见 [使用手册](使用手册.md)、[节点支持范围](docs/node-support.md) 和 [搭建经验](docs/workflow-patterns.md)。
