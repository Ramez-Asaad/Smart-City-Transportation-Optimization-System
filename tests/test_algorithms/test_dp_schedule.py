import unittest
import pandas as pd
import networkx as nx
from unittest.mock import patch, MagicMock
from algorithms.dp_schedule import PublicTransitOptimizer, find_transit_route
from tests import SAMPLE_NEIGHBORHOODS, SAMPLE_ROADS, SAMPLE_FACILITIES

class TestDPScheduler(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test."""
        # Create sample transit data
        self.bus_routes = pd.DataFrame({
            'RouteID': ['B1', 'B2'],
            'Stops': ['1,2,3', '2,3,F1'],
            'DailyPassengers': [5000, 4000]
        })
        
        self.metro_lines = pd.DataFrame({
            'LineID': ['M1'],
            'Stations': ['1,2,3'],
            'DailyPassengers': [10000]
        })
        
        # Create sample demand data
        self.demand_data = {
            ('1', '2'): 1000,
            ('2', '3'): 800,
            ('1', '3'): 600,
            ('2', 'F1'): 400
        }
        
        # Initialize optimizer
        self.optimizer = PublicTransitOptimizer(
            self.bus_routes,
            self.metro_lines,
            self.demand_data
        )
        
        # Create sample graph for transit route testing
        self.graph = nx.Graph()
        self.node_positions = {}
        
        # Add nodes and positions from sample data
        neighborhoods = pd.DataFrame(SAMPLE_NEIGHBORHOODS)
        facilities = pd.DataFrame(SAMPLE_FACILITIES)
        roads = pd.DataFrame(SAMPLE_ROADS)
        
        for _, row in neighborhoods.iterrows():
            self.node_positions[str(row["ID"])] = (row["Y-coordinate"], row["X-coordinate"])
            
        for _, row in facilities.iterrows():
            self.node_positions[row["ID"]] = (row["Y-coordinate"], row["X-coordinate"])
        
        # Add edges
        for _, row in roads.iterrows():
            self.graph.add_edge(
                str(row["FromID"]),
                str(row["ToID"]),
                weight=row["Distance(km)"],
                capacity=row["Current Capacity(vehicles/hour)"],
                condition=row["Condition(1-10)"],
                name=f"Road {row['FromID']}-{row['ToID']}"
            )

    def test_validate_routes(self):
        """Test route validation functionality."""
        # Test bus route validation
        valid_bus_routes = self.optimizer._validate_routes(self.bus_routes, "bus")
        self.assertEqual(len(valid_bus_routes), 2)
        
        # Test with invalid stops
        invalid_routes = pd.DataFrame({
            'RouteID': ['B3'],
            'Stops': ['999,888'],  # Non-existent stops
            'DailyPassengers': [3000]
        })
        valid_routes = self.optimizer._validate_routes(invalid_routes, "bus")
        self.assertEqual(len(valid_routes), 0)

    def test_build_integrated_network(self):
        """Test network building functionality."""
        self.optimizer.build_integrated_network()
        
        # Check if network contains all valid nodes
        for stop in ['1', '2', '3', 'F1']:
            self.assertIn(stop, self.optimizer.network.nodes())
        
        # Check edge types
        bus_edges = [(u, v) for u, v, d in self.optimizer.network.edges(data=True)
                     if d.get('type') == 'bus']
        metro_edges = [(u, v) for u, v, d in self.optimizer.network.edges(data=True)
                      if d.get('type') == 'metro']
        
        self.assertGreater(len(bus_edges), 0)
        self.assertGreater(len(metro_edges), 0)

    def test_optimize_transfer_points(self):
        """Test transfer point optimization."""
        self.optimizer.build_integrated_network()
        transfer_points = self.optimizer.optimize_transfer_points()
        
        # Check if transfer points are returned with scores
        self.assertIsInstance(transfer_points, list)
        if transfer_points:
            point, score = transfer_points[0]
            self.assertIsInstance(point, str)
            self.assertIsInstance(score, (int, float))

    def test_dp_allocate(self):
        """Test dynamic programming allocation."""
        values = [
            ('B1', 1000),
            ('B2', 800),
            ('M1', 1500)
        ]
        
        allocation = self.optimizer._dp_allocate(
            values=values,
            max_units=10,
            min_units=1,
            max_per_route=5
        )
        
        # Check allocation constraints
        self.assertLessEqual(sum(allocation.values()), 10)  # Total units constraint
        for units in allocation.values():
            self.assertGreaterEqual(units, 1)  # Minimum units constraint
            self.assertLessEqual(units, 5)  # Maximum per route constraint

    def test_optimize_resource_allocation(self):
        """Test complete resource allocation optimization."""
        self.optimizer.build_integrated_network()
        bus_alloc, metro_alloc = self.optimizer.optimize_resource_allocation(
            total_buses=10,
            total_trains=4
        )
        
        # Check allocation totals
        self.assertLessEqual(sum(bus_alloc.values()), 10)
        self.assertLessEqual(sum(metro_alloc.values()), 4)
        
        # Check minimum allocations
        for value in bus_alloc.values():
            self.assertGreaterEqual(value, 1)
        for value in metro_alloc.values():
            self.assertGreaterEqual(value, 1)
        
        # Check all routes are allocated
        self.assertEqual(
            set(bus_alloc.keys()),
            set(self.bus_routes['RouteID'])
        )
        self.assertEqual(
            set(metro_alloc.keys()),
            set(self.metro_lines['LineID'])
        )

    def test_generate_schedules(self):
        """Test schedule generation."""
        self.optimizer.build_integrated_network()
        bus_alloc = {'B1': 2, 'B2': 3}
        metro_alloc = {'M1': 2}
        
        bus_schedules, metro_schedules = self.optimizer.generate_schedules(
            bus_alloc,
            metro_alloc
        )
        
        # Check schedule contents
        self.assertEqual(len(bus_schedules), len(bus_alloc))
        self.assertEqual(len(metro_schedules), len(metro_alloc))
        
        # Check bus schedule fields
        bus_fields = [
            'Assigned Vehicles',
            'Interval (min)',
            'Transfer Points',
            'Daily Capacity'
        ]
        
        # Check metro schedule fields
        metro_fields = [
            'Assigned Trains',
            'Interval (min)',
            'Transfer Points',
            'Daily Capacity'
        ]
        
        for schedule in bus_schedules:
            for field in bus_fields:
                self.assertIn(field, schedule)
            
        for schedule in metro_schedules:
            for field in metro_fields:
                self.assertIn(field, schedule)

    @patch('algorithms.dp_schedule.build_map')
    @patch('algorithms.dp_schedule.load_data')
    def test_find_transit_route(self, mock_load_data, mock_build_map):
        """Test transit route finding functionality."""
        # Set up mocks to disable actual visualization
        mock_load_data.return_value = (pd.DataFrame(SAMPLE_NEIGHBORHOODS), 
                                      pd.DataFrame(SAMPLE_ROADS), 
                                      pd.DataFrame(SAMPLE_FACILITIES),
                                      None)
        
        # Create a mock map object
        mock_map = MagicMock()
        mock_map._repr_html_.return_value = "<html>Test Map</html>"
        
        # Set up the build_map mock to return our test data
        mock_build_map.return_value = (mock_map, self.node_positions, None, self.graph)
        
        # Create test transit data
        test_routes = {
            'bus': pd.DataFrame({
                'RouteID': ['B1'],
                'Stops': ['1,2,3'],
                'Frequency(min)': [15],
                'DailyPassengers': [5000]
            }),
            'metro': pd.DataFrame({
                'LineID': ['M1'],
                'Stations': ['1,3'],
                'Frequency(min)': [10],
                'DailyPassengers': [10000]
            })
        }
        
        # Run test with mock transit data
        with patch('algorithms.dp_schedule.get_transit_routes', return_value=test_routes):
            visualization, results = find_transit_route("1", "3", max_transfers=1)
            
            # Check results structure
            self.assertIn("total_distance", results)
            self.assertIn("path", results)
            self.assertIn("transit_types", results)
            self.assertIn("transit_lines", results)
            self.assertIn("transfers", results)
            
            # Verify transit path exists and is valid
            self.assertIsNotNone(results["path"])
            self.assertEqual(results["path"][0], "1")
            self.assertEqual(results["path"][-1], "3")
            
            # Verify the basic HTML structure without checking detailed contents
            self.assertIsInstance(visualization, str)
            self.assertTrue(visualization.startswith("<html>"))

if __name__ == '__main__':
    unittest.main()
