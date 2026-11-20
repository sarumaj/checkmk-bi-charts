"""Fixtures for the unit tests."""

import threading
from collections.abc import Iterator

import pytest

import build_mkp
from checkmk_stub import AGGREGATIONS, Handler, Stub


@pytest.fixture(scope="session")
def built_page() -> None:
    """The page built from src/page/ once per run, as the MKP ships it."""
    build_mkp.build_page()


@pytest.fixture
def stub(built_page: None) -> Iterator[Stub]:
    server = Stub(("127.0.0.1", 0), Handler)
    server.aggregations = dict(AGGREGATIONS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
