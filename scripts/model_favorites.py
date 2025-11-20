"""
Model Favorites/Presets Manager for Stable Diffusion WebUI Forge
Allows users to create, save, and quickly load model presets with associated settings
"""

import json
import os
from pathlib import Path

import gradio as gr
import modules.scripts as scripts
from modules import sd_models, shared
from modules.ui_components import ToolButton


class ModelFavoritesManager(scripts.Script):
    def __init__(self):
        super().__init__()
        self.presets_file = os.path.join(shared.data_path, "model_presets.json")
        self.presets = self.load_presets()

    def title(self):
        return "Model Favorites & Presets"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_presets(self):
        """Load saved model presets from JSON file"""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Model Favorites: Error loading presets: {e}")
                return {"favorites": [], "presets": {}}
        return {"favorites": [], "presets": {}}

    def save_presets(self):
        """Save model presets to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.presets_file), exist_ok=True)
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
        except Exception as e:
            print(f"Model Favorites: Error saving presets: {e}")

    def ui(self, is_img2img):
        with gr.Accordion(open=False, label="Model Favorites & Presets", elem_id="model_favorites_accordion"):
            gr.HTML("""
                <p><b>Model Favorites</b> - Quickly access your frequently used models</p>
                <p><b>Presets</b> - Save complete generation settings with a model for quick recall</p>
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    # Favorites section
                    with gr.Group():
                        gr.HTML("<h4>Favorites</h4>")

                        current_favorites = self.presets.get("favorites", [])
                        favorites_display = gr.CheckboxGroup(
                            label="Favorite Models",
                            choices=current_favorites,
                            value=[],
                            elem_id="model_favorites_list",
                            interactive=True
                        )

                        with gr.Row():
                            add_favorite_btn = gr.Button("⭐ Add Current Model to Favorites", size="sm")
                            remove_favorite_btn = gr.Button("Remove Selected", size="sm")
                            refresh_favorites_btn = ToolButton(value="\U0001f504", elem_id="favorites_refresh")

                with gr.Column(scale=3):
                    # Presets section
                    with gr.Group():
                        gr.HTML("<h4>Presets</h4>")

                        preset_name_input = gr.Textbox(
                            label="Preset Name",
                            placeholder="Enter a name for your preset",
                            elem_id="preset_name_input"
                        )

                        preset_description = gr.Textbox(
                            label="Description (optional)",
                            placeholder="Describe this preset",
                            lines=2,
                            elem_id="preset_description"
                        )

                        preset_list = gr.Dropdown(
                            label="Saved Presets",
                            choices=list(self.presets.get("presets", {}).keys()),
                            value=None,
                            elem_id="preset_list"
                        )

                        with gr.Row():
                            save_preset_btn = gr.Button("💾 Save Current Settings as Preset", size="sm")
                            load_preset_btn = gr.Button("📂 Load Preset", size="sm")
                            delete_preset_btn = gr.Button("🗑️ Delete Preset", size="sm")

                        preset_info = gr.Textbox(
                            label="Preset Info",
                            lines=6,
                            interactive=False,
                            elem_id="preset_info"
                        )

            status_message = gr.HTML(value="", elem_id="model_favorites_status")

            # Event handlers
            def get_current_model():
                """Get the currently selected model"""
                return shared.opts.sd_model_checkpoint

            def add_to_favorites():
                """Add current model to favorites"""
                current_model = get_current_model()
                if current_model and current_model not in self.presets["favorites"]:
                    self.presets["favorites"].append(current_model)
                    self.save_presets()
                    return (
                        gr.update(choices=self.presets["favorites"]),
                        "<p style='color: green;'>✓ Added to favorites!</p>"
                    )
                elif current_model in self.presets["favorites"]:
                    return (
                        gr.update(),
                        "<p style='color: orange;'>⚠ Already in favorites</p>"
                    )
                else:
                    return (
                        gr.update(),
                        "<p style='color: red;'>✗ No model selected</p>"
                    )

            def remove_from_favorites(selected):
                """Remove selected models from favorites"""
                if not selected:
                    return (
                        gr.update(),
                        "<p style='color: orange;'>⚠ No models selected for removal</p>"
                    )

                for model in selected:
                    if model in self.presets["favorites"]:
                        self.presets["favorites"].remove(model)

                self.save_presets()
                return (
                    gr.update(choices=self.presets["favorites"], value=[]),
                    f"<p style='color: green;'>✓ Removed {len(selected)} model(s) from favorites</p>"
                )

            def refresh_favorites():
                """Refresh the favorites list"""
                self.presets = self.load_presets()
                return gr.update(choices=self.presets.get("favorites", []))

            def save_preset(name, description, steps, cfg, sampler, scheduler, width, height):
                """Save current generation settings as a preset"""
                if not name or not name.strip():
                    return (
                        gr.update(),
                        "<p style='color: red;'>✗ Please enter a preset name</p>"
                    )

                current_model = get_current_model()
                preset_data = {
                    "model": current_model,
                    "description": description,
                    "settings": {
                        "steps": steps,
                        "cfg_scale": cfg,
                        "sampler_name": sampler,
                        "scheduler": scheduler,
                        "width": width,
                        "height": height
                    }
                }

                if "presets" not in self.presets:
                    self.presets["presets"] = {}

                self.presets["presets"][name.strip()] = preset_data
                self.save_presets()

                return (
                    gr.update(choices=list(self.presets["presets"].keys()), value=name.strip()),
                    f"<p style='color: green;'>✓ Saved preset '{name}'</p>"
                )

            def load_preset_info(preset_name):
                """Load and display preset information"""
                if not preset_name or preset_name not in self.presets.get("presets", {}):
                    return ""

                preset = self.presets["presets"][preset_name]
                info_lines = [
                    f"Preset: {preset_name}",
                    f"Model: {preset.get('model', 'Unknown')}",
                    f"Description: {preset.get('description', 'No description')}",
                    "",
                    "Settings:",
                ]

                settings = preset.get("settings", {})
                for key, value in settings.items():
                    info_lines.append(f"  {key}: {value}")

                return "\n".join(info_lines)

            def delete_preset(preset_name):
                """Delete a preset"""
                if not preset_name:
                    return (
                        gr.update(),
                        "",
                        "<p style='color: orange;'>⚠ No preset selected</p>"
                    )

                if preset_name in self.presets.get("presets", {}):
                    del self.presets["presets"][preset_name]
                    self.save_presets()
                    return (
                        gr.update(choices=list(self.presets["presets"].keys()), value=None),
                        "",
                        f"<p style='color: green;'>✓ Deleted preset '{preset_name}'</p>"
                    )

                return (
                    gr.update(),
                    "",
                    "<p style='color: red;'>✗ Preset not found</p>"
                )

            # Wire up the events
            add_favorite_btn.click(
                fn=add_to_favorites,
                inputs=[],
                outputs=[favorites_display, status_message]
            )

            remove_favorite_btn.click(
                fn=remove_from_favorites,
                inputs=[favorites_display],
                outputs=[favorites_display, status_message]
            )

            refresh_favorites_btn.click(
                fn=refresh_favorites,
                outputs=[favorites_display]
            )

            preset_list.change(
                fn=load_preset_info,
                inputs=[preset_list],
                outputs=[preset_info]
            )

            delete_preset_btn.click(
                fn=delete_preset,
                inputs=[preset_list],
                outputs=[preset_list, preset_info, status_message]
            )

        # Return components that need to be connected to main UI
        # These will be passed to the run() method
        return [
            preset_name_input, preset_description, preset_list,
            save_preset_btn, load_preset_btn,
            status_message, favorites_display
        ]

    def run(self, p, preset_name_input, preset_description, preset_list,
            save_preset_btn, load_preset_btn, status_message, favorites_display):
        # This script doesn't modify the generation process
        # It's purely for UI management
        return None
