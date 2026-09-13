from comfy_api.latest import io

from .blue_core import BLUE_ENTITY_PACK, BLUE_FIELD, BLUE_RELATION_RESULT, clamp, collect_entities, normalize_entity_pack, pack_score, stable_id


class BlueComputationNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueComputationNode",
            display_name="计算",
            category="Blue/Compute",
            inputs=[
                BLUE_ENTITY_PACK.Input("JSON", optional=True),
                io.Combo.Input("field_type", options=["wind_field", "magnetic_field", "thermal_field", "air_field", "light_field", "force_field", "custom_field"]),
            ],
            outputs=[
                BLUE_RELATION_RESULT.Output(),
            ],
        )

    @classmethod
    def execute(
        cls,
        JSON=None,
        field_type="wind_field",
    ) -> io.NodeOutput:
        pack = normalize_entity_pack(JSON)
        entities = collect_entities(pack) if pack else []
        errors = []
        if not pack:
            errors.append({"missing": "JSON", "message": "缺少实体包"})

        entity_score = pack_score(entities)
        field_intensity = clamp(0.2 + 0.6 * entity_score)
        if field_type == "wind_field":
            field_data = {
                "kind": "BLUE_FIELD",
                "field_type": field_type,
                "data": {
                    "speed": round(1.0 + 4.0 * field_intensity, 3),
                    "coverage": round(clamp(0.2 + entity_score * 0.6), 3),
                    "intensity": round(field_intensity, 3),
                },
            }
        else:
            field_data = {
                "kind": "BLUE_FIELD",
                "field_type": field_type,
                "data": {"intensity": round(field_intensity, 3)},
            }

        relation_result = {
            "id": stable_id("relation", {"pack": pack.get("id") if pack else None, "field_type": field_type}),
            "kind": "BLUE_RELATION_RESULT",
            "payload": {
                "entities": [e.get("id") for e in entities],
                "relations": [
                    {
                        "target": pack.get("id") if pack else "missing",
                        "impact_score": round(entity_score, 3),
                        "field_type": field_type,
                    }
                ],
                "fields": {field_type: field_data.get("data", {})},
            },
            "meta": {"errors": errors},
        }
        if errors:
            relation_result["meta"]["errors"] = errors
        return io.NodeOutput(relation_result, field_data)
