from comfy_api.latest import io

from .blue_core import BLUE_ENTITY, BLUE_ENTITY_PACK, collect_entities


MAX_ENTITY_INPUTS = 24


class BlueEntityPackNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        # 后端预留足够的可选输入。前端只显示当前已展开的槽位，并用“+”继续扩展。
        return io.Schema(
            node_id="BlueEntityPackNode",
            display_name="实体包",
            category="Blue/Entities",
            inputs=[
                BLUE_ENTITY.Input(f"entity_{index}", optional=True)
                for index in range(1, MAX_ENTITY_INPUTS + 1)
            ],
            outputs=[
                BLUE_ENTITY_PACK.Output(),
            ],
        )

    @classmethod
    def execute(cls, entity_1=None, entity_2=None, entity_3=None, **kwargs) -> io.NodeOutput:
        candidates = [entity_1, entity_2, entity_3]
        candidates.extend(
            kwargs.get(f"entity_{index}")
            for index in range(4, MAX_ENTITY_INPUTS + 1)
        )

        entities = collect_entities(*candidates)
        pack = {
            "entities": entities,
        }
        # 保持 dict/list 结构；预览节点再负责格式化为中文 JSON 文本。
        return io.NodeOutput(pack)
