"""
WorkflowBuilder —— 将工作流规范（dict/YAML）部署到 UAgent 平台。

工作流规范格式（YAML 示例）：
  name: "客服机器人"
  description: "..."    # 可选
  nodes:
    - id: start         # 用户自定义 ID（字符串），在 edges 中引用
      type: start

    - id: kb
      type: knowledge_tool
      title: "知识库检索"
      knowledge_ids: [10001]          # 示例 ID；使用时替换为当前环境的知识库 ID
      # 或者直接提供 JSON 字符串：
      # knowledge_ids_json: "[{\"value\":10001,\"label\":\"Example\",\"list\":[]}]"

    - id: llm1
      type: llm
      title: "大模型回答"
      system_prompt: "你是客服助手，参考知识库：{{#kb.text#}}"
      model: doubao-seed-1.6
      memory_enabled: true
      memory_size: 10

    - id: ans
      type: answer
      answer: "{{#llm1.text#}}"

  edges:
    - from: start
      to: kb
    - from: kb
      to: llm1
    - from: llm1
      to: ans

  # 条件分支示例：
  # - from: if_node
  #   from_handle: "true"    # "true" / "false" / 分类 id
  #   to: next_node

支持的 node type：
  start, llm, answer, knowledge_tool, time_tool,
  question_classifier, if_else, code, assigner,
  variable_aggregator, parameter_extractor, http_request,
  wait, rerank, rag_convert, iteration, iteration_start,
  history_query, udesk_ticket, transfer_human, template_transform
"""

import yaml
import json
from typing import Union
from uagent.client import UAgentClient
from uagent import apps as apps_api
from uagent import workflow as wf_api
from uagent import knowledge as kb_api
from uagent import nodes as N

# 每列节点之间的横向间距
_STEP_X = 300
_START_X = 80
_START_Y = 282
_BRANCH_Y_STEP = 200  # 分支节点纵向偏移


