"""
Shared pytest configuration.

Marks every test in test_rvos_poc.py as `live` (they hit the real reasoning
pipeline and need the NDA fixtures), so the offline-safe set is just
`pytest -m "not live"` — no hand-maintained file list to drift. test_rvos_poc.py
itself stays byte-identical; the marker is applied here, at collection time.
"""


def pytest_collection_modifyitems(items):
    import pytest

    for item in items:
        if item.path.name == "test_rvos_poc.py":
            item.add_marker(pytest.mark.live)
