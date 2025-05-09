import unittest
import pandas as pd
import networkx as nx
import folium
from utils.helpers import load_data, build_map, calculate_distance
from tests import SAMPLE_NEIGHBORHOODS, SAMPLE_ROADS, SAMPLE_FACILITIES

class TestHelperFunctions(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test."""
        self.neighborhoods = pd.DataFrame(SAMPLE_NEIGHBORHOODS)
        self.roads = pd.DataFrame(SAMPLE_ROADS)
        self.facilities = pd.DataFrame(SAMPLE_FACILITIES)

    def test_calculate_distance(self):
        """Test distance calculation function."""
        pos1 = (0, 0)
        pos2 = (3, 4)
        self.assertEqual(calculate_distance(pos1, pos2), 5.0)
        
        # Test with real coordinates
        pos1 = (30.0, 31.0)
        pos2 = (30.0, 32.0)
        self.assertGreater(calculate_distance(pos1, pos2), 0)

    def test_build_map(self):
        """Test map building functionality."""
        m, node_positions, neighborhood_ids, graph = build_map(
            self.neighborhoods,
            self.roads,
            self.facilities
        )
        
        # Check map object
        self.assertIsInstance(m, folium.Map)
        
        # Check node positions
        self.assertIsInstance(node_positions, dict)
        expected_nodes = (
            set(str(id) for id in self.neighborhoods["ID"]) |
            set(str(id) for id in self.facilities["ID"])
        )
        self.assertEqual(set(node_positions.keys()), expected_nodes)
        
        # Check neighborhood IDs
        self.assertIsInstance(neighborhood_ids, list)
        self.assertEqual(
            set(neighborhood_ids),
            set(str(id) for id in self.neighborhoods["ID"])
        )
        
        # Check graph
        self.assertIsInstance(graph, nx.Graph)
        
        # Check graph edges
        for _, row in self.roads.iterrows():
            from_id = str(row["FromID"])
            to_id = str(row["ToID"])
            self.assertTrue(graph.has_edge(from_id, to_id))
            
            # Check edge attributes
            edge_data = graph[from_id][to_id]
            self.assertEqual(edge_data["weight"], row["Distance(km)"])
            self.assertEqual(edge_data["capacity"], row["Current Capacity(vehicles/hour)"])
            self.assertEqual(edge_data["condition"], row["Condition(1-10)"])

    def test_build_map_with_scenario(self):
        """Test map building with scenario filtering."""
        scenario = "2"  # Filter out roads connected to node 2
        m, node_positions, neighborhood_ids, graph = build_map(
            self.neighborhoods,
            self.roads,
            self.facilities,
            scenario=scenario
        )
        
        # Check that roads connected to node 2 are filtered out
        for _, row in self.roads.iterrows():
            from_id = str(row["FromID"])
            to_id = str(row["ToID"])
            if scenario in [from_id, to_id]:
                self.assertFalse(graph.has_edge(from_id, to_id))

    def test_build_map_without_facilities(self):
        """Test map building without showing facilities."""
        m, node_positions, neighborhood_ids, graph = build_map(
            self.neighborhoods,
            self.roads,
            self.facilities,
            show_facilities=False
        )
        
        # Check that facility markers are not shown on map
        facility_markers = [child for child in m._children.values() 
                          if isinstance(child, folium.Marker) and 
                          isinstance(child.icon, folium.Icon) and 
                          child.icon.icon == "info-sign"]
        self.assertEqual(len(facility_markers), 0)
        
        # Check that facility nodes are not in the graph
        facility_ids = set(str(id).strip() for id in self.facilities["ID"])
        self.assertTrue(all(fid not in graph.nodes for fid in facility_ids))
        
        # Check that roads connected to facilities are not in the graph
        for _, row in self.roads.iterrows():
            from_id = str(row["FromID"]).strip()
            to_id = str(row["ToID"]).strip()
            if from_id in facility_ids or to_id in facility_ids:
                self.assertFalse(graph.has_edge(from_id, to_id))
        
        # But neighborhood nodes and edges should still be present
        self.assertGreater(len(graph.nodes()), 0)
        self.assertGreater(len(graph.edges()), 0)

    def test_build_map_with_invalid_data(self):
        """Test map building with invalid data."""
        # Create invalid roads data
        invalid_roads = pd.DataFrame({
            "FromID": ["999"],  # Non-existent node
            "ToID": ["888"],    # Non-existent node
            "Name": ["Invalid Road"],
            "Distance(km)": [5.0],
            "Current Capacity(vehicles/hour)": [1000],
            "Condition(1-10)": [8]
        })
        
        # Should still build map with neighborhoods
        m, node_positions, neighborhood_ids, graph = build_map(
            self.neighborhoods,
            invalid_roads,
            pd.DataFrame()  # Empty facilities
        )
        
        # Should have nodes from neighborhoods
        self.assertEqual(
            len(graph.nodes()),
            len(self.neighborhoods)
        )

if __name__ == '__main__':
    unittest.main()