class WorkflowBuilder:
    def __init__(self, client: UAgentClient):
        self.client = client
        self._kb_cache: list[dict] = []

    # ── 公共入口 ────────────────────────────────────────────────────────────

    def deploy_from_file(self, path: str, publish: bool = True) -> dict:
        """从 YAML/JSON 文件加载规范并部署。"""
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".json"):
                spec = json.load(f)
            else:
                spec = yaml.safe_load(f)
        return self.deploy(spec, publish=publish)

    def deploy(self, spec: dict, app_id: str = None, publish: bool = True) -> dict:
        """
        根据 spec 创建（或更新）工作流。
        - spec: 工作流规范 dict
        - app_id: 若提供则更新已有应用；否则新建
        - publish: 部署后是否发布
        返回: {"app_id": ..., "title": ..., "published": bool}
        """
        name = spec.get("name", "新工作流")
        desc = spec.get("description", "")

        workflow_uuid = None
        if app_id:
            result = {"app_id": app_id, "title": name}
            current = wf_api.get_design(self.client, app_id)
            workflow_uuid = current.get("data", {}).get("uuid")
            if not workflow_uuid:
                raise ValueError("更新已有应用前未能读取工作流 uuid")
        else:
            resp = apps_api.create_app(self.client, name, desc=desc)
            app_id = resp["data"]["app_id"]
            result = {"app_id": app_id, "title": name}

        nodes_raw, edges_raw = self._build_graph(spec)
        wf_api.save_design(
            self.client,
            app_id,
            nodes_raw,
            edges_raw,
            uuid=workflow_uuid,
        )

        if publish:
            wf_api.publish(self.client, app_id)
            result["published"] = True
        else:
            result["published"] = False

        return result

    def update(self, app_id: str, spec: dict, publish: bool = False) -> dict:
        """替换已有应用的工作流。"""
        return self.deploy(spec, app_id=app_id, publish=publish)

    # ── 图构建 ───────────────────────────────────────────────────────────────

    def _build_graph(self, spec: dict) -> tuple[list, list]:
        node_specs = spec.get("nodes", [])
        edge_specs = spec.get("edges", [])

        # 第一遍：分配位置（拓扑排序 → 从左到右）
        positions = self._auto_layout(node_specs, edge_specs)

        # 构建 id → node_dict 映射
        id_map: dict[str, dict] = {}
        for ns in node_specs:
            nid = ns["id"]
            x, y = positions.get(nid, (_START_X, _START_Y))
            x = ns.get("x", x)
            y = ns.get("y", y)
            node_dict = self._build_node(ns, nid, x, y)
            id_map[nid] = node_dict

        # 迭代器内部节点使用相对坐标，并标记 parentId / iteration_id。
        # iteration_start 已由专用工厂完成标记，这里补齐绝对坐标。
        for ns in node_specs:
            iter_nid = ns.get("iteration_id")
            if not iter_nid:
                continue
            if iter_nid not in id_map:
                raise ValueError(f"迭代器内部节点 {ns['id']} 引用了未定义的 iteration_id: {iter_nid}")
            iter_pos = id_map[iter_nid].get("position", {"x": 0, "y": 0})
            if ns["type"] == "iteration_start":
                rel_pos = id_map[ns["id"]].get("position", {"x": 60, "y": 195.5})
                id_map[ns["id"]]["positionAbsolute"] = {
                    "x": iter_pos.get("x", 0) + rel_pos.get("x", 0),
                    "y": iter_pos.get("y", 0) + rel_pos.get("y", 0),
                }
                continue
            N.mark_in_iteration(
                id_map[ns["id"]],
                iter_nid=iter_nid,
                rel_x=ns.get("rel_x", 120),
                rel_y=ns.get("rel_y", 160),
                iter_abs_x=iter_pos.get("x", 0),
                iter_abs_y=iter_pos.get("y", 0),
            )

        nodes_list = list(id_map.values())

        # 构建 edges
        # 收集各节点类型用于 sourceType/targetType
        type_map = {nid: node["data"]["type"] for nid, node in id_map.items()}
        spec_map = {ns["id"]: ns for ns in node_specs}
        edges_list = []
        for es in edge_specs:
            src = es["from"]
            tgt = es["to"]
            handle = es.get("from_handle", "source")
            iteration_id = es.get("iteration_id")
            if iteration_id is None:
                src_iter = spec_map.get(src, {}).get("iteration_id")
                tgt_iter = spec_map.get(tgt, {}).get("iteration_id")
                if src_iter and src_iter == tgt_iter:
                    iteration_id = src_iter

            if iteration_id:
                if handle != "source":
                    raise ValueError("迭代器内部边目前只支持 from_handle='source'")
                edge = N.make_iter_edge(
                    source=src,
                    target=tgt,
                    iter_nid=iteration_id,
                    source_type=type_map.get(src, ""),
                    target_type=type_map.get(tgt, ""),
                )
            else:
                edge = N.make_edge(
                    source=src,
                    target=tgt,
                    source_handle=handle,
                    source_type=type_map.get(src, ""),
                    target_type=type_map.get(tgt, ""),
                )
            edges_list.append(edge)

        return nodes_list, edges_list

    def _build_node(self, ns: dict, nid: str, x: float, y: float) -> dict:
        t = ns["type"]

        if t == "start":
            return N.make_start(nid=nid, x=x, y=y)

        if t == "llm":
            return N.make_llm(
                nid=nid,
                title=ns.get("title", "大模型"),
                system_prompt=ns.get("system_prompt", ""),
                model_name=ns.get("model", "doubao-seed-1.6"),
                model_provider=ns.get("model_provider", "langgenius/openai_api_compatible/openai_api_compatible"),
                temperature=ns.get("temperature", 0.7),
                memory_enabled=ns.get("memory_enabled", True),
                memory_size=ns.get("memory_size", 10),
                vision_enabled=ns.get("vision_enabled", False),
                context_enabled=ns.get("context_enabled", False),
                context_variable_selector=ns.get("context_from"),
                enable_thinking=ns.get("enable_thinking"),
                query_prompt_template=ns.get("query_prompt_template", "{{#sys.query#}}"),
                x=x, y=y,
            )

        if t == "answer":
            return N.make_answer(
                nid=nid,
                title=ns.get("title", "直接回答"),
                answer=ns.get("answer", ""),
                x=x, y=y,
            )

        if t == "knowledge_tool":
            kb_json = ns.get("knowledge_ids_json")
            if kb_json is None:
                ids = ns.get("knowledge_ids", [])
                if ids:
                    kb_json = kb_api.build_aggregation_ids_json_from_ids(self.client, ids)
                else:
                    kb_json = "[]"
            q_sel = ns.get("query_from", ["sys", "query"])
            return N.make_knowledge_tool(
                nid=nid,
                title=ns.get("title", "知识库检索"),
                knowledge_ids_json=kb_json,
                query_selector=q_sel,
                top_k=str(ns.get("top_k", 6)),
                ext_aggregation_ids=ns.get("ext_aggregation_ids", ""),
                catalog_ids=ns.get("catalog_ids"),
                ext_catalog_ids=ns.get("ext_catalog_ids"),
                data_types=ns.get("data_types"),
                ext_data_types=ns.get("ext_data_types"),
                meta_filter=ns.get("meta_filter"),
                channel_id=ns.get("channel_id"),
                weight=str(ns.get("weight", "0.7")),
                weight_ratio=str(ns.get("weight_ratio", "0.3")),
                weighted=ns.get("weighted", False),
                mmr=ns.get("mmr", False),
                mmr_filter_k=ns.get("mmr_filter_k", 100),
                mmr_lambda=str(ns.get("mmr_lambda", "0.8")),
                filter_rule=ns.get("filter_rule", ""),
                x=x, y=y,
            )

        if t == "time_tool":
            return N.make_time_tool(
                nid=nid,
                title=ns.get("title", "获取当前时间"),
                fmt=ns.get("format", "%Y-%m-%d %H:%M:%S"),
                timezone=ns.get("timezone", "Asia/Shanghai"),
                x=x, y=y,
            )

        if t == "question_classifier":
            return N.make_question_classifier(
                nid=nid,
                title=ns.get("title", "问题分类"),
                classes=ns.get("classes"),
                instruction=ns.get("instruction", ""),
                model_name=ns.get("model", "doubao-seed-1.6"),
                x=x, y=y,
            )

        if t == "if_else":
            return N.make_if_else(
                nid=nid,
                title=ns.get("title", "条件分支"),
                conditions=ns.get("conditions"),
                logical_operator=ns.get("logical_operator", "and"),
                cases=ns.get("cases"),
                x=x, y=y,
            )

        if t == "code":
            return N.make_code(
                nid=nid,
                title=ns.get("title", "代码执行"),
                code=ns.get("code", "def main(arg1: str) -> dict:\n    return {'result': arg1}\n"),
                language=ns.get("language", "python3"),
                outputs=ns.get("outputs"),
                variables=ns.get("variables"),
                error_strategy=ns.get("error_strategy"),
                x=x, y=y,
            )

        if t == "assigner":
            return N.make_assigner(
                nid=nid,
                title=ns.get("title", "变量赋值"),
                items=ns.get("items"),
                x=x, y=y,
            )

        if t == "variable_aggregator":
            return N.make_variable_aggregator(
                nid=nid,
                title=ns.get("title", "变量聚合"),
                variables=ns.get("variables"),
                output_type=ns.get("output_type", "string"),
                x=x, y=y,
            )

        if t == "parameter_extractor":
            return N.make_parameter_extractor(
                nid=nid,
                title=ns.get("title", "参数提取"),
                instruction=ns.get("instruction", ""),
                parameters=ns.get("parameters"),
                query_selector=ns.get("query_from", ["sys", "query"]),
                model_name=ns.get("model", "doubao-seed-1.6"),
                x=x, y=y,
            )

        if t == "http_request":
            return N.make_http_request(
                nid=nid,
                title=ns.get("title", "HTTP请求"),
                method=ns.get("method", "post"),
                url=ns.get("url", ""),
                headers=ns.get("headers", "Content-Type:application/json"),
                body_value=ns.get("body", "{}"),
                x=x, y=y,
            )

        if t == "wait":
            return N.make_wait(
                nid=nid,
                title=ns.get("title", "等待"),
                wait_time=ns.get("wait_time", 1),
                x=x, y=y,
            )

        if t == "rerank":
            return N.make_rerank(
                nid=nid,
                title=ns.get("title", "Rerank精排"),
                kb_node_id=ns.get("input_node"),
                kb_output_field=ns.get("input_field", "text"),
                query_selector=ns.get("query_from", ["sys", "query"]),
                top_k=ns.get("top_k", 10),
                mmr_lambda=str(ns.get("mmr_lambda", "0.6")),
                rerank_type=ns.get("rerank_type", "bge"),
                x=x, y=y,
            )

        if t == "rag_convert":
            return N.make_rag_convert(
                nid=nid,
                title=ns.get("title", "分片截取转换"),
                kb_node_id=ns.get("input_node"),
                kb_output_field=ns.get("input_field", "text"),
                limit_token=ns.get("limit_token", 15000),
                docs_length=ns.get("docs_length", 10),
                pattern=ns.get(
                    "pattern",
                    "---\\n Source:{title} \\n FileUrl:{file_url} \\n Passage: {doc_content} \\n ---",
                ),
                x=x, y=y,
            )

        if t == "iteration":
            return N.make_iteration(
                nid=nid,
                title=ns.get("title", "迭代器"),
                iterator_selector=ns.get("iterator_from"),
                output_selector=ns.get("output_from"),
                output_type=ns.get("output_type", "array[string]"),
                is_parallel=ns.get("is_parallel", True),
                parallel_nums=ns.get("parallel_nums", 10),
                error_handle_mode=ns.get("error_handle_mode", "terminated"),
                height=ns.get("height", 450),
                width=ns.get("width", 480),
                x=x, y=y,
            )

        if t == "iteration_start":
            iter_nid = ns.get("iteration_id")
            if not iter_nid:
                raise ValueError(f"迭代起始节点 {nid} 缺少 iteration_id")
            node = N.make_iteration_start(
                iter_nid=iter_nid,
                rel_x=ns.get("rel_x", 60),
                rel_y=ns.get("rel_y", 195.5),
                iter_abs_x=ns.get("iter_abs_x", 0),
                iter_abs_y=ns.get("iter_abs_y", 0),
            )
            if node["id"] != nid:
                raise ValueError(f"迭代起始节点 id 必须为 {iter_nid}start，当前为 {nid}")
            return node

        if t == "history_query":
            return N.make_history_query(
                nid=nid,
                title=ns.get("title", "历史消息"),
                conversation_id=ns.get("conversation_id", "{{#sys.conversation_id#}}"),
                query=ns.get("query", ""),
                memory_size=ns.get("memory_size", 100),
                pattern=ns.get("pattern", "Human:{query} \\n AI: {answer} \\n"),
                x=x, y=y,
            )

        if t == "udesk_ticket":
            return N.make_udesk_ticket(
                nid=nid,
                title=ns.get("title", "创建工单"),
                config_identification=ns.get("config_identification", ""),
                template_id=str(ns.get("template_id", "")),
                subject=ns.get("subject", ""),
                content=ns.get("content", ""),
                ticket_field=ns.get("ticket_field", "{}"),
                search_type=ns.get("search_type", ""),
                type_content=ns.get("type_content", ""),
                call_id=ns.get("call_id"),
                call_type=ns.get("call_type"),
                x=x, y=y,
            )

        if t == "transfer_human":
            return N.make_transfer_human(
                nid=nid,
                title=ns.get("title", "转人工"),
                agent_response=ns.get("agent_response", "{{#sys.query#}}"),
                custom_prompt=ns.get("custom_prompt", "{{#sys.query#}}"),
                is_transfer_human=ns.get("is_transfer_human", "true"),
                is_use_system_prompt=ns.get("is_use_system_prompt", "true"),
                x=x, y=y,
            )

        if t == "template_transform":
            return N.make_template_transform(
                nid=nid,
                title=ns.get("title", "模板转换"),
                template=ns.get("template", "{{ arg1 }}"),
                variables=ns.get("variables"),
                x=x, y=y,
            )

        raise ValueError(f"未知节点类型: {t}")

    # ── 自动布局（简单左→右拓扑排序）───────────────────────────────────────

    def _auto_layout(self, node_specs: list, edge_specs: list) -> dict[str, tuple]:
        """
        返回 {node_id: (x, y)} 字典。
        采用 BFS 拓扑排序：每一层的节点纵向均匀分布，横向递增。
        """
        from collections import deque, defaultdict

        ids = [ns["id"] for ns in node_specs]
        # 出边 adjacency
        out_edges: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {i: 0 for i in ids}

        for es in edge_specs:
            src, tgt = es["from"], es["to"]
            out_edges[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

        # BFS
        queue = deque([i for i in ids if in_degree.get(i, 0) == 0])
        layers: list[list[str]] = []
        visited = set()

        while queue:
            layer_size = len(queue)
            layer = []
            for _ in range(layer_size):
                nid = queue.popleft()
                if nid in visited:
                    continue
                visited.add(nid)
                layer.append(nid)
                for tgt in out_edges[nid]:
                    in_degree[tgt] -= 1
                    if in_degree[tgt] == 0:
                        queue.append(tgt)
            if layer:
                layers.append(layer)

        # 未访问节点追加到末尾
        for nid in ids:
            if nid not in visited:
                layers.append([nid])

        positions: dict[str, tuple] = {}
        for col, layer in enumerate(layers):
            x = _START_X + col * _STEP_X
            total = len(layer)
            for row, nid in enumerate(layer):
                # 垂直居中分布
                y = _START_Y + (row - (total - 1) / 2) * _BRANCH_Y_STEP
                positions[nid] = (x, y)

        return positions
