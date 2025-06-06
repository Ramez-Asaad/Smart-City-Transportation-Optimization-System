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
        # Add traffic light icon if the step has a traffic light
        traffic_light_icon = ""
        summary_text = step["summary"]
        if step.get("has_traffic_light"):
            status = step.get("traffic_light_status", "UNKNOWN")
            color = {
                "GREEN": "green",
                "YELLOW": "orange",
                "RED": "red",
                "UNKNOWN": "gray"
            }.get(status, "gray")
            traffic_light_icon = f" 🚦 <span style='color: {color}; font-weight: bold; background-color: rgba(0,0,0,0.05); padding: 2px 5px; border-radius: 3px;'>{status}</span>"
            summary_text = f"{step['summary']}{traffic_light_icon}"
        
        with st.expander(step["summary"]):
            # Display summary with HTML if it contains traffic light info
            if traffic_light_icon:
                st.markdown(f"**Route segment with traffic light:** {summary_text}", unsafe_allow_html=True)
                
            st.write(f"**Mode:** {step['mode']}")
            st.write(f"**From:** {step['from_stop']}")
            st.write(f"**To:** {step['to_stop']}")
            st.write(f"**Travel Time:** {step['travel_time']:.0f} minutes")
            if step.get('has_traffic_light'):
                delay = step.get('traffic_light_delay', 0)
                status = step.get('traffic_light_status', 'UNKNOWN')
                color = {
                    "GREEN": "green",
                    "YELLOW": "orange",
                    "RED": "red",
                    "UNKNOWN": "gray"
                }.get(status, "gray")
                
                # Create a visual impact indicator based on delay
                impact_indicator = ""
                if delay < 0.2:
                    impact_indicator = "Minimal impact"
                elif delay < 1.0:
                    impact_indicator = "Minor delay"
                else:
                    impact_indicator = "Significant delay"
                
                # Display traffic light status with colored box
                st.markdown(f"""
                <div style="background-color: rgba(0,0,0,0.05); padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid {color};">
                    <p><strong>🚦 Traffic Light Status:</strong> <span style="color: {color}; font-weight: bold;">{status}</span></p>
                    <p><strong>Expected Delay:</strong> {delay:.1f} minutes ({impact_indicator})</p>
                </div>
                """, unsafe_allow_html=True)
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
    
    # Remove traffic light options section but keep show_traffic_lights set to True
    show_traffic_lights = True
    
    # Create button - remove traffic lights text since it's always included
    find_route_text = "Find Route"
    
    if st.button(find_route_text, key="find_transit_route"):
        with st.spinner("Finding optimal public transit route..."):
            try:
                # Get current schedules from DP optimization
                schedule_results = controller.run_algorithm(
                    algorithm="DP",
                    source=None,
                    dest=None,
                    time_of_day=time_of_day,
                    total_buses=200,
                    total_trains=30,
                    show_traffic_lights=show_traffic_lights
                )
                
                if not schedule_results or "results" not in schedule_results:
                    st.error("Failed to generate transit schedules.")
                    return
                
                # Find route using schedules
                route_results = controller.find_transit_route(
                    source=source,
                    destination=dest,
                    time_of_day=time_of_day,
                    prefer_metro=prefer_metro,
                    minimize_transfers=minimize_transfers,
                    show_traffic_lights=show_traffic_lights,
                    schedules=schedule_results["results"]
                )
                
                if route_results:
                    render_route_details(route_results)
                    
                    # Remove the traffic light information section but keep traffic lights on the map
            
            except Exception as e:
                st.error(str(e)) 