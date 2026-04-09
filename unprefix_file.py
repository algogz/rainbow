#!/usr/bin/env python3
"""
Remove 1MB random prefix from a file to recover the original.

Usage:
    python3 unprefix_file.py <prefixed_file> [output_file]

If output_file is not specified, the recovered file will be saved with
a .recovered extension.

Example:
    python3 unprefix_file.py prefixed.pdf recovered.pdf
"""

import os
import sys

RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes


def remove_random_prefix(input_path, output_path):
    """Remove 1MB random prefix from a prefixed file."""
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    if not os.path.isfile(input_path):
        print(f"Error: '{input_path}' is not a regular file.")
        sys.exit(1)

    file_size = os.path.getsize(input_path)

    if file_size < RANDOM_PREFIX_SIZE:
        print(f"Error: File size ({file_size:,} bytes) is smaller than prefix size ({RANDOM_PREFIX_SIZE:,} bytes).")
        sys.exit(1)

    # Read the prefixed file, skipping the first 1MB
    with open(input_path, 'rb') as f:
        # Skip the random prefix
        f.seek(RANDOM_PREFIX_SIZE)
        original_data = f.read()

    recovered_size = len(original_data)
    total_size = RANDOM_PREFIX_SIZE + recovered_size

    # Write recovered file
    with open(output_path, 'wb') as f:
        f.write(original_data)

    print(f"Input:  {input_path} ({total_size:,} bytes)")
    print(f"Output: {output_path} ({recovered_size:,} bytes)")
    print(f"Prefix: {RANDOM_PREFIX_SIZE:,} bytes of random data removed")


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python3 unprefix_file.py <prefixed_file> [output_file]")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) == 3:
        output_path = sys.argv[2]
    else:
        # Default: add .recovered extension
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}.recovered{ext}"
        print(f"Warning: No output specified. File will be saved as '{output_path}'")

    remove_random_prefix(input_path, output_path)


if __name__ == "__main__":
    main()
