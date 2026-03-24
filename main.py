import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests
from datetime import datetime


class FileDownloadHandler(BaseHTTPRequestHandler):
    # Allowed base directory for local file serving (empty means all paths allowed)
    # Set this to restrict file access to a specific directory
    BASE_DIR = os.path.abspath('.')

    def do_POST(self):
        """Handle POST requests with target URL or local file path in body"""
        if self.path != '/test':
            self._send_error(404, "Not Found. Use /test endpoint")
            return

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON body for target URL or path
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                target_url = request_data.get('url')
                local_path = request_data.get('path')

                # Validate that either url or path is provided (not both)
                if target_url and local_path:
                    self._send_error(400, "Provide either 'url' or 'path', not both")
                    return
                if not target_url and not local_path:
                    self._send_error(400, "Missing 'url' or 'path' field in request body")
                    return

            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON in request body")
                return

            # Get content either from URL or local file
            if target_url:
                # Download file from target URL with redirection support
                downloaded_content = self._download_file_with_redirect(target_url)
                original_filename = self._extract_filename_from_url(target_url)
            else:
                # Read local file
                downloaded_content = self._read_local_file(local_path)
                original_filename = os.path.basename(local_path)

            # Generate random prefix (1,024,000 bytes)
            random_prefix = os.urandom(1024000)  # 1024000 bytes of random data

            # Combine random prefix + downloaded content
            response_content = random_prefix + downloaded_content

            # Generate timestamp filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            filename = f"{timestamp}_{original_filename}" if original_filename else f"{timestamp}.dat"

            # Send response with file content
            self._send_file_response(response_content, filename)

        except Exception as e:
            self._send_error(500, f"Internal server error: {str(e)}")

    def _download_file_with_redirect(self, url):
        """Download file from URL with automatic redirection support"""
        try:
            # Use requests with redirect following enabled
            response = requests.get(
                url,
                stream=True,
                allow_redirects=True,
                timeout=30,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; FileDownloader/1.0)'}
            )

            # Check if request was successful
            response.raise_for_status()

            # Read content in chunks to handle large files
            content = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content.extend(chunk)

            return bytes(content)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download file from {url}: {str(e)}")

    def _read_local_file(self, file_path):
        """Read file from local filesystem with security validation"""
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(file_path)

            # Security check: prevent directory traversal attacks
            # If BASE_DIR is set (not empty), ensure the file is within it
            if self.BASE_DIR:
                if not abs_path.startswith(self.BASE_DIR):
                    raise Exception(
                        f"Access denied: file path is outside allowed directory. "
                        f"Requested: {abs_path}, Allowed base: {self.BASE_DIR}"
                    )

            # Check if file exists and is a regular file
            if not os.path.exists(abs_path):
                raise Exception(f"File not found: {file_path}")

            if not os.path.isfile(abs_path):
                raise Exception(f"Path is not a file: {file_path}")

            # Read file content in chunks for memory efficiency
            content = bytearray()
            with open(abs_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    content.extend(chunk)

            return bytes(content)

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

    def _send_file_response(self, content, filename):
        """Send file response with appropriate headers"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        error_response = {"error": message}
        self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def log_message(self, format, *args):
        """Override to customize logging format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(host='0.0.0.0', port=30080):
    """Start the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, FileDownloadHandler)

    print(f"File Download Server started on http://{host}:{port}")
    print("\nSupported endpoints:")
    print("  POST /test")
    print("\nRequest formats:")
    print("  Download from URL: {'url': 'https://example.com/file'}")
    print("  Serve local file:  {'path': '/path/to/local/file'}")
    print("\nNote: Local files are served with current directory as base (configurable via BASE_DIR)")
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
