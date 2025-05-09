import streamlit as st
import pandas as pd
from typing import Dict, Any

def render_optimization_results(results: Dict[str, Any]) -> None:
    """Render the optimization results."""
    metrics = results["results"]["metrics"]
    
    # Show key metrics
    metric_cols = st.columns(4)
    metric_cols[0].metric("Buses Allocated", metrics["total_buses_allocated"])
    metric_cols[1].metric("Trains Allocated", metrics["total_trains_allocated"])
    metric_cols[2].metric("Transfer Points", metrics["num_transfer_points"])
    metric_cols[3].metric("Daily Capacity", f"{metrics['total_daily_capacity']:,}")
    
    # Show schedules
    schedule_tabs = st.tabs(["Bus Schedules", "Metro Schedules"])
    
    with schedule_tabs[0]:
        st.dataframe(
            pd.DataFrame(results["results"]["bus_schedules"]),
            use_container_width=True
        )
        
    with schedule_tabs[1]:
        st.dataframe(
            pd.DataFrame(results["results"]["metro_schedules"]),
            use_container_width=True
        )

def render_schedule_optimizer(controller) -> None:
    """Render the schedule optimization interface."""
    st.subheader("Transit Schedule Optimization")
    
    # Configuration inputs
    col1, col2 = st.columns(2)
    total_buses = col1.number_input("Total Available Buses", min_value=50, max_value=500, value=200)
    total_trains = col2.number_input("Total Available Trains", min_value=10, max_value=100, value=30)
    
    if st.button("Optimize Schedules"):
        with st.spinner("Optimizing transit schedules..."):
            try:
                results = controller.run_algorithm(
                    algorithm="DP",
                    source=None,
                    dest=None,
                    time_of_day=None,
                    total_buses=total_buses,
                    total_trains=total_trains
                )
                
                if results and "results" in results:
                    render_optimization_results(results)
                else:
                    st.error("Failed to generate schedules")
            except Exception as e:
                st.error(str(e)) 