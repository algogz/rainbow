# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A simple HTTP file download proxy server that accepts POST requests to either download files from a URL or serve local files from the server's filesystem. All responses are prepended with 1,024,000 bytes of cryptographically secure random data before being returned.

**Data Encoding**: The server uses a custom encoding scheme where the data parameter is a base64-encoded string containing a reversed type prefix (`url:` or `path:`) and value.

## Development Commands

```bash
# Install dependencies
pip3 install -e .

# Start the server (runs on port 30080)
python3 main.py

# Run the test suite (requires server to be running)
python3 test_server.py
```

## Architecture

### Server Implementation (`main.py`)
- Built on Python's built-in `HTTPServer` and `BaseHTTPRequestHandler` - no external web framework
- Single endpoint: `POST /test`
- Default configuration: `0.0.0.0:30080`

### Data Encoding Scheme

**Client Side (Encoding)**:
1. Create string: `url:<actual_url>` or `path:<file_path>`
2. Reverse the entire string: `:<lru_atuala>#` or `>:elif_atuala#` (reversed)
3. Base64 encode the reversed string

**Server Side (Decoding)**:
1. Base64 decode the input
2. Reverse the string back to original
3. Extract type prefix (`url:` or `path:`) and value

### Request Flow

1. Client sends POST to `/test` with JSON: `{"data": "<base64_encoded_reversed_string>"}`
2. Server base64 decodes and reverses the data string
3. Server checks if decoded string starts with `url:` or `path:`
4. Server either downloads from URL or reads local file
5. Server generates 1,024,000 bytes random prefix using `os.urandom()`
6. Server returns: `random_prefix (1MB) + file_content`

### Key Constants
- `RANDOM_PREFIX_SIZE = 1024000` (1,024,000 bytes)
- `BASE_DIR = os.path.abspath('.')` - restricts local file access to current directory
- Download timeout: 30 seconds
- Stream chunk size: 8,192 bytes (8KB)

### Security Features
- **Path Validation**: Absolute path resolution prevents `../` directory traversal
- **Base Directory Restriction**: Files outside `BASE_DIR` are rejected with error
- **Data Type Validation**: Only accepts `url:` or `path:` prefixes after decoding
- **Base64 Validation**: Rejects invalid base64 encoding

### Error Handling
- 400: Invalid JSON, missing 'data' field, or invalid data type prefix
- 403: File path outside allowed base directory
- 404: Wrong endpoint or local file not found
- 500: Invalid base64 encoding, download failures, or file read errors

## Python Environment

- **Target Python Version**: 3.14+
- **Local Path** (macOS): `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`

## Testing

The test script (`test_server.py`) includes four test suites:
1. **URL Download Test**: Validates URL download with redirects and random prefix
2. **Local File Serving Test**: Creates test file and validates local file serving
3. **Security Test**: Validates path traversal attack prevention
4. **Invalid Data Type Test**: Validates error handling for invalid data prefixes

All tests verify:
- Correct endpoint response
- Content structure (random prefix + real content)
- File size verification
- Automatic extraction of real content by skipping the random prefix

## Encoding Helper

To encode data for requests:
```python
import base64

def encode_data(data_type, value):
    """Encode data for the server request"""
    data_str = f"{data_type}:{value}"
    reversed_str = data_str[::-1]
    encoded_bytes = base64.b64encode(reversed_str.encode('utf-8'))
    return encoded_bytes.decode('utf-8')

# Usage
encoded = encode_data('url', 'https://example.com/file.pdf')
# or
encoded = encode_data('path', './local/file.pdf')
```

## Client Script (`dl.py`)

A convenient client script is provided for downloading files. It handles:
- Auto-detection of mode (URL vs local file) based on input
- Encoding/decoding of the data parameter
- Removal of the random prefix from server responses
- Proper filename handling

### Usage
```bash
# Download from URL
python dl.py https://example.com/file.pdf

# Serve local file
python dl.py /path/to/local/file.txt

# Custom output filename
python dl.py https://example.com/file.pdf -o my_file.pdf

# Custom server URL
python dl.py https://example.com/file.pdf --server http://remote-server:30080
```

### Mode Detection
- If location starts with `http://` or `https://` (case-insensitive) → URL mode
- Otherwise → Local file mode

