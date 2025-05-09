import unittest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import test modules
from tests.test_algorithms.test_a_star import TestAStarAlgorithm
from tests.test_algorithms.test_dijkstra import TestDijkstraAlgorithm
from tests.test_algorithms.test_dp_schedule import TestDPScheduler
from tests.test_utils.test_helpers import TestHelperFunctions
from tests.test_ui.test_components import TestUIComponents

def run_tests():
    """Run all test cases and return the results."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    test_cases = [
        TestAStarAlgorithm,
        TestDijkstraAlgorithm,
        TestDPScheduler,
        TestHelperFunctions,
        TestUIComponents
    ]
    
    for test_case in test_cases:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(test_case))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests()) 