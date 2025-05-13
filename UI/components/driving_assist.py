import streamlit as st
from typing import Dict, Any

def render_driving_assist(controller) -> None:
    """Render the driving assistance interface with different routing algorithms."""
    with st.form("driving_assist_form"):
        col1, col2 = st.columns(2)
        
        # Get neighborhood names for dropdowns
        neighborhood_names = controller.get_neighborhood_names()
        
        source = col1.selectbox(
            "Source Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x],
            key="driving_source"
        )
        
        dest = col2.selectbox(
            "Destination Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x],
            key="driving_dest"
        )
        
        time_of_day = st.selectbox(
            "Time of Day",
            ["Morning Rush", "Midday", "Evening Rush", "Night"],
            key="driving_time"
        )
        
        # Use a predefined list of scenario options
        scenario_options = [
            "None", 
            "Main Street Closed",
            "Downtown Congestion",
            "Rush Hour",
            "Custom..."
        ]
        
        selected_scenario = st.selectbox(
            "Scenario",
            options=scenario_options,
            key="driving_scenario_select"
        )
        
        # Show text input for custom scenario
        custom_scenario = ""
        if selected_scenario == "Custom...":
            custom_scenario = st.text_input("Describe your custom scenario")
            scenario = custom_scenario
        elif selected_scenario == "None":
            scenario = None
        else:
            scenario = selected_scenario
        
        col1, col2 = st.columns(2)
        algo = col1.selectbox(
            "Algorithm",
            ["Dijkstra", "A*", "MST"],
            key="driving_algo"
        )
        
        consider_conditions = col2.checkbox(
            "Consider Road Conditions",
            key="driving_conditions"
        )
        avoid_congestion = col2.checkbox(
            "Avoid Congested Routes",
            key="driving_congestion"
        )
        
        show_traffic_lights = st.checkbox(
            "Show Traffic Lights",
            value=True,
            key="show_traffic_lights"
        )
        
        submitted = st.form_submit_button("Run Algorithm")

    if submitted:
        with st.spinner("Running analysis..."):
            try:
                # Prepare algorithm-specific parameters
                kwargs = {
                    "consider_road_condition": consider_conditions,
                    "avoid_congestion": avoid_congestion,
                    "show_traffic_lights": show_traffic_lights
                }
                
                if algo == "MST":
                    results = controller.run_algorithm(
                        "MST", source, dest, time_of_day, scenario,
                        **kwargs
                    )
                elif algo == "A*":
                    results = controller.run_algorithm(
                        "A*", source, None, time_of_day, scenario,
                        show_traffic_lights=show_traffic_lights
                    )
                else:  # Basic Dijkstra
                    results = controller.run_algorithm(
                        "Dijkstra", source, dest, time_of_day, scenario,
                        **kwargs
                    )
                
                # Display results using the controller's display method
                controller.display_results(results)
                
                # If traffic lights are shown, display a legend
                if show_traffic_lights:
                    st.info("""
                    **Traffic Light Legend:**
                    - 🟢 **GREEN**: Minimal delay (< 0.1 min)
                    - 🟡 **YELLOW**: Brief delay (~0.5 min)
                    - 🔴 **RED**: Significant delay (varies based on remaining red time)
                    """)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}") 