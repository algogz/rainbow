# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A simple HTTP file download proxy server that accepts POST requests with a target URL, downloads the file (with automatic redirect handling), prepends 1,024,000 bytes of cryptographically secure random data, and returns the combined content as a downloadable file.

## Development Commands

```bash
# Install dependencies (uses uv for Python package management)
pip3 install -e .

# Start the server (runs on port 30080)
python3 main.py

# Run the test suite (requires server to be running)
python3 test_server.py
```

## Architecture

### Server Implementation (`main.py`)
- Built on Python's built-in `HTTPServer` and `BaseHTTPRequestHandler` - no external web framework
- Single endpoint: `POST /test` (note: documentation mentions `/download` but code implements `/test`)
- Default configuration: `0.0.0.0:30080`

### Request Flow
1. Client sends POST to `/test` with JSON body: `{"url": "https://example.com/file"}`
2. Server parses request and validates URL presence
3. Server downloads target file using `requests` library with redirect following
4. Server generates 1,024,000 bytes random prefix using `os.urandom()`
5. Server returns: `random_prefix (1MB) + downloaded_content`

### Key Constants
- `RANDOM_PREFIX_SIZE = 1024000` (1,024,000 bytes)
- Download timeout: 30 seconds
- Stream chunk size: 8,192 bytes (8KB)

### Error Handling
- 400: Invalid JSON or missing URL
- 404: Wrong endpoint
- 500: Download failures or processing errors

## Python Environment

- **Target Python Version**: 3.14+
- **Local Path** (macOS): `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`

## Testing

The test script (`test_server.py`) validates:
- Correct endpoint response
- Content structure (random prefix + real content)
- File size verification
- Automatic extraction of real content by skipping the random prefix

## Notes

- The README.md documents port 8080 and endpoint `/download`, but the actual implementation uses port 30080 and endpoint `/test`. The test script uses `/download` with port 30080, suggesting the endpoint may have been renamed without updating all references.
