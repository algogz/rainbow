# File Download Web Server

A simple Python web server that accepts HTTP POST or GET requests to either download files from a URL or serve local files from the server's filesystem, with all responses prefixed with 1,024,000 bytes of random data.

**Data Encoding**: The server uses RSA encryption with OAEP padding. The client encrypts a `<type>:<value>` string with the public key and base64-encodes the result.

## Features

- **HTTP POST/GET Endpoint**: `/test` endpoint that accepts JSON requests or a `?seed=<encoded>` query string
- **URL Download**: Downloads files from any URL with automatic redirection support
- **Local File Serving**: Serves files from the server's local filesystem with security validation
- **Random Prefix**: Prepends 1,024,000 bytes of random data to all file content
- **Timestamp Filenames**: Generates response filenames with timestamp + original filename (e.g., `202511232358_example.pdf`)
- **Security**: Path validation prevents directory traversal attacks
- **Custom Encoding**: Uses RSA OAEP (SHA256) encryption + base64 encoding for the payload
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

The server expects the RSA-encrypted payload either as the `data` JSON field (POST) or
as a query parameter named `seed` (GET, with `data` accepted as a legacy alias):

1. **Format**: `<type>:<value>` where type is either `url` or `path`
2. **Process**:
   - Start with: `url:https://example.com/file.pdf` or `path:/path/to/file`
   - **RSA encrypt with `public_key.pem`** (OAEP + SHA256)
   - **Encode with base64**

### Encoding Examples

**Python Example:**
```python
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

def encode_data(data_type, value, public_key):
    """Encode data for the server request"""
    data_str = f"{data_type}:{value}"
    encrypted = public_key.encrypt(
        data_str.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(encrypted).decode("utf-8")

public_key = serialization.load_pem_public_key(open("public_key.pem", "rb").read())
url_encoded = encode_data("url", "https://example.com/file.pdf", public_key)
path_encoded = encode_data("path", "./data/report.pdf", public_key)
```

**Bash Example:**
```bash
# The helper client (dl.py) can print the encoded payload for you:
python dl.py https://example.com/file.pdf -m GET
```

### Make Requests

**Download via POST (JSON body):**
```bash
ENCODED_DATA="<base64-rsa payload from dl.py / your encoder>"

curl -X POST http://localhost:30080/test \
  -H "Content-Type: application/json" \
  -d "{\"data\": \"$ENCODED_DATA\"}" \
  --output downloaded_file.dat
```

**Download via GET (seed query parameter):**
```bash
ENCODED_DATA="<base64-rsa payload from dl.py / your encoder>"

curl -G http://localhost:30080/test \
  --data-urlencode "seed=$ENCODED_DATA" \
  --output downloaded_file.dat
```

The GET `seed` value is the exact same encrypted payload the POST `data` field carries,
so both methods reuse the same decode + download pipeline on the server.

### Request Format

**Endpoints**:
- `POST /test` with JSON body `{"data": "<encoded>"}`
- `GET /test?seed=<encoded>` (`?data=<encoded>` is kept as a legacy alias)

**Headers** (POST):
- `Content-Type: application/json`

**Encoding Steps**:
1. Create string: `url:<actual_url>` or `path:<file_path>`
2. RSA-encrypt the string with the public key (OAEP + SHA256)
3. Base64-encode the encrypted bytes

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

By default, the server allows downloading any file that the server process has access to. This can be restricted using the `BASE_DIR` constant in `main.py`:

```python
# Default: Allow all paths (respects OS file permissions)
BASE_DIR = ''

# To restrict to a specific directory:
BASE_DIR = '/var/www/files'
```

### Security Features

- **OS Permission Respect**: Only serves files that the server process has read access to
- **File Type Validation**: Only serves regular files (not directories or special files)
- **Data Validation**: Only accepts `url:` or `path:` prefixes after decoding
- **Optional Base Directory**: Can be configured to restrict access to a specific directory

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
3. **GET seed Test**: Tests `GET /test?seed=<payload>` returns the same payload as POST
4. **Security Test**: Tests path traversal attack prevention
5. **Invalid Data Type Test**: Tests error handling for invalid data prefixes

### Content Extraction

The test script automatically extracts the real downloaded content by skipping the first 1,024,000 random bytes:

- **Total Response**: 1,024,000 bytes random + real content
- **Extracted Content**: Only the downloaded file content
- **Saved Files**: `extracted_url_content.dat`, `extracted_local_file.txt`

The request payload is RSA-encrypted; decrypting an intercepted payload requires
`private_key.pem` and is out of scope for the response-extraction helpers.

### Manual Content Extraction

To manually extract the real content from downloaded files:

```python
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
- **Data Encoding**: RSA OAEP (SHA256) encryption + base64 encoding for the payload
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
- Missing 'data' body field (POST) or 'seed' query parameter (GET)
- Invalid base64 encoding
- Invalid data type prefix (not `url:` or `path:`)
- Network errors during URL download
- HTTP errors (404, 500, etc.) from target URL
- Timeouts during URL download
- Invalid URLs
- Local file not found
- Local file path outside allowed base directory
- Permission denied when reading local file
