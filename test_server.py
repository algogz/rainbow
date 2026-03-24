#!/usr/bin/env python3
"""
Test script for the rainbow server
"""
import requests
import json
import time
import os


def test_url_download():
    """Test URL download functionality"""
    base_url = "http://localhost:30080"

    print("\n" + "=" * 60)
    print("TEST 1: URL Download")
    print("=" * 60)

    # Test with a sample URL that will redirect
    test_url = "https://httpbin.org/redirect/2"  # This will redirect to /get

    # Define constants
    RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes

    # Prepare the request data
    request_data = {
        "url": test_url
    }

    try:
        print(f"Sending POST request to {base_url}/test")
        print(f"Target URL: {test_url}")
        print()

        # Send POST request
        response = requests.post(
            f"{base_url}/test",
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
                return False

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
            filename = "extracted_url_content.dat"
            with open(filename, 'wb') as f:
                f.write(real_content)

            print(f"✓ Real content saved to: {filename}")
            print(f"✓ File size on disk: {os.path.getsize(filename):,} bytes")

            # Verify content integrity
            if real_content_size > 0:
                print("✓ Response contains random prefix + real downloaded content")
                return True
            else:
                print("! Warning: Response only contains random prefix, no downloaded content")
                return False

        else:
            print(f"✗ Error! Status code: {response.status_code}")
            print(f"✗ Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Server is not running!")
        print("Please start the server first: python3 main.py")
        return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_local_file():
    """Test local file serving functionality"""
    base_url = "http://localhost:30080"

    print("\n" + "=" * 60)
    print("TEST 2: Local File Serving")
    print("=" * 60)

    # Define constants
    RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes

    # Create a test file
    test_filename = "test_local_file.txt"
    test_content = b"This is a test file for local file serving.\n" * 100  # ~3KB

    try:
        # Create test file
        with open(test_filename, 'wb') as f:
            f.write(test_content)
        print(f"✓ Created test file: {test_filename} ({len(test_content)} bytes)")

        # Prepare the request data
        request_data = {
            "path": test_filename
        }

        print(f"\nSending POST request to {base_url}/test")
        print(f"Local file path: {test_filename}")
        print()

        # Send POST request
        response = requests.post(
            f"{base_url}/test",
            json=request_data,
            timeout=60,
            stream=True
        )

        if response.status_code == 200:
            print(f"✓ Success! Response status: {response.status_code}")
            print(f"✓ Content-Type: {response.headers.get('Content-Type')}")
            print(f"✓ Content-Disposition: {response.headers.get('Content-Disposition')}")

            # Get total content size
            total_content = response.content
            total_size = len(total_content)
            print(f"✓ Total download size: {total_size:,} bytes")

            # Verify the file structure: 1,024,000 bytes random + file content
            if total_size <= RANDOM_PREFIX_SIZE:
                print(f"✗ Error: Response size ({total_size}) is smaller than expected random prefix ({RANDOM_PREFIX_SIZE})")
                return False

            # Extract and save only the real file content (skip random prefix)
            received_content = total_content[RANDOM_PREFIX_SIZE:]
            received_size = len(received_content)

            print(f"✓ Random prefix size: {RANDOM_PREFIX_SIZE:,} bytes (skipped)")
            print(f"✓ Real content size: {received_size:,} bytes")
            print(f"✓ Verification: {total_size} = {RANDOM_PREFIX_SIZE} + {received_size}")

            # Save the received content to a file
            output_filename = "extracted_local_file.txt"
            with open(output_filename, 'wb') as f:
                f.write(received_content)

            print(f"✓ Extracted content saved to: {output_filename}")
            print(f"✓ File size on disk: {os.path.getsize(output_filename):,} bytes")

            # Verify content integrity
            if received_content == test_content:
                print("✓ Content integrity verified: received content matches original file")
                return True
            else:
                print("✗ Error: Received content does not match original file")
                print(f"  Expected size: {len(test_content)}, Received size: {len(received_content)}")
                return False

        else:
            print(f"✗ Error! Status code: {response.status_code}")
            print(f"✗ Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Server is not running!")
        print("Please start the server first: python3 main.py")
        return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

    finally:
        # Clean up test file
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print(f"\n✓ Cleaned up test file: {test_filename}")


def test_security_validation():
    """Test security: path traversal prevention"""
    base_url = "http://localhost:30080"

    print("\n" + "=" * 60)
    print("TEST 3: Security - Path Traversal Prevention")
    print("=" * 60)

    # Try to access a file outside the allowed directory
    request_data = {
        "path": "../../../etc/passwd"  # Try to access system file
    }

    print(f"Sending POST request with path traversal attempt: {request_data['path']}")
    print()

    try:
        response = requests.post(
            f"{base_url}/test",
            json=request_data,
            timeout=10
        )

        if response.status_code == 500 or response.status_code == 403:
            print(f"✓ Security test passed! Server rejected the path traversal attempt.")
            print(f"✓ Status code: {response.status_code}")
            try:
                error = response.json()
                print(f"✓ Error message: {error.get('error', 'N/A')}")
            except:
                print(f"✓ Response: {response.text[:200]}")
            return True
        else:
            print(f"✗ Security test failed! Server accepted the path traversal attempt.")
            print(f"✗ Status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error during security test: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Rainbow Server Test Suite")
    print("=" * 60)
    print("Make sure the server is running (python3 main.py) before running this test.")
    print()

    time.sleep(2)  # Give time to read the instructions

    # Run all tests
    results = []

    results.append(("URL Download", test_url_download()))
    results.append(("Local File Serving", test_local_file()))
    results.append(("Security Validation", test_security_validation()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    main()