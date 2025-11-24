#!/usr/bin/env python3
"""
Script to compress large PNG grid images to reduce file size while maintaining quality.

This script can convert large PNG files to:
1. Optimized PNG with maximum compression (lossless)
2. WebP lossless format (better compression than PNG)

IMPORTANT: This script must be run from the webui's root directory with Python.

Usage:
    python scripts/compress_large_pngs.py [options] <input_file_or_directory>

Examples:
    # Convert a single file to optimized PNG
    python scripts/compress_large_pngs.py outputs/txt2img-grids/2024-11-24/grid.png

    # Convert all PNGs in a directory to WebP lossless
    python scripts/compress_large_pngs.py --format webp outputs/txt2img-grids/

    # Dry run to see what would be converted
    python scripts/compress_large_pngs.py --dry-run outputs/txt2img-grids/

    # Only process files larger than 1GB
    python scripts/compress_large_pngs.py --min-size 1000 outputs/txt2img-grids/

    # Replace original files (CAUTION: make backups first!)
    python scripts/compress_large_pngs.py --replace --format webp large_grid.png
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image, PngImagePlugin
import pillow_avif  # noqa: F401

def format_size(bytes_size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_png_metadata(image_path):
    """Extract PNG metadata/info chunks."""
    try:
        img = Image.open(image_path)
        metadata = {}
        if hasattr(img, 'info'):
            metadata = img.info.copy()
        img.close()
        return metadata
    except Exception as e:
        print(f"Warning: Could not read metadata from {image_path}: {e}")
        return {}

def compress_png_optimized(input_path, output_path, preserve_metadata=True):
    """Compress PNG with maximum lossless compression."""
    print(f"  Converting to optimized PNG...")

    # Disable PIL's image size limit for very large images
    Image.MAX_IMAGE_PIXELS = None

    # Get metadata before opening
    metadata = get_png_metadata(input_path) if preserve_metadata else {}

    # Open and save with maximum compression
    img = Image.open(input_path)

    # Prepare PNG info if we have metadata
    pnginfo = None
    if metadata:
        pnginfo = PngImagePlugin.PngInfo()
        for k, v in metadata.items():
            pnginfo.add_text(k, str(v))

    # Save with maximum compression
    img.save(output_path, format='PNG', compress_level=9, optimize=True, pnginfo=pnginfo)
    img.close()

def compress_to_webp(input_path, output_path, preserve_metadata=True):
    """Convert PNG to WebP lossless format."""
    print(f"  Converting to WebP lossless...")

    # Disable PIL's image size limit for very large images
    Image.MAX_IMAGE_PIXELS = None

    # Get metadata before opening (for potential later use)
    metadata = get_png_metadata(input_path) if preserve_metadata else {}

    # Open image
    img = Image.open(input_path)

    # Convert RGBA to RGB if needed (WebP supports RGBA but some viewers have issues)
    # Actually, let's keep RGBA if it exists

    # Save as WebP lossless
    # Note: WebP doesn't support PNG text chunks, but we can add to EXIF if needed
    img.save(output_path, format='WEBP', lossless=True, quality=100, method=6)
    img.close()

    if metadata and preserve_metadata:
        print(f"  Note: WebP doesn't support PNG metadata chunks. Metadata not transferred.")

def process_file(input_path, output_format='png', suffix='_compressed',
                 dry_run=False, replace=False, preserve_metadata=True):
    """Process a single file."""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return False

    if not input_path.suffix.lower() == '.png':
        print(f"Skipping non-PNG file: {input_path}")
        return False

    # Get file size
    original_size = input_path.stat().st_size

    print(f"\nProcessing: {input_path}")
    print(f"  Original size: {format_size(original_size)}")

    if dry_run:
        print(f"  [DRY RUN] Would convert to {output_format.upper()}")
        return True

    # Determine output path
    if replace:
        output_path = input_path.with_suffix(f'.tmp{input_path.suffix}')
        final_path = input_path
    else:
        if output_format == 'webp':
            output_path = input_path.with_stem(input_path.stem + suffix).with_suffix('.webp')
        else:  # optimized PNG
            output_path = input_path.with_stem(input_path.stem + suffix).with_suffix('.png')
        final_path = output_path

    try:
        # Convert based on format
        if output_format == 'webp':
            compress_to_webp(input_path, output_path, preserve_metadata)
        else:  # optimized PNG
            compress_png_optimized(input_path, output_path, preserve_metadata)

        # Get new file size
        new_size = output_path.stat().st_size
        savings = original_size - new_size
        savings_percent = (savings / original_size * 100) if original_size > 0 else 0

        print(f"  New size: {format_size(new_size)}")
        print(f"  Saved: {format_size(savings)} ({savings_percent:.1f}%)")

        # If replacing, move temp file to original location
        if replace and output_path != final_path:
            output_path.replace(final_path)
            print(f"  Replaced original file")
        else:
            print(f"  Saved to: {final_path}")

        return True

    except Exception as e:
        print(f"  Error: {e}")
        # Clean up temp file if it exists
        if output_path.exists() and output_path != input_path:
            output_path.unlink()
        return False

def process_directory(directory, output_format='png', suffix='_compressed',
                     dry_run=False, replace=False, preserve_metadata=True,
                     min_size_mb=0, recursive=False):
    """Process all PNG files in a directory."""
    directory = Path(directory)

    if not directory.exists() or not directory.is_dir():
        print(f"Error: Directory not found: {directory}")
        return

    # Find all PNG files
    if recursive:
        png_files = list(directory.rglob('*.png'))
    else:
        png_files = list(directory.glob('*.png'))

    # Filter by minimum size if specified
    min_size_bytes = min_size_mb * 1024 * 1024
    if min_size_mb > 0:
        png_files = [f for f in png_files if f.stat().st_size >= min_size_bytes]

    if not png_files:
        print(f"No PNG files found in {directory}")
        if min_size_mb > 0:
            print(f"(with minimum size of {min_size_mb} MB)")
        return

    print(f"Found {len(png_files)} PNG file(s) to process")
    if min_size_mb > 0:
        print(f"(filtered to files >= {min_size_mb} MB)")

    successful = 0
    failed = 0

    for png_file in png_files:
        if process_file(png_file, output_format, suffix, dry_run, replace, preserve_metadata):
            successful += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Summary: {successful} successful, {failed} failed")

def main():
    parser = argparse.ArgumentParser(
        description='Compress large PNG grid images while maintaining quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'input',
        help='Input PNG file or directory'
    )

    parser.add_argument(
        '-f', '--format',
        choices=['png', 'webp'],
        default='png',
        help='Output format: "png" for optimized PNG (default), "webp" for WebP lossless'
    )

    parser.add_argument(
        '-s', '--suffix',
        default='_compressed',
        help='Suffix to add to output filenames (default: "_compressed")'
    )

    parser.add_argument(
        '-r', '--replace',
        action='store_true',
        help='Replace original files instead of creating new ones'
    )

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Show what would be done without actually converting files'
    )

    parser.add_argument(
        '--no-metadata',
        action='store_true',
        help='Do not preserve PNG metadata (parameters, generation info)'
    )

    parser.add_argument(
        '--min-size',
        type=float,
        default=0,
        metavar='MB',
        help='Only process files larger than this size in MB (default: process all)'
    )

    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    if input_path.is_file():
        # Process single file
        success = process_file(
            input_path,
            output_format=args.format,
            suffix=args.suffix,
            dry_run=args.dry_run,
            replace=args.replace,
            preserve_metadata=not args.no_metadata
        )
        sys.exit(0 if success else 1)
    else:
        # Process directory
        process_directory(
            input_path,
            output_format=args.format,
            suffix=args.suffix,
            dry_run=args.dry_run,
            replace=args.replace,
            preserve_metadata=not args.no_metadata,
            min_size_mb=args.min_size,
            recursive=args.recursive
        )

if __name__ == '__main__':
    main()
