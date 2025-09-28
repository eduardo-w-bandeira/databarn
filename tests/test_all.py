import pytest
import glob
import os

# Find all test files in the current directory that start with 'test_'
test_files = glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py"))

# Run pytest on the discovered test files
pytest.main(test_files)