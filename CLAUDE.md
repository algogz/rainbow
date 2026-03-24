# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A simple HTTP file download proxy server that accepts POST requests to either download files from a URL or serve local files from the server's filesystem. All responses are prepended with 1,024,000 bytes of cryptographically secure random data before being returned.

## Development Commands

```bash
# Install dependencies (uses pip for Python package management)
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

### Request Flow

**URL Download Mode:**
1. Client sends POST to `/test` with JSON body: `{"url": "https://example.com/file"}`
2. Server parses request and validates either `url` or `path` (not both)
3. Server downloads target file using `requests` library with redirect following
4. Server generates 1,024,000 bytes random prefix using `os.urandom()`
5. Server returns: `random_prefix (1MB) + downloaded_content`

**Local File Mode:**
1. Client sends POST to `/test` with JSON body: `{"path": "./local/file.pdf"}`
2. Server validates path is within `BASE_DIR` (default: current directory)
3. Server reads local file in 8KB chunks
4. Server generates 1,024,000 bytes random prefix using `os.urandom()`
5. Server returns: `random_prefix (1MB) + file_content`

### Key Constants
- `RANDOM_PREFIX_SIZE = 1024000` (1,024,000 bytes)
- `BASE_DIR = os.path.abspath('.')` - restricts local file access to current directory
- Download timeout: 30 seconds
- Stream chunk size: 8,192 bytes (8KB)

### Security Features
- **Path Validation**: Absolute path resolution prevents `../` directory traversal
- **Base Directory Restriction**: Files outside `BASE_DIR` are rejected with error
- **Mutual Exclusivity**: Request must contain either `url` OR `path`, not both

### Error Handling
- 400: Invalid JSON, missing both fields, or both fields provided
- 403: File path outside allowed base directory
- 404: Wrong endpoint or local file not found
- 500: Download failures, processing errors, or file read errors

## Python Environment

- **Target Python Version**: 3.14+
- **Local Path** (macOS): `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`

## Testing

The test script (`test_server.py`) includes three test suites:
1. **URL Download Test**: Validates URL download with redirects and random prefix
2. **Local File Serving Test**: Creates test file and validates local file serving
3. **Security Test**: Validates path traversal attack prevention

All tests verify:
- Correct endpoint response
- Content structure (random prefix + real content)
- File size verification
- Automatic extraction of real content by skipping the random prefix
