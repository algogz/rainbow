#!/usr/bin/env python3
"""
Test script for the file download server
"""
import requests
import json
import time
import os


def test_server():
    """Test the file download server"""
    base_url = "http://localhost:8080"

    print("Testing File Download Server...")
    print("=" * 50)

    # Test with a sample URL that will redirect
    test_url = "https://httpbin.org/redirect/2"  # This will redirect to /get

    # Define constants
    RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes

    # Prepare the request data
    request_data = {
        "url": test_url
    }

    try:
        print(f"Sending POST request to {base_url}/download")
        print(f"Target URL: {test_url}")
        print()

        # Send POST request
        response = requests.post(
            f"{base_url}/download",
            json=request_data,
            timeout=60,
            stream=True  # Stream the response to handle large files
        )

        if response.status_code == 200:
            print(f"✓ Success! Response status: {response.status_code}")
            print(f"✓ Content-Type: {response.headers.get('Content-Type')}")
            print(f"✓ Content-Disposition: {response.headers.get('Content-Disposition')}")

            # Get total content size
            total_content = response.content
            total_size = len(total_content)
            print(f"✓ Total download size: {total_size:,} bytes")

            # Verify the file structure: 1,024,000 bytes random + downloaded content
            if total_size <= RANDOM_PREFIX_SIZE:
                print(f"✗ Error: Response size ({total_size}) is smaller than expected random prefix ({RANDOM_PREFIX_SIZE})")
                return

            # Extract and save only the real downloaded content (skip random prefix)
            real_content = total_content[RANDOM_PREFIX_SIZE:]
            real_content_size = len(real_content)

            print(f"✓ Random prefix size: {RANDOM_PREFIX_SIZE:,} bytes (skipped)")
            print(f"✓ Real content size: {real_content_size:,} bytes")
            print(f"✓ Verification: {total_size} = {RANDOM_PREFIX_SIZE} + {real_content_size}")

            # Check if the response starts with random data (first 1,024,000 bytes should be random)
            first_chunk = total_content[:100]
            print(f"✓ First 100 bytes (should be random): {first_chunk[:50].hex()}...")

            # Save the real content to a file
            filename = "extracted_real_content.dat"
            with open(filename, 'wb') as f:
                f.write(real_content)

            print(f"✓ Real content saved to: {filename}")
            print(f"✓ File size on disk: {os.path.getsize(filename):,} bytes")

            # Show a preview of the real content (first 200 bytes)
            if real_content_size > 0:
                print(f"✓ First 200 bytes of real content:")
                try:
                    # Try to decode as text first
                    preview_text = real_content[:200].decode('utf-8', errors='replace')
                    print(f"   Text preview: {preview_text[:100]}...")
                except:
                    # If not text, show as hex
                    preview_hex = real_content[:50].hex()
                    print(f"   Binary preview: {preview_hex}...")
            else:
                print("⚠ Warning: No real content found after random prefix")

            # Verify content integrity
            if real_content_size > 0:
                print("✓ Response contains random prefix + real downloaded content")
            else:
                print("! Warning: Response only contains random prefix, no downloaded content")

        else:
            print(f"✗ Error! Status code: {response.status_code}")
            print(f"✗ Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Server is not running!")
        print("Please start the server first: python3 main.py")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


if __name__ == "__main__":
    print("File Download Server Test Script")
    print("Make sure the server is running (python3 main.py) before running this test.")
    print()

    time.sleep(2)  # Give time to read the instructions
    test_server()