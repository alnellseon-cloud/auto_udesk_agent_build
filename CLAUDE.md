# UAgent 智能工作流搭建工具

## 项目定位

**Claude Code 就是智能层。** 本项目不需要任何 AI API Key。
用户用自然语言在对话框里描述需求 → Claude Code 理解并设计工作流 → 直接调用 UAgent 平台 API 完成搭建/修改/测试。

平台地址由 `UAGENT_BASE_URL` 配置，仓库不保存真实环境域名。

---

## 环境准备

配置 `.env` 文件（参考 `.env.example`）：
```
UAGENT_BASE_URL=https://your-uagent-host.example.com
UAGENT_EMAIL=your@email.com          # 推荐：自动登录，token 过期自动刷新
UAGENT_PASSWORD_MD5=<md5_of_password>
UAGENT_TOKEN=Bearer <token>          # 备用：手动填短期 token
UC_BASE_URL=https://your-user-center-host.example.com
```

**自动登录**（推荐）：配置 `UAGENT_EMAIL` + `UAGENT_PASSWORD_MD5`，client.py 在 token 过期（401）时自动重新登录并将新 token 写回 `.env`，无需手动操作。

注意：`.env` 必须是 **UTF-8 无 BOM** 编码，否则 dotenv 读不到配置。

安装依赖（仅需一次，使用项目虚拟环境）：
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
之后运行脚本用 `.venv/bin/python xxx.py`，或先 `source .venv/bin/activate` 再 `python xxx.py`。

---

## 所有操作都在项目目录下执行

```bash
cd /path/to/auto_udesk_agent_build
```

Python 脚本开头固定加：
```python
import sys; sys.path.insert(0, '.')
```

---

## 核心模块速查

### uagent/ — API 封装层

```python
from uagent.client import UAgentClient
from uagent import apps as apps_api
from uagent import workflow as wf_api
from uagent import nodes as N
from uagent import knowledge as kb_api
from uagent import models as models_api

client = UAgentClient()   # 自动读 .env
```

| 模块 | 功能 |
|---|---|
| `apps_api.create_app(client, title)` | 创建应用，返回 `app_id` |
| `apps_api.list_apps(client)` | 列出所有应用 |
| `apps_api.delete_app(client, app_id)` | 删除应用 |
| `wf_api.get_design(client, app_id)` | 获取当前工作流 JSON |
| `wf_api.save_design(client, app_id, nodes, edges, uuid=data['uuid'])` | 全量保存工作流（**必须传 uuid**，否则返回 400 conflict） |
| `wf_api.publish(client, app_id)` | 发布草稿 |
| `wf_api.run_preview(client, app_id, query)` | 运行测试，返回 SSE 事件列表 |
| `kb_api.list_datasets(client)` | 列出知识库（含 id、name）|
| `models_api.list_model_names(client)` | 列出可用模型 |

### uagent/nodes.py — 节点工厂

每个函数返回符合平台格式的节点 dict，`nid` 参数指定节点 ID（字符串），位置用 `x/y` 控制。

```python
N.make_start(nid='start', x=80, y=282)
N.make_llm(nid='llm1', title='大模型', system_prompt='...', model_name='doubao-seed-1.6', x=380, y=282)
N.make_answer(nid='ans', answer='{{#llm1.text#}}', x=680, y=282)
N.make_knowledge_tool(nid='kb', knowledge_ids_json='[...]', x=380, y=282)
N.make_question_classifier(nid='cls', classes=[...], x=380, y=282)
N.make_if_else(nid='ife', conditions=[...], x=380, y=282)       # 单分支
N.make_if_else(nid='ife', cases=[                               # 多分支（elif）
    {"conditions": [...], "logical_operator": "and"},           #   → sourceHandle="true"
    {"conditions": [...], "case_id": "elif1"},                  #   → sourceHandle="elif1"
], x=380, y=282)
N.make_code(nid='code1', code='def main(...): ...', x=380, y=282)
N.make_parameter_extractor(nid='pe', parameters=[...], x=380, y=282)
N.make_http_request(nid='http1', method='post', url='...', body_value='{}', x=380, y=282)
N.make_time_tool(nid='time1', x=380, y=282)
N.make_assigner(nid='asgn', items=[...], x=380, y=282)
N.make_wait(nid='wait1', wait_time=1, x=380, y=282)             # 等待节点（秒）
N.make_rag_convert(nid='rag1', kb_node_id='kb', limit_token=15000, docs_length=10, x=380, y=282)
N.make_rerank(nid='rr1', kb_node_id='kb', query_selector=['code1','semantic_query'], top_k=10, x=380, y=282)
N.make_edge(source='llm1', target='ans')                        # 普通连线
N.make_edge(source='cls', target='path1', source_handle='1')   # 分类器/条件分支出口
N.make_edge(source='ife', target='t1', source_handle='true')   # if-else true 分支
N.make_edge(source='ife', target='t2', source_handle='elif1')  # if-else elif 分支
N.make_edge(source='ife', target='t3', source_handle='false')  # if-else else 分支
```

