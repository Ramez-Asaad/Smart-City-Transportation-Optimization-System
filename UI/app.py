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
    page_title="CityWise",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
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
        border-bottom: 2px solid #262730;
    }
    
    .logo-image {
        max-width: 200px;
    }
    .logo-title{    
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(45deg, #FF4B4B, #FF8F8F);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
    }
    
    .logo-subtitle {
        font-size: 14px;
        color: #888;
        text-align: center;
        margin-top: 5px;
    }
    
    /* Custom button styling */
    .stButton>button {
        width: 100%;
        border: none;
        padding: 15px 20px;
        margin: 5px 0;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        background-color: transparent;
        color: #FAFAFA;
        font-size: 16px;
    }
    
    .stButton>button:hover {
        background-color: #262730;
        border: none;
    }
    
    .stButton>button:active, .stButton>button:focus {
        background-color: #FF4B4B !important;
        border: none;
        box-shadow: none;
    }
    
    .stButton>button[data-active="true"] {
        background-color: #FF4B4B !important;
        border: none;
    }
    
    .menu-icon {
        margin-right: 10px;
        font-size: 20px;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #FF4B4B;
        border-radius: 5px;
    }
    
    /* Main content styling */
    .main-title {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 30px;
        color: #FAFAFA;
    }
    
    /* Card styling */
    .stCard {
        border-radius: 15px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
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
</style>
""", unsafe_allow_html=True)

# Get the current query parameters
if "page" not in st.query_params:
    st.query_params["page"] = "Dashboard"
current_page = st.query_params["page"]

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()

neighborhoods, roads, facilities = load_data()

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
                <img src="data:image/png;base64,{}" class="logo-image" alt="CityWise Logo">
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
        button_html = f'{icon}{menu_item}'
        is_active = menu_item == current_page
        button_style = "background-color: #FF4B4B;" if is_active else ""
        
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
        <div style="position: fixed; bottom: 20px; left: 20px; font-size: 12px; color: #666;">
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
    
    # Create tabs for different data views
    data_tabs = st.tabs(["Neighborhoods", "Roads", "Facilities"])
    
    with data_tabs[0]:
        st.subheader("Neighborhoods Data")
        st.dataframe(neighborhoods, use_container_width=True)
        
    with data_tabs[1]:
        st.subheader("Roads Data")
        st.dataframe(roads, use_container_width=True)
        
    with data_tabs[2]:
        st.subheader("Facilities Data")
        st.dataframe(facilities, use_container_width=True)

elif current_page == "Reports":
    st.markdown('<h1 class="main-title">Analytics & Reports</h1>', unsafe_allow_html=True)
    render_reports(neighborhoods, roads, facilities)
