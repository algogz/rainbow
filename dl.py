#!/usr/bin/env python3
"""
Client script for downloading files via the rainbow server.

This script accepts a location parameter (URL or local file path),
encodes it, sends it to the server, and saves the downloaded file
with the random prefix removed.
"""
import argparse
import base64
import sys
import os
import requests


def encode_data(data_type, value):
    """Encode data for the server request

    Args:
        data_type: 'url' or 'path'
        value: The URL or file path

    Returns:
        Base64 encoded string of the reversed data
    """
    # Create the data string with type prefix
    data_str = f"{data_type}:{value}"
    # Reverse the string
    reversed_str = data_str[::-1]
    # Encode to bytes and then base64
    encoded_bytes = base64.b64encode(reversed_str.encode('utf-8'))
    return encoded_bytes.decode('utf-8')


def download_file(server_url, location, output_filename=None):
    """Download a file via the rainbow server

    Args:
        server_url: The base URL of the rainbow server (e.g., http://localhost:30080)
        location: URL or local file path to download
        output_filename: Optional output filename. If not provided, uses the
                        filename from the server response or a generated name.

    Returns:
        The path to the saved file, or None on failure.
    """
    RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes

    # Determine data type based on location
    if location.lower().startswith('http://') or location.lower().startswith('https://'):
        data_type = 'url'
        print(f"Mode: URL download")
        print(f"URL: {location}")
    else:
        data_type = 'path'
        print(f"Mode: Local file serving")
        print(f"Path: {location}")

    # Encode the data
    encoded_data = encode_data(data_type, location)

    # Send request to server
    print(f"\nConnecting to server: {server_url}/test")
    try:
        response = requests.post(
            f"{server_url}/test",
            json={"data": encoded_data},
            stream=True,
            timeout=300  # 5 minute timeout for large files
        )
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {server_url}")
        print("Make sure the server is running (python3 main.py)")
        return None
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

    # Check for errors
    if response.status_code != 200:
        print(f"Error: Server returned status code {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error message: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"Response: {response.text[:200]}")
        return None

    # Get filename from response headers
    content_disposition = response.headers.get('Content-Disposition', '')
    filename = None
    if content_disposition:
        # Extract filename from Content-Disposition header
        # Format: attachment; filename="YYYYMMDDHHMM_original_filename.ext"
        for part in content_disposition.split(';'):
            if 'filename=' in part:
                filename = part.split('filename=')[1].strip('"')
                break

    # Determine output filename
    if output_filename:
        save_path = output_filename
    elif filename:
        # Remove the timestamp prefix from the server-generated filename
        # Format: YYYYMMDDHHMM_original_filename.ext
        parts = filename.split('_', 1)
        if len(parts) == 2:
            save_path = parts[1]
        else:
            save_path = filename
    else:
        # Generate a default filename
        if data_type == 'url':
            save_path = os.path.basename(location) or "downloaded_file"
        else:
            save_path = os.path.basename(location) or "downloaded_file"

    print(f"\nReceiving data...")
    print(f"Total size: {len(response.content):,} bytes")

    # Verify the file has the expected random prefix
    total_size = len(response.content)
    if total_size <= RANDOM_PREFIX_SIZE:
        print(f"Error: Response size ({total_size}) is too small")
        print(f"Expected at least {RANDOM_PREFIX_SIZE:,} bytes (random prefix)")
        return None

    # Extract real content by skipping the random prefix
    real_content = response.content[RANDOM_PREFIX_SIZE:]
    real_size = len(real_content)

    print(f"Random prefix: {RANDOM_PREFIX_SIZE:,} bytes (removed)")
    print(f"Real content: {real_size:,} bytes")

    # Save the file
    try:
        with open(save_path, 'wb') as f:
            f.write(real_content)
        print(f"\n✓ Saved to: {save_path}")
        print(f"✓ File size: {os.path.getsize(save_path):,} bytes")
        return save_path
    except IOError as e:
        print(f"Error: Could not write to file: {str(e)}")
        return None


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Download files via the rainbow server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Download from URL
  python dl.py https://example.com/file.pdf

  # Serve local file from server
  python dl.py /path/to/local/file.txt

  # Specify custom output filename
  python dl.py https://example.com/file.pdf -o my_file.pdf

  # Use custom server URL
  python dl.py https://example.com/file.pdf --server http://remote-server:30080
        '''
    )

    parser.add_argument(
        'location',
        help='URL (starts with http:// or https://) or local file path'
    )

    parser.add_argument(
        '-o', '--output',
        dest='output',
        help='Output filename (default: auto-detected from response)'
    )

    parser.add_argument(
        '-s', '--server',
        dest='server',
        default='http://localhost:30080',
        help='Server URL (default: http://localhost:30080)'
    )

    args = parser.parse_args()

    # Download the file
    result = download_file(args.server, args.location, args.output)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
