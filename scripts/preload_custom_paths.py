"""
Preload script to apply custom paths before WebUI starts
This ensures custom paths are applied early in the startup process
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def preload(parser):
    """Called during extension preloading to add command line arguments"""
    # This function can be used to add additional arguments if needed
    pass

def on_app_started(blocks, app):
    """Called when the webui app is started"""
    # Import here to ensure modules are loaded
    try:
        from modules import shared
        if hasattr(shared, 'opts'):
            apply_custom_paths_from_settings()
    except Exception as e:
        print(f"Custom Paths: Could not apply paths at startup: {e}")

def apply_custom_paths_from_settings():
    """Read custom paths from config and apply them"""
    from modules import shared
    from modules.shared import cmd_opts

    try:
        # Read config file directly
        config_file = os.path.join(shared.data_path, "config.json")
        if os.path.exists(config_file):
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)

            paths_to_set = {
                'custom_ckpt_dir': 'ckpt_dir',
                'custom_lora_dir': 'lora_dir',
                'custom_embeddings_dir': 'embeddings_dir',
                'custom_hypernetwork_dir': 'hypernetwork_dir',
                'custom_vae_dir': 'vae_dir',
            }

            applied = 0
            for config_key, cmd_key in paths_to_set.items():
                custom_path = config.get(config_key, '').strip()
                if custom_path and os.path.exists(custom_path):
                    # Only override if not already set via command line
                    current_val = getattr(cmd_opts, cmd_key, None)
                    if not current_val or current_val == getattr(cmd_opts, cmd_key):
                        setattr(cmd_opts, cmd_key, custom_path)
                        applied += 1
                        print(f"Custom Paths: Set {cmd_key} = {custom_path}")

            if applied > 0:
                print(f"Custom Paths: Applied {applied} custom path(s) from settings")

    except Exception as e:
        print(f"Custom Paths: Error reading config: {e}")
