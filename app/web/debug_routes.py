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

    # Reproduce the real failing code path exactly: the actual OpenAI SDK
    # client, with the real key, doing a real GET (models.list) and then a
    # real POST (chat.completions.create) with the same shape our
    # question-generator uses. This isolates SDK-construction vs. the
    # specific POST + JSON body + response_format combination.
    import os

    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    results["openai_key_present"] = bool(api_key)

    try:
        sdk_client = OpenAI(api_key=api_key, timeout=10)
        r = sdk_client.models.list()
        results["openai_sdk_models_list"] = {"ok": True, "count": len(r.data)}
    except Exception as exc:
        results["openai_sdk_models_list"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        import httpx

        custom_http_client = httpx.Client(timeout=10, http2=False, trust_env=False)
        sdk_client = OpenAI(api_key=api_key, timeout=10, http_client=custom_http_client)
        r = sdk_client.models.list()
        results["openai_sdk_custom_http_client"] = {"ok": True, "count": len(r.data)}
    except Exception as exc:
        results["openai_sdk_custom_http_client"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Isolate further: is it proxy env vars (trust_env) or HTTP/2 specifically?
    try:
        import httpx

        c = httpx.Client(timeout=10, trust_env=False)
        sdk_client = OpenAI(api_key=api_key, timeout=10, http_client=c)
        r = sdk_client.models.list()
        results["openai_sdk_no_trust_env_only"] = {"ok": True, "count": len(r.data)}
    except Exception as exc:
        results["openai_sdk_no_trust_env_only"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    try:
        import httpx as _httpx  # noqa: F401  (proxy env inspection only)

        proxy_env = {
            k: os.environ.get(k)
            for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                      "http_proxy", "https_proxy", "all_proxy", "no_proxy")
            if os.environ.get(k) is not None
        }
        results["proxy_env_vars_set"] = proxy_env
    except Exception as exc:
        results["proxy_env_vars_set"] = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        sdk_client = OpenAI(api_key=api_key, timeout=10)
        r = sdk_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Respond with JSON: {\"status\": \"OK\"}"}],
            response_format={"type": "json_object"},
            timeout=10,
        )
        results["openai_sdk_chat_completion"] = {"ok": True, "content": r.choices[0].message.content}
    except Exception as exc:
        results["openai_sdk_chat_completion"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return jsonify(results)
