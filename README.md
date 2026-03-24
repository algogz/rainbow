# File Download Web Server

A simple Python web server that accepts HTTP POST requests to either download files from a URL or serve local files from the server's filesystem, with all responses prefixed with 1,024,000 bytes of random data.

## Features

- **HTTP POST Endpoint**: `/test` endpoint that accepts JSON requests
- **URL Download**: Downloads files from any URL with automatic redirection support
- **Local File Serving**: Serves files from the server's local filesystem with security validation
- **Random Prefix**: Prepends 1,024,000 bytes of random data to all file content
- **Timestamp Filenames**: Generates response filenames with timestamp + original filename (e.g., `202511232358_example.pdf`)
- **Security**: Path validation prevents directory traversal attacks
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## Installation

1. Install dependencies:
```bash
pip3 install -e .
```

## Usage

### Start the Server

```bash
python3 main.py
```

The server will start on `http://localhost:30080` by default.

### Make Requests

Send POST requests to `/test` endpoint with JSON body.

**Download from URL:**
```bash
curl -X POST http://localhost:30080/test \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.pdf"}' \
  --output downloaded_file.dat
```

**Serve local file:**
```bash
curl -X POST http://localhost:30080/test \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/local/file.pdf"}' \
  --output downloaded_file.dat
```

### Request Format

**Endpoint**: `POST /test`

**Headers**:
- `Content-Type: application/json`

**Body** (choose one):
```json
{
  "url": "https://example.com/target-file"
}
```

OR

```json
{
  "path": "/path/to/local/file"
}
```

**Security Note**: Local file serving is restricted to files within the server's current working directory by default. This can be configured by modifying the `BASE_DIR` constant in `main.py`.

### Response Format

**Success Response** (Status: 200):
- **Content-Type**: `application/octet-stream`
- **Content-Disposition**: `attachment; filename="YYYYMMDDHHMM_original_filename.ext"` (or `.dat` if no original filename)
- **Content**: 1,024,000 bytes of random data + file content

**Error Responses**:
- **400 Bad Request**: Invalid JSON, missing both 'url' and 'path', or both provided
- **403 Forbidden**: Local file path is outside the allowed base directory
- **404 Not Found**: Wrong endpoint or local file not found
- **500 Internal Server Error**: Download or processing errors

## Local File Serving

### Security Configuration

The server restricts local file access using the `BASE_DIR` constant in `main.py`:

```python
# Default: Allow files from current directory only
BASE_DIR = os.path.abspath('.')

# To allow all paths (not recommended for production):
BASE_DIR = ''

# To restrict to a specific directory:
BASE_DIR = '/var/www/files'
```

### Security Features

- **Path Validation**: Absolute path resolution prevents `../` directory traversal
- **Base Directory Restriction**: Files outside `BASE_DIR` are rejected
- **File Existence Check**: Returns 404 if file doesn't exist
- **Regular File Check**: Only serves regular files (not directories or special files)

### Example Local File Request

```python
import requests

# Serve a file from the server's filesystem
response = requests.post(
    'http://localhost:30080/test',
    json={'path': './data/report.pdf'},
    stream=True
)

if response.status_code == 200:
    with open('downloaded_report.pdf', 'wb') as f:
        # Skip first 1MB (random prefix)
        f.write(response.content[1024000:])
```

## Testing

Run the test script to verify the server works:

```bash
# Terminal 1: Start the server
python3 main.py

# Terminal 2: Run the test
python3 test_server.py
```

### Content Extraction

The test script automatically extracts the real downloaded content by skipping the first 1,024,000 random bytes:

- **Total Response**: 1,024,000 bytes random + real content
- **Extracted Content**: Only the downloaded file content
- **Saved File**: `extracted_real_content.dat`

The test script will:
1. Download the complete response from the server
2. Skip the first 1,024,000 bytes (random prefix)
3. Extract only the real downloaded content
4. Save it to `extracted_real_content.dat`
5. Show a preview of the real content

### Manual Content Extraction

To manually extract the real content from downloaded files:

```python
import os

RANDOM_PREFIX_SIZE = 1024000  # 1,024,000 bytes

with open('downloaded_file.dat', 'rb') as f:
    content = f.read()

# Skip random prefix and extract real content
real_content = content[RANDOM_PREFIX_SIZE:]

with open('real_content.dat', 'wb') as f:
    f.write(real_content)

print(f"Original size: {len(content):,} bytes")
print(f"Real content: {len(real_content):,} bytes")
```

## Example Implementation Details

- **Random Data Generation**: Uses `os.urandom(1024000)` for cryptographically secure random bytes
- **URL Redirection Support**: Built-in support for HTTP redirects using the `requests` library
- **Local File Access**: Reads local files in 8KB chunks for memory efficiency
- **Security**: Path sanitization using `os.path.abspath()` to prevent directory traversal
- **Timeout**: 30-second timeout for URL downloads to prevent hanging
- **Dual Mode**: Supports both URL downloads and local file serving in a single endpoint

## Configuration

You can modify the server host and port in `main.py`:

```python
run_server(host='0.0.0.0', port=30080)  # Listen on all interfaces, default port
```

## Dependencies

- Python 3.14+
- requests >= 2.31.0

## Error Scenarios Handled

- Invalid JSON request body
- Missing both 'url' and 'path' fields, or both provided together
- Network errors during URL download
- HTTP errors (404, 500, etc.) from target URL
- Timeouts during URL download
- Invalid URLs
- Local file not found
- Local file path outside allowed base directory
- Permission denied when reading local file