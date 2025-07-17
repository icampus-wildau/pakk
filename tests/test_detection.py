#!/usr/bin/env python3
"""Test script to verify pakkage type detection methods."""

import os
import sys
import tempfile
import pytest

# Add the pakk directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../pakk'))

from pakk.types.base import TypeBase
from pakk.pakkage.init_helper import InitHelperBase
from pakk.helper.loader import PakkLoader

# Test cases for different project types
TEST_CASES = [
    ("Python Project", ["setup.py", "requirements.txt", "main.py"], ["Python"]),
    ("Python Project (Deep)", ["src/main.py", "src/__init__.py", "tests/test_main.py"], ["Python"]),
    ("ROS2 Project", ["package.xml", "CMakeLists.txt", "launch/"], ["ROS2"]),
    ("ROS2 Project (Deep)", ["src/package.xml", "src/launch/", "src/msg/"], ["ROS2"]),
    ("Web Project", ["package.json", "index.html", "src/"], ["Web"]),
    ("Web Project (Deep)", ["frontend/package.json", "frontend/src/", "frontend/index.html"], ["Web"]),
    ("Asset Project", ["assets/", "models/", "textures/"], ["Asset"]),
    ("Asset Project (Deep)", ["resources/assets/", "resources/models/", "resources/textures/"], ["Asset"]),
    ("Setup Project", ["setup.sh", "Dockerfile", "Makefile"], ["Setup"]),
    ("Setup Project (Deep)", ["scripts/setup.sh", "docker/Dockerfile", "build/Makefile"], ["Setup"]),
    ("Runnable Project", ["main", "run.sh", "start.py"], ["Runnable"]),
    ("Runnable Project (Deep)", ["bin/main", "scripts/run.sh", "scripts/start.py"], ["Runnable"]),
    ("Mixed Project", ["setup.py", "package.json", "assets/"], ["Python", "Web", "Asset"]),
]

@pytest.mark.parametrize("name, files, expected_types", TEST_CASES)
def test_detection_methods(name, files, expected_types):
    # Initialize types (only once per session)
    TypeBase.initialize()
    types = TypeBase.get_type_classes()
    type_map = {t.PAKKAGE_TYPE: t for t in types}
    available_type_choices = [t.PAKKAGE_TYPE for t in types if t.CONFIGURABLE_TYPE]

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        for file_path in files:
            full_path = os.path.join(temp_dir, file_path)
            if file_path.endswith('/'):
                os.makedirs(full_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write("# Test file")
        # Make some files executable for runnable test
        if "Runnable" in expected_types:
            for file_path in files:
                if not file_path.endswith('/'):
                    full_path = os.path.join(temp_dir, file_path)
                    os.chmod(full_path, 0o755)
        # Test detection
        detected_types = []
        for type_name in available_type_choices:
            type_class = type_map[type_name]
            module_name = type_class.__module__
            helper_cls = PakkLoader.get_module_subclasses(module_name, InitHelperBase)
            helper_cls = helper_cls[0] if len(helper_cls) > 0 else None
            if helper_cls is not None and issubclass(helper_cls, InitHelperBase):
                try:
                    if helper_cls.is_suitable_for_directory(temp_dir):
                        detected_types.append(type_name)
                except Exception as e:
                    pytest.fail(f"Error detecting {type_name}: {e}")
        assert set(expected_types) == set(detected_types), (
            f"{name}: Expected {set(expected_types)}, detected {set(detected_types)}"
        ) 