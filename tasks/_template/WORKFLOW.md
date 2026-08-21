# 工作流快照：[工作流名称]

> **AI 编排助手开会话时必读此文件。** 有变更时同步更新。

---

## 基本信息

| 项目 | 值 |
|---|---|
| **App ID** | `待填写` |
| **平台** | `由 UAGENT_BASE_URL 配置` |
| **最后更新** | YYYY-MM-DD |
| **当前状态** | 待填写（开发中 / 已发布 / 有 Bug 待修复） |

---

## 工作流用途

[一段话描述工作流做什么，解决什么问题]

---

## 会话变量（Conversation Variables）

| 变量名 | 用途 |
|---|---|
| `变量名` | 用途描述 |

---

## 关键节点清单

| 节点标题 | 类型 | 节点 ID | 作用 |
|---|---|---|---|
| 起始节点 | start | `start` | 工作流入口 |
| ... | ... | 按标题查 / 固定ID | ... |

> 通过标题查找节点：`next(n for n in nodes if n['data'].get('title') == '节点标题')`

---

## 已知问题

无 / 列出问题及状态

---

## 待完成事项

- [ ] 事项1
- [ ] 事项2

---

## 知识库信息（无知识库则删除此节）

| 项目 | 值 |
|---|---|
| **dataset_id** | `待填写`（UAgent 平台知识库 ID） |
| **KMS kb_id** | `待填写`（Udesk KMS 知识库 ID） |
| **文件列表** | 文件名 → material_id / doc_id |

---

## 本目录文件说明

```
<task-slug>/
  WORKFLOW.md        ← 本文件：工作流当前状态（AI 编排助手必读）
  README.md          ← 变更日志（人类读）
  scripts/           ← 任务脚本
    governance.py        # 数据治理（有知识库时）
    upload_all.py        # 上传同步（有知识库时）
    build_workflow.py    # 工作流构建
    test_workflow.py     # 工作流测试
  logs/              ← 运行日志（.txt）
  raw_material/      ← 原始素材（有知识库时）
  governed/          ← 治理后文档（有知识库时）
```
