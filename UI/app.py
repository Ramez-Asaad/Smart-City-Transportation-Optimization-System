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

st.set_page_config("Cairo Smart City", layout="wide")

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()
    
neighborhoods, roads, facilities = load_data()

# Initialize traffic simulator if not in session state
if 'traffic_simulator' not in st.session_state:
    _, node_positions, _, graph = st.session_state.controller.base_map, st.session_state.controller.node_positions, st.session_state.controller.neighborhood_ids, st.session_state.controller.graph
    st.session_state.traffic_simulator = TrafficSimulator(graph, node_positions, roads)
    st.session_state.traffic_visualizer = TrafficVisualizer(node_positions, st.session_state.traffic_simulator)

# Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Data", "Reports"])

# ------ DASHBOARD ------
if menu == "Dashboard":
    st.title("Smart City Dashboard")
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

# ------ DATA ------
elif menu == "Data":
    st.title("Data Management")
    
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

# ------ REPORTS ------
elif menu == "Reports":
    render_reports(neighborhoods, roads, facilities)
