"""
Comprehensive test runner for the databarn package.

This module provides functionality to run all tests in the databarn test suite,
including individual test modules and specific test categories.

Usage:
    python -m pytest tests/test_all.py -v
    python tests/test_all.py  # Direct execution
"""

import pytest
import sys
import os
from pathlib import Path

# Add the parent directory to the path to ensure databarn can be imported
TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all test modules to ensure they're discovered
# Note: We don't import them directly to avoid execution during import


def run_all_tests(verbose=True, capture=False):
    """
    Run all tests in the databarn test suite.
    
    Args:
        verbose (bool): Enable verbose output
        capture (bool): Capture stdout/stderr (True) or show output (False)
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    test_args = [
        str(TESTS_DIR),  # Run all tests in the tests directory
        "-v" if verbose else "",
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker validation
        "--disable-warnings" if not verbose else "",
    ]
    
    # Remove empty strings from args
    test_args = [arg for arg in test_args if arg]
    
    if not capture:
        test_args.append("-s")  # Don't capture output
    
    print("Running all databarn tests...")
    print(f"Test directory: {TESTS_DIR}")
    print(f"Arguments: {' '.join(test_args)}")
    print("-" * 60)
    
    return pytest.main(test_args)


def run_specific_module(module_name, verbose=True):
    """
    Run tests from a specific module.
    
    Args:
        module_name (str): Name of the test module (e.g., 'barn', 'cob')
        verbose (bool): Enable verbose output
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    test_file = TESTS_DIR / f"test_{module_name}.py"
    
    if not test_file.exists():
        print(f"Error: Test file {test_file} does not exist!")
        return 1
    
    test_args = [
        str(test_file),
        "-v" if verbose else "",
        "--tb=short",
        "-s"  # Don't capture output
    ]
    
    # Remove empty strings from args
    test_args = [arg for arg in test_args if arg]
    
    print(f"Running tests for module: {module_name}")
    print(f"Test file: {test_file}")
    print("-" * 60)
    
    return pytest.main(test_args)


def run_by_category():
    """
    Run tests organized by category/component.
    """
    categories = {
        "Core Data Structures": ["test_cob.py", "test_barn.py"],
        "Advanced Features": ["test_dna_methods.py", "test_decorators.py"],
        "Utility Functions": ["test_funcs.py"],
        "Integration & Misc": ["test_misc.py"]
    }
    
    print("Available test categories:")
    for i, (category, files) in enumerate(categories.items(), 1):
        print(f"{i}. {category}: {', '.join(files)}")
    
    choice = input("\nEnter category number (1-4) or 'all' for all categories: ").strip()
    
    if choice.lower() == 'all':
        return run_all_tests()
    
    try:
        category_num = int(choice)
        if 1 <= category_num <= len(categories):
            category_name = list(categories.keys())[category_num - 1]
            test_files = categories[category_name]
            
            print(f"\nRunning {category_name} tests...")
            test_paths = [str(TESTS_DIR / file) for file in test_files]
            
            test_args = test_paths + ["-v", "--tb=short", "-s"]
            return pytest.main(test_args)
        else:
            print("Invalid category number!")
            return 1
    except ValueError:
        print("Invalid input! Please enter a number or 'all'.")
        return 1


if __name__ == "__main__":
    """
    Main execution block for direct script running.
    Provides an interactive menu for running different test suites.
    """
    if len(sys.argv) > 1:
        # Handle command line arguments
        if sys.argv[1] == "--module" and len(sys.argv) > 2:
            # Run specific module: python test_all.py --module barn
            exit_code = run_specific_module(sys.argv[2])
        elif sys.argv[1] == "--category":
            # Run by category: python test_all.py --category
            exit_code = run_by_category()
        elif sys.argv[1] == "--help":
            print(__doc__)
            print("\nUsage options:")
            print("  python test_all.py                    # Interactive menu")
            print("  python test_all.py --module <name>    # Run specific module")
            print("  python test_all.py --category         # Run by category")
            print("  python test_all.py --help             # Show this help")
            print("\nAvailable modules: barn, cob, decorators, dna_methods, funcs, misc")
            exit_code = 0
        else:
            # Run all tests with any other argument
            exit_code = run_all_tests()
    else:
        # Interactive mode
        print("=" * 60)
        print("DataBarn Test Suite Runner")
        print("=" * 60)
        print("1. Run all tests")
        print("2. Run tests by category")
        print("3. Run specific module")
        print("4. Exit")
        
        while True:
            choice = input("\nSelect an option (1-4): ").strip()
            
            if choice == "1":
                exit_code = run_all_tests()
                break
            elif choice == "2":
                exit_code = run_by_category()
                break
            elif choice == "3":
                modules = ["barn", "cob", "decorators", "dna_methods", "funcs", "misc"]
                print(f"\nAvailable modules: {', '.join(modules)}")
                module = input("Enter module name: ").strip()
                exit_code = run_specific_module(module)
                break
            elif choice == "4":
                print("Exiting...")
                exit_code = 0
                break
            else:
                print("Invalid choice! Please enter 1-4.")
                continue
    
    sys.exit(exit_code)