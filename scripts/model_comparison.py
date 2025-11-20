"""
Model Comparison Script for Stable Diffusion WebUI Forge
Allows batch testing of multiple models with multiple prompts to compare quality and style
"""

import os
import re
from collections import namedtuple
from copy import copy
from PIL import Image, ImageDraw, ImageFont

import gradio as gr
import modules.scripts as scripts
from modules import sd_models, processing, images, shared, errors
from modules.processing import process_images, Processed, StableDiffusionProcessingTxt2Img
from modules.shared import opts, state
from modules.images import get_font
from modules.ui_components import ToolButton


def add_model_banner(image, model_name, position="bottom", font_size=None, padding=10,
                     bg_color=(0, 0, 0, 200), text_color=(255, 255, 255, 255)):
    """
    Add a semi-transparent banner with model name to an image

    Args:
        image: PIL Image object
        model_name: Text to display on the banner
        position: "top" or "bottom"
        font_size: Font size (auto-calculated if None)
        padding: Padding around text
        bg_color: Background color (R, G, B, A)
        text_color: Text color (R, G, B, A)

    Returns:
        PIL Image with banner
    """
    print(f"      add_model_banner called: '{model_name}', image size: {image.size}, mode: {image.mode}")
    # Create a copy and convert to RGBA for semi-transparent drawing
    img = image.copy()
    original_mode = img.mode
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
        print(f"      Converted from {original_mode} to RGBA")

    draw = ImageDraw.Draw(img)

    # Auto-calculate font size based on image width if not specified
    if font_size is None:
        font_size = max(12, min(32, img.width // 40))

    font = get_font(font_size)

    # Get text bounding box
    bbox = draw.textbbox((0, 0), model_name, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate banner dimensions
    banner_height = text_height + (padding * 2)
    banner_width = img.width

    # Calculate position
    if position == "top":
        banner_y = 0
        text_y = padding
    else:  # bottom
        banner_y = img.height - banner_height
        text_y = banner_y + padding

    # Draw semi-transparent background rectangle
    draw.rectangle(
        [(0, banner_y), (banner_width, banner_y + banner_height)],
        fill=bg_color
    )

    # Center text horizontally
    text_x = (banner_width - text_width) // 2

    # Draw text
    draw.text((text_x, text_y), model_name, font=font, fill=text_color)
    print(f"      Banner drawn at position {position}, rectangle: {(0, banner_y, banner_width, banner_y + banner_height)}")

    # Convert back to original mode if needed
    if original_mode != 'RGBA':
        # If converting back to RGB, need to handle alpha channel properly
        if original_mode == 'RGB':
            # Create white background and alpha composite properly
            background = Image.new('RGBA', img.size, (255, 255, 255, 255))
            composited = Image.alpha_composite(background, img)
            img = composited.convert('RGB')
            print(f"      Alpha composited RGBA onto RGB background")
        else:
            img = img.convert(original_mode)
        print(f"      Converted back to {original_mode}")

    print(f"      Returning bannered image, size: {img.size}, mode: {img.mode}")
    return img


class Script(scripts.Script):
    def title(self):
        return "Model Comparison"

    def ui(self, is_img2img):
        with gr.Row():
            gr.HTML("<p>Select models to compare. The same prompt(s) will be run through each selected model.</p>")

        with gr.Row():
            with gr.Column(scale=3):
                # Model selection
                model_filter = gr.Textbox(
                    label="Filter models (optional)",
                    placeholder="Enter text to filter model list",
                    elem_id=self.elem_id("filter")
                )

                model_checkboxes = gr.CheckboxGroup(
                    label="Select Models",
                    choices=sd_models.checkpoint_tiles(use_short=False),
                    value=[],
                    elem_id=self.elem_id("models"),
                    interactive=True
                )

                with gr.Row():
                    select_all_btn = gr.Button("Select All", size="sm")
                    deselect_all_btn = gr.Button("Deselect All", size="sm")
                    refresh_models_btn = ToolButton(value="\U0001f504", elem_id=self.elem_id("refresh"))

            with gr.Column(scale=2):
                # Prompt batch input
                prompt_batch = gr.Textbox(
                    label="Batch Prompts (one per line)",
                    placeholder="Enter multiple prompts, one per line.\nEach will be run against all selected models.",
                    lines=10,
                    elem_id=self.elem_id("prompts")
                )

                gr.HTML("<p><b>Note:</b> Leave empty to use the main prompt above.</p>")

        with gr.Row():
            with gr.Column():
                # Seed options
                seed_mode = gr.Radio(
                    label="Seed Mode",
                    choices=["Use same seed for all", "Random seed for each"],
                    value="Use same seed for all",
                    elem_id=self.elem_id("seed_mode")
                )

                fixed_seed = gr.Number(
                    label="Fixed Seed (leave -1 for random)",
                    value=-1,
                    elem_id=self.elem_id("fixed_seed")
                )

            with gr.Column():
                # Banner options
                banner_enabled = gr.Checkbox(label="Add model name banner", value=True)
                banner_position = gr.Radio(
                    label="Banner Position",
                    choices=["top", "bottom"],
                    value="bottom",
                    elem_id=self.elem_id("banner_pos")
                )
                banner_font_size = gr.Slider(
                    label="Banner Font Size",
                    minimum=8,
                    maximum=64,
                    value=0,
                    step=1,
                    elem_id=self.elem_id("font_size")
                )
                gr.HTML("<p><small>Font size 0 = auto-calculated based on image width</small></p>")

        with gr.Row():
            create_grid = gr.Checkbox(
                label="Create comparison grid",
                value=True,
                elem_id=self.elem_id("grid")
            )
            grid_columns = gr.Slider(
                label="Grid columns",
                minimum=1,
                maximum=10,
                value=3,
                step=1,
                elem_id=self.elem_id("grid_cols")
            )

        # Event handlers
        def update_model_list():
            return gr.update(choices=sd_models.checkpoint_tiles(use_short=False))

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

        def filter_models(filter_text):
            if not filter_text:
                return gr.update(choices=sd_models.checkpoint_tiles(use_short=False))
            all_models = sd_models.checkpoint_tiles(use_short=False)
            filtered = [m for m in all_models if filter_text.lower() in m.lower()]
            return gr.update(choices=filtered)

        refresh_models_btn.click(fn=update_model_list, outputs=[model_checkboxes])
        select_all_btn.click(fn=select_all_models, inputs=[model_filter], outputs=[model_checkboxes])
        deselect_all_btn.click(fn=deselect_all_models, outputs=[model_checkboxes])
        model_filter.change(fn=filter_models, inputs=[model_filter], outputs=[model_checkboxes])

        return [
            model_checkboxes, prompt_batch, seed_mode, fixed_seed,
            banner_enabled, banner_position, banner_font_size, create_grid, grid_columns
        ]

    def run(self, p, model_checkboxes, prompt_batch, seed_mode, fixed_seed,
            banner_enabled, banner_position, banner_font_size, create_grid, grid_columns):

        # Validation
        if not model_checkboxes or len(model_checkboxes) == 0:
            print("Model Comparison: No models selected, running normal generation")
            return None

        # Parse prompts
        prompts = []
        if prompt_batch and prompt_batch.strip():
            prompts = [line.strip() for line in prompt_batch.split('\n') if line.strip()]
        else:
            # Use the main prompt if no batch prompts specified
            prompts = [p.prompt]

        if not prompts:
            print("Model Comparison: No prompts provided, running normal generation")
            return None

        # Store original settings
        original_checkpoint = opts.sd_model_checkpoint
        original_prompt = p.prompt
        original_seed = p.seed

        # Determine if we should use a fixed seed
        use_fixed_seed = (seed_mode == "Use same seed for all")
        if use_fixed_seed and fixed_seed >= 0:
            base_seed = fixed_seed
        elif use_fixed_seed:
            base_seed = p.seed if p.seed >= 0 else -1
        else:
            base_seed = -1  # Will generate random seed for each

        all_images = []
        all_prompts = []
        all_seeds = []
        all_infotexts = []

        total_iterations = len(model_checkboxes) * len(prompts)
        current_iteration = 0

        # Set the job count for progress tracking
        state.job_count = total_iterations

        print(f"Model Comparison: Starting comparison with {len(model_checkboxes)} models and {len(prompts)} prompts ({total_iterations} total images)")

        try:
            # Loop through each model
            for model_idx, model_name in enumerate(model_checkboxes):
                if state.interrupted:
                    break

                print(f"\nModel Comparison: Loading model {model_idx + 1}/{len(model_checkboxes)}: {model_name}")

                # Get checkpoint info
                checkpoint_info = sd_models.get_closet_checkpoint_match(model_name)
                if checkpoint_info is None:
                    print(f"Model Comparison: Could not find checkpoint: {model_name}, skipping...")
                    continue

                # Loop through each prompt
                for prompt_idx, prompt in enumerate(prompts):
                    if state.interrupted:
                        break

                    current_iteration += 1
                    state.job_no = current_iteration
                    state.job = f"Model {model_idx + 1}/{len(model_checkboxes)}, Prompt {prompt_idx + 1}/{len(prompts)}"

                    # Create a copy of the processing parameters
                    p_copy = copy(p)
                    p_copy.prompt = prompt

                    # Prevent auto-saving during process_images() - we'll save after adding banner
                    p_copy.do_not_save_samples = True

                    # Override model checkpoint for this generation
                    if not hasattr(p_copy, 'override_settings') or p_copy.override_settings is None:
                        p_copy.override_settings = {}
                    p_copy.override_settings['sd_model_checkpoint'] = checkpoint_info.name

                    # Set seed
                    if use_fixed_seed:
                        p_copy.seed = base_seed
                        p_copy.subseed = -1
                    else:
                        p_copy.seed = -1  # Random seed
                        p_copy.subseed = -1

                    # Process single image
                    print(f"  Generating image {current_iteration}/{total_iterations}: {prompt[:50]}...")

                    try:
                        processed = process_images(p_copy)

                        # Process each generated image
                        for img_idx, img in enumerate(processed.images):
                            print(f"    Image type: {type(img)}, Is PIL Image: {isinstance(img, Image.Image)}")
                            # Add banner if enabled
                            if banner_enabled:
                                if isinstance(img, Image.Image):
                                    banner_text = checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name
                                    font_size = banner_font_size if banner_font_size > 0 else None
                                    print(f"    Adding banner: {banner_text}")
                                    img = add_model_banner(
                                        img,
                                        banner_text,
                                        position=banner_position,
                                        font_size=font_size
                                    )
                                    print(f"    Banner added, image mode: {img.mode}")
                                else:
                                    print(f"    WARNING: Image is not a PIL Image, cannot add banner!")

                            # Create infotext
                            infotext = f"Model: {checkpoint_info.short_title if hasattr(checkpoint_info, 'short_title') else model_name}\n"
                            if hasattr(processed, 'infotexts') and img_idx < len(processed.infotexts):
                                infotext += processed.infotexts[img_idx]
                            elif hasattr(processed, 'info'):
                                infotext += processed.info

                            # Save the bannered image to disk (always save comparison results)
                            if opts.samples_save and isinstance(img, Image.Image):
                                images.save_image(
                                    img,
                                    p.outpath_samples,
                                    "",
                                    processed.seed if hasattr(processed, 'seed') else p_copy.seed,
                                    prompt,
                                    opts.samples_format,
                                    info=infotext,
                                    p=p
                                )
                                print(f"    Saved bannered image to {p.outpath_samples}")

                            all_images.append(img)
                            all_prompts.append(prompt)
                            all_seeds.append(processed.seed if hasattr(processed, 'seed') else p_copy.seed)
                            all_infotexts.append(infotext)

                    except Exception as e:
                        print(f"Model Comparison: Error generating image: {e}")
                        errors.report(f"Model Comparison: Failed to generate with {model_name}", exc_info=True)
                        continue

        finally:
            # Restore original model settings
            print(f"\nModel Comparison: Complete - original model will be restored on next generation")
            # The model will automatically revert when the next generation without override_settings runs

        # Create grid if requested (minimum 4 images for 2x2 grid)
        print(f"Model Comparison: Grid creation enabled: {create_grid}, images count: {len(all_images)}")
        if create_grid and len(all_images) >= 4:
            print(f"Model Comparison: Creating comparison grid with {len(all_images)} images...")
            try:
                grid = images.image_grid(all_images, rows=None)
                print(f"Model Comparison: Grid created, size: {grid.size}, mode: {grid.mode}")

                grid_infotext = f"Model Comparison Grid: {len(model_checkboxes)} models x {len(prompts)} prompts"

                # Save grid to disk if grid saving is enabled
                if opts.grid_save:
                    images.save_image(
                        grid,
                        p.outpath_grids,
                        "model_comparison_grid",
                        all_seeds[0] if all_seeds else -1,
                        all_prompts[0] if all_prompts else p.prompt,
                        opts.grid_format,
                        info=grid_infotext,
                        p=p,
                        grid=True
                    )
                    print(f"Model Comparison: Grid saved to {p.outpath_grids}")

                all_images.insert(0, grid)
                all_prompts.insert(0, "Comparison Grid")
                all_seeds.insert(0, -1)
                all_infotexts.insert(0, grid_infotext)
                print(f"Model Comparison: Grid inserted at position 0, total images now: {len(all_images)}")
            except Exception as e:
                print(f"Model Comparison: Error creating grid: {e}")
                errors.report(f"Model Comparison: Failed to create grid", exc_info=True)
        elif create_grid and len(all_images) > 1:
            print(f"Model Comparison: Skipping grid creation - need at least 4 images for grid (have {len(all_images)})")
        elif create_grid:
            print(f"Model Comparison: Grid creation enabled but only {len(all_images)} image(s) generated")

        # Create result object
        result = Processed(
            p,
            images_list=all_images,
            seed=all_seeds[0] if all_seeds else -1,
            info=f"Model Comparison: {len(model_checkboxes)} models, {len(prompts)} prompts, {len(all_images)} images",
            infotexts=all_infotexts,
            all_prompts=all_prompts,
            all_seeds=all_seeds,
        )

        print(f"\nModel Comparison: Complete! Generated {len(all_images)} images")

        return result
