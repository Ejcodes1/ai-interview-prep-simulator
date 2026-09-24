"""TEMPORARY diagnostic route — remove before final submission.

Isolates why the openai SDK's httpx-based client fails to connect to
api.openai.com from Render's network while `requests`-based calls
(Adzuna) succeed, by testing DNS resolution, `requests`, and raw
`httpx` against the same host independently.
"""
from __future__ import annotations

import socket

from flask import Blueprint, jsonify

debug_bp = Blueprint("debug", __name__)


@debug_bp.get("/debug/network-check")
def network_check():
    results = {}

    try:
        ip = socket.gethostbyname("api.openai.com")
        results["dns"] = {"ok": True, "resolved_ip": ip}
    except Exception as exc:
        results["dns"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        import requests

        r = requests.get("https://api.openai.com/v1/models", timeout=8,
                          headers={"Authorization": "Bearer invalid"})
        results["requests_lib"] = {"ok": True, "status": r.status_code}
    except Exception as exc:
        results["requests_lib"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        import httpx

        r = httpx.get("https://api.openai.com/v1/models", timeout=8,
                       headers={"Authorization": "Bearer invalid"})
        results["httpx_lib"] = {"ok": True, "status": r.status_code}
    except Exception as exc:
        results["httpx_lib"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        import httpx

        client = httpx.Client(http2=False, timeout=8)
        r = client.get("https://api.openai.com/v1/models",
                        headers={"Authorization": "Bearer invalid"})
        results["httpx_http1_only"] = {"ok": True, "status": r.status_code}
    except Exception as exc:
        results["httpx_http1_only"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return jsonify(results)
