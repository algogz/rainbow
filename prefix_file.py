#!/usr/bin/env python3
"""
Add 1MB random prefix to a file.

Usage:
    python3 prefix_file.py <input_file> [output_file]

If output_file is not specified, the prefixed file will overwrite the input file
(adding a .prefixed extension is recommended to avoid data loss).

Example:
    python3 prefix_file.py original.pdf prefixed.pdf
"""

import os
import sys

RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes


def add_random_prefix(input_path, output_path):
    """Add 1MB random prefix to a file."""
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    if not os.path.isfile(input_path):
        print(f"Error: '{input_path}' is not a regular file.")
        sys.exit(1)

    # Read the original file
    with open(input_path, 'rb') as f:
        original_data = f.read()

    # Generate random prefix
    random_prefix = os.urandom(RANDOM_PREFIX_SIZE)

    # Write prefixed file
    with open(output_path, 'wb') as f:
        f.write(random_prefix)
        f.write(original_data)

    original_size = len(original_data)
    prefixed_size = RANDOM_PREFIX_SIZE + original_size

    print(f"Input:  {input_path} ({original_size:,} bytes)")
    print(f"Output: {output_path} ({prefixed_size:,} bytes)")
    print(f"Prefix: {RANDOM_PREFIX_SIZE:,} bytes of random data added")


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python3 prefix_file.py <input_file> [output_file]")
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) == 3:
        output_path = sys.argv[2]
    else:
        # Default: add .prefixed extension
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}.prefixed{ext}"
        print(f"Warning: No output specified. File will be saved as '{output_path}'")

    add_random_prefix(input_path, output_path)


if __name__ == "__main__":
    main()
