from comfy_api.latest import io

from .blue_core import BLUE_RULE, BLUE_RULE_PACK, collect_rules


MAX_RULE_INPUTS = 24


class BlueRulePackNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueRulePackNode",
            display_name="规则包",
            category="Blue/Rules",
            inputs=[BLUE_RULE.Input(f"rule_{index}", optional=True) for index in range(1, MAX_RULE_INPUTS + 1)],
            outputs=[BLUE_RULE_PACK.Output()],
        )

    @classmethod
    def execute(cls, rule_1=None, rule_2=None, rule_3=None, **kwargs) -> io.NodeOutput:
        candidates = [rule_1, rule_2, rule_3]
        candidates.extend(kwargs.get(f"rule_{index}") for index in range(4, MAX_RULE_INPUTS + 1))
        rules = collect_rules(*candidates)

        properties = [rule for rule in rules if isinstance(rule, dict) and rule.get("rule_kind") != "method"]
        methods = [rule for rule in rules if isinstance(rule, dict) and rule.get("rule_kind") == "method"]

        pack = {
            # 新结构：像类一样将属性和方法分组。
            "properties": properties,
            "methods": methods,
            # 兼容现有 World/UI/Simulation 消费逻辑，暂时继续保留扁平 rules。
            "rules": rules,
        }
        return io.NodeOutput(pack)
