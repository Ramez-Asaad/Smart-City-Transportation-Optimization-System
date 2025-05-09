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

st.set_page_config("Cairo Smart City", layout="wide")

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()

# Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Data", "Reports"])

# ------ DASHBOARD ------
if menu == "Dashboard":
    st.title("Smart City Dashboard")
    
    # Load data for metrics
    neighborhoods, roads, facilities = load_data()
    
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


# ------ DATA MANAGEMENT ------
elif menu == "Data":
    st.title("Data Management")
    
    neighborhoods, roads, facilities = load_data()
    
    st.subheader("Network Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Neighborhoods")
        st.dataframe(neighborhoods)
        
    with col2:
        st.markdown("### Roads")
        st.dataframe(roads)
        
    with col3:
        st.markdown("### Facilities")
        st.dataframe(facilities)
    
    st.subheader("Network Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Population", f"{neighborhoods['Population'].sum():,}")
        st.metric("Total Road Length", f"{roads['Distance(km)'].sum():.1f} km")
        
    with col2:
        st.metric("Average Road Length", f"{roads['Distance(km)'].mean():.1f} km")
        st.metric("Number of Facilities", len(facilities))

# ------ REPORTS ------
elif menu == "Reports":
    st.title("Network Analysis Reports")
    
    report_type = st.selectbox(
        "Report Type",
        ["Network Overview",
         "Traffic Analysis",
         "Emergency Response",
         "Infrastructure Condition"]
    )
    
    if report_type == "Network Overview":
        neighborhoods, roads, facilities = load_data()
        
        st.subheader("Network Metrics")
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Total Population", f"{neighborhoods['Population'].sum():,}")
        col2.metric("Road Network", f"{roads['Distance(km)'].sum():.1f} km")
        col3.metric("Service Points", len(facilities))
        
        st.subheader("Population Distribution")
        st.bar_chart(neighborhoods.set_index('Name')['Population'])
        
        st.subheader("Facility Types")
        facility_counts = facilities['Type'].value_counts()
        st.bar_chart(facility_counts)
    
    elif report_type == "Traffic Analysis":
        st.info("Traffic analysis report will be implemented in the next phase")
    
    elif report_type == "Emergency Response":
        st.info("Emergency response analysis will be implemented in the next phase")
    
    else:  # Infrastructure Condition
        st.info("Infrastructure condition report will be implemented in the next phase")
