"""Fire-and-forget HTTP exporter: batches events and POSTs to the OSS
ingestion API from a background thread running its own asyncio loop.
Includes circuit breaker, exponential backoff retry, and graceful shutdown.
"""
from __future__ import annotations

import asyncio
import atexit
import logging
import queue
import random
import threading
from typing import Any

import httpx

from .circuit_breaker import CircuitBreaker
from .config import TokenSightConfig

logger = logging.getLogger("tokensight.exporter")


class HttpExporter:
    def __init__(self, config: TokenSightConfig) -> None:
        self._endpoint: str = config.api_endpoint.rstrip("/") + "/api/ingest"
        self._api_key: str = config.api_key
        self._max_retries: int = config.max_retries
        self._batch_size: int = config.batch_size
        self._flush_interval: float = config.flush_interval_seconds

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=config.queue_max_size)
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_recovery_seconds,
        )

        self._shutdown = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="tokensight-exporter",
        )
        self._thread.start()
        self._ready.wait(timeout=5.0)

        atexit.register(self._atexit_flush)

    def emit(self, event: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("Tokensight exporter queue full — dropping event")

    def flush(self) -> None:
        if self._loop is not None and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._drain(), self._loop)
            try:
                future.result(timeout=10.0)
            except Exception:
                logger.warning("Flush failed", exc_info=True)

    def shutdown(self, timeout: float = 5.0) -> None:
        self._shutdown.set()
        self._thread.join(timeout=timeout)

    def _atexit_flush(self) -> None:
        remaining = self._queue.qsize()
        if remaining > 0:
            logger.info("Graceful shutdown: flushing %d pending events …", remaining)
        self.flush()
        self.shutdown(timeout=5.0)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_until_complete(self._async_main())
        finally:
            self._loop.close()

    async def _async_main(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            self._http = client
            while not self._shutdown.is_set():
                await asyncio.sleep(self._flush_interval)
                await self._drain()
            await self._drain()

    async def _drain(self) -> None:
        batch: list[dict[str, Any]] = []
        while len(batch) < self._batch_size:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if not batch:
            return
        if not self._circuit_breaker.allow_request():
            return
        await self._send_batch_with_retry(batch)

    async def _send_batch_with_retry(self, batch: list[dict[str, Any]]) -> None:
        endpoint = self._endpoint if len(batch) == 1 else self._endpoint + "/batch"
        payload = batch[0] if len(batch) == 1 else {"events": batch}

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post(
                    endpoint, json=payload, headers={"X-API-Key": self._api_key},
                )
                if resp.status_code < 400:
                    self._circuit_breaker.record_success()
                    return
                if 400 <= resp.status_code < 500:
                    logger.warning(
                        "Tokensight ingestion returned %d (client error, not retrying): %s",
                        resp.status_code, resp.text[:200],
                    )
                    return
                logger.warning(
                    "Tokensight ingestion returned %d (attempt %d/%d)",
                    resp.status_code, attempt + 1, self._max_retries + 1,
                )
                self._circuit_breaker.record_failure()
            except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
                logger.warning(
                    "Tokensight ingestion connection error (attempt %d/%d): %s",
                    attempt + 1, self._max_retries + 1, exc,
                )
                self._circuit_breaker.record_failure()
            except Exception:
                logger.warning("Tokensight ingestion failed (not retrying)", exc_info=True)
                self._circuit_breaker.record_failure()
                return

            if attempt < self._max_retries:
                base_delay = 2 ** attempt
                jitter = random.uniform(0, base_delay * 0.5)
                await asyncio.sleep(base_delay + jitter)

        logger.warning(
            "Tokensight ingestion exhausted all %d retries — dropping %d event(s)",
            self._max_retries, len(batch),
        )
