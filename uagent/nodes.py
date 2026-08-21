"""
节点工厂函数 —— 生成符合 UAgent/Dify API 格式的节点和边 dict。

节点 ID 规则：
- 13 位毫秒时间戳字符串，如 "1778351808860"
- 特殊固定 ID（初始默认）：'start'、'llm'、'answer'
- 推荐使用 make_node_id() 生成，保证同批次唯一
"""
import time
import uuid as _uuid


def make_node_id() -> str:
    t = int(time.time() * 1000)
    time.sleep(0.001)  # 避免同毫秒重复
    return str(t)


# ── 边 ────────────────────────────────────────────────────────────────────────

def make_edge(
    source: str,
    target: str,
    source_handle: str = "source",
    source_type: str = "",
    target_type: str = "",
) -> dict:
    edge_id = f"{source}-{source_handle}-{target}-target"
    return {
        "id": edge_id,
        "type": "custom",
        "selected": False,
        "source": source,
        "sourceHandle": source_handle,
        "target": target,
        "targetHandle": "target",
        "zIndex": 0,
        "data": {
            "isInLoop": False,
            "sourceType": source_type,
            "targetType": target_type,
        },
    }


# ── 开始节点 ──────────────────────────────────────────────────────────────────

def make_start(nid: str = None, x: float = 80, y: float = 282) -> dict:
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {"type": "start", "title": "开始", "desc": "", "variables": []},
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 大模型节点 ────────────────────────────────────────────────────────────────

def make_llm(
    nid: str = None,
    title: str = "大模型",
    system_prompt: str = "",
    model_name: str = "doubao-seed-1.6",
    model_provider: str = "langgenius/openai_api_compatible/openai_api_compatible",
    temperature: float = 0.7,
    memory_enabled: bool = True,
    memory_size: int = 10,
    vision_enabled: bool = False,
    context_enabled: bool = False,
    context_variable_selector: list = None,
    x: float = 380,
    y: float = 282,
    enable_thinking: bool = None,
    query_prompt_template: str = "{{#sys.query#}}",
) -> dict:
    """
    context_variable_selector: 当需要注入知识库上下文时，设置为 RAG Convert 节点的输出路径，
      如 ['rag_conv', 'text']，同时在 system_prompt 中用 {{#context#}} 引用。
      这是平台正确引用知识库的方式，不要用 variables + {{knowledge_context}}。
    """
    completion_params = {"temperature": temperature}
    if enable_thinking is not None:
        completion_params["enable_thinking"] = enable_thinking

    memory = None
    if memory_enabled is not None:
        memory = {
            "window": {"enabled": memory_enabled, "size": memory_size},
            "query_prompt_template": query_prompt_template,
            "role_prefix": {"assistant": "", "user": ""},
        }

    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "llm",
            "title": title,
            "desc": "",
            "variables": [],
            "model": {
                "provider": model_provider,
                "name": model_name,
                "mode": "chat",
                "completion_params": completion_params,
            },
            "prompt_template": [{"role": "system", "text": system_prompt}],
            "context": {
                "enabled": context_enabled or bool(context_variable_selector),
                "variable_selector": context_variable_selector or [],
            },
            "vision": {"enabled": vision_enabled},
            "memory": memory,
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 直接回答节点 ───────────────────────────────────────────────────────────────

def make_answer(
    nid: str = None,
    title: str = "直接回答",
    answer: str = "",
    x: float = 680,
    y: float = 282,
) -> dict:
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "answer",
            "title": title,
            "desc": "",
            "variables": [],
            "answer": answer,
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 知识库检索工具节点 ─────────────────────────────────────────────────────────

