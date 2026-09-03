#!/usr/bin/env python3
"""Loopback MCP proxy that pins PrimeAgent to the Content Studio OV tenant."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable, Mapping


HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def build_upstream_headers(source: Mapping[str, str], body_length: int) -> dict[str, str]:
    headers = {
        key: value
        for key, value in source.items()
        if key.lower() not in HOP_BY_HOP | {"host", "content-length"}
    }
    headers["Host"] = "127.0.0.1:1933"
    headers["X-OpenViking-Account"] = os.environ.get(
        "OPENVIKING_ACCOUNT", "content-studio"
    )
    headers["X-OpenViking-User"] = os.environ.get("OPENVIKING_USER", "alan")
    headers["X-OpenViking-Actor-Peer"] = os.environ.get(
        "OPENVIKING_AGENT", "prime-agent"
    )
    if body_length:
        headers["Content-Length"] = str(body_length)
    return headers


class TenantProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "OpenVikingTenantProxy/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length else b""

    def _proxy(self, *, stream: bool = False) -> None:
        if not (self.path == "/mcp" or self.path.startswith("/mcp?")):
            self._send_json(404, {"status": "error", "message": "Only /mcp is proxied"})
            return

        body = self._body()
        headers = build_upstream_headers(dict(self.headers.items()), len(body))
        upstream = http.client.HTTPConnection("127.0.0.1", 1933, timeout=90)
        try:
            upstream.request(self.command, self.path, body=body or None, headers=headers)
            response = upstream.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP | {"content-length", "server", "date"}:
                    self.send_header(key, value)
            self.send_header("Connection", "close")

            if stream:
                self.end_headers()
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            else:
                response_body = response.read()
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
        except Exception as exc:
            if not self.wfile.closed:
                try:
                    self._send_json(502, {"status": "error", "message": str(exc)})
                except Exception:
                    pass
        finally:
            upstream.close()
            self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            upstream = http.client.HTTPConnection("127.0.0.1", 1933, timeout=5)
            try:
                upstream.request("GET", "/health")
                response = upstream.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                self._send_json(200 if response.status == 200 else 502, {
                    "status": "ok" if response.status == 200 else "error",
                    "tenant": os.environ.get("OPENVIKING_ACCOUNT", "content-studio"),
                    "upstream": payload,
                })
            except Exception as exc:
                self._send_json(502, {"status": "error", "message": str(exc)})
            finally:
                upstream.close()
            return
        self._proxy(stream=True)

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1934)
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("the tenant proxy must remain loopback-only")
    server = ThreadingHTTPServer((args.host, args.port), TenantProxyHandler)
    server.daemon_threads = True
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