#### assigner 写入 conversation 作用域（多轮机型记忆）

```python
# 当用户确认机型后，写入 conversation.model_type，后续轮次直接读取
N.make_assigner(nid='save_model', items=[{
    "input_type": "variable",
    "operation": "over-write",
    "write_mode": "over-write",
    "variable_selector": ["conversation", "model_type"],   # 写入对话级变量
    "value": ["cls_node_id", "class_name"],                # 从分类器读出口名
}])
# 后续节点通过 {{#conversation.model_type#}} 引用，无需 LLM 从历史猜测
```

#### 三阶段 RAG 标准链路

```
KB检索(make_knowledge_tool) → Rerank精排(make_rerank) → 分片转换(make_rag_convert) → LLM
```

- KB节点 `top_k=20`（宽召回） → Rerank `top_k=10`（精排缩减） → RAG Convert `docs_length=10, limit_token=15000`
- LLM 节点开启 `context_enabled=True`，`context.variable_selector=["rag1","text"]`
- 适用于文档量大、相关性要求高的场景；简单场景直接 KB → LLM 即可

### builder/ — 从 YAML/JSON 规范一键部署

```python
from builder.builder import WorkflowBuilder
builder = WorkflowBuilder(client)

# 新建应用并部署
result = builder.deploy(spec_dict, publish=True)
# result: {"app_id": "...", "title": "...", "published": True}

# 更新已有应用
builder.update(app_id, spec_dict, publish=False)

# 从文件部署
builder.deploy_from_file('examples/simple_qa.yaml')
```

---

## 常用操作模板

### 查询平台资源
```python
# 列出知识库
datasets = kb_api.list_datasets(client)
for ds in datasets:
    print(ds['id'], ds['name'])

# 列出应用
resp = apps_api.list_apps(client)
for a in resp['data']['list']:
    print(a['app_id'], a['title'])

# 列出模型
models_api.list_model_names(client)
```

### 最小工作流（start → llm → answer）
```python
nodes = [
    N.make_start(nid='start', x=80, y=282),
    N.make_llm(nid='llm', system_prompt='你是...', x=380, y=282),
    N.make_answer(nid='ans', answer='{{#llm.text#}}', x=680, y=282),
]
edges = [N.make_edge('start','llm'), N.make_edge('llm','ans')]

resp = apps_api.create_app(client, '应用名称')
app_id = resp['data']['app_id']
wf_api.save_design(client, app_id, nodes, edges)
wf_api.publish(client, app_id)
```

### 测试工作流并提取答案（必须使用同一会话）

**所有测试必须在同一 `DIALOG_ID` 下连续运行**，否则无法发现上下文继承失败、多轮记忆丢失等问题。
**禁止自己用 `uuid.uuid4()` 生成 `dialog_id`**——自生成 UUID 会返回 404 "Conversation Not Exists"。

```python
DIALOG_ID = ''  # ← 首次必须为空字符串

def run_test(query):
    global DIALOG_ID
    events = wf_api.run_preview(client, app_id, query, dialog_id=DIALOG_ID)
    for ev in events:
        # 从首次响应的 workflow_started 事件取 conversation_id，后续复用
        if not DIALOG_ID and ev.get('conversation_id'):
            DIALOG_ID = ev['conversation_id']
        if ev.get('type') == 'node_finished':
            d = ev['data']
            if d.get('node_type') == 'answer':
                print('Answer:', d['data']['outputs'].get('answer'))
        if ev.get('type') == 'workflow_finished':
            print('Status:', ev['data']['status'])
```

模板脚本 `_template/scripts/test_workflow.py` 已内置此模式，复制后直接可用。

### 修改已有工作流
```python
# GET 当前状态
resp = wf_api.get_design(client, app_id)
data = resp['data']
nodes = data['grap']['nodes']
edges = data['grap']['edges']
wf_uuid = data['uuid']          # ← 必须保存，POST 时需要带上

# 在内存中修改（例如修改 LLM 提示词）
for n in nodes:
    if n['data']['type'] == 'llm':
        n['data']['prompt_template'][0]['text'] = '新的提示词'

# POST 全量保存（uuid 参数防止并发冲突，不传会 400）
wf_api.save_design(client, app_id, nodes, edges, uuid=wf_uuid)
```

