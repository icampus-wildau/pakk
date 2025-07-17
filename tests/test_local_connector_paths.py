#!/usr/bin/env python3
"""Test script to verify LocalConnector path detection and pakkage discovery."""

import os
import sys
import tempfile
import pytest

# Add the pakk directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../pakk'))

from pakk.connector.local import LocalConnector
from pakk.pakkage.core import PakkageConfig


def test_is_path_detection():
    """Test the is_path method for various path formats."""
    connector = LocalConnector()
    
    # Test absolute paths (using temp directory that we know exists)
    with tempfile.TemporaryDirectory() as temp_dir:
        assert connector.is_path(temp_dir) == True
        assert connector.is_path(os.path.join(temp_dir, "subdir")) == True
    
    # Test home directory paths
    assert connector.is_path("~/test") == True
    assert connector.is_path("~/Documents") == True
    
    # Test relative paths
    assert connector.is_path("./test") == True
    assert connector.is_path("../test") == True
    
    # Test non-paths
    assert connector.is_path("ros2-package") == False
    assert connector.is_path("my-package@1.0.0") == False
    assert connector.is_path("") == False


def test_get_absolute_path():
    """Test the get_absolute_path method."""
    connector = LocalConnector()
    
    # Test absolute paths (using temp directory)
    with tempfile.TemporaryDirectory() as temp_dir:
        assert connector.get_absolute_path(temp_dir) == temp_dir
    
    # Test home directory paths
    home = os.path.expanduser("~")
    assert connector.get_absolute_path("~/test") == os.path.join(home, "test")
    
    # Test relative paths
    current_dir = os.getcwd()
    assert connector.get_absolute_path("./test") == os.path.abspath(os.path.join(current_dir, "test"))
    assert connector.get_absolute_path("../test") == os.path.abspath(os.path.join(current_dir, "..", "test"))
    
    # Test non-paths
    assert connector.get_absolute_path("ros2-package") == None


def test_discover_path_based_pakkages():
    """Test discovering pakkages from paths."""
    connector = LocalConnector()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a simple pakkage structure
        pakkage_dir = os.path.join(temp_dir, "test-package")
        os.makedirs(pakkage_dir)
        
        # Create a minimal pakk.cfg file with correct format
        pakk_cfg_content = """[info]
id = test-group/test-package
version = 1.0.0
name = Test Package
description = A test package

[Type.Generic]
"""
        
        with open(os.path.join(pakkage_dir, "pakk.cfg"), "w") as f:
            f.write(pakk_cfg_content)
        
        # Test discovering the pakkage from its path
        pakkage_ids = [pakkage_dir]
        discovered_pakkages, path_mapping = connector.discover_path_based_pakkages(pakkage_ids)
        
        # Verify that the pakkage was discovered
        assert len(discovered_pakkages) == 1
        assert "test-group/test-package" in discovered_pakkages.pakkages
        
        # Verify the path mapping
        assert pakkage_dir in path_mapping
        assert path_mapping[pakkage_dir] == "test-group/test-package"


def test_discover_path_based_pakkages_multiple():
    """Test discovering pakkages when multiple are found at a path."""
    connector = LocalConnector()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple pakkages in subdirectories
        pakkage1_dir = os.path.join(temp_dir, "package1")
        pakkage2_dir = os.path.join(temp_dir, "package2")
        
        os.makedirs(pakkage1_dir)
        os.makedirs(pakkage2_dir)
        
        # Create pakk.cfg files with correct format
        pakk_cfg_content1 = """[info]
id = test-group/package1
version = 1.0.0
name = Package 1
description = First test package

[Type.Generic]
"""
        
        pakk_cfg_content2 = """[info]
id = test-group/package2
version = 1.0.0
name = Package 2
description = Second test package

[Type.Generic]
"""
        
        with open(os.path.join(pakkage1_dir, "pakk.cfg"), "w") as f:
            f.write(pakk_cfg_content1)
        
        with open(os.path.join(pakkage2_dir, "pakk.cfg"), "w") as f:
            f.write(pakk_cfg_content2)
        
        # Test discovering pakkages from the parent directory
        pakkage_ids = [temp_dir]
        discovered_pakkages, path_mapping = connector.discover_path_based_pakkages(pakkage_ids)
        
        # When multiple pakkages are found, they should not be added to avoid ambiguity
        # The warning should be logged and no mapping should be created
        assert len(discovered_pakkages) == 0
        assert len(path_mapping) == 0


def test_discover_path_based_pakkages_none():
    """Test discovering pakkages when none are found at a path."""
    connector = LocalConnector()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a directory without any pakkages
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)
        
        # Test discovering pakkages from the empty directory
        pakkage_ids = [empty_dir]
        discovered_pakkages, path_mapping = connector.discover_path_based_pakkages(pakkage_ids)
        
        # Should not discover any pakkages
        assert len(discovered_pakkages) == 0
        assert len(path_mapping) == 0


def test_discover_path_based_pakkages_mixed():
    """Test discovering pakkages with mixed path and non-path inputs."""
    connector = LocalConnector()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a pakkage
        pakkage_dir = os.path.join(temp_dir, "test-package")
        os.makedirs(pakkage_dir)
        
        pakk_cfg_content = """[info]
id = test-group/test-package
version = 1.0.0
name = Test Package
description = A test package

[Type.Generic]
"""
        
        with open(os.path.join(pakkage_dir, "pakk.cfg"), "w") as f:
            f.write(pakk_cfg_content)
        
        # Test with mixed inputs: a path and a regular pakkage name
        pakkage_ids = [pakkage_dir, "ros2-package"]
        discovered_pakkages, path_mapping = connector.discover_path_based_pakkages(pakkage_ids)
        
        # Should discover the pakkage from the path but ignore the non-path
        assert len(discovered_pakkages) == 1
        assert "test-group/test-package" in discovered_pakkages.pakkages
        
        # Should only map the path
        assert pakkage_dir in path_mapping
        assert "ros2-package" not in path_mapping


if __name__ == "__main__":
    pytest.main([__file__]) 