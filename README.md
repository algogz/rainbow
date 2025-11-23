# File Download Web Server

A simple Python web server that accepts HTTP POST requests with a target URL, downloads the file from that URL (with redirection support), and returns the file content prefixed with 1,024,000 bytes of random data.

## Features

- **HTTP POST Endpoint**: `/download` endpoint that accepts JSON requests
- **File Download**: Downloads files from any URL with automatic redirection support
- **Random Prefix**: Prepends 1,024,000 bytes of random data to downloaded content
- **Timestamp Filenames**: Generates response filenames with timestamp format (e.g., `202511232358.dat`)
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

The server will start on `http://localhost:8080` by default.

### Make Requests

Send POST requests to `/download` endpoint with JSON body:

```bash
curl -X POST http://localhost:8080/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.pdf"}' \
  --output downloaded_file.dat
```

### Request Format

**Endpoint**: `POST /download`

**Headers**:
- `Content-Type: application/json`

**Body**:
```json
{
  "url": "https://example.com/target-file"
}
```

### Response Format

**Success Response** (Status: 200):
- **Content-Type**: `application/octet-stream`
- **Content-Disposition**: `attachment; filename="YYYYMMDDHHMM.dat"`
- **Content**: 1,024,000 bytes of random data + downloaded file content

**Error Responses**:
- **400 Bad Request**: Invalid JSON or missing URL
- **404 Not Found**: Wrong endpoint
- **500 Internal Server Error**: Download or processing errors

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
- **Redirection Support**: Built-in support for HTTP redirects using the `requests` library
- **Memory Efficiency**: Streams large files in 8KB chunks to handle files of any size
- **Timeout**: 30-second timeout for downloads to prevent hanging

## Configuration

You can modify the server host and port in `main.py`:

```python
run_server(host='0.0.0.0', port=8080)  # Listen on all interfaces
```

## Dependencies

- Python 3.14+
- requests >= 2.31.0

## Error Scenarios Handled

- Invalid JSON request body
- Missing URL field in request
- Network errors during download
- HTTP errors (404, 500, etc.) from target URL
- Timeouts during download
- Invalid URLs