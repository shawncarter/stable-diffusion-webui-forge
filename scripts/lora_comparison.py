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


def sanitize_folder_name(name):
    """Sanitize a string to be used as a folder name"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Remove leading/trailing spaces and dots
    name = name.strip('. ')
    # Limit length
    if len(name) > 100:
        name = name[:100]
    return name if name else "untitled"


def add_lora_banner(image, lora_name, model_name, position="bottom", font_size=None, padding=10):
    """Add banner with LoRA and model name to image"""
    img = image.copy()
    original_mode = img.mode
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    draw = ImageDraw.Draw(img)

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

    # Convert back to original mode if needed
    if original_mode != 'RGBA':
        # If converting back to RGB, need to handle alpha channel properly
        if original_mode == 'RGB':
            # Create white background and alpha composite properly
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            composited = Image.alpha_composite(background, img)
            img = composited.convert('RGB')
        else:
            img = img.convert(original_mode)

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

        with gr.Row():
            folder_organization = gr.Radio(
                label="Folder Organization",
                choices=["Flat (all in one folder)", "By LoRA", "By Model", "By LoRA/Model"],
                value="Flat (all in one folder)",
                elem_id="lora_comparison_folder_org"
            )
            gr.HTML("<p><small>Organize saved images into subfolders for easier review</small></p>")

        # Event handlers
        def update_lora_list():
            return gr.update(choices=self.get_lora_list())

        def update_model_list():
            return gr.update(choices=sd_models.checkpoint_tiles(use_short=False))

        def select_all_loras(filter_text):
            """Select all LoRAs (filtered if filter is active)"""
            if filter_text:
                all_loras = self.get_lora_list()
                filtered = [l for l in all_loras if filter_text.lower() in l.lower()]
                return gr.update(value=filtered)
            else:
                return gr.update(value=self.get_lora_list())

        def deselect_all_loras():
            return gr.update(value=[])

        def select_all_models(filter_text):
            """Select all models (filtered if filter is active)"""
            if filter_text:
                all_models = sd_models.checkpoint_tiles(use_short=False)
                filtered = [m for m in all_models if filter_text.lower() in m.lower()]
                return gr.update(value=filtered)
            else:
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
        select_all_loras_btn.click(fn=select_all_loras, inputs=[lora_filter], outputs=[lora_checkboxes])
        deselect_all_loras_btn.click(fn=deselect_all_loras, outputs=[lora_checkboxes])
        select_all_models_btn.click(fn=select_all_models, inputs=[model_filter], outputs=[model_checkboxes])
        deselect_all_models_btn.click(fn=deselect_all_models, outputs=[model_checkboxes])
        lora_filter.change(fn=filter_loras, inputs=[lora_filter], outputs=[lora_checkboxes])
        model_filter.change(fn=filter_models, inputs=[model_filter], outputs=[model_checkboxes])

        return [
            lora_checkboxes, model_checkboxes, lora_weight,
            use_triggers, seed_mode, banner_enabled, banner_position, create_grid,
            folder_organization
        ]

    def get_lora_list(self):
        """Get list of available LoRAs with folder paths"""
        if not LORA_AVAILABLE:
            return []
        try:
            networks.list_available_networks()
            lora_list = []
            lora_dir = shared.cmd_opts.lora_dir

            for name, network_on_disk in networks.available_networks.items():
                # Get relative path from lora_dir
                full_path = network_on_disk.filename
                try:
                    rel_path = os.path.relpath(full_path, lora_dir)
                    # Remove .safetensors or other extensions for cleaner display
                    display_name = os.path.splitext(rel_path)[0]
                    # Normalize path separators for consistency
                    display_name = display_name.replace(os.sep, '/')
                    lora_list.append(display_name)
                except:
                    # Fallback to just the name if relative path fails
                    lora_list.append(name)

            return sorted(lora_list)
        except Exception as e:
            print(f"LoRA Comparison: Error getting LoRA list: {e}")
            return []

    def get_lora_triggers(self, lora_display_name):
        """Get activation triggers for a LoRA from its metadata"""
        if not LORA_AVAILABLE:
            return ""
        try:
            # Extract basename from display name (folder/name format)
            lora_basename = os.path.basename(lora_display_name)
            lora_on_disk = networks.available_networks.get(lora_basename)
            if lora_on_disk and hasattr(lora_on_disk, 'metadata'):
                # Try to get activation text from metadata
                if lora_on_disk.metadata:
                    activation_text = lora_on_disk.metadata.get("ss_tag_frequency", "")
                    if not activation_text:
                        activation_text = lora_on_disk.metadata.get("activation_text", "")
                    if activation_text:
                        return str(activation_text)
        except Exception as e:
            print(f"LoRA Comparison: Could not get triggers for {lora_display_name}: {e}")
        return ""

    def run(self, p, lora_checkboxes, model_checkboxes, lora_weight,
            use_triggers, seed_mode, banner_enabled, banner_position, create_grid,
            folder_organization):

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
        print(f"LoRA Comparison: Loop order - Model outer (load once), LoRA inner (efficient)")

        try:
            # Loop through each model first (more efficient - load model once per model)
            for model_idx, model_name in enumerate(model_checkboxes):
                if state.interrupted:
                    break

                # Get checkpoint info
                checkpoint_info = sd_models.get_closet_checkpoint_match(model_name)
                if checkpoint_info is None:
                    print(f"  Could not find checkpoint: {model_name}, skipping...")
                    continue

                # EXPLICITLY load model once at start of outer loop - not via override_settings
                print(f"\n[Model {model_idx + 1}/{len(model_checkboxes)}] Loading model: {checkpoint_info.short_title}")
                sd_models.reload_model_weights(info=checkpoint_info)
                print(f"  Model loaded successfully")

                # Loop through each LoRA with this model (model stays loaded)
                for lora_idx, lora_display_name in enumerate(lora_checkboxes):
                    if state.interrupted:
                        break

                    current_iteration += 1
                    state.job_no = current_iteration
                    state.job = f"Model {model_idx + 1}/{len(model_checkboxes)}, LoRA {lora_idx + 1}/{len(lora_checkboxes)}"

                    print(f"  [{current_iteration}/{total_iterations}] Testing LoRA: {lora_display_name}")

                    # Extract basename for LoRA loading (networks.available_networks uses basename)
                    lora_basename = os.path.basename(lora_display_name)
                    # Get LoRA name without extension to use as trigger word
                    lora_name_no_ext = os.path.splitext(lora_basename)[0]

                    # Get activation triggers for this LoRA
                    triggers = ""
                    if use_triggers:
                        triggers = self.get_lora_triggers(lora_display_name)
                        if triggers:
                            print(f"    Using triggers: {triggers[:50]}...")

                    # Build prompt with LoRA and triggers (use basename for <lora:...>)
                    # Include LoRA name as trigger word (usually the activation trigger)
                    lora_prompt = f"<lora:{lora_basename}:{lora_weight}> {lora_name_no_ext}"
                    if triggers:
                        lora_prompt += f" {triggers}"

                    # Create processing copy
                    p_copy = copy(p)

                    # Prevent auto-saving during process_images() - we'll save after adding banner
                    p_copy.do_not_save_samples = True

                    # Set prompt with LoRA
                    p_copy.prompt = f"{original_prompt}, {lora_prompt}" if original_prompt else lora_prompt

                    # NO override_settings for model - model is already loaded above
                    # This prevents model from being reloaded on every process_images() call

                    # Set seed
                    if use_fixed_seed:
                        p_copy.seed = base_seed
                    else:
                        p_copy.seed = -1

                    try:
                        processed = process_images(p_copy)

                        for img_idx, img in enumerate(processed.images):
                            if banner_enabled and isinstance(img, Image.Image):
                                # Use display name (already has folder, no extension)
                                lora_display = lora_display_name
                                model_display = checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name
                                img = add_lora_banner(img, lora_display, model_display, position=banner_position)

                            infotext = f"LoRA: {lora_display_name} (weight: {lora_weight})\n"
                            infotext += f"Model: {checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name}\n"
                            if hasattr(processed, 'infotexts') and img_idx < len(processed.infotexts):
                                infotext += processed.infotexts[img_idx]

                            # Save the bannered image to disk (always save comparison results)
                            if opts.samples_save and isinstance(img, Image.Image):
                                # Determine save path based on folder organization
                                save_path = p.outpath_samples
                                use_subfolders = False  # Disable date subfolders when organizing

                                if folder_organization == "By LoRA":
                                    lora_folder = sanitize_folder_name(lora_display_name)
                                    save_path = os.path.join(p.outpath_samples, lora_folder)
                                    use_subfolders = True
                                elif folder_organization == "By Model":
                                    model_folder = sanitize_folder_name(checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name)
                                    save_path = os.path.join(p.outpath_samples, model_folder)
                                    use_subfolders = True
                                elif folder_organization == "By LoRA/Model":
                                    lora_folder = sanitize_folder_name(lora_display_name)
                                    model_folder = sanitize_folder_name(checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name)
                                    save_path = os.path.join(p.outpath_samples, lora_folder, model_folder)
                                    use_subfolders = True

                                images.save_image(
                                    img,
                                    save_path,
                                    "",
                                    processed.seed if hasattr(processed, 'seed') else p_copy.seed,
                                    p_copy.prompt,
                                    opts.samples_format,
                                    info=infotext,
                                    p=p,
                                    save_to_dirs=False if use_subfolders else None  # Disable date folders when using organization
                                )

                            all_images.append(img)
                            all_prompts.append(p_copy.prompt)
                            all_seeds.append(processed.seed if hasattr(processed, 'seed') else p_copy.seed)
                            all_infotexts.append(infotext)

                    except Exception as e:
                        print(f"    Error: {e}")
                        errors.report(f"LoRA Comparison: Failed with {lora_display_name} @ {model_name}", exc_info=True)
                        continue

        finally:
            print(f"\nLoRA Comparison: Complete")

        # Create grid if requested (minimum 4 images for 2x2 grid)
        print(f"LoRA Comparison: Grid creation enabled: {create_grid}, images count: {len(all_images)}")
        if create_grid and len(all_images) >= 4:
            print(f"LoRA Comparison: Creating comparison grid with {len(all_images)} images...")
            try:
                # Grid layout: rows = models, columns = loras
                grid = images.image_grid(all_images, rows=len(model_checkboxes))
                print(f"LoRA Comparison: Grid created ({len(model_checkboxes)} models × {len(lora_checkboxes)} LoRAs), size: {grid.size}, mode: {grid.mode}")

                grid_infotext = f"LoRA Comparison Grid: {len(lora_checkboxes)} LoRAs x {len(model_checkboxes)} models"

                # Save grid to disk if grid saving is enabled
                if opts.grid_save:
                    images.save_image(
                        grid,
                        p.outpath_grids,
                        "lora_comparison_grid",
                        all_seeds[0] if all_seeds else -1,
                        all_prompts[0] if all_prompts else p.prompt,
                        opts.grid_format,
                        info=grid_infotext,
                        p=p,
                        grid=True
                    )
                    print(f"LoRA Comparison: Grid saved to {p.outpath_grids}")

                all_images.insert(0, grid)
                all_prompts.insert(0, "LoRA Comparison Grid")
                all_seeds.insert(0, -1)
                all_infotexts.insert(0, grid_infotext)
                print(f"LoRA Comparison: Grid inserted at position 0, total images now: {len(all_images)}")
            except Exception as e:
                print(f"LoRA Comparison: Error creating grid: {e}")
                errors.report(f"LoRA Comparison: Failed to create grid", exc_info=True)
        elif create_grid and len(all_images) > 1:
            print(f"LoRA Comparison: Skipping grid creation - need at least 4 images for grid (have {len(all_images)})")
        elif create_grid:
            print(f"LoRA Comparison: Grid creation enabled but only {len(all_images)} image(s) generated")

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
