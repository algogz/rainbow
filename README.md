# File Download Web Server

A simple Python web server that accepts HTTP POST requests to either download files from a URL or serve local files from the server's filesystem, with all responses prefixed with 1,024,000 bytes of random data.

**Data Encoding**: The server uses a custom encoding scheme where the data parameter is base64-encoded and contains a reversed string with type prefix (`url:` or `path:`).

## Features

- **HTTP POST Endpoint**: `/test` endpoint that accepts JSON requests
- **URL Download**: Downloads files from any URL with automatic redirection support
- **Local File Serving**: Serves files from the server's local filesystem with security validation
- **Random Prefix**: Prepends 1,024,000 bytes of random data to all file content
- **Timestamp Filenames**: Generates response filenames with timestamp + original filename (e.g., `202511232358_example.pdf`)
- **Security**: Path validation prevents directory traversal attacks
- **Custom Encoding**: Uses reversed + base64 encoding for the data parameter
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## Installation

```bash
pip3 install -e .
```

## Usage

### Start the Server

```bash
python3 main.py
```

The server will start on `http://localhost:30080` by default.

### Data Encoding Format

The server expects a single `data` parameter that contains:

1. **Format**: `<type>:<value>` where type is either `url` or `path`
2. **Process**:
   - Start with: `url:https://example.com/file.pdf` or `path:/path/to/file`
   - **Reverse the string**
   - **Encode with base64**

### Encoding Examples

**Python Example:**
```python
import base64

def encode_data(data_type, value):
    """Encode data for the server request"""
    # Create the data string with type prefix
    data_str = f"{data_type}:{value}"
    # Reverse the string
    reversed_str = data_str[::-1]
    # Encode to bytes and then base64
    encoded_bytes = base64.b64encode(reversed_str.encode('utf-8'))
    return encoded_bytes.decode('utf-8')

# URL download example
url_encoded = encode_data('url', 'https://example.com/file.pdf')

# Local file example
path_encoded = encode_data('path', './data/report.pdf')
```

**Bash Example:**
```bash
# Encode URL download request
echo -n "url:https://example.com/file.pdf" | rev | base64

# Encode local file request
echo -n "path:/path/to/file" | rev | base64
```

### Make Requests

**Download from URL:**
```bash
# Step 1: Encode the data
ENCODED_DATA=$(echo -n "url:https://httpbin.org/get" | rev | base64)

# Step 2: Send the request
curl -X POST http://localhost:30080/test \
  -H "Content-Type: application/json" \
  -d "{\"data\": \"$ENCODED_DATA\"}" \
  --output downloaded_file.dat
```

**Serve local file:**
```bash
# Step 1: Encode the data
ENCODED_DATA=$(echo -n "path:/path/to/local/file.pdf" | rev | base64)

# Step 2: Send the request
curl -X POST http://localhost:30080/test \
  -H "Content-Type: application/json" \
  -d "{\"data\": \"$ENCODED_DATA\"}" \
  --output downloaded_file.dat
```

### Request Format

**Endpoint**: `POST /test`

**Headers**:
- `Content-Type: application/json`

**Body**:
```json
{
  "data": "<base64_encoded_reversed_string>"
}
```

**Encoding Steps**:
1. Create string: `url:<actual_url>` or `path:<file_path>`
2. Reverse the entire string
3. Encode the reversed string with base64

**Security Note**: Local file serving is restricted to files within the server's current working directory by default. This can be configured by modifying the `BASE_DIR` constant in `main.py`.

### Response Format

**Success Response** (Status: 200):
- **Content-Type**: `application/octet-stream`
- **Content-Disposition**: `attachment; filename="YYYYMMDDHHMM_original_filename.ext"` (or `.dat` if no original filename)
- **Content**: 1,024,000 bytes of random data + file content