---

## 新建任务 SOP

用户说"帮我新建一个任务，工作流名叫 XXX，App ID 是 YYY"时，执行以下步骤，不使用 TaskCreate 工具：

1. 在 `tasks/` 下创建 `<英文短名>/` 目录（短横线或下划线分隔），并建立以下标准子目录：
   ```
   tasks/<slug>/
     README.md       ← 变更日志（从 _template/README.md 复制）
     WORKFLOW.md     ← 工作流规格和当前状态（从 _template/WORKFLOW.md 复制）
     scripts/        ← 任务脚本（治理/上传/构建/测试）
     logs/           ← 运行日志（.txt 文件）
     raw_material/   ← 原始素材（仅有知识库的任务需要）
     governed/       ← 治理后文档（仅有知识库的任务需要）
   ```
2. 填入 App ID、工作流名称、当前日期、用途描述
3. 在 `tasks/README.md` 的"现有任务"表格追加一行

**脚本命名约定（放入 `scripts/` 子目录）：**
- `governance.py` — 文档数据治理
- `upload_all.py` — 上传同步到知识库
- `build_workflow.py` — 工作流构建/更新
- `test_workflow.py` — 工作流测试（从 `_template/scripts/test_workflow.py` 复制，替换 APP_ID 和 TEST_CASES；日志自动以 UTF-8 写入 `logs/test_YYYYMMDD_HHMMSS.txt`）
- `fix_*.py` — 特定问题修复（如 `fix_kb_filter.py`）

**跨任务通用的功能应封装到 `uagent/` 模块中，不要在任务目录间复制脚本。**

### 任务完成 / 每次调整后必须执行

每次完成一个阶段（初次搭建、修改节点、修复 Bug、调优提示词等）后，必须同时更新两个文件：

| 文件 | 更新内容 | 读者 |
|---|---|---|
| `WORKFLOW.md` | 节点状态、已知问题、待办事项（保持当前快照准确） | Claude（下次会话自动读取） |
| `README.md` | 追加一条变更记录：日期 + 做了什么 + 测试结果 + 遗留问题 | 人类（历史归档） |

**不更新 README.md 的后果**：人类无法从文件中了解工作流历史，只能靠记忆或翻聊天记录。

---

## 关键约定

| 事项 | 规则 |
|---|---|
| **工作流操作模式** | Mode B 全量提交：每次修改都提交完整的 nodes + edges |
| **节点 ID** | 任意唯一字符串，推荐 13 位时间戳或有意义的短名如 `'start'`、`'llm1'` |
| **变量引用** | `{{#node_id.field#}}`，如 `{{#llm1.text#}}`、`{{#sys.query#}}` |
| **条件分支出口** | `source_handle='true'` / `'false'` |
| **分类器出口** | `source_handle=class['id']`，如 `'1'`、`'2'` |
| **发布流程** | `save_design` 保存草稿 → `publish` 发布，两步缺一不可 |
| **Token** | `.env` 文件需 UTF-8 无 BOM，否则读取失败 |
| **代理** | `session.trust_env = False`，绕过系统代理直连平台 |

---

## 经验、记忆与知识库

- 稳定、跨客户可复用的搭建方法维护在 `docs/workflow-patterns.md`；节点清单维护在 `docs/node-support.md`。
- Claude Code 项目记忆通常位于 `~/.claude/projects/<project-key>/memory/`；只有用户明确要求时才沉淀记忆。
- 知识库任务按“治理 → 上传同步 → 验证切片 → 修正问题分片 → 构建 → 同会话测试”执行；若已安装 `kb-management` skill，按其说明操作。
- dataset 被多个工作流共用时，必须为知识库节点配置文档级过滤项；平台域名、租户标识及具体资源 ID 只放在本地任务配置中。
- 多媒体输出格式、三阶段 RAG、历史消息、多轮变量和副作用节点门控详见 `docs/workflow-patterns.md`。

---

## Claude 行为约定

编排过程中若发现以下情况，主动提议更新 CLAUDE.md，说明原因，等用户确认后再写入：
- 发现新的节点类型或节点参数
- 发现平台接口行为与现有文档描述不符
- 某类场景形成了可复用的固定模板

---

## CLI 工具（可选）

```bash
python main.py list                         # 列出应用
python main.py build examples/simple_qa.yaml  # 从 YAML 部署
python main.py test <app_id> "你好"          # 测试
python main.py publish <app_id>             # 发布
python main.py delete <app_id>              # 删除
```
