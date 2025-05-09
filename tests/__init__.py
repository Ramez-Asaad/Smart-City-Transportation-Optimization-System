import os
import sys
from pathlib import Path

# Add project root to Python path for test imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Test data paths
TEST_DATA_DIR = os.path.join(project_root, "tests", "test_data")

def get_test_data_path(filename):
    """Get the full path to a test data file."""
    return os.path.join(TEST_DATA_DIR, filename)

# Common test data
SAMPLE_NEIGHBORHOODS = [
    {"ID": "1", "Name": "Test Area 1", "Population": 10000, "Type": "Residential", "X-coordinate": 31.25, "Y-coordinate": 29.96},
    {"ID": "2", "Name": "Test Area 2", "Population": 20000, "Type": "Mixed", "X-coordinate": 31.34, "Y-coordinate": 30.06},
    {"ID": "3", "Name": "Test Area 3", "Population": 15000, "Type": "Business", "X-coordinate": 31.24, "Y-coordinate": 30.04},
    {"ID": "5", "Name": "Test Area 5", "Population": 25000, "Type": "Mixed", "X-coordinate": 31.32, "Y-coordinate": 30.09}
]

SAMPLE_ROADS = [
    {"FromID": "1", "ToID": "2", "Name": "Test Road 1", "Distance(km)": 5.0, "Current Capacity(vehicles/hour)": 1000, "Condition(1-10)": 8},
    {"FromID": "2", "ToID": "3", "Name": "Test Road 2", "Distance(km)": 3.0, "Current Capacity(vehicles/hour)": 800, "Condition(1-10)": 7},
    {"FromID": "1", "ToID": "3", "Name": "Test Road 3", "Distance(km)": 4.0, "Current Capacity(vehicles/hour)": 1200, "Condition(1-10)": 9}
]

SAMPLE_FACILITIES = [
    {"ID": "F1", "Name": "Test Hospital", "Type": "Medical", "X-coordinate": 31.28, "Y-coordinate": 30.01},
    {"ID": "F2", "Name": "Test School", "Type": "Education", "X-coordinate": 31.30, "Y-coordinate": 30.02}
]
