import streamlit as st
import sys
import os
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
from controller.controller import TransportationController
from utils.helpers import load_data
from components.dashboard_metrics import render_dashboard_metrics, render_public_transit_section
from components.transit_planner import render_route_planner
from components.schedule_optimizer import render_schedule_optimizer
from components.driving_assist import render_driving_assist
from components.reports import render_reports
from utils.traffic_simulation import TrafficSimulator
from utils.visualization import TrafficVisualizer

# Helper function to encode the image
def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as image_file:
        import base64
        return base64.b64encode(image_file.read()).decode()

# Get the logo as favicon
logo_path = "logo_transperant.png"
if os.path.exists(logo_path):
    encoded_logo = get_base64_encoded_image(logo_path)
    favicon = f"data:image/png;base64,{encoded_logo}"
else:
    favicon = "🌆"  # Fallback emoji if logo not found

# Set page config with custom theme
st.set_page_config(
    page_title="GreedyMinds",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Global styles */
    .stApp {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 0;
    }
    
    .sidebar-content {
        padding: 20px 10px;
    }
    
    /* Logo container styling */
    .logo-container {
        text-align: center;
        padding: 20px 10px;
        border-bottom: 1px solid #E5D3A9;
    }
    
    .logo-image {
        max-width: 140px;
    }

    .logo-title {    
        font-size: 28px;
        font-weight: 600;
        background: linear-gradient(90deg, #C08A38, #E5B660);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
    }
    
    .logo-subtitle {
        font-size: 14px;
        color: #8C6D3F;
        text-align: center;
        margin-top: 5px;
    }
    
    /* Custom button styling */
    .stButton>button {
        width: 100%;
        border: none;
        padding: 12px 16px;
        margin: 4px 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        background-color: transparent;
        color: #5A4214;
        font-size: 15px;
        letter-spacing: 0.2px;
    }
    
    .stButton>button:hover {
        background-color: #F5ECD9;
        border: none;
    }
    
    .stButton>button:active, .stButton>button:focus {
        background-color: #C08A38 !important;
        color: white;
        border: none;
        box-shadow: none;
    }
    
    .stButton>button[data-active="true"] {
        background-color: #C08A38 !important;
        color: white;
        border: none;
    }
    
    .menu-icon {
        margin-right: 10px;
        font-size: 18px;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #D9BD7E;
        border-radius: 10px;
    }
    
    /* Main content styling */
    .main-title {
        font-size: 28px;
        font-weight: 600;
        margin-bottom: 24px;
        color: #5A4214;
    }
    
    /* Card styling */
    .stCard {
        border-radius: 8px;
        border: 1px solid #E5D3A9;
        box-shadow: 0 2px 4px rgba(192, 138, 56, 0.1);
    }
    
    /* DataFrames and tables */
    .dataframe {
        border: 1px solid #E5D3A9;
        border-collapse: collapse;
    }
    
    .dataframe th {
        background-color: #F5ECD9;
        color: #5A4214;
        font-weight: 600;
        padding: 8px 10px;
        border: 1px solid #E5D3A9;
    }
    
    .dataframe td {
        padding: 8px 10px;
        border: 1px solid #E5D3A9;
    }
    
    /* Metrics styling */
    .stMetric label {
        color: #8C6D3F !important;
    }
    
    /* Hide default button styling */
    .stButton>button:hover {
        border: none;
        box-shadow: none;
    }
    
    .stButton>button:focus {
        border: none;
        box-shadow: none;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 16px;
        border-radius: 6px 6px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #F5ECD9;
        border-bottom: 2px solid #C08A38;
    }
    
    /* Info and success messages */
    .stAlert {
        background-color: #FFFBF0;
        border-left-color: #C08A38;
    }
    
    /* Maps and visualizations */
    .folium-map {
        border: 1px solid #E5D3A9;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Get the current query parameters
if "page" not in st.query_params:
    st.query_params["page"] = "Dashboard"
current_page = st.query_params["page"]

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()

# Load base network data
neighborhoods, roads, facilities, traffic_lights = load_data()

# Initialize traffic simulator if not in session state
if 'traffic_simulator' not in st.session_state:
    _, node_positions, _, graph = st.session_state.controller.base_map, st.session_state.controller.node_positions, st.session_state.controller.neighborhood_ids, st.session_state.controller.graph
    st.session_state.traffic_simulator = TrafficSimulator(graph, node_positions, roads)
    st.session_state.traffic_visualizer = TrafficVisualizer(node_positions, st.session_state.traffic_simulator)

# Custom sidebar with icons
with st.sidebar:
    # Logo section
    logo_path = "logo_transperant.png"
    if os.path.exists(logo_path):
        st.markdown("""
            <div class="logo-container">
                <img src="data:image/png;base64,{}" class="logo-image" alt="GreedyMinds Logo">
                <div class="logo-title">CityWise</div>
                <div class="logo-subtitle">Smart Urban Transportation</div>
            </div>
        """.format(get_base64_encoded_image(logo_path)), unsafe_allow_html=True)
    else:
        st.error("Logo file not found. Please check the path: " + logo_path)
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    
    # Menu items with icons
    menu_items = {
        "Dashboard": "📊",
        "Data": "📁",
        "Reports": "📈"
    }
    
    # Create buttons for each menu item
    for menu_item, icon in menu_items.items():
        button_html = f'{icon} {menu_item}'
        is_active = menu_item == current_page
        button_style = "background-color: #C08A38; color: white;" if is_active else ""
        
        if st.button(
            button_html,
            key=f"btn_{menu_item}",
            help=f"View {menu_item}",
            use_container_width=True
        ):
            # Update query parameters for navigation
            st.query_params["page"] = menu_item
            st.markdown(f'<meta http-equiv="refresh" content="0; URL=?page={menu_item}">', unsafe_allow_html=True)
            st.stop()
    
    # Add system info at bottom of sidebar
    st.markdown("""
        <div style="position: fixed; bottom: 20px; left: 20px; font-size: 12px; color: #8C6D3F;">
            <div style="margin-bottom: 5px;">🕒 System Status: Online</div>
            <div>📡 Last Updated: Just Now</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


# Main content based on selection
if current_page == "Dashboard":
    st.markdown('<h1 class="main-title">CityWise Dashboard</h1>', unsafe_allow_html=True)
    # Render dashboard metrics
    render_dashboard_metrics(neighborhoods, roads, facilities)
    
    # Create main navigation tabs
    main_tabs = st.tabs(["Route Planning", "Network Status", "Schedule Optimization"])
    
    # Route Planning Tab
    with main_tabs[0]:
        # Create sub-tabs for different routing options
        route_tabs = st.tabs(["Public Transit", "Driving Assist"])
        
        # Public Transit sub-tab
        with route_tabs[0]:
            render_route_planner(st.session_state.controller, neighborhoods, facilities)
        
        # Driving Assist sub-tab
        with route_tabs[1]:
            render_driving_assist(st.session_state.controller)
    
    # Network Status Tab (Now with Traffic Simulation)
    with main_tabs[1]:
        st.session_state.traffic_visualizer.display_traffic_simulation()
    
    # Schedule Optimization Tab
    with main_tabs[2]:
        render_schedule_optimizer(st.session_state.controller)

elif current_page == "Data":
    st.markdown('<h1 class="main-title">Data Management</h1>', unsafe_allow_html=True)
    
    # Create helper functions to translate IDs to names
    def get_translated_neighborhoods(neighborhoods_df):
        """Returns a copy of the dataframe with readable names for display"""
        df = neighborhoods_df.copy()
        return df
    
    def get_translated_roads(roads_df, neighborhood_names):
        """Returns a copy of the roads dataframe with readable names"""
        df = roads_df.copy()
        # Add columns with translated names
        df['From Location'] = df['FromID'].apply(lambda x: f"{x} - {neighborhood_names.get(str(x), 'Unknown')}" if str(x) in neighborhood_names else x)
        df['To Location'] = df['ToID'].apply(lambda x: f"{x} - {neighborhood_names.get(str(x), 'Unknown')}" if str(x) in neighborhood_names else x)
        # Reorder columns to show translated names first
        cols = df.columns.tolist()
        cols = ['Name', 'From Location', 'To Location'] + [col for col in cols if col not in ['Name', 'From Location', 'To Location']]
        return df[cols]
    
    def get_translated_facilities(facilities_df):
        """Returns a copy of the facilities dataframe with readable names"""
        df = facilities_df.copy()
        return df
    
    def get_translated_traffic_lights(traffic_lights_df, neighborhood_names):
        """Returns a copy of the traffic lights dataframe with readable names"""
        df = traffic_lights_df.copy()
        if not df.empty:
            # Add columns with translated names
            df['From Location'] = df['FromID'].apply(lambda x: f"{x} - {neighborhood_names.get(str(x), 'Unknown')}" if str(x) in neighborhood_names else x)
            df['To Location'] = df['ToID'].apply(lambda x: f"{x} - {neighborhood_names.get(str(x), 'Unknown')}" if str(x) in neighborhood_names else x)
            # Reorder columns
            cols = df.columns.tolist()
            cols = ['ID', 'IntersectionID', 'From Location', 'To Location'] + [col for col in cols if col not in ['ID', 'IntersectionID', 'From Location', 'To Location', 'FromID', 'ToID']]
            return df[cols]
        return df
    
    def get_translated_bus_routes(bus_routes_df, neighborhood_names):
        """Returns a copy of the bus routes dataframe with translated stop names"""
        df = bus_routes_df.copy()
        if not df.empty and 'Stops' in df.columns:
            # Create a new column with translated stop names
            df['Translated Stops'] = df['Stops'].apply(
                lambda stops: ', '.join([
                    f"{stop.strip()} - {neighborhood_names.get(stop.strip(), 'Unknown')}" 
                    for stop in str(stops).split(',')
                    if stop.strip() in neighborhood_names
                ]) if stops else ''
            )
            # Reorder columns
            cols = df.columns.tolist()
            new_cols = ['RouteID', 'Translated Stops'] + [col for col in cols if col not in ['RouteID', 'Translated Stops', 'Stops']]
            return df[new_cols]
        return df
    
    def get_translated_metro_lines(metro_lines_df, neighborhood_names):
        """Returns a copy of the metro lines dataframe with translated station names"""
        df = metro_lines_df.copy()
        if not df.empty and 'Stations' in df.columns:
            # Create a new column with translated station names
            df['Translated Stations'] = df['Stations'].apply(
                lambda stations: ', '.join([
                    f"{station.strip()} - {neighborhood_names.get(station.strip(), 'Unknown')}"
                    for station in str(stations).split(',')
                    if station.strip() in neighborhood_names
                ]) if stations else ''
            )
            # Reorder columns
            cols = df.columns.tolist()
            new_cols = ['LineID', 'Translated Stations'] + [col for col in cols if col not in ['LineID', 'Translated Stations', 'Stations']]
            return df[new_cols]
        return df
    
    # Get neighborhood names for translation
    neighborhood_names = st.session_state.controller.get_neighborhood_names()
    
    # Create tabs for different data views
    data_tabs = st.tabs(["Neighborhoods", "Roads", "Facilities", "Traffic Lights", "Bus Routes", "Metro Lines"])
    
    with data_tabs[0]:
        st.subheader("Neighborhoods Data")
        translated_neighborhoods = get_translated_neighborhoods(neighborhoods)
        
        # Add view toggle
        view_raw = st.checkbox("View Raw Data", key="neighborhoods_raw", value=False)
        display_df = neighborhoods if view_raw else translated_neighborhoods
        
        st.dataframe(display_df, use_container_width=True)
        
        # Add download button for neighborhoods data
        csv = neighborhoods.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Neighborhoods Data",
            data=csv,
            file_name="neighborhoods.csv",
            mime="text/csv"
        )
        
    with data_tabs[1]:
        st.subheader("Roads Data")
        translated_roads = get_translated_roads(roads, neighborhood_names)
        
        # Add view toggle
        view_raw = st.checkbox("View Raw Data", key="roads_raw", value=False)
        display_df = roads if view_raw else translated_roads
        
        st.dataframe(display_df, use_container_width=True)
        
        # Add download button for roads data
        csv = roads.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Roads Data",
            data=csv,
            file_name="roads.csv",
            mime="text/csv"
        )
        
    with data_tabs[2]:
        st.subheader("Facilities Data")
        translated_facilities = get_translated_facilities(facilities)
        
        # Add view toggle
        view_raw = st.checkbox("View Raw Data", key="facilities_raw", value=False)
        display_df = facilities if view_raw else translated_facilities
        
        st.dataframe(display_df, use_container_width=True)
        
        # Add download button for facilities data
        csv = facilities.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Facilities Data",
            data=csv,
            file_name="facilities.csv",
            mime="text/csv"
        )
        
    with data_tabs[3]:
        st.subheader("Traffic Lights Data")
        # Display traffic lights data with explanation
        st.info("Traffic lights are placed at intersections and regulate traffic flow. Each traffic light follows a cycle pattern of green, yellow, and red phases.")
        
        # Translate traffic lights data
        translated_traffic_lights = get_translated_traffic_lights(traffic_lights, neighborhood_names)
        
        # Add view toggle
        view_raw = st.checkbox("View Raw Data", key="traffic_lights_raw", value=False)
        display_df = traffic_lights if view_raw else translated_traffic_lights
        
        # Add search box for traffic lights
        if not traffic_lights.empty:
            search_term = st.text_input("🔍 Search Traffic Lights", key="traffic_lights_search")
            if search_term:
                # Filter the dataframe based on search term
                filtered_data = display_df[
                    display_df.astype(str).apply(
                        lambda row: row.str.contains(search_term, case=False).any(),
                        axis=1
                    )
                ]
                st.dataframe(filtered_data, use_container_width=True)
            else:
                st.dataframe(display_df, use_container_width=True)
        else:
            st.dataframe(display_df, use_container_width=True)
        
        # Add download button for traffic lights data
        if not traffic_lights.empty:
            csv = traffic_lights.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Traffic Lights Data",
                data=csv,
                file_name="traffic_lights.csv",
                mime="text/csv"
            )
        
        # Add visualization metrics
        if not traffic_lights.empty:
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Total Traffic Lights", len(traffic_lights))
            
            # Calculate average cycle times
            avg_cycle = traffic_lights["CycleTime"].mean()
            avg_green = traffic_lights["GreenTime"].mean()
            
            metrics_col2.metric("Avg. Cycle Time", f"{avg_cycle:.1f}s")
            metrics_col3.metric("Avg. Green Time", f"{avg_green:.1f}s")
    
    with data_tabs[4]:
        st.subheader("Bus Routes Data")
        # Load bus routes data
        try:
            # Get bus routes directly from controller
            bus_routes = st.session_state.controller.bus_routes
            
            if not bus_routes.empty:
                st.info("Bus routes connect neighborhoods and facilities with scheduled services.")
                
                # Translate bus routes data
                translated_bus_routes = get_translated_bus_routes(bus_routes, neighborhood_names)
                
                # Add view toggle
                view_raw = st.checkbox("View Raw Data", key="bus_routes_raw", value=False)
                display_df = bus_routes if view_raw else translated_bus_routes
                
                # Add search box for bus routes
                search_term = st.text_input("🔍 Search Bus Routes", key="bus_routes_search")
                if search_term:
                    # Filter the dataframe based on search term
                    filtered_data = display_df[
                        display_df.astype(str).apply(
                            lambda row: row.str.contains(search_term, case=False).any(),
                            axis=1
                        )
                    ]
                    st.dataframe(filtered_data, use_container_width=True)
                else:
                    st.dataframe(display_df, use_container_width=True)
                
                # Add download button for bus routes data
                csv = bus_routes.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Bus Routes Data",
                    data=csv,
                    file_name="bus_routes.csv",
                    mime="text/csv"
                )
                
                # Add metrics
                metrics_col1, metrics_col2 = st.columns(2)
                metrics_col1.metric("Total Bus Routes", len(bus_routes))
                
                # Calculate total stops
                total_stops = sum(len(str(route).split(',')) for route in bus_routes["Stops"] if route)
                metrics_col2.metric("Total Bus Stops", total_stops)
            else:
                st.warning("No bus routes data available.")
        except Exception as e:
            st.error(f"Error loading bus routes data: {str(e)}")
    
    with data_tabs[5]:
        st.subheader("Metro Lines Data")
        # Load metro lines data
        try:
            # Get metro lines directly from controller
            metro_lines = st.session_state.controller.metro_lines
            
            if not metro_lines.empty:
                st.info("Metro lines provide rapid transit between major stations with higher capacity than bus routes.")
                
                # Translate metro lines data
                translated_metro_lines = get_translated_metro_lines(metro_lines, neighborhood_names)
                
                # Add view toggle
                view_raw = st.checkbox("View Raw Data", key="metro_lines_raw", value=False)
                display_df = metro_lines if view_raw else translated_metro_lines
                
                # Add search box for metro lines
                search_term = st.text_input("🔍 Search Metro Lines", key="metro_lines_search")
                if search_term:
                    # Filter the dataframe based on search term
                    filtered_data = display_df[
                        display_df.astype(str).apply(
                            lambda row: row.str.contains(search_term, case=False).any(),
                            axis=1
                        )
                    ]
                    st.dataframe(filtered_data, use_container_width=True)
                else:
                    st.dataframe(display_df, use_container_width=True)
                
                # Add download button for metro lines data
                csv = metro_lines.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Metro Lines Data",
                    data=csv,
                    file_name="metro_lines.csv",
                    mime="text/csv"
                )
                
                # Add metrics
                metrics_col1, metrics_col2 = st.columns(2)
                metrics_col1.metric("Total Metro Lines", len(metro_lines))
                
                # Calculate total stations
                total_stations = sum(len(str(line).split(',')) for line in metro_lines["Stations"] if line)
                metrics_col2.metric("Total Metro Stations", total_stations)
            else:
                st.warning("No metro lines data available.")
        except Exception as e:
            st.error(f"Error loading metro lines data: {str(e)}")

elif current_page == "Reports":
    st.markdown('<h1 class="main-title">Analytics & Reports</h1>', unsafe_allow_html=True)
    render_reports(neighborhoods, roads, facilities)