def make_knowledge_tool(
    nid: str = None,
    title: str = "知识库检索",
    knowledge_ids_json: str = "[]",
    query_selector: list = None,
    top_k: str = "6",
    x: float = 380,
    y: float = 282,
    ext_aggregation_ids="",
    catalog_ids=None,
    ext_catalog_ids=None,
    data_types=None,
    ext_data_types=None,
    meta_filter=None,
    channel_id=None,
    weight: str = "0.7",
    weight_ratio: str = "0.3",
    weighted: bool = False,
    mmr: bool = False,
    mmr_filter_k: int = 100,
    mmr_lambda: str = "0.8",
    filter_rule="",
) -> dict:
    q_sel = query_selector or ["sys", "query"]
    query_ref = f"{{{{#{q_sel[0]}.{q_sel[1]}#}}}}"
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_knowledge_search",
            "provider_name": "udesk_knowledge_search",
            "provider_type": "builtin",
            "tool_name": "udesk_knowledge_search_mix",
            "tool_label": "知识检索",
            "output_schema": None,
            "params": {
                "query": "", "aggregation_ids": "", "ext_aggregation_ids": "",
                "catalog_ids": "", "ext_catalog_ids": "", "data_types": "",
                "ext_data_types": "", "top_k": "", "weight": "", "weight_ratio": "",
                "weighted": "", "mmr": "", "mmr_filter_k": "", "mmr_lamda": "",
                "filter_rule": "", "meta_filter": "", "channel_id": "",
            },
            "tool_configurations": {
                "aggregation_ids": {"type": "mixed", "value": knowledge_ids_json},
                "top_k": {"type": "constant", "value": top_k},
                "weight": {"type": "constant", "value": weight},
                "weight_ratio": {"type": "mixed", "value": weight_ratio},
                "weighted": {"type": "constant", "value": weighted},
                "mmr": {"type": "constant", "value": mmr},
                "mmr_filter_k": {"type": "constant", "value": mmr_filter_k},
                "mmr_lamda": {"type": "constant", "value": mmr_lambda},
                "catalog_ids": {"type": "mixed", "value": catalog_ids},
                "data_types": {"type": "mixed", "value": data_types},
                "filter_rule": {"type": "mixed", "value": filter_rule},
            },
            "tool_parameters": {
                "query": {"type": "mixed", "value": query_ref},
                "ext_aggregation_ids": {"type": "mixed", "value": ext_aggregation_ids},
                "ext_catalog_ids": {"type": "mixed", "value": ext_catalog_ids},
                "ext_data_types": {"type": "mixed", "value": ext_data_types},
                "meta_filter": {"type": "mixed", "value": meta_filter},
                "channel_id": {"type": "mixed", "value": channel_id},
            },
            "paramSchemas": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 内置时间工具节点 ───────────────────────────────────────────────────────────

def make_time_tool(
    nid: str = None,
    title: str = "获取当前时间",
    fmt: str = "%Y-%m-%d %H:%M:%S",
    timezone: str = "Asia/Shanghai",
    x: float = 380,
    y: float = 282,
) -> dict:
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "time",
            "provider_name": "time",
            "provider_type": "builtin",
            "tool_name": "current_time",
            "tool_label": "获取当前时间",
            "output_schema": None,
            "params": {"format": "", "timezone": ""},
            "tool_configurations": {
                "format": {"type": "constant", "value": fmt},
                "timezone": {"type": "constant", "value": timezone},
            },
            "tool_parameters": {},
            "paramSchemas": [],
            "variables": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 历史消息查询工具节点 ───────────────────────────────────────────────────────

