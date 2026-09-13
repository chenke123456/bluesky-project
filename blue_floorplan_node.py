import hashlib

from PIL import Image, ImageDraw, ImageFont
from comfy_api.latest import io

from .blue_core import BLUE_ENTITY, BLUE_ENTITY_PACK, collect_entities, entity_position, normalize_entity, normalize_entity_pack, pil_to_tensor, render_text


class BlueFloorplanNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueFloorplanNode",
            display_name="Blue 平面图节点",
            category="Blue/Visualization",
            inputs=[
                BLUE_ENTITY_PACK.Input("entity_pack", optional=True),
                BLUE_ENTITY.Input("entity", optional=True),
                io.Int.Input("size", default=768, min=256, max=2048, step=64),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, entity_pack=None, entity=None, size=768) -> io.NodeOutput:
        entities = []
        pack = normalize_entity_pack(entity_pack)
        if pack:
            entities.extend(collect_entities(pack))
        if entity:
            normalized = normalize_entity(entity)
            if normalized:
                entities.append(normalized)

        canvas = int(size)
        image = Image.new("RGB", (canvas, canvas), (250, 250, 248))
        draw = ImageDraw.Draw(image)

        if not entities:
            render_text(image, "Empty Floorplan", ["No entity data provided"], box=(20, 20), color=(20, 20, 20))
            return io.NodeOutput(pil_to_tensor(image))

        margin = 36
        usable = canvas - margin * 2
        cols = max(1, int((len(entities) ** 0.5) + 0.999))
        rows = max(1, (len(entities) + cols - 1) // cols)
        cell_w = usable / cols
        cell_h = usable / rows

        for idx, ent in enumerate(entities):
            row = idx // cols
            col = idx % cols
            x_pos, y_pos = entity_position(ent)
            left = margin + int((x_pos if x_pos is not None else col / max(1, cols - 1)) * (usable - cell_w))
            top = margin + int((y_pos if y_pos is not None else row / max(1, rows - 1)) * (usable - cell_h))
            right = min(canvas - margin, left + int(cell_w * 0.88))
            bottom = min(canvas - margin, top + int(cell_h * 0.82))
            color_seed = int(hashlib.sha1(ent.get("id", "").encode("utf-8")).hexdigest()[:6], 16)
            color = (
                80 + color_seed % 140,
                90 + (color_seed // 3) % 120,
                110 + (color_seed // 7) % 100,
            )
            draw.rounded_rectangle((left, top, right, bottom), radius=10, outline=(30, 30, 30), fill=color, width=2)
            label = f"{ent.get('entity_type', 'entity')}\n{ent.get('name', '')}"
            draw.text((left + 8, top + 8), label, fill=(15, 15, 15), font=ImageFont.load_default())

        render_text(
            image,
            "Floorplan",
            [f"entity_count={len(entities)}", f"size={canvas}"],
            box=(18, 18),
            color=(20, 20, 20),
        )
        return io.NodeOutput(pil_to_tensor(image))
