"""
Apply custom paths from settings at startup
This script runs during WebUI initialization to apply user-configured paths
"""

import os
from modules import shared

def apply_custom_paths():
    """Apply custom paths from settings to command line options"""
    if not hasattr(shared, 'opts') or shared.opts is None:
        return

    # Get custom paths from settings
    custom_paths = {
        'ckpt_dir': shared.opts.data.get('custom_ckpt_dir', ''),
        'lora_dir': shared.opts.data.get('custom_lora_dir', ''),
        'embeddings_dir': shared.opts.data.get('custom_embeddings_dir', ''),
        'hypernetwork_dir': shared.opts.data.get('custom_hypernetwork_dir', ''),
        'vae_dir': shared.opts.data.get('custom_vae_dir', ''),
    }

    # Apply non-empty custom paths
    applied = []
    for key, value in custom_paths.items():
        if value and os.path.exists(value):
            setattr(shared.cmd_opts, key, value)
            applied.append(f"{key} -> {value}")
            print(f"Custom Paths: Applied {key} = {value}")
        elif value:
            print(f"Custom Paths: Warning - {key} path does not exist: {value}")

    if applied:
        print(f"Custom Paths: Applied {len(applied)} custom path(s)")
    else:
        print("Custom Paths: No custom paths configured")

# This will be called by preload.py
if __name__ == "__main__":
    apply_custom_paths()