**Error Responses**:
- **400 Bad Request**: Invalid JSON, missing 'data' field, or invalid data type prefix
- **403 Forbidden**: Local file path is outside the allowed base directory
- **404 Not Found**: Wrong endpoint or local file not found
- **500 Internal Server Error**: Invalid base64 encoding, download or processing errors

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
- **File Existence Check**: Returns error if file doesn't exist
- **Regular File Check**: Only serves regular files (not directories or special files)
- **Data Validation**: Only accepts `url:` or `path:` prefixes after decoding

### Example Local File Request

```python
import requests
import base64

def encode_data(data_type, value):
    data_str = f"{data_type}:{value}"
    reversed_str = data_str[::-1]
    encoded_bytes = base64.b64encode(reversed_str.encode('utf-8'))
    return encoded_bytes.decode('utf-8')

# Serve a file from the server's filesystem
encoded_data = encode_data('path', './data/report.pdf')
response = requests.post(
    'http://localhost:30080/test',
    json={'data': encoded_data},
    stream=True
)

if response.status_code == 200:
    with open('downloaded_report.pdf', 'wb') as f:
        # Skip first 1MB (random prefix)
        f.write(response.content[1024000:])
```

## Client Script

A convenient client script `dl.py` is provided for downloading files via the rainbow server. It automatically handles the encoding/decoding and removes the random prefix.

### Usage

```bash
# Download from URL
python dl.py https://example.com/file.pdf

# Serve local file from server
python dl.py /path/to/local/file.txt

# Specify custom output filename
python dl.py https://example.com/file.pdf -o my_file.pdf

# Use custom server URL
python dl.py https://example.com/file.pdf --server http://remote-server:30080
```

### How It Works

The client script:
1. **Auto-detects mode**: If location starts with `http://` or `https://`, uses URL mode; otherwise uses local file mode
2. **Encodes the request**: Applies the reverse + base64 encoding required by the server
3. **Downloads the file**: Streams the response from the server
4. **Removes the prefix**: Strips the 1MB random prefix from the response
5. **Saves the file**: Writes the real content to disk with the correct filename

### Example Output

```
$ python dl.py https://httpbin.org/json
Mode: URL download
URL: https://httpbin.org/json

Connecting to server: http://localhost:30080/test

Receiving data...
Total size: 1,024,429 bytes
Random prefix: 1,024,000 bytes (removed)
Real content: 429 bytes

✓ Saved to: json
✓ File size: 429 bytes
```

## Testing

Run the test script to verify the server works:

```bash
# Terminal 1: Start the server
python3 main.py

# Terminal 2: Run the test
python3 test_server.py
```

The test suite includes:
1. **URL Download Test**: Tests URL download with redirects
2. **Local File Serving Test**: Tests local file serving with integrity verification
3. **Security Test**: Tests path traversal attack prevention
4. **Invalid Data Type Test**: Tests error handling for invalid data prefixes

### Content Extraction

The test script automatically extracts the real downloaded content by skipping the first 1,024,000 random bytes:

- **Total Response**: 1,024,000 bytes random + real content
- **Extracted Content**: Only the downloaded file content
- **Saved Files**: `extracted_url_content.dat`, `extracted_local_file.txt`

### Manual Content Extraction

To manually extract the real content from downloaded files:

```python
import base64

# Helper function to decode the data format
def decode_data(encoded_data):
    """Decode base64 encoded and reversed data string"""
    decoded_bytes = base64.b64decode(encoded_data)
    decoded_str = decoded_bytes.decode('utf-8')
    reversed_str = decoded_str[::-1]  # Reverse back
    return reversed_str

# Extract real content from response
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
- **Data Encoding**: Base64 + reverse encoding for obfuscation
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
- Missing 'data' field
- Invalid base64 encoding
- Invalid data type prefix (not `url:` or `path:`)
- Network errors during URL download
- HTTP errors (404, 500, etc.) from target URL
- Timeouts during URL download
- Invalid URLs
- Local file not found
- Local file path outside allowed base directory
- Permission denied when reading local file
