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
    st.write("### Public Transit Route Planner")
    
    # Debug section
    if st.checkbox("Show Debug Information", value=False):
        with st.expander("Transit Network Status"):
            # Show available transit data
            st.write("Bus Routes:")
            st.dataframe(controller.bus_routes if not controller.bus_routes.empty else "No bus routes available")
            
            st.write("Metro Lines:")
            st.dataframe(controller.metro_lines if not controller.metro_lines.empty else "No metro lines available")
            
            st.write("Transfer Points:")
            st.write(list(controller.transfer_points) if controller.transfer_points else "No transfer points found")
    
    col1, col2 = st.columns(2)
    
    # Get neighborhood names
    neighborhood_names = controller.get_neighborhood_names()
    
    # Source selection
    source = col1.selectbox(
        "Starting Point",
        options=list(neighborhood_names.keys()),
        format_func=lambda x: f"{x} - {neighborhood_names[x]}",
        key="transit_source"
    )
    
    # Destination selection
    dest = col2.selectbox(
        "Destination",
        options=list(neighborhood_names.keys()),
        format_func=lambda x: f"{x} - {neighborhood_names[x]}",
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
                # Show selected locations
                st.write("Selected Route:")
                st.write(f"From: {source} - {neighborhood_names[source]}")
                st.write(f"To: {dest} - {neighborhood_names[dest]}")
                
                # Get current schedules from DP optimization
                st.write("Optimizing transit schedules...")
                schedule_results = controller.run_algorithm(
                    algorithm="DP",
                    source=None,
                    dest=None,
                    time_of_day=time_of_day,
                    total_buses=200,  # Default values
                    total_trains=30
                )
                
                if not schedule_results or "results" not in schedule_results:
                    st.error("Failed to generate transit schedules.")
                    if st.checkbox("Show Schedule Debug Info"):
                        st.write("Schedule Results:", schedule_results)
                    return
                
                st.write("Finding route with optimized schedules...")
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
                # Show detailed error information
                if st.checkbox("Show Error Details"):
                    st.error("Detailed Error Information:")
                    st.write("Source Location:", source)
                    st.write("Destination:", dest)
                    st.write("Time of Day:", time_of_day)
                    st.write("Preferences:", {
                        "prefer_metro": prefer_metro,
                        "minimize_transfers": minimize_transfers
                    })
                    # Show transit data status
                    st.write("Transit Data Status:")
                    st.write("- Bus Routes Available:", not controller.bus_routes.empty)
                    st.write("- Metro Lines Available:", not controller.metro_lines.empty)
                    st.write("- Number of Transfer Points:", len(controller.transfer_points)) 