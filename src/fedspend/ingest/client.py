"""HTTP client for the USAspending v2 API.

Two properties matter for an analysis that has to be defensible months later:

1. **Retries with backoff** - USAspending rate-limits and occasionally 502s on
   large aggregations. A transient failure must not silently truncate a series.
2. **Content-addressed disk cache** - every response is stored under a hash of
   its request body. Re-running the pipeline is free, works offline, and makes
   the published numbers exactly reproducible from the cached payloads.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..logging_utils import get_logger

log = get_logger(__name__)


class UsaSpendingError(RuntimeError):
    """Raised when the API returns an unrecoverable response."""


class RetryableError(RuntimeError):
    """Transient failure worth retrying."""


class UsaSpendingClient:
    """Thin, cached, retrying wrapper over the USAspending v2 search endpoints."""

    def __init__(
        self,
        base_url: str,
        cache_dir: Path,
        *,
        timeout: int = 120,
        max_retries: int = 5,
        backoff: float = 2.0,
        cache_enabled: bool = True,
        min_interval_seconds: float = 0.2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.cache_enabled = cache_enabled
        self.min_interval = min_interval_seconds
        self._last_call = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "fedspend/2.0 (portfolio analytics)"}
        )
        self.stats = {"cache_hits": 0, "network_calls": 0}

    # ------------------------------------------------------------- caching
    def _cache_path(self, endpoint: str, payload: dict[str, Any]) -> Path:
        blob = json.dumps({"endpoint": endpoint, "payload": payload}, sort_keys=True)
        digest = hashlib.sha256(blob.encode()).hexdigest()[:24]
        slug = endpoint.strip("/").replace("/", "_")[:60]
        return self.cache_dir / f"{slug}__{digest}.json"

    # -------------------------------------------------------------- request
    def post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        cache_file = self._cache_path(endpoint, payload)
        if self.cache_enabled and cache_file.exists():
            self.stats["cache_hits"] += 1
            return json.loads(cache_file.read_text(encoding="utf-8"))

        data = self._post_uncached(endpoint, payload)
        if self.cache_enabled:
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        return data

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def _post_uncached(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        @retry(
            retry=retry_if_exception_type(RetryableError),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=self.backoff, min=self.backoff, max=60),
            reraise=True,
        )
        def _call() -> dict[str, Any]:
            self._throttle()
            url = f"{self.base_url}/{endpoint.strip('/')}/"
            self.stats["network_calls"] += 1
            try:
                resp = self.session.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:  # network flake
                # USAspending drops keep-alive connections on heavy aggregations.
                # Rebuild the session so the retry opens a fresh TCP connection
                # instead of reusing the half-closed one.
                self._reset_session()
                raise RetryableError(str(exc)) from exc

            if resp.status_code in (429, 500, 502, 503, 504):
                raise RetryableError(f"HTTP {resp.status_code} from {url}")
            if resp.status_code >= 400:
                raise UsaSpendingError(f"HTTP {resp.status_code} from {url}: {resp.text[:400]}")
            try:
                return resp.json()
            except ValueError as exc:
                raise RetryableError(f"Non-JSON response from {url}") from exc

        return _call()

    def _reset_session(self) -> None:
        # Closing a half-dead session must never mask the error that caused it.
        with contextlib.suppress(Exception):
            self.session.close()
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "fedspend/2.0 (portfolio analytics)"}
        )

    # ---------------------------------------------------------- pagination
    def paged_category(
        self,
        category: str,
        filters: dict[str, Any],
        *,
        page_limit: int = 100,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """Return every row of a ``spending_by_category`` aggregation."""
        endpoint = f"search/spending_by_category/{category}"
        rows: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            payload = {
                "filters": filters,
                "category": category,
                "limit": page_limit,
                "page": page,
            }
            data = self.post(endpoint, payload)
            batch = data.get("results", [])
            rows.extend(batch)
            if not data.get("page_metadata", {}).get("hasNext"):
                break
        return rows
