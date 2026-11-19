"""Fixtures for the unit tests."""

import threading
from collections.abc import Iterator

import pytest

from checkmk_stub import AGGREGATIONS, Handler, Stub


@pytest.fixture
def stub() -> Iterator[Stub]:
    server = Stub(("127.0.0.1", 0), Handler)
    server.aggregations = dict(AGGREGATIONS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
