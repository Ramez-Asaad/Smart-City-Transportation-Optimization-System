import unittest
import pandas as pd
import streamlit as st
from unittest.mock import patch, MagicMock, PropertyMock
from UI.components.dashboard_metrics import render_dashboard_metrics
from UI.components.transit_planner import render_route_planner
from UI.components.reports import render_reports
from tests import SAMPLE_NEIGHBORHOODS, SAMPLE_ROADS, SAMPLE_FACILITIES

class TestUIComponents(unittest.TestCase):
    def setUp(self):
        """Set up test data before each test."""
        self.neighborhoods = pd.DataFrame(SAMPLE_NEIGHBORHOODS)
        self.roads = pd.DataFrame(SAMPLE_ROADS)
        self.facilities = pd.DataFrame(SAMPLE_FACILITIES)
        
        # Mock controller with proper node positions
        self.mock_controller = MagicMock()
        self.mock_controller.get_neighborhood_names.return_value = {
            "1": "Test Area 1",
            "2": "Test Area 2",
            "3": "Test Area 3"
        }
        # Mock node_positions with real coordinates
        self.mock_controller.node_positions = {
            str(row["ID"]): (row["Y-coordinate"], row["X-coordinate"])
            for _, row in pd.concat([self.neighborhoods, self.facilities]).iterrows()
        }

    @patch("streamlit.metric")
    @patch("streamlit.columns")
    def test_dashboard_metrics(self, mock_columns, mock_metric):
        """Test dashboard metrics rendering."""
        # Mock columns to return list of MagicMocks
        mock_cols = [MagicMock(), MagicMock(), MagicMock()]
        mock_columns.return_value = mock_cols
        
        # Add metric method to each column mock
        for col in mock_cols:
            col.metric = mock_metric
        
        render_dashboard_metrics(self.neighborhoods, self.roads, self.facilities)
        
        # Verify metrics were displayed
        self.assertGreater(mock_metric.call_count, 0)

    @patch("streamlit.selectbox")
    @patch("streamlit.button")
    @patch("streamlit.columns")
    def test_route_planner(self, mock_columns, mock_button, mock_selectbox):
        """Test route planner interface."""
        # Mock columns return
        mock_cols = [MagicMock(), MagicMock()]
        mock_columns.return_value = mock_cols
        
        # Set up mock returns
        mock_selectbox.side_effect = ["1", "3", "Morning Rush"]
        mock_button.return_value = True
        
        render_route_planner(self.mock_controller, self.neighborhoods, self.facilities)
        
        # Verify controller interaction
        self.mock_controller.get_neighborhood_names.assert_called_once()
        
        # Verify UI elements were called
        self.assertGreater(mock_selectbox.call_count, 0)
        mock_button.assert_called()

    @patch("streamlit.dataframe")
    @patch("streamlit.columns")
    @patch("UI.components.transit_maps.create_bus_routes_map")
    @patch("UI.components.transit_maps.create_metro_map")
    def test_network_status(self, mock_metro_map, mock_bus_map, mock_columns, mock_dataframe):
        """Test network status display."""
        # Mock columns return
        mock_cols = [MagicMock(), MagicMock(), MagicMock()]
        mock_columns.return_value = mock_cols
        
        # Mock map creation functions
        mock_bus_map.return_value = "<div>Bus Map</div>"
        mock_metro_map.return_value = "<div>Metro Map</div>"
        
        # Set up mock network status with sample data
        network_status = {
            "metro_lines": [{"Line": "M1", "Status": "Normal"}],
            "bus_routes": [{"Route": "B1", "Status": "Normal", "Stops": "1,2,3"}],
            "transfer_points": [{"Location": "T1", "Status": "Open"}],
            "last_updated": "Now"
        }
        self.mock_controller.get_network_status.return_value = network_status
        
        # Mock neighborhoods data for map creation
        mock_neighborhoods = pd.DataFrame({
            "ID": ["1", "2", "3"],
            "Name": ["Area 1", "Area 2", "Area 3"],
            "Y-coordinate": [30.0, 30.1, 30.2],
            "X-coordinate": [31.0, 31.1, 31.2]
        })
                
        # Verify controller call
        self.mock_controller.get_network_status.assert_called_once()
        
        # Verify data display
        self.assertGreater(mock_dataframe.call_count, 0)
        mock_bus_map.assert_called_once()
        mock_metro_map.assert_called_once()

    @patch("streamlit.plotly_chart")
    @patch("streamlit.columns")
    @patch("streamlit.tabs")
    def test_reports(self, mock_tabs, mock_columns, mock_chart):
        """Test reports generation."""
        # Mock tabs return
        mock_tab_items = [MagicMock() for _ in range(4)]
        for tab in mock_tab_items:
            # Add columns method to each tab
            tab.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_tabs.return_value = mock_tab_items
        
        # Mock columns return for each tab
        mock_cols = [MagicMock(), MagicMock(), MagicMock()]  # Return 3 columns as expected
        mock_columns.return_value = mock_cols
        
        # Add plotly_chart method to each column mock
        for col in mock_cols:
            col.plotly_chart = mock_chart
        
        render_reports(self.neighborhoods, self.roads, self.facilities)
        
        # Verify charts were created
        self.assertGreater(mock_chart.call_count, 0)

    @patch("streamlit.error")
    @patch("streamlit.columns")
    def test_error_handling(self, mock_columns, mock_error):
        """Test error handling in UI components."""
        # Mock columns return
        mock_cols = [MagicMock(), MagicMock(), MagicMock()]
        mock_columns.return_value = mock_cols
        
        # Create invalid data to trigger error
        invalid_neighborhoods = pd.DataFrame(columns=["ID", "Name", "Population"])  # Missing required columns
        
        # Render component with invalid data
        render_dashboard_metrics(invalid_neighborhoods, self.roads, self.facilities)
        
        # Verify error was displayed
        mock_error.assert_called_with("Error: Invalid neighborhood data format")

if __name__ == '__main__':
    unittest.main()
