"""Shared fixtures for integration tests — no real HTTP calls made."""

import json
from typing import Callable

import httpx
import pytest

from ttd_data import DataClient

SAMPLE_TOKEN = "test_token"


class MockTransport(httpx.BaseTransport):
    """Intercepts all httpx requests and delegates to a handler function."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


class AsyncMockTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]):
        self._handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def json_response(status_code: int, body: dict) -> httpx.Response:
    content = json.dumps(body).encode()
    return httpx.Response(
        status_code=status_code,
        headers={
            "content-type": "application/json",
            "content-length": str(len(content)),
        },
        content=content,
    )


@pytest.fixture
def make_client():
    """Factory fixture: given a handler fn, returns a DataClient with a mock transport."""

    def _make(handler: Callable[[httpx.Request], httpx.Response]) -> DataClient:
        transport = MockTransport(handler)
        http_client = httpx.Client(transport=transport)
        return DataClient(client=http_client)

    return _make


@pytest.fixture
def make_async_client():
    """Factory fixture for async DataClient with a mock transport."""

    def _make(handler: Callable[[httpx.Request], httpx.Response]) -> DataClient:
        transport = AsyncMockTransport(handler)
        async_http_client = httpx.AsyncClient(transport=transport)
        return DataClient(async_client=async_http_client)

    return _make