def make_history_query(
    nid: str = None,
    title: str = "历史消息",
    conversation_id: str = "{{#sys.conversation_id#}}",
    query: str = "",
    memory_size: int = 100,
    pattern: str = "Human:{query} \\n AI: {answer} \\n",
    x: float = 380,
    y: float = 282,
) -> dict:
    """查询当前会话的历史消息，适用于工单摘要、升级人工或会话审计。

    输出字段为 text；默认使用 sys.conversation_id 查询当前会话。
    pattern 支持 {query} 和 {answer} 占位符。
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_rag",
            "provider_name": "udesk_rag",
            "provider_type": "builtin",
            "tool_name": "udesk_history_query",
            "tool_label": "历史消息",
            "output_schema": None,
            "params": {
                "conversation_id": "",
                "history_message_pattern": "",
                "memory_size": "",
                "query": "",
            },
            "tool_configurations": {
                "history_message_pattern": {"type": "mixed", "value": pattern},
                "memory_size": {"type": "constant", "value": str(memory_size)},
            },
            "tool_parameters": {
                "conversation_id": {"type": "mixed", "value": conversation_id},
                "query": {"type": "mixed", "value": query},
            },
            "paramSchemas": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 内置 Udesk 工单创建工具节点 ────────────────────────────────────────────────

def make_udesk_ticket(
    nid: str = None,
    title: str = "创建工单",
    config_identification: str = "",
    template_id: str = "",
    subject: str = "",
    content: str = "",
    ticket_field: str = "{}",
    search_type: str = "",
    type_content: str = "",
    x: float = 380,
    y: float = 282,
    call_id=None,
    call_type=None,
) -> dict:
    """
    内置工单工具 udesk_order_assistant_v2 / udesk_ticket_create_v2。

    所有文本参数都支持 {{#node.field#}} / {{#conversation.var#}} 变量引用。
    - config_identification: 当前租户的第三方继承配置标识，由平台管理员提供
    - template_id: 工单模板 ID（在 Udesk 后台对应工单类型）
    - subject / content: 工单主题、问题描述，可写变量引入实际内容
    - ticket_field: 自定义字段 JSON 字符串，如
        '{"TextField_2557":"{{#conversation.name#}}","TextField_2720":"{{#conversation.phone#}}"}'
    - search_type / type_content: 按 email/cellphone/customer_id 关联已有客户（可留空）
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_order_assistant_v2",
            "provider_name": "udesk_order_assistant_v2",
            "provider_type": "builtin",
            "tool_name": "udesk_ticket_create_v2",
            "tool_label": "Create a Udesk ticket",
            "output_schema": None,
            "params": {
                "call_id": "", "call_type": "", "config_identification": "",
                "content": "", "subject": "", "template_id": "",
                "ticket_field": "", "type": "", "type_content": "",
            },
            "tool_configurations": {},
            "tool_parameters": {
                "config_identification": {"type": "mixed", "value": config_identification},
                "subject": {"type": "mixed", "value": subject},
                "content": {"type": "mixed", "value": content},
                "template_id": {"type": "mixed", "value": template_id},
                "ticket_field": {"type": "mixed", "value": ticket_field},
                "type": {"type": "mixed", "value": search_type},
                "type_content": {"type": "mixed", "value": type_content},
                "call_id": {"type": "mixed", "value": call_id},
                "call_type": {"type": "mixed", "value": call_type},
            },
            "paramSchemas": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 内置 Udesk 转人工工具节点 ──────────────────────────────────────────────────

def make_transfer_human(
    nid: str = None,
    title: str = "转人工",
    agent_response: str = "{{#sys.query#}}",
    custom_prompt: str = "{{#sys.query#}}",
    is_transfer_human: str = "true",
    is_use_system_prompt: str = "true",
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    内置转人工工具 udesk_transfe_human / transfer_human。
    触发后把当前会话转接到人工坐席。返回 JSON（含 message/data），
    一般再接一个 code 节点解析出文本，再接 answer 输出。
    - agent_response: 转接前 AI 给客户的话术（可写变量，如某 LLM 节点输出）
    - is_transfer_human: 'true' 表示执行转接
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_transfe_human",
            "provider_name": "udesk_transfe_human",
            "provider_type": "builtin",
            "tool_name": "transfer_human",
            "tool_label": "转人工",
            "output_schema": None,
            "params": {
                "agent_response": "", "custom_prompt": "", "is_transfer_human": "",
                "is_use_system_prompt": "", "param_list_json": "",
            },
            "tool_configurations": {},
            "tool_parameters": {
                "agent_response": {"type": "mixed", "value": agent_response},
                "custom_prompt": {"type": "mixed", "value": custom_prompt},
                "is_transfer_human": {"type": "mixed", "value": is_transfer_human},
                "is_use_system_prompt": {"type": "mixed", "value": is_use_system_prompt},
                "param_list_json": {"type": "mixed", "value": None},
            },
            "paramSchemas": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 问题分类器节点 ─────────────────────────────────────────────────────────────

def make_question_classifier(
    nid: str = None,
    title: str = "问题分类",
    classes: list = None,
    instruction: str = "",
    model_name: str = "doubao-seed-1.6",
    model_provider: str = "langgenius/openai_api_compatible/openai_api_compatible",
    x: float = 380,
    y: float = 282,
) -> dict:
    default_classes = [
        {"id": "1", "name": "分类1", "description": ""},
        {"id": "2", "name": "分类2", "description": ""},
    ]
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "question-classifier-plus",
            "title": title,
            "desc": "",
            "selected": False,
            "classes": classes or default_classes,
            "instruction": instruction,
            "memory": {
                "query_prompt_template": "{{#sys.query#}}",
                "window": {"enabled": True, "size": 50},
            },
            "model": {
                "completion_params": {"temperature": 0.7},
                "mode": "chat",
                "name": model_name,
                "provider": model_provider,
            },
            "query_variable_selector": ["sys", "query"],
            "topics": [],
            "vision": {"enabled": False},
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 条件分支节点 ───────────────────────────────────────────────────────────────

def make_if_else(
    nid: str = None,
    title: str = "条件分支",
    conditions: list = None,
    logical_operator: str = "and",
    cases: list = None,
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    单分支（legacy）：
      conditions = [{"variable_selector": [...], "comparison_operator": "contains",
                     "value": "xxx", "varType": "string"}]
      → 生成一个 case_id="true" 的分支，else 用边 sourceHandle="false"

    多分支（elif）：
      cases = [
        {"conditions": [...], "logical_operator": "and"},           # → case_id="true"
        {"conditions": [...], "logical_operator": "and",
         "case_id": "my_elif"},                                      # → case_id="my_elif"
      ]
      边连法：make_edge(nid, target1, source_handle="true")
              make_edge(nid, target2, source_handle="my_elif")
              make_edge(nid, else_target, source_handle="false")
    """
    def _build_conds(raw_list):
        return [
            {
                "id": str(_uuid.uuid4()),
                "variable_selector": c.get("variable_selector", []),
                "varType": c.get("varType", "string"),
                "comparison_operator": c.get("comparison_operator", "="),
                "value": c.get("value", ""),
            }
            for c in raw_list
        ]

    if cases:
        built_cases = []
        for i, c in enumerate(cases):
            case_id = "true" if i == 0 else c.get("case_id", str(_uuid.uuid4()))
            built_cases.append({
                "id": case_id,
                "case_id": case_id,
                "logical_operator": c.get("logical_operator", "and"),
                "conditions": _build_conds(c.get("conditions", [])),
            })
    else:
        built_cases = [{
            "id": "true",
            "case_id": "true",
            "logical_operator": logical_operator,
            "conditions": _build_conds(conditions or []),
        }]

    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "if-else",
            "title": title,
            "desc": "",
            "selected": False,
            "cases": built_cases,
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 代码节点 ───────────────────────────────────────────────────────────────────

def make_code(
    nid: str = None,
    title: str = "代码执行",
    code: str = "def main(arg1: str) -> dict:\n    return {'result': arg1}\n",
    language: str = "python3",
    outputs: dict = None,
    variables: list = None,
    x: float = 380,
    y: float = 282,
    error_strategy: str = None,
) -> dict:
    node = {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "code",
            "title": title,
            "desc": "",
            "code": code,
            "code_language": language,
            "outputs": outputs or {"result": {"children": None, "type": "string"}},
            "variables": variables or [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }
    if error_strategy is not None:
        node["data"]["error_strategy"] = error_strategy
    return node


# ── 变量赋值节点 ───────────────────────────────────────────────────────────────

def make_assigner(
    nid: str = None,
    title: str = "变量赋值",
    items: list = None,
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    items 格式：
    [{"input_type": "variable", "operation": "over-write", "write_mode": "over-write",
      "variable_selector": ["conversation", "var_name"],
      "value": ["source_node_id", "source_field"]}]
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "assigner",
            "title": title,
            "desc": "",
            "version": "2",
            "items": items or [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 变量聚合节点 ────────────────────────────────────────────────────────────────────

def make_variable_aggregator(
    nid: str = None,
    title: str = "变量聚合",
    variables: list = None,
    output_type: str = "string",
    x: float = 380,
    y: float = 282,
) -> dict:
    """聚合多条互斥分支的输出，为下游节点提供统一的 output 字段。

    variables 格式：[["llm_a", "text"], ["llm_b", "text"]]
    平台会选取实际执行分支的值，并从 output 字段输出。
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "variable-aggregator",
            "title": title,
            "desc": "",
            "selected": False,
            "variables": variables or [],
            "output_type": output_type,
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 参数提取节点 ───────────────────────────────────────────────────────────────

def make_parameter_extractor(
    nid: str = None,
    title: str = "参数提取",
    instruction: str = "",
    parameters: list = None,
    query_selector: list = None,
    model_name: str = "doubao-seed-1.6",
    model_provider: str = "langgenius/openai_api_compatible/openai_api_compatible",
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    parameters 格式：
    [{"name": "city", "description": "城市名称", "type": "string", "required": False}]
    """
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "parameter-extractor",
            "title": title,
            "desc": "",
            "selected": False,
            "instruction": instruction,
            "reasoning_mode": "prompt",
            "model": {
                "completion_params": {"temperature": 0.7},
                "mode": "chat",
                "name": model_name,
                "provider": model_provider,
            },
            "memory": {
                "query_prompt_template": "{{#sys.query#}}",
                "role_prefix": {"assistant": "", "user": ""},
                "window": {"enabled": True, "size": 10},
            },
            "parameters": parameters or [],
            "query": query_selector or ["sys", "query"],
            "variables": [],
            "vision": {"enabled": False},
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── HTTP 请求节点 ──────────────────────────────────────────────────────────────

def make_http_request(
    nid: str = None,
    title: str = "HTTP请求",
    method: str = "post",
    url: str = "",
    headers: str = "Content-Type:application/json",
    body_value: str = "{}",
    auth_type: str = "no-auth",
    x: float = 380,
    y: float = 282,
) -> dict:
    kv_id = f"kv-{int(time.time() * 1000)}"
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "http-request",
            "title": title,
            "desc": "",
            "selected": False,
            "method": method,
            "url": url,
            "headers": headers,
            "params": "",
            "authorization": {"type": auth_type, "config": None},
            "body": {
                "type": "json",
                "data": [{"id": kv_id, "key": "", "type": "text", "value": body_value}],
            },
            "timeout": {
                "max_connect_timeout": 0,
                "max_read_timeout": 0,
                "max_write_timeout": 0,
            },
            "retry_config": {
                "retry_enabled": True,
                "max_retries": 3,
                "retry_interval": 100,
            },
            "variables": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 等待节点 ───────────────────────────────────────────────────────────────────

def make_wait(
    nid: str = None,
    title: str = "等待",
    wait_time: int = 1,
    x: float = 380,
    y: float = 282,
) -> dict:
    """等待指定秒数，可用于流程节奏控制或避免并发冲突。"""
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_wait",
            "provider_name": "udesk_wait",
            "provider_type": "builtin",
            "tool_name": "udesk_wait",
            "tool_label": "等待",
            "output_schema": None,
            "params": {"wait_time": ""},
            "tool_configurations": {},
            "tool_parameters": {
                "wait_time": {"type": "constant", "value": wait_time},
            },
            "paramSchemas": [],
            "variables": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── RAG 分片截取转换节点 ────────────────────────────────────────────────────────

def make_rag_convert(
    nid: str = None,
    title: str = "分片截取转换",
    kb_node_id: str = None,
    kb_output_field: str = "text",
    limit_token: int = 15000,
    docs_length: int = 10,
    pattern: str = "---\\n Source:{title} \\n FileUrl:{file_url} \\n Passage: {doc_content} \\n ---",
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    将知识库检索结果（KB节点输出）截取并格式化为 LLM 可读的上下文。

    接在 KB 检索节点（或 Rerank 节点）之后，输出可直接注入 LLM context。
    输出字段为 text，在 LLM 的 context.variable_selector 中引用：
      ["rag_node_id", "text"]

    pattern 占位符：{title} {file_url} {doc_content}
    """
    doc_ref = f"{{{{#{kb_node_id}.{kb_output_field}#}}}}" if kb_node_id else "{{#sys.query#}}"
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_rag",
            "provider_name": "udesk_rag",
            "provider_type": "builtin",
            "tool_name": "udesk_passage_covert",
            "tool_label": "分片截取转换",
            "output_schema": None,
            "params": {
                "convert_message_pattern": "",
                "doc_contents": "",
                "docs_lenth": "",
                "is_convert_message": "",
                "limit_token_size": "",
            },
            "tool_configurations": {
                "convert_message_pattern": {"type": "mixed", "value": pattern},
                "docs_lenth": {"type": "constant", "value": docs_length},
                "is_convert_message": {"type": "constant", "value": True},
                "limit_token_size": {"type": "constant", "value": str(limit_token)},
            },
            "tool_parameters": {
                "doc_contents": {"type": "mixed", "value": doc_ref},
            },
            "paramSchemas": [],
            "variables": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── Rerank 精排节点 ────────────────────────────────────────────────────────────

def make_rerank(
    nid: str = None,
    title: str = "Rerank精排",
    kb_node_id: str = None,
    kb_output_field: str = "text",
    query_selector: list = None,
    top_k: int = 10,
    mmr_lambda: str = "0.6",
    rerank_type: str = "bge",
    x: float = 380,
    y: float = 282,
) -> dict:
    """
    对 KB 检索结果进行精排，提升相关性排序。

    接在 KB 检索节点之后，输出传给 make_rag_convert 或直接传给 LLM context。
    输出字段为 text。

    query_selector: 原始查询变量路径，如 ["code_node_id", "semantic_query"]
                    或 ["sys", "query"]
    """
    doc_ref = f"{{{{#{kb_node_id}.{kb_output_field}#}}}}" if kb_node_id else ""
    q_sel = query_selector or ["sys", "query"]
    query_ref = f"{{{{#{q_sel[0]}.{q_sel[1]}#}}}}"
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "tool",
            "title": title,
            "desc": "",
            "selected": False,
            "provider_id": "udesk_document",
            "provider_name": "udesk_document",
            "provider_type": "builtin",
            "tool_name": "document_rerank",
            "tool_label": "Rerank精排",
            "output_schema": None,
            "params": {
                "doc_contents": "",
                "mmr_lambda": "",
                "query": "",
                "rerank_type": "",
                "top_k": "",
            },
            "tool_configurations": {
                "mmr_lambda": {"type": "mixed", "value": mmr_lambda},
                "rerank_type": {"type": "constant", "value": rerank_type},
                "top_k": {"type": "constant", "value": top_k},
            },
            "tool_parameters": {
                "doc_contents": {"type": "mixed", "value": doc_ref},
                "query": {"type": "mixed", "value": query_ref},
            },
            "paramSchemas": [],
            "variables": [],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }


# ── 模板转换节点 ───────────────────────────────────────────────────────────────

# ── 迭代器节点组 ────────────────────────────────────────────────────────────────

def make_iteration(
    nid: str = None,
    title: str = "迭代器",
    iterator_selector: list = None,
    output_selector: list = None,
    output_type: str = "array[string]",
    is_parallel: bool = True,
    parallel_nums: int = 10,
    error_handle_mode: str = "terminated",
    height: int = 450,
    width: int = 480,
    x: float = 380,
    y: float = 282,
) -> dict:
    """迭代器容器节点。内部节点用 mark_in_iteration() 标记，内部边用 make_iter_edge()。
    start_node_id 自动设为 nid+'start'。"""
    nid = nid or make_node_id()
    return {
        "id": nid,
        "type": "custom",
        "data": {
            "type": "iteration",
            "title": title,
            "desc": "",
            "selected": False,
            "iterator_selector": iterator_selector or [],
            "output_selector": output_selector or [],
            "output_type": output_type,
            "is_parallel": is_parallel,
            "parallel_nums": parallel_nums,
            "error_handle_mode": error_handle_mode,
            "start_node_id": nid + "start",
            "height": height,
            "width": width,
        },
        "position": {"x": x, "y": y},
        "positionAbsolute": {"x": x, "y": y},
        "height": height,
        "width": width,
        "zIndex": 1,
        "targetPosition": "left",
        "sourcePosition": "right",
    }


def make_iteration_start(
    iter_nid: str,
    rel_x: float = 60,
    rel_y: float = 195.5,
    iter_abs_x: float = 0,
    iter_abs_y: float = 0,
) -> dict:
    """迭代器内部起始节点（固定，不可拖动）。id = iter_nid + 'start'。"""
    return {
        "id": iter_nid + "start",
        "type": "custom-iteration-start",
        "parentId": iter_nid,
        "data": {
            "type": "iteration-start",
            "title": "",
            "desc": "",
            "isInIteration": True,
        },
        "position": {"x": rel_x, "y": rel_y},
        "positionAbsolute": {"x": iter_abs_x + rel_x, "y": iter_abs_y + rel_y},
        "draggable": False,
        "selectable": False,
        "width": 44,
        "height": 48,
        "zIndex": 1002,
        "sourcePosition": "right",
        "targetPosition": "left",
    }


def mark_in_iteration(
    node: dict,
    iter_nid: str,
    rel_x: float,
    rel_y: float,
    iter_abs_x: float = 0,
    iter_abs_y: float = 0,
) -> dict:
    """将普通节点标记为迭代器内部节点（in-place 修改并返回）。"""
    node["parentId"] = iter_nid
    node["position"] = {"x": rel_x, "y": rel_y}
    node["positionAbsolute"] = {"x": iter_abs_x + rel_x, "y": iter_abs_y + rel_y}
    node["zIndex"] = 1002
    node["data"]["isInIteration"] = True
    node["data"]["isInLoop"] = False
    node["data"]["iteration_id"] = iter_nid
    return node


def make_iter_edge(
    source: str,
    target: str,
    iter_nid: str,
    source_type: str = "",
    target_type: str = "",
) -> dict:
    """迭代器内部连线（自动打上 isInIteration 标记）。"""
    edge = make_edge(source, target, "source", source_type, target_type)
    edge["data"]["isInIteration"] = True
    edge["data"]["iteration_id"] = iter_nid
    edge["zIndex"] = 1002
    return edge


# ── 模板转换节点 ───────────────────────────────────────────────────────────────

def make_template_transform(
    nid: str = None,
    title: str = "模板转换",
    template: str = "{{ arg1 }}",
    variables: list = None,
    x: float = 380,
    y: float = 282,
) -> dict:
    return {
        "id": nid or make_node_id(),
        "type": "custom",
        "data": {
            "type": "template-transform",
            "title": title,
            "desc": "",
            "template": template,
            "variables": variables or [{"value_selector": [], "variable": "arg1"}],
        },
        "position": {"x": x, "y": y},
        "targetPosition": "left",
        "sourcePosition": "right",
    }
