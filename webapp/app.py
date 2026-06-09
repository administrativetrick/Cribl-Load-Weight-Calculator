#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 James Curtis
"""Cribl Weight Load Calculator — self-hostable web app.

Stdlib-only HTTP server wrapping the same calculation module the Agent
Skill uses (skill/cribl-weight-load-calculator/scripts/cribl_weights.py).

Endpoints:
    GET  /                  single-page UI
    GET  /healthz           liveness probe
    POST /api/calculate     {"receivers":[{"name":"idx1","weight":1},...],
                             "total": 300, "unit": "events/sec"}
    POST /api/from-percent  {"percents": [25, 25, 50]}

Run locally:  python webapp/app.py            (default port 8080)
              PORT=9000 python webapp/app.py
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
try:
    # Docker image: cribl_weights.py is copied next to app.py
    sys.path.insert(0, str(APP_DIR))
    import cribl_weights
except ImportError:
    # Repo checkout: import from the skill's scripts directory
    sys.path.insert(0, str(APP_DIR.parent / "skill" / "cribl-weight-load-calculator" / "scripts"))
    import cribl_weights

INDEX_HTML = (APP_DIR / "index.html").read_bytes()
MAX_BODY = 64 * 1024
MAX_RECEIVERS = 1000


def calculate(payload):
    receivers = payload.get("receivers")
    if not isinstance(receivers, list) or not receivers:
        raise ValueError("'receivers' must be a non-empty list")
    if len(receivers) > MAX_RECEIVERS:
        raise ValueError(f"too many receivers (max {MAX_RECEIVERS})")
    nodes = []
    for i, r in enumerate(receivers):
        if not isinstance(r, dict) or "weight" not in r:
            raise ValueError(f"receiver {i + 1} must be an object with a 'weight'")
        name = str(r.get("name") or f"node{i + 1}")
        nodes.append((name, cribl_weights.parse_weight(r["weight"], f"weight for {name}")))
    total = payload.get("total")
    if total is not None:
        total = cribl_weights.parse_weight(total, "total")
    total_weight, rows = cribl_weights.distribute(nodes, total)
    return {
        "total_weight": total_weight,
        "total": total,
        "unit": payload.get("unit") or None,
        "receivers": rows,
    }


def from_percent(payload):
    percents = payload.get("percents")
    if not isinstance(percents, list) or len(percents) < 2:
        raise ValueError("'percents' must be a list of at least two numbers")
    if len(percents) > MAX_RECEIVERS:
        raise ValueError(f"too many entries (max {MAX_RECEIVERS})")
    weights, shares = cribl_weights.smallest_integer_weights(percents)
    result = {
        "normalized_percent": [float(s * 100) for s in shares],
        "weights": weights,
    }
    if max(weights) > 100:
        approx, err = cribl_weights.approximate_weights(shares)
        result["approximation"] = {"weights": approx, "max_error_percent": err * 100}
    return result


ROUTES = {"/api/calculate": calculate, "/api/from-percent": from_percent}


class Handler(BaseHTTPRequestHandler):
    server_version = "CriblWeightCalc/1.0"

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        elif self.path == "/healthz":
            self._send(200, b'{"status":"ok"}')
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        handler = ROUTES.get(self.path)
        if handler is None:
            self._send(404, b'{"error":"not found"}')
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            self._send(400, b'{"error":"request body required (max 64 KiB)"}')
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            result = handler(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode())
            return
        self._send(200, json.dumps(result).encode())

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Cribl Weight Load Calculator listening on :{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
