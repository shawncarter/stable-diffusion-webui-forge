#!/bin/bash
#######################################################
# Example webui-user.sh with custom paths configured
# Copy this file to webui-user.sh and customize paths
#######################################################

# Uncomment and set your custom paths below
# Use absolute paths (full paths starting with /)

# Example for external drive or different directory structure
# export COMMANDLINE_ARGS="--ckpt-dir /path/to/your/checkpoints \
#                          --lora-dir /path/to/your/loras \
#                          --embeddings-dir /path/to/your/embeddings \
#                          --vae-dir /path/to/your/vaes \
#                          --hypernetwork-dir /path/to/your/hypernetworks"

# Example: Models on external SSD
# export COMMANDLINE_ARGS="--ckpt-dir /media/username/ExternalSSD/SD-Models/checkpoints \
#                          --lora-dir /media/username/ExternalSSD/SD-Models/loras"

# Example: Shared model library from another WebUI installation
# export COMMANDLINE_ARGS="--ckpt-dir /home/user/stable-diffusion-webui/models/Stable-diffusion \
#                          --lora-dir /home/user/stable-diffusion-webui/models/Lora"

# Additional useful arguments:
# --listen                              # Allow network access
# --port 7860                           # Set custom port
# --xformers                            # Enable xformers for better performance
# --no-half                             # Disable half precision (fixes some model issues)
# --medvram                             # Optimize for medium VRAM
# --lowvram                             # Optimize for low VRAM

# You can combine multiple arguments:
# export COMMANDLINE_ARGS="--ckpt-dir /path/to/checkpoints --lora-dir /path/to/loras --xformers --listen"
