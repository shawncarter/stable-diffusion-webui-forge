# Compress Large PNG Grids Script

This script helps you compress large PNG grid images (like LoRA comparison grids) to reduce file size while maintaining 100% quality and resolution.

## Problem It Solves

Large comparison grids can produce enormous PNG files (2-3+ GB) that:
- Take up excessive disk space
- Can exceed texture size limits in viewers
- Are slow to load and transfer

## What It Does

The script converts large PNGs to more efficiently compressed formats:

1. **Optimized PNG** - Re-saves with maximum lossless compression (compress_level=9, optimize=True)
   - Same format, much smaller file size (typically 20-40% reduction)
   - Maintains all metadata and generation parameters
   - 100% lossless, identical quality

2. **WebP Lossless** - Converts to WebP lossless format
   - Even better compression (typically 25-50% smaller than optimized PNG)
   - 100% lossless, identical quality
   - Widely supported by modern browsers and image viewers
   - Note: Generation parameter metadata is not transferred to WebP

## Usage

Run from the webui root directory:

```bash
# Show help
python scripts/compress_large_pngs.py --help

# Convert a single file to optimized PNG
python scripts/compress_large_pngs.py your_large_grid.png

# Convert to WebP lossless (better compression)
python scripts/compress_large_pngs.py --format webp your_large_grid.png

# Process all large PNGs in a directory (only files > 100MB)
python scripts/compress_large_pngs.py --min-size 100 outputs/txt2img-grids/

# Dry run to see what would happen (no actual conversion)
python scripts/compress_large_pngs.py --dry-run --min-size 500 outputs/

# Process directory recursively
python scripts/compress_large_pngs.py --recursive --format webp outputs/

# Replace original files (BACKUP FIRST!)
python scripts/compress_large_pngs.py --replace --format webp large_grid.png
```

## Options

- `-f, --format {png,webp}` - Output format: 'png' (optimized) or 'webp' (lossless)
- `-s, --suffix SUFFIX` - Suffix for output files (default: '_compressed')
- `-r, --replace` - Replace original files (use with caution!)
- `-d, --dry-run` - Show what would be done without converting
- `--min-size MB` - Only process files larger than X megabytes
- `--recursive` - Process subdirectories recursively
- `--no-metadata` - Don't preserve PNG metadata

## Recommendations

### For Archiving
Use **WebP lossless** (`--format webp`) for best compression:
```bash
python scripts/compress_large_pngs.py --format webp --min-size 500 outputs/txt2img-grids/
```

### For Keeping PNG Format
Use **optimized PNG** (default) to stay in PNG format with better compression:
```bash
python scripts/compress_large_pngs.py --min-size 500 outputs/txt2img-grids/
```

### Testing First
Always do a dry run first to see what will be processed:
```bash
python scripts/compress_large_pngs.py --dry-run --min-size 100 outputs/
```

## Example Output

```
Processing: outputs/txt2img-grids/xyz_grid_2024-11-24.png
  Original size: 2.89 GB
  Converting to WebP lossless...
  New size: 1.45 GB
  Saved: 1.44 GB (49.8%)
  Saved to: outputs/txt2img-grids/xyz_grid_2024-11-24_compressed.webp
```

## Safety Notes

1. **Default behavior creates NEW files** - Your originals are safe unless you use `--replace`
2. **Test on one file first** before batch processing
3. **Make backups** before using `--replace` option
4. The process is **100% lossless** - no quality loss at all
5. **Metadata preservation**: PNG metadata is preserved in PNG output but not in WebP

## Technical Details

- Handles very large images (tested with 46848 x 43008 pixels, ~2 billion pixels)
- Uses PIL/Pillow for image processing
- PNG compression uses compress_level=9 and optimize=True
- WebP uses lossless=True, quality=100, method=6
- Preserves PNG text chunks (generation parameters) when converting to PNG

## Future Grid Generation

Future grids will automatically use optimized compression thanks to the fix in `modules/images.py`. This script is for converting your existing large files.
