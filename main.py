import os
import random
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests
from datetime import datetime


class FileDownloadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests with target URL in body"""
        if self.path != '/download':
            self._send_error(404, "Not Found. Use /download endpoint")
            return

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON body for target URL
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                target_url = request_data.get('url')

                if not target_url:
                    self._send_error(400, "Missing 'url' field in request body")
                    return

            except json.JSONDecodeError:
                self._send_error(400, "Invalid JSON in request body")
                return

            # Download file from target URL with redirection support
            downloaded_content = self._download_file_with_redirect(target_url)

            # Generate random prefix (1,024,000 bytes)
            random_prefix = os.urandom(1024000)  # 1024000 bytes of random data

            # Combine random prefix + downloaded content
            response_content = random_prefix + downloaded_content

            # Generate timestamp filename
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            filename = f"{timestamp}.dat"

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


def run_server(host='localhost', port=8080):
    """Start the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, FileDownloadHandler)

    print(f"File Download Server started on http://{host}:{port}")
    print("POST to /download with JSON body: {'url': 'https://example.com/file'}")
    print("Press Ctrl+C to stop the server")

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
