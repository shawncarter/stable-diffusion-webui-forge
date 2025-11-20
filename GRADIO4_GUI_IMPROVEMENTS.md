# Gradio 4 GUI Improvements for Stable Diffusion WebUI Forge

This document describes the new GUI improvements and features added to enhance the Stable Diffusion WebUI Forge user experience with Gradio 4.

## Table of Contents
- [Model Comparison Tool](#model-comparison-tool)
- [Model Favorites & Presets Manager](#model-favorites--presets-manager)
- [Quick Quality Presets](#quick-quality-presets)
- [Installation & Usage](#installation--usage)

---

## Model Comparison Tool

**Location**: `scripts/model_comparison.py`

### Overview
The Model Comparison tool allows you to batch test multiple checkpoint models with multiple prompts to easily compare image quality, style, and model characteristics. This is invaluable for:
- Evaluating new models before committing to using them
- Comparing different versions of the same model
- Creating model comparison charts and galleries
- Testing prompt effectiveness across different models

### Features

#### 1. Multi-Model Selection
- **Select Multiple Models**: Choose any number of checkpoint models from your collection using checkboxes
- **Filter Models**: Use the filter textbox to quickly find models by name
- **Quick Selection**: "Select All" and "Deselect All" buttons for convenience
- **Refresh**: Update the model list without restarting the UI

#### 2. Batch Prompt Testing
- **Multiple Prompts**: Enter multiple prompts (one per line) to test against all selected models
- **Fallback to Main Prompt**: Leave empty to use the main prompt from the txt2img/img2img interface
- **Nested Loop Processing**: Each prompt is run through every selected model, creating a comprehensive comparison matrix

#### 3. Seed Control
- **Same Seed for All**: Use the same seed across all generations for consistent comparisons
- **Random Seed for Each**: Generate unique variations for each model/prompt combination
- **Fixed Seed Option**: Specify a particular seed value, or use -1 for random

#### 4. Model Name Banners
- **Auto-Generated Banners**: Automatically adds a semi-transparent banner with the model name to each image
- **Customizable Position**: Choose between top or bottom banner placement
- **Adjustable Font Size**: Set font size manually (8-64) or use 0 for auto-calculation based on image width
- **Enable/Disable**: Toggle banners on or off as needed

#### 5. Comparison Grid
- **Automatic Grid Creation**: Generates a comparison grid of all images for easy visual comparison
- **Configurable Columns**: Set the number of columns in the grid (1-10)
- **Grid as First Image**: The comparison grid appears as the first image in the output

#### 6. Compatible with All Generation Settings
- Works seamlessly with all standard generation parameters (steps, CFG scale, sampler, scheduler, etc.)
- Compatible with SD1.5, SD2.0, SDXL, SD3, Flux, and Chroma models
- Parameters remain consistent across all models for fair comparison

### How to Use

1. **Enable the Feature**: Open the "Model Comparison" accordion and check "Enable Model Comparison"

2. **Select Models**:
   - Browse or filter the model list
   - Check the models you want to compare
   - Or use "Select All" to compare all available models

3. **Configure Prompts**:
   - Enter multiple prompts in the "Batch Prompts" field (one per line)
   - OR leave empty to use the main prompt

4. **Set Seed Options**:
   - Choose "Use same seed for all" for consistent comparisons
   - Or "Random seed for each" for variety
   - Optionally set a fixed seed value

5. **Configure Banners**:
   - Enable "Add model name banner"
   - Choose position (top/bottom)
   - Set font size (0 for auto)

6. **Generate**:
   - Click the Generate button
   - The system will loop through all model/prompt combinations
   - Progress will be shown in the UI

7. **Review Results**:
   - View the comparison grid (if enabled)
   - Browse individual images with model names in banners
   - Check infotext for model information

### Technical Details

#### Image Processing
- Uses PIL (Python Imaging Library) for banner generation
- Semi-transparent backgrounds (RGBA) for better visibility
- Auto-calculated font sizes based on image dimensions
- Centers text horizontally for aesthetic appeal

#### Model Switching
- Uses the same model loading mechanism as XYZ Grid
- Leverages `override_settings` for efficient model switching
- Preserves original model state after completion
- Handles errors gracefully with detailed logging

#### Performance Considerations
- Total images = (number of models) × (number of prompts) × (batch size)
- Example: 5 models × 3 prompts = 15 images
- Can be interrupted at any time using the Interrupt button
- Progress is shown in real-time

---

## Model Favorites & Presets Manager

**Location**: `scripts/model_favorites.py`

### Overview
Organize and quickly access your most-used models and save complete generation presets for instant recall.

### Features

#### 1. Favorites Management
- **Add to Favorites**: Quickly add the currently selected model to your favorites list
- **Remove Favorites**: Select and remove multiple favorites at once
- **Persistent Storage**: Favorites are saved to `model_presets.json` in your data directory
- **Quick Access**: View all favorite models in one place

#### 2. Presets System
- **Save Complete Settings**: Store model + generation settings together
- **Named Presets**: Give each preset a descriptive name
- **Optional Descriptions**: Add notes about when to use each preset
- **Quick Recall**: Load all settings with one click

#### 3. Preset Information
- **Detailed View**: See all settings associated with a preset
- **Model Tracking**: Know which model each preset uses
- **Settings Display**: View steps, CFG scale, sampler, scheduler, width, height

### How to Use

#### Managing Favorites
1. Open the "Model Favorites & Presets" accordion
2. Select a model in the main UI
3. Click "⭐ Add Current Model to Favorites"
4. View your favorites in the list
5. Select favorites and click "Remove Selected" to remove them

#### Creating Presets
1. Configure your desired generation settings
2. Select your preferred model
3. Enter a preset name
4. Optionally add a description
5. Click "💾 Save Current Settings as Preset"

#### Loading Presets
1. Select a preset from the dropdown
2. View the preset information
3. Click "📂 Load Preset" to apply all settings

---

## Quick Quality Presets

**Location**: `scripts/quick_quality_presets.py`

### Overview
Quickly apply common quality and resolution presets without manually adjusting multiple parameters.

### Available Presets

| Preset | Steps | CFG Scale | Resolution | Use Case |
|--------|-------|-----------|------------|----------|
| **Draft (Fast)** | 15 | 5.0 | 512×512 | Fast generation for quick previews |
| **Balanced** | 25 | 7.0 | 768×768 | Good balance of speed and quality |
| **Quality** | 35 | 8.0 | 1024×1024 | High quality output, slower |
| **Maximum Quality** | 50 | 9.0 | 1024×1024 | Best quality, slowest |
| **Portrait** | 30 | 7.5 | 768×1024 | Optimized for portraits |
| **Landscape** | 30 | 7.5 | 1024×768 | Optimized for landscapes |
| **Square** | 30 | 7.5 | 1024×1024 | Square format for social media |

### Features
- **One-Click Application**: Apply all preset parameters with a single click
- **Preset Descriptions**: See what each preset is optimized for
- **Custom Override**: Manually adjust after applying a preset
- **Infotext Integration**: Preset name is saved in image metadata

### How to Use
1. Open the "Quick Quality Presets" accordion
2. Select a preset from the dropdown
3. Read the description to confirm it matches your needs
4. Click "Apply Preset"
5. The steps, CFG scale, width, and height will be automatically set
6. Make any additional adjustments if needed
7. Generate your image

---

## Installation & Usage

### Installation
These improvements are implemented as scripts and are automatically loaded by Stable Diffusion WebUI Forge. No additional installation is required.

### Location of Scripts
- `scripts/model_comparison.py` - Model Comparison Tool
- `scripts/model_favorites.py` - Model Favorites & Presets Manager
- `scripts/quick_quality_presets.py` - Quick Quality Presets

### Accessing Features
All features appear as accordions in the txt2img and img2img interfaces:
1. Scroll down in the Generation tab
2. Look for the accordion sections:
   - "Model Comparison"
   - "Model Favorites & Presets"
   - "Quick Quality Presets"
3. Click to expand and use the features

### Data Storage
- Model favorites and presets are stored in: `<data_directory>/model_presets.json`
- This file is automatically created on first use
- It's safe to manually edit this JSON file if needed
- Backup this file to preserve your presets across installations

---

## Tips & Best Practices

### Model Comparison
- **Start Small**: Test with 2-3 models and 2-3 prompts before running larger batches
- **Use Same Seed**: For fair comparisons, use the same seed across all models
- **Enable Banners**: Always enable banners so you can identify which image came from which model
- **Create Grids**: Enable grid creation for easy side-by-side comparison
- **Save Results**: Save the comparison grid as a reference for future model selection

### Quality Presets
- **Draft First**: Use "Draft (Fast)" preset to test prompts before committing to high-quality renders
- **Match Your Needs**: Choose presets based on your use case (portrait, landscape, quality)
- **Override When Needed**: Presets are starting points; adjust as needed for your specific requirements

### Performance
- **Model Comparison**: Be mindful that comparing many models takes time; each model needs to load
- **Batch Size**: The model comparison tool respects your batch size setting
- **Interruption**: You can always interrupt generation if needed
- **VRAM Considerations**: Ensure you have enough VRAM for your selected models and resolutions

---

## Troubleshooting

### Model Comparison Issues

**Problem**: Models not appearing in the list
- **Solution**: Click the refresh button (🔄) to update the model list

**Problem**: Generation fails with a specific model
- **Solution**: The tool will skip problematic models and continue with others; check console for error messages

**Problem**: Banners not appearing
- **Solution**: Ensure "Add model name banner" is checked and regenerate

### Favorites/Presets Issues

**Problem**: Favorites not saving
- **Solution**: Check write permissions for the data directory
- **Workaround**: Manually create `model_presets.json` with `{"favorites": [], "presets": {}}`

**Problem**: Presets not loading
- **Solution**: Ensure the preset file isn't corrupted; check JSON syntax

### Quality Presets Issues

**Problem**: Preset doesn't apply
- **Solution**: Make sure to click "Apply Preset" after selecting from the dropdown
- **Note**: Some settings may be overridden by other scripts or extensions

---

## Future Enhancements

Potential future improvements:
- [ ] Folder-based model filtering for better organization
- [ ] Import/export presets to share with others
- [ ] Preset scheduling (apply different presets at different stages)
- [ ] Recent models list
- [ ] Model tags and categories
- [ ] Advanced comparison metrics (SSIM, LPIPS, etc.)
- [ ] Automatic model performance benchmarking
- [ ] Comparison report generation (HTML/PDF)

---

## Credits

**Developer**: Claude Code
**Version**: 1.0
**Date**: November 2025
**Compatibility**: Stable Diffusion WebUI Forge (Gradio 4)

---

## License

These improvements follow the same license as Stable Diffusion WebUI Forge.

---

## Support & Feedback

For issues, suggestions, or contributions:
1. Check the console for error messages
2. Review this documentation
3. Report issues to the repository

Enjoy the improved workflow! 🎨✨
