import unittest

from builder.builder import WorkflowBuilder
from uagent import nodes as N


class NodeFactoryTests(unittest.TestCase):
    def test_llm_supports_model_controls(self):
        node = N.make_llm(
            nid="llm",
            memory_enabled=False,
            memory_size=50,
            enable_thinking=False,
            query_prompt_template="{{#rewrite.complete#}}",
        )

        self.assertEqual(
            node["data"]["model"]["completion_params"],
            {"temperature": 0.7, "enable_thinking": False},
        )
        self.assertEqual(
            node["data"]["memory"]["query_prompt_template"],
            "{{#rewrite.complete#}}",
        )

        no_memory = N.make_llm(nid="confirm", memory_enabled=None)
        self.assertIsNone(no_memory["data"]["memory"])

    def test_code_supports_fail_branch_strategy(self):
        node = N.make_code(nid="parse", error_strategy="fail-branch")
        self.assertEqual(node["data"]["error_strategy"], "fail-branch")

    def test_knowledge_tool_supports_dynamic_dataset_and_retrieval_controls(self):
        node = N.make_knowledge_tool(
            nid="hybrid",
            knowledge_ids_json='[{"value":10001,"label":"Example KB"}]',
            query_selector=["iterator", "item"],
            top_k="20",
            ext_aggregation_ids="{{#conversation.dataset_id#}}",
            ext_data_types="",
            meta_filter="",
            channel_id="",
            weight_ratio="0.1",
            mmr_lambda="0.6",
        )

        data = node["data"]
        self.assertEqual(
            data["tool_parameters"]["query"]["value"],
            "{{#iterator.item#}}",
        )
        self.assertEqual(
            data["tool_parameters"]["ext_aggregation_ids"]["value"],
            "{{#conversation.dataset_id#}}",
        )
        self.assertEqual(data["tool_configurations"]["top_k"]["value"], "20")
        self.assertEqual(data["tool_configurations"]["weight_ratio"]["value"], "0.1")
        self.assertEqual(data["tool_configurations"]["mmr_lamda"]["value"], "0.6")

    def test_variable_aggregator_matches_platform_shape(self):
        variables = [["business", "text"], ["chitchat", "text"]]
        node = N.make_variable_aggregator(
            nid="merge",
            variables=variables,
            output_type="string",
        )

        self.assertEqual(node["data"]["type"], "variable-aggregator")
        self.assertEqual(node["data"]["variables"], variables)
        self.assertEqual(node["data"]["output_type"], "string")

    def test_history_query_matches_platform_tool(self):
        node = N.make_history_query(
            nid="history",
            memory_size=100,
            pattern="Human:{query} \\n AI: {answer} \\n",
        )

        data = node["data"]
        self.assertEqual(data["provider_id"], "udesk_rag")
        self.assertEqual(data["tool_name"], "udesk_history_query")
        self.assertEqual(
            data["tool_parameters"]["conversation_id"]["value"],
            "{{#sys.conversation_id#}}",
        )
        self.assertEqual(data["tool_configurations"]["memory_size"]["value"], "100")

    def test_ticket_supports_conversation_call_context(self):
        node = N.make_udesk_ticket(
            nid="ticket",
            call_id="{{#sys.conversation_id#}}",
            call_type="",
        )

        parameters = node["data"]["tool_parameters"]
        self.assertEqual(parameters["call_id"]["value"], "{{#sys.conversation_id#}}")
        self.assertEqual(parameters["call_type"]["value"], "")


