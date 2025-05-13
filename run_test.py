#!/usr/bin/env python
import sys
import os
from pathlib import Path
import unittest
import time

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

class ImprovedTestResult(unittest.TextTestResult):
    """Custom test result class with better formatting and more information."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.verbosity = verbosity
        self.test_counts = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
        self.start_time = time.time()
    
    def startTest(self, test):
        self.test_counts['total'] += 1
        if self.verbosity > 1:
            self.stream.write('\n' + '=' * 70 + '\n')
            self.stream.write(f"Running: {test.id()}\n")
            self.stream.write('-' * 70 + '\n')
            if test._testMethodDoc:
                self.stream.write(f"Description: {test._testMethodDoc}\n")
                self.stream.write('-' * 70 + '\n')
        super().startTest(test)
    
    def addSuccess(self, test):
        self.test_counts['passed'] += 1
        if self.verbosity > 1:
            self.stream.write("PASS\n")
        else:
            self.stream.write('.')
        self.stream.flush()
    
    def addError(self, test, err):
        self.test_counts['errors'] += 1
        if self.verbosity > 1:
            self.stream.write("ERROR\n")
        else:
            self.stream.write('E')
        super().addError(test, err)
    
    def addFailure(self, test, err):
        self.test_counts['failed'] += 1
        if self.verbosity > 1:
            self.stream.write("FAIL\n")
        else:
            self.stream.write('F')
        super().addFailure(test, err)
    
    def addSkip(self, test, reason):
        self.test_counts['skipped'] += 1
        if self.verbosity > 1:
            self.stream.write(f"SKIPPED: {reason}\n")
        else:
            self.stream.write('s')
        super().addSkip(test, reason)
    
    def printErrors(self):
        if self.verbosity > 1:
            self.stream.write('\n' + '=' * 70 + '\n')
            self.stream.write("TEST RESULT DETAILS\n")
            self.stream.write('=' * 70 + '\n')
        
        super().printErrors()
    
    def printTotal(self):
        elapsed_time = time.time() - self.start_time
        self.stream.write('\n' + '=' * 70 + '\n')
        self.stream.write(f"TEST SUMMARY\n")
        self.stream.write('-' * 70 + '\n')
        self.stream.write(f"Total tests: {self.test_counts['total']}\n")
        self.stream.write(f"Passed: {self.test_counts['passed']}\n")
        self.stream.write(f"Failed: {self.test_counts['failed']}\n")
        self.stream.write(f"Errors: {self.test_counts['errors']}\n")
        self.stream.write(f"Skipped: {self.test_counts['skipped']}\n")
        self.stream.write(f"Time taken: {elapsed_time:.3f} seconds\n")
        self.stream.write('=' * 70 + '\n')

class ImprovedTestRunner(unittest.TextTestRunner):
    """Custom test runner using the improved result class."""
    
    resultclass = ImprovedTestResult
    
    def run(self, test):
        result = super().run(test)
        result.printTotal()
        return result

def run_test(test_path=None, verbosity=2):
    """
    Run specified test file or all tests if none specified.
    
    Args:
        test_path: Path or module name of the test to run (e.g., 'tests/test_algorithms/test_dijkstra.py')
        verbosity: Level of output detail (0=quiet, 1=normal, 2=verbose)
    """
    print("\nStarting test execution...\n")
    print(f"Python path: {sys.path}")
    
    if test_path:
        # Convert file path to module format if needed
        if test_path.endswith('.py'):
            # Remove .py extension and convert path separators to dots
            test_module = test_path.replace('/', '.').replace('\\', '.').replace('.py', '')
        else:
            test_module = test_path

        print(f"Running test module: {test_module}\n")
        suite = unittest.TestLoader().loadTestsFromName(test_module)
    else:
        # Run all tests
        print("Running all tests\n")
        from tests.run_tests import run_tests
        return run_tests()
    
    # Run the tests
    runner = ImprovedTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    # Parse verbosity level
    verbosity = 2  # Default to verbose
    args = sys.argv[1:]
    if "-v" in args:
        verbosity = 2
        args.remove("-v")
    elif "-q" in args:
        verbosity = 0
        args.remove("-q")
    
    if args:
        # Run specific test module
        test_path = args[0]
        sys.exit(run_test(test_path, verbosity))
    else:
        print("Usage: python run_test.py [options] <test_path>")
        print("Options:")
        print("  -v         Verbose output")
        print("  -q         Quiet output")
        print("\nExamples:")
        print("  python run_test.py tests.test_algorithms.test_dijkstra")
        print("  python run_test.py tests/test_algorithms/test_dijkstra.py")
        print("  python run_test.py")  # Run all tests
        sys.exit(1) 