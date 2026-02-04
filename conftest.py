"""Project-wide pytest configuration."""

import os
import sys
from pathlib import Path
from typing import Iterable

import pytest

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

for module_name in list(sys.modules):
    if module_name == "services" or module_name.startswith("services."):
        del sys.modules[module_name]


def _missing_modules(modules: Iterable[str]) -> list[str]:
    missing = []
    for name in modules:
        if name not in sys.modules:
            try:
                __import__(name)
            except Exception:
                missing.append(name)
    return missing


def pytest_ignore_collect(collection_path: Path, config):
    missing = _missing_modules(["flask_sqlalchemy"])
    if missing:
        if "tests" in collection_path.parts:
            return True
        skip_targets = {"test_batch_import.py", "test_mining_calculator.py"}
        if collection_path.name in skip_targets:
            return True
        if "tests/integration/test_batch_import.py" in str(collection_path):
            return True
        if "tests/unit/test_mining_calculator.py" in str(collection_path):
            return True
    if os.environ.get("RUN_DEMO_TESTS") != "1":
        if "demo_secure_onboarding" in collection_path.parts:
            return True
    if os.environ.get("RUN_MODULE_COMM_TESTS") != "1":
        if "module_communication" in collection_path.parts:
            return True
    return False
