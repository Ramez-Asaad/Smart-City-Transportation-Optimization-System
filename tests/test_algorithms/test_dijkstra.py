import unittest
import pandas as pd
import networkx as nx
from algorithms.dijkstra import dijkstra_shortest_path, run_dijkstra
from tests import SAMPLE_NEIGHBORHOODS, SAMPLE_ROADS, SAMPLE_FACILITIES

class TestDijkstraAlgorithm(unittest.TestCase):
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
                condition=row["Condition(1-10)"]
            )

    def test_dijkstra_basic_path(self):
        """Test basic shortest path finding."""
        start = "1"
        end = "3"
        path, distance = dijkstra_shortest_path(self.graph, start, end)
        
        # Check path exists
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 1)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], end)
        
        # Check path continuity
        for i in range(len(path) - 1):
            self.assertTrue(self.graph.has_edge(path[i], path[i + 1]))

    def test_dijkstra_with_conditions(self):
        """Test path finding considering road conditions."""
        start = "1"
        end = "3"
        path, distance = dijkstra_shortest_path(
            self.graph, 
            start, 
            end,
            consider_road_condition=True,
            condition_weight=0.5
        )
        
        # Path should still be valid
        self.assertIsNotNone(path)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], end)
        
        # Distance should be greater when considering conditions
        _, basic_distance = dijkstra_shortest_path(self.graph, start, end)
        self.assertGreaterEqual(distance, basic_distance)

    def test_dijkstra_no_path(self):
        """Test when no path exists."""
        # Create isolated node
        self.graph.add_node("4")
        path, distance = dijkstra_shortest_path(self.graph, "1", "4")
        
        # Should return empty path and infinite distance
        self.assertEqual(len(path), 0)
        self.assertEqual(distance, float('inf'))

    def test_run_dijkstra_visualization(self):
        """Test the visualization wrapper function."""
        visualization, results = run_dijkstra("1", "3")
        
        # Check visualization output
        self.assertIsInstance(visualization, str)
        self.assertIn("<!DOCTYPE html>", visualization)
        
        # Check results structure
        self.assertIn("total_distance", results)
        self.assertIn("path", results)
        self.assertIn("num_segments", results)
        self.assertIn("considered_conditions", results)

    def test_run_dijkstra_with_scenario(self):
        """Test path finding with scenario filtering."""
        # Test with a scenario that blocks node 2
        visualization, results = run_dijkstra("1", "3", scenario="2")
        
        # Should still find a path (through other nodes)
        self.assertIsNotNone(results["path"])
        self.assertNotIn("2", results["path"])

if __name__ == '__main__':
    unittest.main()
