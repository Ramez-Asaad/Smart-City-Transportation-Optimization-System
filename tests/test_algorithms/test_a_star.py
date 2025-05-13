import unittest
import pandas as pd
import networkx as nx
from unittest.mock import patch, MagicMock
from algorithms.a_star import calculate_distance, heuristic, a_star, find_nearest_hospital, run_a_star
from tests import SAMPLE_NEIGHBORHOODS, SAMPLE_ROADS, SAMPLE_FACILITIES

class TestAStarAlgorithm(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test."""
        self.neighborhoods = pd.DataFrame(SAMPLE_NEIGHBORHOODS)
        self.roads = pd.DataFrame(SAMPLE_ROADS)
        self.facilities = pd.DataFrame(SAMPLE_FACILITIES)
        
        # Create test graph
        self.graph = nx.Graph()
        self.node_positions = {}
        
        # Add nodes and positions
        for _, row in self.neighborhoods.iterrows():
            self.node_positions[str(row["ID"])] = (row["Y-coordinate"], row["X-coordinate"])
            
        for _, row in self.facilities.iterrows():
            self.node_positions[row["ID"]] = (row["Y-coordinate"], row["X-coordinate"])
        
        # Add edges
        for _, row in self.roads.iterrows():
            self.graph.add_edge(
                str(row["FromID"]),
                str(row["ToID"]),
                weight=row["Distance(km)"],
                capacity=row["Current Capacity(vehicles/hour)"],
                condition=row["Condition(1-10)"],
                name=f"Road {row['FromID']}-{row['ToID']}"
            )

    def test_calculate_distance(self):
        """Test Euclidean distance calculation."""
        coord1 = (0, 0)
        coord2 = (3, 4)
        self.assertEqual(calculate_distance(coord1, coord2), 5.0)

    def test_heuristic(self):
        """Test heuristic function."""
        start_pos = (30.0, 31.0)
        goal_pos = (30.0, 32.0)
        # Heuristic should be admissible (less than or equal to actual distance)
        self.assertLessEqual(
            heuristic(start_pos, goal_pos) / 50,  # Divide by scale factor
            calculate_distance(start_pos, goal_pos)
        )

    def test_a_star_path_exists(self):
        """Test A* algorithm when path exists."""
        start = "1"
        goal = "3"
        path, cost = a_star(self.graph, start, goal, self.node_positions)
        
        # Check path exists and is valid
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 1)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], goal)
        
        # Check path continuity
        for i in range(len(path) - 1):
            self.assertTrue(self.graph.has_edge(path[i], path[i + 1]))

    def test_a_star_no_path(self):
        """Test A* algorithm when no path exists."""
        # Create isolated node
        self.graph.add_node("4")
        path, cost = a_star(self.graph, "1", "4", self.node_positions)
        self.assertIsNone(path)
        self.assertEqual(cost, float('inf'))

    def test_find_nearest_hospital(self):
        """Test finding nearest hospital functionality."""
        # Filter for hospitals
        hospitals = self.facilities[self.facilities["Type"] == "Medical"]
        
        # Test from a location with accessible hospital
        path, cost, hospital = find_nearest_hospital("1", self.graph, hospitals, self.node_positions)
        
        self.assertIsNotNone(path)
        self.assertLess(cost, float('inf'))
        self.assertEqual(hospital, "Test Hospital")
        
        # Verify path ends at hospital
        self.assertEqual(path[-1], "F1")

    def test_find_nearest_hospital_no_access(self):
        """Test finding nearest hospital when no hospital is accessible."""
        # Create isolated test data
        isolated_graph = nx.Graph()
        isolated_graph.add_node("1")
        isolated_graph.add_node("F1")
        
        hospitals = self.facilities[self.facilities["Type"] == "Medical"]
        
        path, cost, hospital = find_nearest_hospital("1", isolated_graph, hospitals, self.node_positions)
        
        self.assertIsNone(path)
        self.assertEqual(cost, float('inf'))
        self.assertIsNone(hospital)

    @patch('algorithms.a_star.build_map')
    @patch('algorithms.a_star.load_data')
    def test_run_a_star(self, mock_load_data, mock_build_map):
        """Test the A* visualization wrapper function."""
        # Set up mocks to disable actual visualization
        mock_load_data.return_value = (self.neighborhoods, self.roads, self.facilities, None)
        
        # Create a mock map object
        mock_map = MagicMock()
        mock_map._repr_html_.return_value = "<html>Test Map</html>"
        
        # Set up the build_map mock to return our test data
        mock_build_map.return_value = (mock_map, self.node_positions, None, self.graph)
        
        # Run the test
        visualization, results = run_a_star("1", "3")
        
        # Check results structure
        self.assertIn("total_distance", results)
        self.assertIn("path", results)
        self.assertIn("num_segments", results)
        
        # Verify the basic HTML structure without checking detailed contents
        self.assertIsInstance(visualization, str)
        self.assertTrue(visualization.startswith("<html>"))

    @patch('algorithms.a_star.build_map')
    @patch('algorithms.a_star.load_data')
    def test_run_a_star_with_scenario(self, mock_load_data, mock_build_map):
        """Test A* with scenario filtering."""
        # Set up mocks to disable actual visualization
        mock_load_data.return_value = (self.neighborhoods, self.roads, self.facilities, None)
        
        # Create a mock map object
        mock_map = MagicMock()
        mock_map._repr_html_.return_value = "<html>Test Map</html>"
        
        # For scenario testing, remove node 2 from the graph
        scenario_graph = self.graph.copy()
        scenario_graph.remove_node("2")
        
        # Set up the build_map mock to return our modified graph
        mock_build_map.return_value = (mock_map, self.node_positions, None, scenario_graph)
        
        # Run the test
        visualization, results = run_a_star("1", "3", scenario="2")
        
        # Should still find a path (through other nodes)
        self.assertIsNotNone(results["path"])
        self.assertNotIn("2", results["path"])

if __name__ == '__main__':
    unittest.main()