class BuilderCoverageTests(unittest.TestCase):
    def test_builder_covers_node_families_and_iteration_metadata(self):
        builder = WorkflowBuilder(client=object())
        spec = {
            "name": "Node factory coverage",
            "nodes": [
                {"id": "start", "type": "start"},
                {
                    "id": "route",
                    "type": "if_else",
                    "cases": [
                        {
                            "conditions": [
                                {
                                    "variable_selector": ["parse", "category"],
                                    "comparison_operator": "contains",
                                    "value": "Business",
                                }
                            ]
                        },
                        {
                            "case_id": "other",
                            "conditions": [
                                {
                                    "variable_selector": ["parse", "category"],
                                    "comparison_operator": "contains",
                                    "value": "Other",
                                }
                            ],
                        },
                    ],
                },
                {
                    "id": "save_dataset",
                    "type": "assigner",
                    "items": [],
                },
                {
                    "id": "iter",
                    "type": "iteration",
                    "iterator_from": ["parse", "question_all"],
                    "output_from": ["hybrid", "text"],
                    "is_parallel": False,
                },
                {
                    "id": "iterstart",
                    "type": "iteration_start",
                    "iteration_id": "iter",
                },
                {
                    "id": "hybrid",
                    "type": "knowledge_tool",
                    "iteration_id": "iter",
                    "rel_x": 120,
                    "rel_y": 160,
                    "knowledge_ids_json": "[]",
                    "query_from": ["iter", "item"],
                    "ext_aggregation_ids": "{{#conversation.dataset_id#}}",
                },
                {
                    "id": "merge",
                    "type": "variable_aggregator",
                    "variables": [["business", "text"], ["chitchat", "text"]],
                },
                {
                    "id": "rerank",
                    "type": "rerank",
                    "input_node": "aggregate_code",
                    "input_field": "aggregation_data",
                    "query_from": ["parse", "questions_complete"],
                },
                {
                    "id": "chunk",
                    "type": "rag_convert",
                    "input_node": "rerank",
                    "limit_token": 20000,
                },
                {
                    "id": "business",
                    "type": "llm",
                    "context_from": ["chunk", "text"],
                    "memory_enabled": False,
                    "enable_thinking": False,
                },
                {
                    "id": "parse",
                    "type": "code",
                    "error_strategy": "fail-branch",
                },
                {
                    "id": "aggregate_code",
                    "type": "code",
                },
                {
                    "id": "chitchat",
                    "type": "llm",
                },
                {
                    "id": "history",
                    "type": "history_query",
                },
                {
                    "id": "ticket",
                    "type": "udesk_ticket",
                    "call_id": "{{#sys.conversation_id#}}",
                },
                {
                    "id": "answer",
                    "type": "answer",
                    "answer": "{{#business.text#}}",
                },
            ],
            "edges": [
                {"from": "start", "to": "parse"},
                {"from": "parse", "to": "route"},
                {"from": "route", "from_handle": "true", "to": "save_dataset"},
                {"from": "save_dataset", "to": "iter"},
                {"from": "iterstart", "to": "hybrid"},
                {"from": "iter", "to": "aggregate_code"},
                {"from": "aggregate_code", "to": "rerank"},
                {"from": "rerank", "to": "chunk"},
                {"from": "chunk", "to": "business"},
                {"from": "business", "to": "merge"},
                {"from": "chitchat", "to": "merge"},
                {"from": "merge", "to": "history"},
                {"from": "history", "to": "ticket"},
                {"from": "business", "to": "answer"},
            ],
        }

        nodes, edges = builder._build_graph(spec)
        node_map = {node["id"]: node for node in nodes}

        self.assertEqual(node_map["merge"]["data"]["type"], "variable-aggregator")
        self.assertEqual(node_map["history"]["data"]["tool_name"], "udesk_history_query")
        self.assertEqual(node_map["ticket"]["data"]["tool_name"], "udesk_ticket_create_v2")
        self.assertEqual(node_map["hybrid"]["parentId"], "iter")
        self.assertTrue(node_map["hybrid"]["data"]["isInIteration"])
        self.assertEqual(node_map["iterstart"]["parentId"], "iter")

        internal_edge = next(edge for edge in edges if edge["source"] == "iterstart")
        self.assertTrue(internal_edge["data"]["isInIteration"])
        self.assertEqual(internal_edge["data"]["iteration_id"], "iter")


if __name__ == "__main__":
    unittest.main()
