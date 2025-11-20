"""
LoRA Comparison Script for Stable Diffusion WebUI Forge
Test multiple LoRAs against multiple checkpoint models with their activation triggers
"""

import os
import sys
from copy import copy
from PIL import Image, ImageDraw, ImageFont

import gradio as gr
import modules.scripts as scripts
from modules import sd_models, processing, images, shared, errors
from modules.processing import process_images, Processed
from modules.shared import opts, state
from modules.images import get_font
from modules.ui_components import ToolButton

# Import lora networks if available
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'extensions-builtin', 'sd_forge_lora'))
    import networks
    LORA_AVAILABLE = True
except:
    LORA_AVAILABLE = False
    print("LoRA Comparison: Could not import LoRA networks module")


def add_lora_banner(image, lora_name, model_name, position="bottom", font_size=None, padding=10):
    """Add banner with LoRA and model name to image"""
    img = image.copy()
    draw = ImageDraw.Draw(img, 'RGBA')

    if font_size is None:
        font_size = max(12, min(32, img.width // 40))

    font = get_font(font_size)

    # Create text with both LoRA and model name
    banner_text = f"{lora_name} @ {model_name}"

    bbox = draw.textbbox((0, 0), banner_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    banner_height = text_height + (padding * 2)
    banner_width = img.width

    if position == "top":
        banner_y = 0
        text_y = padding
    else:
        banner_y = img.height - banner_height
        text_y = banner_y + padding

    # Draw semi-transparent background
    draw.rectangle(
        [(0, banner_y), (banner_width, banner_y + banner_height)],
        fill=(0, 0, 0, 200)
    )

    text_x = (banner_width - text_width) // 2
    draw.text((text_x, text_y), banner_text, font=font, fill=(255, 255, 255, 255))

    return img


class Script(scripts.Script):
    def title(self):
        return "LoRA Comparison"

    def ui(self, is_img2img):
        if not LORA_AVAILABLE:
            gr.HTML("<p style='color: red;'><b>LoRA module not available.</b> This feature requires the LoRA extension to be loaded.</p>")
            return []

        with gr.Row():
            gr.HTML("""
                <p><b>LoRA Comparison</b> - Test multiple LoRAs against multiple checkpoint models</p>
                <p>Each LoRA will be tested with its activation triggers (if defined) against all selected models.</p>
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    gr.HTML("<h4>Select LoRAs</h4>")

                    lora_filter = gr.Textbox(
                        label="Filter LoRAs",
                        placeholder="Enter text to filter LoRA list",
                    elem_id="lora_comparison_filter"
                )

                lora_checkboxes = gr.CheckboxGroup(
                    label="Select LoRAs to Test",
                    choices=self.get_lora_list(),
                    value=[],
                    elem_id="lora_comparison_loras",
                    interactive=True
                )

                with gr.Row():
                    select_all_loras_btn = gr.Button("Select All", size="sm")
                    deselect_all_loras_btn = gr.Button("Deselect All", size="sm")
                    refresh_loras_btn = ToolButton(value="\U0001f504", elem_id="lora_comparison_refresh_loras")

                use_triggers = gr.Checkbox(
                    label="Use activation triggers from LoRA metadata",
                    value=True,
                    elem_id="lora_comparison_use_triggers"
                )
                gr.HTML("<p><small>If enabled, will automatically add activation text from LoRA metadata to prompts</small></p>")

            with gr.Column(scale=2):
                gr.HTML("<h4>Select Checkpoint Models</h4>")

                model_filter = gr.Textbox(
                    label="Filter Models",
                    placeholder="Enter text to filter model list",
                    elem_id="lora_comparison_model_filter"
                )

                model_checkboxes = gr.CheckboxGroup(
                    label="Select Models",
                    choices=sd_models.checkpoint_tiles(use_short=False),
                    value=[],
                    elem_id="lora_comparison_models",
                    interactive=True
                )

                with gr.Row():
                    select_all_models_btn = gr.Button("Select All", size="sm")
                    deselect_all_models_btn = gr.Button("Deselect All", size="sm")
                    refresh_models_btn = ToolButton(value="\U0001f504", elem_id="lora_comparison_refresh_models")

        with gr.Row():
            with gr.Column():
                lora_weight = gr.Slider(
                    label="LoRA Weight",
                    minimum=0.0,
                    maximum=2.0,
                    value=1.0,
                    step=0.05,
                    elem_id="lora_comparison_weight"
                )

                seed_mode = gr.Radio(
                    label="Seed Mode",
                    choices=["Use same seed for all", "Random seed for each"],
                    value="Use same seed for all",
                    elem_id="lora_comparison_seed_mode"
                )

            with gr.Column():
                banner_enabled = gr.Checkbox(label="Add LoRA/Model banner", value=True)
                banner_position = gr.Radio(
                    label="Banner Position",
                    choices=["top", "bottom"],
                    value="bottom",
                    elem_id="lora_comparison_banner_pos"
                )

        with gr.Row():
            create_grid = gr.Checkbox(
                label="Create comparison grid",
                value=True,
                elem_id="lora_comparison_grid"
            )

        # Event handlers
        def update_lora_list():
            return gr.update(choices=self.get_lora_list())

        def update_model_list():
            return gr.update(choices=sd_models.checkpoint_tiles(use_short=False))

        def select_all_loras():
            return gr.update(value=self.get_lora_list())

        def deselect_all_loras():
            return gr.update(value=[])

        def select_all_models():
            return gr.update(value=sd_models.checkpoint_tiles(use_short=False))

        def deselect_all_models():
            return gr.update(value=[])

        def filter_loras(filter_text):
            if not filter_text:
                return gr.update(choices=self.get_lora_list())
            all_loras = self.get_lora_list()
            filtered = [l for l in all_loras if filter_text.lower() in l.lower()]
            return gr.update(choices=filtered)

        def filter_models(filter_text):
            if not filter_text:
                return gr.update(choices=sd_models.checkpoint_tiles(use_short=False))
            all_models = sd_models.checkpoint_tiles(use_short=False)
            filtered = [m for m in all_models if filter_text.lower() in m.lower()]
            return gr.update(choices=filtered)

        # Wire up events
        refresh_loras_btn.click(fn=update_lora_list, outputs=[lora_checkboxes])
        refresh_models_btn.click(fn=update_model_list, outputs=[model_checkboxes])
        select_all_loras_btn.click(fn=select_all_loras, outputs=[lora_checkboxes])
        deselect_all_loras_btn.click(fn=deselect_all_loras, outputs=[lora_checkboxes])
        select_all_models_btn.click(fn=select_all_models, outputs=[model_checkboxes])
        deselect_all_models_btn.click(fn=deselect_all_models, outputs=[model_checkboxes])
        lora_filter.change(fn=filter_loras, inputs=[lora_filter], outputs=[lora_checkboxes])
        model_filter.change(fn=filter_models, inputs=[model_filter], outputs=[model_checkboxes])

        return [
            lora_checkboxes, model_checkboxes, lora_weight,
            use_triggers, seed_mode, banner_enabled, banner_position, create_grid
        ]

    def get_lora_list(self):
        """Get list of available LoRAs"""
        if not LORA_AVAILABLE:
            return []
        try:
            networks.list_available_networks()
            return list(networks.available_networks.keys())
        except Exception as e:
            print(f"LoRA Comparison: Error getting LoRA list: {e}")
            return []

    def get_lora_triggers(self, lora_name):
        """Get activation triggers for a LoRA from its metadata"""
        if not LORA_AVAILABLE:
            return ""
        try:
            lora_on_disk = networks.available_networks.get(lora_name)
            if lora_on_disk and hasattr(lora_on_disk, 'metadata'):
                # Try to get activation text from metadata
                if lora_on_disk.metadata:
                    activation_text = lora_on_disk.metadata.get("ss_tag_frequency", "")
                    if not activation_text:
                        activation_text = lora_on_disk.metadata.get("activation_text", "")
                    if activation_text:
                        return str(activation_text)
        except Exception as e:
            print(f"LoRA Comparison: Could not get triggers for {lora_name}: {e}")
        return ""

    def run(self, p, lora_checkboxes, model_checkboxes, lora_weight,
            use_triggers, seed_mode, banner_enabled, banner_position, create_grid):

        if not LORA_AVAILABLE:
            print("LoRA Comparison: LoRA module not available")
            return None

        if not lora_checkboxes or not model_checkboxes:
            print("LoRA Comparison: No LoRAs or models selected")
            return None

        # Store original settings
        original_prompt = p.prompt
        original_seed = p.seed

        use_fixed_seed = (seed_mode == "Use same seed for all")
        base_seed = p.seed if use_fixed_seed and p.seed >= 0 else -1

        all_images = []
        all_prompts = []
        all_seeds = []
        all_infotexts = []

        total_iterations = len(lora_checkboxes) * len(model_checkboxes)
        current_iteration = 0

        # Set the job count for progress tracking
        state.job_count = total_iterations

        print(f"LoRA Comparison: Testing {len(lora_checkboxes)} LoRAs against {len(model_checkboxes)} models ({total_iterations} total images)")

        try:
            # Loop through each LoRA
            for lora_idx, lora_name in enumerate(lora_checkboxes):
                if state.interrupted:
                    break

                # Get activation triggers for this LoRA
                triggers = ""
                if use_triggers:
                    triggers = self.get_lora_triggers(lora_name)
                    if triggers:
                        print(f"  Using triggers: {triggers[:50]}...")

                # Build prompt with LoRA and triggers
                lora_alias = lora_name
                lora_prompt = f"<lora:{lora_alias}:{lora_weight}>"
                if triggers:
                    lora_prompt += f" {triggers}"

                # Loop through each model
                for model_idx, model_name in enumerate(model_checkboxes):
                    if state.interrupted:
                        break

                    current_iteration += 1
                    state.job_no = current_iteration
                    state.job = f"LoRA {lora_idx + 1}/{len(lora_checkboxes)}, Model {model_idx + 1}/{len(model_checkboxes)}"

                    print(f"  [{current_iteration}/{total_iterations}] Testing {lora_name} with {model_name}")

                    # Get checkpoint info
                    checkpoint_info = sd_models.get_closet_checkpoint_match(model_name)
                    if checkpoint_info is None:
                        print(f"    Could not find checkpoint: {model_name}, skipping...")
                        continue

                    # Create processing copy
                    p_copy = copy(p)

                    # Set prompt with LoRA
                    p_copy.prompt = f"{original_prompt}, {lora_prompt}" if original_prompt else lora_prompt

                    # Override model
                    if not hasattr(p_copy, 'override_settings') or p_copy.override_settings is None:
                        p_copy.override_settings = {}
                    p_copy.override_settings['sd_model_checkpoint'] = checkpoint_info.name

                    # Set seed
                    if use_fixed_seed:
                        p_copy.seed = base_seed
                    else:
                        p_copy.seed = -1

                    try:
                        processed = process_images(p_copy)

                        for img_idx, img in enumerate(processed.images):
                            if banner_enabled and isinstance(img, Image.Image):
                                lora_display = lora_name.split('.')[0]  # Remove extension
                                model_display = checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name
                                img = add_lora_banner(img, lora_display, model_display, position=banner_position)

                            all_images.append(img)
                            all_prompts.append(p_copy.prompt)
                            all_seeds.append(processed.seed if hasattr(processed, 'seed') else p_copy.seed)

                            infotext = f"LoRA: {lora_name} (weight: {lora_weight})\n"
                            infotext += f"Model: {checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name}\n"
                            if hasattr(processed, 'infotexts') and img_idx < len(processed.infotexts):
                                infotext += processed.infotexts[img_idx]
                            all_infotexts.append(infotext)

                    except Exception as e:
                        print(f"    Error: {e}")
                        errors.report(f"LoRA Comparison: Failed with {lora_name} @ {model_name}", exc_info=True)
                        continue

        finally:
            print(f"\nLoRA Comparison: Complete")

        # Create grid if requested
        if create_grid and len(all_images) > 1:
            grid = images.image_grid(all_images, rows=None)
            all_images.insert(0, grid)
            all_prompts.insert(0, "LoRA Comparison Grid")
            all_seeds.insert(0, -1)
            all_infotexts.insert(0, f"LoRA Comparison Grid: {len(lora_checkboxes)} LoRAs x {len(model_checkboxes)} models")

        result = Processed(
            p,
            images_list=all_images,
            seed=all_seeds[0] if all_seeds else -1,
            info=f"LoRA Comparison: {len(lora_checkboxes)} LoRAs, {len(model_checkboxes)} models, {len(all_images)} images",
            infotexts=all_infotexts,
            all_prompts=all_prompts,
            all_seeds=all_seeds,
        )

        print(f"Generated {len(all_images)} images")
        return result
