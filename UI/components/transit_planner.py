import streamlit as st
from typing import Dict, Any
import pandas as pd

def render_route_details(route_results: Dict[str, Any]) -> None:
    """Render the route details section including map and journey details."""
    # Display the route map
    st.subheader("Route Map")
    st.components.v1.html(route_results["visualization"], height=500)
    
    # Display route details
    st.subheader("Route Details")
    
    # Journey overview with separate travel and waiting times
    overview_cols = st.columns(5)
    overview_cols[0].metric("Travel Time", f"{route_results['total_travel_time']:.0f} min")
    overview_cols[1].metric("Waiting Time", f"{route_results['total_waiting_time']:.0f} min")
    overview_cols[2].metric("Total Distance", f"{route_results['total_distance']:.1f} km")
    overview_cols[3].metric("Transfers", str(route_results['num_transfers']))
    overview_cols[4].metric("Total Cost", f"EGP {route_results['total_cost']:.2f}")
    
    # Step by step instructions
    st.subheader("Journey Steps")
    for step in route_results["steps"]:
        with st.expander(step["summary"]):
            st.write(f"**Mode:** {step['mode']}")
            st.write(f"**From:** {step['from_stop']}")
            st.write(f"**To:** {step['to_stop']}")
            st.write(f"**Travel Time:** {step['travel_time']:.0f} minutes")
            if step['wait_time'] > 0:
                st.write(f"**Wait Time:** {step['wait_time']:.0f} minutes")
            st.write(f"**Next departure:** {step['next_departure']}")
            if step.get("line_info"):
                st.write(f"**Line:** {step['line_info']}")
            if step.get("transfer_info"):
                st.info(step["transfer_info"])

def render_route_planner(controller, neighborhoods, facilities) -> None:
    """Render the route planning interface."""
    col1, col2 = st.columns(2)
    
    # Get neighborhood names
    neighborhood_names = controller.get_neighborhood_names()
    
    # Source selection
    source = col1.selectbox(
        "Starting Point",
        options=list(neighborhood_names.keys()),
        format_func=lambda x: neighborhood_names[x],
        key="transit_source"
    )
    
    # Destination selection (now only neighborhoods)
    dest = col2.selectbox(
        "Destination",
        options=list(neighborhood_names.keys()),
        format_func=lambda x: neighborhood_names[x],
        key="transit_dest"
    )
    
    # Time selection
    time_of_day = st.selectbox(
        "Time of Day",
        ["Morning Rush", "Midday", "Evening Rush", "Night"],
        key="transit_time"
    )
    
    # Route preferences
    pref_col1, pref_col2 = st.columns(2)
    prefer_metro = pref_col1.checkbox("Prefer Metro When Possible", value=True)
    minimize_transfers = pref_col2.checkbox("Minimize Transfers", value=True)
    
    if st.button("Find Route", key="find_transit_route"):
        with st.spinner("Finding optimal public transit route..."):
            try:
                # Get current schedules from DP optimization
                schedule_results = controller.run_algorithm(
                    algorithm="DP",
                    source=None,
                    dest=None,
                    time_of_day=time_of_day,
                    total_buses=200,  # Default values
                    total_trains=30
                )
                
                # Find route using schedules
                route_results = controller.find_transit_route(
                    source=source,
                    destination=dest,
                    time_of_day=time_of_day,
                    prefer_metro=prefer_metro,
                    minimize_transfers=minimize_transfers,
                    schedules=schedule_results["results"]
                )
                
                if route_results:
                    render_route_details(route_results)
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}") 