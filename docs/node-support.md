# 节点支持范围

节点工厂位于 `uagent/nodes.py`，YAML/JSON 映射位于 `builder/builder.py`。

| Builder 类型 | 节点用途 | 工厂函数 |
|---|---|---|
| `start` | 流程入口 | `make_start` |
| `llm` | 模型推理与 RAG 上下文注入 | `make_llm` |
| `answer` | 最终回复 | `make_answer` |
| `knowledge_tool` | 知识库宽召回/混合检索 | `make_knowledge_tool` |
| `rerank` | 召回结果精排 | `make_rerank` |
| `rag_convert` | 分片截断和上下文格式化 | `make_rag_convert` |
| `question_classifier` | 意图分类路由 | `make_question_classifier` |
| `if_else` | 单分支或多分支条件判断 | `make_if_else` |
| `code` | 确定性数据处理 | `make_code` |
| `assigner` | 写入流程/会话变量 | `make_assigner` |
| `variable_aggregator` | 合并互斥分支输出 | `make_variable_aggregator` |
| `parameter_extractor` | 从对话提取结构化参数 | `make_parameter_extractor` |
| `http_request` | 调用外部 HTTP 服务 | `make_http_request` |
| `wait` | 延时和节奏控制 | `make_wait` |
| `iteration` | 遍历数组并聚合结果 | `make_iteration` |
| `iteration_start` | 迭代容器内部入口 | `make_iteration_start` |
| `history_query` | 查询当前会话历史消息 | `make_history_query` |
| `udesk_ticket` | 调用平台内置工单工具 | `make_udesk_ticket` |
| `transfer_human` | 调用平台内置转人工工具 | `make_transfer_human` |
| `time_tool` | 获取时间 | `make_time_tool` |
| `template_transform` | 模板化文本转换 | `make_template_transform` |

平台可能按租户、版本或插件开放不同工具。`provider_id`、`tool_name`、模型名和工具参数应以目标环境导出的真实节点为准；仓库中的工厂用于复用结构，不代表每个环境都具备对应能力。
