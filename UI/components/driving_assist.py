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
        
        scenario = st.text_input(
            "Scenario Options (e.g., Road Closure ID)",
            key="driving_scenario"
        )
        
        col1, col2 = st.columns(2)
        algo = col1.selectbox(
            "Algorithm",
            ["Dijkstra", "Time-Aware Dijkstra", "A*", "MST"],
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
        
        submitted = st.form_submit_button("Run Algorithm")

    if submitted:
        with st.spinner("Running analysis..."):
            try:
                # Prepare algorithm-specific parameters
                kwargs = {
                    "consider_road_condition": consider_conditions,
                    "avoid_congestion": avoid_congestion
                }
                
                if algo == "MST":
                    results = controller.run_algorithm(
                        "MST", source, dest, time_of_day, scenario,
                        mst_algorithm="Prim"
                    )
                elif algo == "Time-Aware Dijkstra":
                    results = controller.run_algorithm(
                        "Dijkstra", source, dest, time_of_day, scenario,
                        avoid_congestion=True
                    )
                elif algo == "A*":
                    results = controller.run_algorithm(
                        "A*", source, None, time_of_day, scenario
                    )
                else:  # Basic Dijkstra
                    results = controller.run_algorithm(
                        "Dijkstra", source, dest, time_of_day, scenario,
                        **kwargs
                    )
                
                # Display results using the controller's display method
                controller.display_results(results)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}") 