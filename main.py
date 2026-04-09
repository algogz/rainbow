import os
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests
from datetime import datetime


class FileDownloadHandler(BaseHTTPRequestHandler):
    BASE_DIR = ""
    TIMEOUT_SECONDS = 30
    CHUNK_SIZE = 8192
    RANDOM_PREFIX_SIZE = 1024000

    def do_POST(self):
        """Handle POST requests with encoded data parameter"""
        if self.path != "/test":
            self._send_error(404, "Not Found. Use /test endpoint")
            return

        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON body for encoded data
            try:
                request_data = json.loads(post_data.decode("utf-8"))
                encoded_data = request_data.get("data")

                if not encoded_data:
                    self._send_error(400, "Missing 'data' field in request body")
                    return

            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON in request body")
                return

            # Decode and parse the data
            try:
                decoded_str = base64.b64decode(encoded_data).decode("utf-8")
                reversed_str = decoded_str[::-1]

                # Extract type and value
                if reversed_str.startswith("url:"):
                    data_type, data_value = "url", reversed_str[4:]
                elif reversed_str.startswith("path:"):
                    data_type, data_value = "path", reversed_str[5:]
                else:
                    self._send_error(
                        400, "Decoded data must start with 'url:' or 'path:'"
                    )
                    return
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                # Base64 or UTF-8 decoding errors - let outer handler catch as 500
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
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(total_size))
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
    print("  POST /test")
    print("\nRequest format:")
    print("  {'data': '<base64_encoded_reversed_string>'}")
    print("\nData encoding:")
    print("  1. Create string: 'url:<actual_url>' or 'path:<file_path>'")
    print("  2. Reverse the string")
    print("  3. Encode with base64")
    print("\nExample:")
    print("  'url:https://example.com/file.pdf' → reverse → base64 encode")
    print("  'path:/path/to/local/file' → reverse → base64 encode")
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
