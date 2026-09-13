from comfy_api.latest import ComfyExtension, io

from .blue_computation_node import BlueComputationNode
from .blue_entity_node import BlueEntityNode
from .blue_executor_node import BlueExecutorNode
from .blue_entity_pack_node import BlueEntityPackNode
from .blue_entity_instancer_node import BlueEntityInstancerNode
from .blue_field_render_node import BlueFieldRenderNode
from .blue_floorplan_node import BlueFloorplanNode
from .blue_html_output_node import BlueHtmlOutputNode
from . import blue_http_routes  # 注册 /bluenode/live 与 /bluenode/live-data
from .blue_prompt_booster_node import BluePromptBoosterNode
from .blue_rule_node import BlueRuleNode
from .blue_rule_pack_node import BlueRulePackNode
from .blue_world_node import BlueWorldNode
from .blue_simulation_node import BlueSimulationNode

WEB_DIRECTORY = "./web"


class BlueNodeExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            BlueRuleNode,
            BlueRulePackNode,
            BlueExecutorNode,
            BlueEntityNode,
            BlueEntityInstancerNode,
            BlueEntityPackNode,
            BluePromptBoosterNode,
            BlueComputationNode,
            BlueFieldRenderNode,
            BlueFloorplanNode,
            BlueHtmlOutputNode,
            BlueWorldNode,
            BlueSimulationNode,
        ]


async def comfy_entrypoint() -> BlueNodeExtension:
    return BlueNodeExtension()
