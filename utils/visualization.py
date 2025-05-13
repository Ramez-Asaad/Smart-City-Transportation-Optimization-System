import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
from typing import Dict, List
import time
from branca.element import Figure, JavascriptLink, CssLink

class TrafficVisualizer:
    def __init__(self, node_positions: Dict, traffic_simulator):
        """
        Initialize traffic visualizer.
        
        Args:
            node_positions: Dictionary mapping node IDs to coordinates
            traffic_simulator: TrafficSimulator instance
        """
        self.node_positions = node_positions
        self.simulator = traffic_simulator
        
    def create_base_map(self) -> folium.Map:
        """Create base map for visualization."""
        # Calculate center coordinates
        center_lat = np.mean([pos[0] for pos in self.node_positions.values()])
        center_lon = np.mean([pos[1] for pos in self.node_positions.values()])
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles="cartodbdark_matter"  # Dark theme for better visualization
        )
        
        # Add required scripts for animation
        m.get_root().header.add_child(JavascriptLink("https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js"))
        
        return m
        
    def add_traffic_layer(self, m: folium.Map):
        """
        Add traffic visualization layer to map.
        
        Args:
            m: Folium map object
        """
        # Draw roads with traffic indicators
        for road_id, state in self.simulator.traffic_state.items():
            from_id, to_id = road_id.split("-")
            
            if from_id in self.node_positions and to_id in self.node_positions:
                # Get road color based on congestion
                color = self.simulator.get_congestion_color(state["congestion_level"])
                
                # Calculate width based on traffic volume
                width = 2 + (state["congestion_level"] * 4)
                
                # Create popup with traffic info
                popup_html = f"""
                <div style="width:200px;">
                    <h4>Traffic Information</h4>
                    <p>Current Load: {state['current_load']} vehicles</p>
                    <p>Capacity: {state['capacity']} vehicles/hour</p>
                    <p>Congestion: {state['congestion_level']*100:.1f}%</p>
                </div>
                """
                
                # Draw the road
                folium.PolyLine(
                    locations=[
                        self.node_positions[from_id],
                        self.node_positions[to_id]
                    ],
                    color=color,
                    weight=width,
                    opacity=0.8,
                    popup=popup_html
                ).add_to(m)
                
                # Add animated traffic flow indicators
                if state["congestion_level"] > 0.3:
                    self._add_flow_animation(m, from_id, to_id, color)
    
    def _add_flow_animation(self, m: folium.Map, from_id: str, to_id: str, color: str):
        """Add animated flow indicators to show traffic direction."""
        start_pos = self.node_positions[from_id]
        end_pos = self.node_positions[to_id]
        
        # Calculate intermediate points for animation
        num_points = 5
        lat_steps = np.linspace(start_pos[0], end_pos[0], num_points)
        lon_steps = np.linspace(start_pos[1], end_pos[1], num_points)
        
        for i in range(num_points - 1):
            folium.CircleMarker(
                location=[lat_steps[i], lon_steps[i]],
                radius=3,
                color=color,
                fill=True,
                popup="Traffic Flow Indicator"
            ).add_to(m)
    
    def add_legend(self, m: folium.Map):
        """Add traffic legend to map."""
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; 
                    border:2px solid grey; z-index:9999; 
                    background-color:black;
                    padding: 10px;
                    font-size:14px;
                    opacity: 0.8">
            <p><strong>Traffic Conditions</strong></p>
            <p>
                <i style="background: green; padding: 7px;">&nbsp;&nbsp;&nbsp;</i>
                Light Traffic
            </p>
            <p>
                <i style="background: yellow; padding: 7px;">&nbsp;&nbsp;&nbsp;</i>
                Moderate Traffic
            </p>
            <p>
                <i style="background: orange; padding: 7px;">&nbsp;&nbsp;&nbsp;</i>
                Heavy Traffic
            </p>
            <p>
                <i style="background: red; padding: 7px;">&nbsp;&nbsp;&nbsp;</i>
                Severe Congestion
            </p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def display_metrics(self, metrics: Dict):
        """Display traffic metrics in Streamlit."""
        st.markdown("""
        <style>
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .metric-card {
            background-color: #1E1E1E;
            border-radius: 10px;
            padding: 15px;
            width: 23%;
            text-align: center;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label {
            font-size: 14px;
            color: #888;
        }
        </style>
        """, unsafe_allow_html=True)

        metric_html = f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-value">{metrics['total_vehicles']:,}</div>
                <div class="metric-label">Total Vehicles</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['avg_congestion']*100:.1f}%</div>
                <div class="metric-label">Average Congestion</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['congested_roads']}</div>
                <div class="metric-label">Congested Roads</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['free_flowing_roads']}</div>
                <div class="metric-label">Free Flowing Roads</div>
            </div>
        </div>
        """
        st.markdown(metric_html, unsafe_allow_html=True)
    
    def display_traffic_simulation(self):
        """Main method to display the traffic simulation."""
        # Create two columns for controls
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Real-time Network Status")
        
        with col2:
            # Use the current time period from simulator as default
            new_time = st.selectbox(
                "Time Period",
                ["Morning Rush", "Midday", "Evening Rush", "Night"],
                index=["Morning Rush", "Midday", "Evening Rush", "Night"].index(self.simulator.current_time_period),
                help="Select time period to view traffic patterns",
                key="time_period"
            )
            
            # Only update if time period changed
            if new_time != self.simulator.current_time_period:
                self.simulator.update_traffic_state(new_time)
        
        # Display metrics at the top
        metrics = self.simulator.get_traffic_metrics()
        self.display_metrics(metrics)
        
        # Create and display map
        m = self.create_base_map()
        self.add_traffic_layer(m)
        self.add_legend(m)
        st_folium(m, height=800)
        
        # Add refresh button with loading animation
        if st.button("↻ Refresh Traffic Data", help="Generate new traffic patterns"):
            with st.spinner("Updating traffic data..."):
                time.sleep(0.5)  # Brief pause for visual feedback
                self.simulator.update_traffic_state(new_time)
                st.experimental_rerun()
