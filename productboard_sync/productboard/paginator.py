from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse


def paginate(
    request_fn: Callable,
    method: str,
    url: str,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> Generator[Any, None, None]:
    cursor = None
    while True:
        req_params = dict(params or {})
        if cursor:
            req_params["pageCursor"] = cursor

        response = request_fn(method, url, req_params, json_body)
        data = response.json()

        for item in data.get("data", []):
            yield item

        next_url = (data.get("links") or {}).get("next")
        if not next_url:
            break

        parsed = urlparse(next_url)
        cursor_list = parse_qs(parsed.query).get("pageCursor", [None])
        cursor = cursor_list[0] if cursor_list else None
        if not cursor:
            break
