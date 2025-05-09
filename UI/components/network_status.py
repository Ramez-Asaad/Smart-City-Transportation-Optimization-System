import streamlit as st
import pandas as pd
from .transit_maps import create_bus_routes_map, create_metro_map

def render_network_status(controller) -> None:
    """Render the network status overview."""
    # Get current schedules
    current_status = controller.get_network_status()
    
    # Create tabs for different views
    status_tabs = st.tabs(["Live Status", "Network Maps"])
    
    # Live Status Tab
    with status_tabs[0]:
        st.subheader("Live Network Status")
        
        # Display metro lines status
        st.markdown("#### Metro Lines")
        metro_status = pd.DataFrame(current_status["metro_lines"])
        st.dataframe(metro_status, use_container_width=True)
        
        # Display bus routes status
        st.markdown("#### Bus Routes")
        bus_status = pd.DataFrame(current_status["bus_routes"])
        st.dataframe(bus_status, use_container_width=True)
        
        # Display transfer points status
        st.markdown("#### Transfer Points")
        transfer_status = pd.DataFrame(current_status["transfer_points"])
        st.dataframe(transfer_status, use_container_width=True)
    
    # Network Maps Tab
    with status_tabs[1]:
        try:
            # Load transit data
            bus_routes = pd.read_csv('data/bus_routes.csv')
            metro_lines = pd.read_csv('data/metro_lines.csv')
            neighborhoods = pd.read_csv('data/neighborhoods.csv')
            
            # Create sub-tabs for bus and metro maps
            map_tabs = st.tabs(["Bus Network", "Metro Network"])
            
            # Bus Network Map
            with map_tabs[0]:
                st.subheader("Bus Routes Network")
                bus_map_html = create_bus_routes_map(controller, neighborhoods, bus_routes)
                st.components.v1.html(bus_map_html, height=600)
            
            # Metro Network Map
            with map_tabs[1]:
                st.subheader("Metro Lines Network")
                metro_map_html = create_metro_map(controller, neighborhoods, metro_lines)
                st.components.v1.html(metro_map_html, height=600)
        except Exception as e:
            st.error("Failed to load network maps") 