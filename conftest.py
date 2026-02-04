import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO_PATH = os.path.join(PROJECT_ROOT, "demo_secure_onboarding")

def _ensure_project_root_first() -> None:
    # Ensure project root wins over nested demo packages for imports.
    if PROJECT_ROOT in sys.path:
        sys.path.remove(PROJECT_ROOT)
    sys.path.insert(0, PROJECT_ROOT)
    # Avoid demo package shadowing top-level modules during tests.
    if DEMO_PATH in sys.path:
        sys.path.remove(DEMO_PATH)


_ensure_project_root_first()


def pytest_configure(config):
    _ensure_project_root_first()


def pytest_sessionstart(session):
    _ensure_project_root_first()


def pytest_ignore_collect(collection_path, config):
    parts = collection_path.parts
    # Skip demo integration tests unless explicitly enabled.
    if "demo_secure_onboarding" in parts and not os.environ.get(
        "RUN_DEMO_SECURE_ONBOARDING_TESTS"
    ):
        return True
    # Skip module communication integration tests unless explicitly enabled.
    if "module_communication" in parts and "tests" in parts and not os.environ.get(
        "RUN_MODULE_COMMUNICATION_INTEGRATION_TESTS"
    ):
        return True
    try:
        import flask_sqlalchemy  # noqa: F401
        return False
    except Exception:
        # If Flask-SQLAlchemy isn't installed, skip app-level tests.
        if "tests" in parts:
            return True
        filename = collection_path.name
        return filename in {"test_batch_import.py"}


def pytest_collection_modifyitems(config, items):
    try:
        import flask_sqlalchemy  # noqa: F401
        return
    except Exception:
        pass

    skip_marker = pytest.mark.skip(
        reason="flask_sqlalchemy not available in test environment"
    )
    for item in items:
        nodeid = item.nodeid
        if "test_batch_import.py" in nodeid:
            item.add_marker(skip_marker)
