"""Shared fixtures for the GraphQL unit tests. No network: requests are served
by an httpx MockTransport that records what was sent."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx
import pytest


class RecordingTransport:
    """Captures each request body and replays a canned response."""

    def __init__(self, response: Dict[str, Any]) -> None:
        self.requests: List[Dict[str, Any]] = []
        self._response = response

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "body": json.loads(request.content),
                "headers": dict(request.headers),
                "url": str(request.url),
            }
        )
        return httpx.Response(200, json=self._response)

    @property
    def last_query(self) -> str:
        return self.requests[-1]["body"]["query"]

    @property
    def last_variables(self) -> Dict[str, Any]:
        return self.requests[-1]["body"]["variables"]


@pytest.fixture
def graphql_ops():
    """Returns a factory: `make(ops_cls, response)` -> (ops_cls instance
    wired to a recording transport, RecordingTransport)."""
    from ttd_data.graphql import GraphQLTransport

    def make(ops_cls, response: Dict[str, Any] | None = None, ttd_auth=None):
        recorder = RecordingTransport(response or {"data": {}})
        http = httpx.Client(transport=httpx.MockTransport(recorder.handler))
        return ops_cls(GraphQLTransport(client=http, ttd_auth=ttd_auth)), recorder

    return make
