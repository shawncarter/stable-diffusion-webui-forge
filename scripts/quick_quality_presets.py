"""
Quick Quality Presets for Stable Diffusion WebUI Forge
Provides easy-to-use quality presets for different use cases
"""

import gradio as gr
import modules.scripts as scripts
from modules import shared


class Script(scripts.Script):
    def title(self):
        return "Quick Quality Presets"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    # Define quality presets
    PRESETS = {
        "Draft (Fast)": {
            "steps": 15,
            "cfg_scale": 5.0,
            "width": 512,
            "height": 512,
            "description": "Fast generation for quick previews"
        },
        "Balanced": {
            "steps": 25,
            "cfg_scale": 7.0,
            "width": 768,
            "height": 768,
            "description": "Good balance of speed and quality"
        },
        "Quality": {
            "steps": 35,
            "cfg_scale": 8.0,
            "width": 1024,
            "height": 1024,
            "description": "High quality output, slower"
        },
        "Maximum Quality": {
            "steps": 50,
            "cfg_scale": 9.0,
            "width": 1024,
            "height": 1024,
            "description": "Best quality, slowest"
        },
        "Portrait": {
            "steps": 30,
            "cfg_scale": 7.5,
            "width": 768,
            "height": 1024,
            "description": "Optimized for portraits"
        },
        "Landscape": {
            "steps": 30,
            "cfg_scale": 7.5,
            "width": 1024,
            "height": 768,
            "description": "Optimized for landscapes"
        },
        "Square": {
            "steps": 30,
            "cfg_scale": 7.5,
            "width": 1024,
            "height": 1024,
            "description": "Square format for social media"
        }
    }

    def ui(self, is_img2img):
        with gr.Accordion(open=False, label="Quick Quality Presets", elem_id="quick_presets_accordion"):
            gr.HTML("""
                <p>Quickly apply common quality and resolution presets.
                Select a preset below to automatically set steps, CFG scale, and dimensions.</p>
            """)

            with gr.Row():
                preset_dropdown = gr.Dropdown(
                    label="Quality Preset",
                    choices=["Custom"] + list(self.PRESETS.keys()),
                    value="Custom",
                    elem_id="quick_preset_dropdown"
                )

                apply_preset_btn = gr.Button("Apply Preset", size="sm", variant="primary")

            preset_description = gr.Textbox(
                label="Preset Description",
                value="Custom settings",
                interactive=False,
                elem_id="preset_description_display"
            )

            # Hidden output to trigger updates
            preset_data = gr.JSON(value={}, visible=False, elem_id="preset_data_output")

            def get_preset_description(preset_name):
                """Get description for selected preset"""
                if preset_name == "Custom" or preset_name not in self.PRESETS:
                    return "Custom settings"
                return self.PRESETS[preset_name]["description"]

            def prepare_preset_data(preset_name):
                """Prepare preset data for application"""
                if preset_name == "Custom" or preset_name not in self.PRESETS:
                    return {}
                return self.PRESETS[preset_name]

            # Update description when preset changes
            preset_dropdown.change(
                fn=get_preset_description,
                inputs=[preset_dropdown],
                outputs=[preset_description]
            )

            # Prepare data when apply is clicked
            apply_preset_btn.click(
                fn=prepare_preset_data,
                inputs=[preset_dropdown],
                outputs=[preset_data]
            )

        return [preset_dropdown, preset_data]

    def process(self, p, preset_dropdown, preset_data):
        """Apply preset to processing parameters"""
        if preset_data and isinstance(preset_data, dict) and "steps" in preset_data:
            print(f"Quick Preset: Applying '{preset_dropdown}' preset")

            # Apply settings from preset
            if "steps" in preset_data:
                p.steps = preset_data["steps"]
            if "cfg_scale" in preset_data:
                p.cfg_scale = preset_data["cfg_scale"]
            if "width" in preset_data:
                p.width = preset_data["width"]
            if "height" in preset_data:
                p.height = preset_data["height"]

            # Add to extra params for infotext
            p.extra_generation_params["quality_preset"] = preset_dropdown

    def run(self, p, preset_dropdown, preset_data):
        # Processing is done in process() method
        return None
