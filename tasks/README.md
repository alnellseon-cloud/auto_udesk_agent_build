# tasks/ — 工作流编排任务目录

每个子目录对应一个独立的工作流编排任务。

## 目录结构

```
tasks/
  _template/          ← 新任务模板
  <workflow-slug>/
    README.md         ← 变更日志（人类读）
    WORKFLOW.md       ← 工作流规格和当前状态（Claude 开会话必读）
    scripts/          ← 任务脚本
      governance.py       # 文档治理
      upload_all.py       # 上传同步
      build_workflow.py   # 工作流构建
      test_workflow.py    # 测试
    logs/             ← 运行日志（.txt）
    raw_material/     ← 原始素材（有知识库时）
    governed/         ← 治理后文档（有知识库时）
```

## 本地任务与仓库边界

客户任务、App ID、运行日志、原始材料和治理后文档仅保存在本地，默认不提交到 Git。
GitHub 仓库只保留本文件和 `_template/`，供新任务复制使用。

## 新建任务步骤

详见项目根目录的 `AGENTS.md` 或 `CLAUDE.md` 中“新建任务 SOP”，简要：
1. 创建 `tasks/<slug>/` 及标准子目录（scripts/, logs/, 按需加 raw_material/, governed/）
2. 复制 `_template/` 中的 WORKFLOW.md 和 README.md，填入 App ID 和描述
3. 在 WORKFLOW.md 中记录工作流节点结构
4. 本文件"现有任务"表格追加一行
