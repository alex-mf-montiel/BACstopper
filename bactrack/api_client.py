"""Standard-library client for the generic BACtrack HTTP API."""

import json
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BACtrackAPIError(RuntimeError):
    """Raised when the BACtrack API cannot fulfill a request."""


def create_remote_test(
    base_url: str,
    metadata: Any = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Create a test through the HTTP API and return its initial state."""
    payload = json.dumps({"metadata": {} if metadata is None else metadata}).encode()
    request = Request(
        f"{base_url.rstrip('/')}/tests",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = _http_error_detail(exc)
        raise BACtrackAPIError(f"BACtrack API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise BACtrackAPIError(f"Could not reach BACtrack API: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BACtrackAPIError("Timed out connecting to BACtrack API") from exc


def stream_remote_test(
    base_url: str,
    test_id: str,
    timeout: float = 120.0,
) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Yield parsed SSE event names and full state snapshots for a test."""
    request = Request(
        f"{base_url.rstrip('/')}/tests/{test_id}/events",
        headers={"Accept": "text/event-stream"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            yield from parse_sse(response)
    except HTTPError as exc:
        detail = _http_error_detail(exc)
        raise BACtrackAPIError(f"BACtrack API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise BACtrackAPIError(f"BACtrack event stream failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BACtrackAPIError("BACtrack event stream timed out") from exc


def parse_sse(lines: Iterable[bytes]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Parse the subset of SSE used by the BACtrack API."""
    event_name = "message"
    data_lines = []

    for raw_line in lines:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line:
            if data_lines:
                yield event_name, json.loads("\n".join(data_lines))
            event_name = "message"
            data_lines = []
        elif line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        yield event_name, json.loads("\n".join(data_lines))


def _http_error_detail(exc: HTTPError) -> str:
    try:
        payload = json.load(exc)
        return str(payload.get("detail", payload))
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return str(exc.reason)
