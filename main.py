import os
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


# Load private key at module level
PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), 'private_key.pem')

def load_private_key():
    """Load RSA private key from file"""
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())


class FileDownloadHandler(BaseHTTPRequestHandler):
    BASE_DIR = ""
    TIMEOUT_SECONDS = 30
    CHUNK_SIZE = 8192
    RANDOM_PREFIX_SIZE = 1024000

    ENDPOINT = "/test"
    # Accepted GET query parameters. "seed" is the canonical name; "data" is
    # kept as a backward-compatible alias for older clients.
    QUERY_PARAMS = ("seed", "data")

    def do_POST(self):
        """Handle POST requests with encoded data in the JSON body."""
        if not self._check_endpoint():
            return

        encoded_data = self._read_encoded_data_from_body()
        if encoded_data is None:
            return

        self._dispatch(encoded_data)

    def do_GET(self):
        """Handle GET requests with the encoded data in the query string."""
        if not self._check_endpoint():
            return

        encoded_data = self._read_encoded_data_from_query()
        if encoded_data is None:
            return

        self._dispatch(encoded_data)

    def _check_endpoint(self):
        """Return True when the request targets the supported endpoint."""
        if urlparse(self.path).path != self.ENDPOINT:
            self._send_error(404, f"Not Found. Use {self.ENDPOINT} endpoint")
            return False
        return True

    def _read_encoded_data_from_body(self):
        """Extract the encoded payload from the JSON POST body.

        Returns the encoded string, or None after sending an error response.
        """
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            request_data = json.loads(post_data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(400, "Invalid JSON in request body")
            return None

        encoded_data = request_data.get("data") if isinstance(request_data, dict) else None
        if not encoded_data:
            self._send_error(400, "Missing 'data' field in request body")
            return None

        return encoded_data

    def _read_encoded_data_from_query(self):
        """Extract the encoded payload from the GET query string.

        Returns the encoded string, or None after sending an error response.
        """
        query_params = parse_qs(urlparse(self.path).query)

        for name in self.QUERY_PARAMS:
            values = query_params.get(name)
            if values and values[0]:
                return values[0]

        self._send_error(
            400,
            f"Missing '{self.QUERY_PARAMS[0]}' query parameter",
        )
        return None

    def _dispatch(self, encoded_data):
        """Run the shared download pipeline, guarding against client aborts."""
        try:
            self._handle_request(encoded_data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_error(500, f"Internal server error: {str(e)}")
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _handle_request(self, encoded_data):
        """Common handler for both POST and GET requests"""
        try:
            # Decode and parse the data
            try:
                # Base64 decode
                encrypted_data = base64.b64decode(encoded_data)
                # RSA decrypt with private key
                private_key = load_private_key()
                decrypted_bytes = private_key.decrypt(
                    encrypted_data,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                data_str = decrypted_bytes.decode('utf-8')

                # Extract type and value
                if data_str.startswith("url:"):
                    data_type, data_value = "url", data_str[4:]
                elif data_str.startswith("path:"):
                    data_type, data_value = "path", data_str[5:]
                else:
                    self._send_error(
                        400, "Decrypted data must start with 'url:' or 'path:'"
                    )
                    return
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                # Base64 or decryption errors - let outer handler catch as 500
                raise Exception(f"Data decoding error: {str(e)}")

            if data_type == "url":
                original_filename = self._extract_filename_from_url(data_value)
                content_size = self._get_url_content_size(data_value)
                content_generator = self._download_file_streaming(data_value)
            elif data_type == "path":
                original_filename = os.path.basename(data_value)
                content_size = self._get_local_file_size(data_value)
                content_generator = self._read_local_file_streaming(data_value)
            else:
                self._send_error(
                    400, f"Invalid data type. Must start with 'url:' or 'path:'"
                )
                return

            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            filename = (
                f"{timestamp}_{original_filename}"
                if original_filename
                else f"{timestamp}.dat"
            )

            self._send_response_with_size(content_generator, content_size, filename)

        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_error(500, f"Internal server error: {str(e)}")
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _download_file_streaming(self, url):
        """Download file from URL as a streaming generator"""
        try:
            response = requests.get(
                url,
                stream=True,
                allow_redirects=True,
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FileDownloader/1.0)"},
            )
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                if chunk:
                    yield chunk

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download file from {url}: {str(e)}")

    def _read_local_file_streaming(self, file_path):
        """Read local file as a streaming generator"""
        abs_path = os.path.abspath(file_path)

        try:
            with open(abs_path, "rb") as f:
                while True:
                    chunk = f.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except OSError as e:
            raise Exception(f"Failed to read local file {file_path}: {str(e)}")

    def _extract_filename_from_url(self, url):
        """Extract filename from URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            filename = os.path.basename(path)
            return filename if filename else None
        except Exception:
            return None

    def _get_local_file_size(self, file_path):
        """Get the size of a local file"""
        abs_path = os.path.abspath(file_path)

        if self.BASE_DIR:
            if not abs_path.startswith(self.BASE_DIR):
                raise Exception(
                    f"Access denied: file path is outside allowed directory. "
                    f"Requested: {abs_path}, Allowed base: {self.BASE_DIR}"
                )

        if not os.path.exists(abs_path):
            raise Exception(f"File not found: {file_path}")

        if not os.path.isfile(abs_path):
            raise Exception(f"Path is not a file: {file_path}")

        return os.path.getsize(abs_path)

    def _get_url_content_size(self, url):
        """Get the content size of a URL by making a HEAD request"""
        try:
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=self.TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FileDownloader/1.0)"},
            )
            response.raise_for_status()

            content_length = response.headers.get('Content-Length')
            if content_length:
                return int(content_length)
            else:
                raise Exception(f"Server does not provide Content-Length header for {url}. Cannot determine file size for streaming.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get content size from {url}: {str(e)}")

    def _send_response_with_size(self, content_generator, content_size, filename):
        """Send response with known content size - writes random prefix first, then streams content"""
        total_size = self.RANDOM_PREFIX_SIZE + content_size

        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(total_size))
        self.send_header("Server", "nginx")
        self.send_header("Last-Modified", "Mon, 15 Jan 2024 12:00:00 GMT")
        self.end_headers()

        try:
            # Write random prefix in chunks
            remaining = self.RANDOM_PREFIX_SIZE
            chunk_size = 8192
            while remaining > 0:
                chunk = os.urandom(min(chunk_size, remaining))
                self.wfile.write(chunk)
                remaining -= len(chunk)

            # Stream content
            for chunk in content_generator:
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        error_response = {"error": message}
        self.wfile.write(json.dumps(error_response).encode("utf-8"))

    def log_message(self, format, *args):
        """Override to customize logging format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host="0.0.0.0", port=30080):
    """Start the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, FileDownloadHandler)

    print(f"File Download Server started on http://{host}:{port}")
    print("\nSupported endpoints:")
    print("  POST /test  - with JSON body: {'data': '<encoded>'}")
    print("  GET /test   - with query: ?seed=<encoded>  ('data' also accepted)")
    print("\nData encoding:")
    print("  1. Create string: 'url:<actual_url>' or 'path:<file_path>'")
    print("  2. RSA encrypt with public_key.pem (OAEP + SHA256)")
    print("  3. Base64 encode")
    print("\nExample:")
    print("  'url:https://example.com/file.pdf' → RSA encrypt → base64 encode")
    print("  'path:/path/to/local/file' → RSA encrypt → base64 encode")
    print(
        "\nNote: Local files are served with current directory as base (configurable via BASE_DIR)"
    )
    print("\nPress Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is shutting down...")
        httpd.server_close()


def main():
    """Main function to start the server"""
    run_server()


if __name__ == "__main__":
    main()
