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
from components.network_status import render_network_status
from components.schedule_optimizer import render_schedule_optimizer
from components.driving_assist import render_driving_assist
from components.reports import render_reports

st.set_page_config("Cairo Smart City", layout="wide")

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()

# Load data once for reuse
neighborhoods, roads, facilities = load_data()

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
    
    # Network Status Tab
    with main_tabs[1]:
        render_network_status(st.session_state.controller)
    
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
