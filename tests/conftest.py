"""Pytest configuration for crypto-portfolio-tracker tests."""

import pytest


def pytest_configure(config):
    """Disable ape plugin during tests."""
    # Unregister ape pytest plugin to avoid network connection issues
    config.pluginmanager.set_blocked("ape_test")
