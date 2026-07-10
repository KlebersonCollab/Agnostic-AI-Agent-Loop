"""
Lightweight HTTP server for the Agent Memory Graph frontend.

This module serves `front/index.html` and exposes the persistent memory
artifact (`.agents/memory/memory_graph.jsonl`) over HTTP so the frontend can
load it without CORS/`file://` restrictions.

It is designed to be started in a background daemon thread by `cli.run_cli()`,
so the memory graph viewer comes up automatically with the agent — no manual
`python -m http.server` required.

Usage (standalone):
    python front/server.py [--host 127.0.0.1] [--port 8090] [--no-browser]

The server has ZERO third-party dependencies (uses only the stdlib).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import socketserver
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

# Project root = two levels up from this file (front/ -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONT_DIR = Path(__file__).resolve().parent
MEMORY_PATH = PROJECT_ROOT / ".agents" / "memory" / "memory_graph.jsonl"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090


class MemoryGraphHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the frontend and a live JSONL endpoint for the memory graph."""

    def __init__(self, *args, directory: str = str(FRONT_DIR), **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):  # noqa: N802 (stdlib naming)
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return self._serve_file(FRONT_DIR / "index.html", "text/html; charset=utf-8")

        if path == "/api/memory.jsonl":
            return self._serve_memory()

        # Fallback: let SimpleHTTPRequestHandler serve static files from front/
        return super().do_GET()

    def _serve_file(self, filepath: Path, content_type: str):
        if not filepath.exists():
            self.send_error(404, f"File not found: {filepath.name}")
            return
        try:
            data = filepath.read_bytes()
        except OSError as exc:
            self.send_error(500, f"Could not read file: {exc}")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_memory(self):
        if not MEMORY_PATH.exists():
            # Return an empty, well-formed JSONL so the frontend renders an empty graph
            payload = b""
        else:
            try:
                payload = MEMORY_PATH.read_bytes()
            except OSError as exc:
                self.send_error(500, f"Could not read memory graph: {exc}")
                return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):  # silence default stderr logging
        return


class _ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> _ThreadingHTTPServer:
    """Create (but do not start) the HTTP server instance."""
    handler = functools.partial(MemoryGraphHandler, directory=str(FRONT_DIR))
    return _ThreadingHTTPServer((host, port), handler)


def start_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool = True,
) -> tuple[_ThreadingHTTPServer, int]:
    """
    Start the frontend server in a background daemon thread.

    Returns the server instance and the actual port it bound to (useful when
    the requested port is busy and we fall back to port 0).
    """
    server = build_server(host, port)
    actual_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://{host}:{actual_port}/"
    if open_browser:
        # Open in a new browser tab after a short delay to let the server bind
        def open_tab_silently():
            try:
                # Redirect file descriptors 1 (stdout) and 2 (stderr) to devnull during subprocess spawn
                null_fd = os.open(os.devnull, os.O_RDWR)
                save_stdout = os.dup(1)
                save_stderr = os.dup(2)
                try:
                    os.dup2(null_fd, 1)
                    os.dup2(null_fd, 2)
                    webbrowser.open_new_tab(url)
                finally:
                    os.dup2(save_stdout, 1)
                    os.dup2(save_stderr, 2)
                    os.close(null_fd)
                    os.close(save_stdout)
                    os.close(save_stderr)
            except Exception:
                # Fallback if dup2/dup operations fail (e.g. non-standard environments)
                try:
                    webbrowser.open_new_tab(url)
                except Exception:
                    pass

        threading.Timer(0.8, open_tab_silently).start()

    return server, actual_port


def main():
    parser = argparse.ArgumentParser(description="Agent Memory Graph frontend server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser tab")
    args = parser.parse_args()

    server, port = start_server(args.host, args.port, open_browser=not args.no_browser)
    url = f"http://{args.host}:{port}/"
    print(f"🧠 Agent Memory Graph running at: {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down memory graph server...")
        server.shutdown()


if __name__ == "__main__":
    main()
