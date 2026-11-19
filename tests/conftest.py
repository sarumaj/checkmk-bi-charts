"""Fixtures shared by the unit and the integration tests."""

import os

import pytest


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args: dict[str, object]) -> dict[str, object]:
    # Chromium refuses to start its sandbox as root, which is what CI containers run as.
    if os.geteuid() == 0:
        return {**browser_type_launch_args, "args": ["--no-sandbox"]}
    return browser_type_launch_args
