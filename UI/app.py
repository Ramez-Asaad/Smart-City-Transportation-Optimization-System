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

st.set_page_config("Cairo Smart City", layout="wide")

# Initialize controller if not in session state
if 'controller' not in st.session_state:
    st.session_state.controller = TransportationController()

# Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Data", "Algorithms", "Reports"])

# ------ DASHBOARD ------
if menu == "Dashboard":
    st.title("Smart City Dashboard")
    
    # Load data for metrics
    neighborhoods, roads, facilities = load_data()
    
    # Top-level metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Nodes", str(len(neighborhoods)), "Network Points")
    col2.metric("Edges", str(len(roads)), "Connections")
    col3.metric("Facilities", str(len(facilities)), "Service Points")

    # Public Transportation Section
    st.subheader("Public Transportation Network")
    
    # Create tabs for different views
    transit_tabs = st.tabs(["Route Planning", "Network Status", "Schedule Optimization"])
    
    with transit_tabs[0]:
        col1, col2 = st.columns(2)
        
        # Get neighborhood and facility names
        neighborhood_names = st.session_state.controller.get_neighborhood_names()
        facility_names = {
            str(row["ID"]): row["Name"]
            for _, row in facilities.iterrows()
        }
        
        # Combine all possible destinations
        all_destinations = {**neighborhood_names, **facility_names}
        
        # Source selection (neighborhoods only)
        source = col1.selectbox(
            "Starting Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x],
            key="transit_source"
        )
        
        # Destination selection (neighborhoods and facilities)
        dest = col2.selectbox(
            "Destination",
            options=list(all_destinations.keys()),
            format_func=lambda x: all_destinations[x],
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
                    schedule_results = st.session_state.controller.run_algorithm(
                        algorithm="DP",
                        source=None,
                        dest=None,
                        time_of_day=time_of_day,
                        total_buses=200,  # Default values
                        total_trains=30
                    )
                    
                    # Find route using schedules
                    route_results = st.session_state.controller.find_transit_route(
                        source=source,
                        destination=dest,
                        time_of_day=time_of_day,
                        prefer_metro=prefer_metro,
                        minimize_transfers=minimize_transfers,
                        schedules=schedule_results["results"]
                    )
                    
                    if route_results:
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
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
    
    with transit_tabs[1]:
        # Network status overview
        st.subheader("Live Network Status")
        
        # Get current schedules
        current_status = st.session_state.controller.get_network_status()
        
        # Display metro lines status
        st.markdown("#### Metro Lines")
        metro_status = pd.DataFrame(current_status["metro_lines"])
        st.dataframe(metro_status, use_container_width=True)
        
        # Display bus routes status
        st.markdown("#### Bus Routes")
        bus_status = pd.DataFrame(current_status["bus_routes"])
        st.dataframe(bus_status, use_container_width=True)
        
        # Display transfer points status
        st.markdown("#### Transfer Points")
        transfer_status = pd.DataFrame(current_status["transfer_points"])
        st.dataframe(transfer_status, use_container_width=True)
    
    with transit_tabs[2]:
        st.subheader("Schedule Optimization")
        
        # Input parameters
        col1, col2 = st.columns(2)
        
        total_buses = col1.number_input(
            "Total Available Buses",
            min_value=50,
            max_value=500,
            value=200,
            help="Total number of buses available for allocation"
        )
        
        total_trains = col2.number_input(
            "Total Available Trains",
            min_value=10,
            max_value=100,
            value=30,
            help="Total number of metro trains available for allocation"
        )
        
        if st.button("Optimize Schedules"):
            with st.spinner("Optimizing public transit schedules..."):
                try:
                    results = st.session_state.controller.run_algorithm(
                        algorithm="DP",
                        source=None,
                        dest=None,
                        time_of_day=None,
                        total_buses=total_buses,
                        total_trains=total_trains
                    )
                    
                    if results:
                        # Display optimization results
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
                            
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    st.subheader("Run Analysis")

    with st.form("run_analysis"):
        col1, col2 = st.columns(2)
        
        # Get neighborhood names for dropdowns
        neighborhood_names = st.session_state.controller.get_neighborhood_names()
        
        source = col1.selectbox(
            "Source Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x]
        )
        
        dest = col2.selectbox(
            "Destination Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x]
        )
        
        time_of_day = st.selectbox(
            "Time of Day",
            ["Morning Rush", "Midday", "Evening Rush", "Night"]
        )
        
        scenario = st.text_input("Scenario Options (e.g., Road Closure ID)")
        
        col1, col2 = st.columns(2)
        algo = col1.selectbox(
            "Algorithm",
            ["Dijkstra", "Time-Aware Dijkstra", "A*", "MST"]
        )
        
        consider_conditions = col2.checkbox("Consider Road Conditions")
        
        submitted = st.form_submit_button("Run Algorithm")

    if submitted:
        with st.spinner("Running analysis..."):
            # Prepare algorithm-specific parameters
            kwargs = {
                "consider_road_condition": consider_conditions
            }
            
            if algo == "MST":
                results = st.session_state.controller.run_algorithm(
                    "MST", source, dest, time_of_day, scenario,
                    mst_algorithm="Prim"
                )
            elif algo == "Time-Aware Dijkstra":
                results = st.session_state.controller.run_algorithm(
                    "Dijkstra", source, dest, time_of_day, scenario,
                    avoid_congestion=True
                )
            elif algo == "A*":
                results = st.session_state.controller.run_algorithm(
                    "A*", source, None, time_of_day, scenario
                )
            else:  # Basic Dijkstra
                results = st.session_state.controller.run_algorithm(
                    "Dijkstra", source, dest, time_of_day, scenario,
                    **kwargs
                )
            
            # Display results
            st.session_state.controller.display_results(results)

    # Analytics Section
    st.subheader("Network Analytics")
    
    # Infrastructure Analysis
    col1, col2, col3 = st.columns(3)
    
    # Road Condition Analysis
    avg_condition = roads["Condition(1-10)"].mean()
    poor_roads = len(roads[roads["Condition(1-10)"] < 6])
    col1.metric(
        "Average Road Condition",
        f"{avg_condition:.1f}/10",
        f"{poor_roads} roads need maintenance"
    )
    
    # Network Capacity
    total_capacity = roads["Current Capacity(vehicles/hour)"].sum()
    avg_capacity = roads["Current Capacity(vehicles/hour)"].mean()
    col2.metric(
        "Total Network Capacity",
        f"{total_capacity:,.0f} vehicles/hour",
        f"Avg: {avg_capacity:,.0f} per road"
    )
    
    # Population Coverage
    total_pop = neighborhoods["Population"].sum()
    col3.metric(
        "Total Population Served",
        f"{total_pop:,.0f}",
        f"{len(facilities)} service points"
    )
    
    # Detailed Analytics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Road Conditions Distribution")
        condition_dist = pd.DataFrame(roads["Condition(1-10)"].value_counts()).reset_index()
        condition_dist.columns = ["Condition", "Count"]
        condition_dist = condition_dist.sort_values("Condition")
        st.bar_chart(condition_dist.set_index("Condition"))
        
    with col2:
        st.subheader("Population by Area Type")
        pop_by_type = neighborhoods.groupby("Type")["Population"].sum().reset_index()
        st.bar_chart(pop_by_type.set_index("Type"))
    
    # Road Network Analysis
    st.subheader("Road Network Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Road Length Distribution
        st.subheader("Road Length Distribution")
        fig_dist = pd.DataFrame(roads["Distance(km)"].describe())
        st.dataframe(fig_dist)
        
    with col2:
        # Connectivity Analysis
        st.subheader("Area Connectivity")
        connectivity = pd.DataFrame(roads.groupby("FromID").size()).reset_index()
        connectivity.columns = ["Area", "Connections"]
        connectivity = connectivity.sort_values("Connections", ascending=False).head(5)
        st.dataframe(connectivity)
    
    # Facility Distribution
    st.subheader("Facility Distribution")
    facility_types = facilities["Type"].value_counts()
    st.bar_chart(facility_types)

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

# ------ ALGORITHMS ------
elif menu == "Algorithms":
    st.title("Algorithm Selection")
    
    algo_type = st.selectbox(
        "Choose Algorithm",
        ["Shortest Path (Dijkstra)",
         "Time-Aware Routing",
         "Emergency Services (A*)",
         "Network Analysis (MST)",
         "Public Transit Scheduling (DP)"]
    )
    
    if algo_type == "Public Transit Scheduling (DP)":
        st.title("Public Transit Schedule Optimization")
        
        # Input parameters in the sidebar
        st.sidebar.markdown("### Optimization Parameters")
        
        total_buses = st.sidebar.number_input(
            "Total Available Buses",
            min_value=50,
            max_value=500,
            value=200,
            help="Total number of buses available for allocation"
        )
        
        total_trains = st.sidebar.number_input(
            "Total Available Trains",
            min_value=10,
            max_value=100,
            value=30,
            help="Total number of metro trains available for allocation"
        )
        
        if st.sidebar.button("Run Optimization"):
            with st.spinner("Optimizing public transit schedules..."):
                try:
                    # Run the DP scheduling algorithm
                    results = st.session_state.controller.run_algorithm(
                        algorithm="DP",
                        source=None,
                        dest=None,
                        time_of_day=None,
                        total_buses=total_buses,
                        total_trains=total_trains
                    )
                    
                    if results:
                        # Show network visualization
                        st.subheader("Network Visualization")
                        st.components.v1.html(results["visualization"], height=600)
                        
                        # Display optimization metrics
                        st.subheader("Optimization Results")
                        metrics = results["results"]["metrics"]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric(
                            "Total Buses Allocated",
                            f"{metrics['total_buses_allocated']} units",
                            help="Total number of buses assigned to routes"
                        )
                        col2.metric(
                            "Total Trains Allocated",
                            f"{metrics['total_trains_allocated']} units",
                            help="Total number of trains assigned to metro lines"
                        )
                        col3.metric(
                            "Transfer Points",
                            metrics["num_transfer_points"],
                            help="Number of optimized transfer points between bus and metro"
                        )
                        col4.metric(
                            "Daily Capacity",
                            f"{metrics['total_daily_capacity']:,} passengers",
                            help="Total daily passenger capacity across all routes"
                        )
                        
                        # Create tabs for detailed results
                        tabs = st.tabs([
                            "Transfer Points",
                            "Bus Allocation",
                            "Metro Allocation",
                            "Schedules"
                        ])
                        
                        # Transfer Points Tab
                        with tabs[0]:
                            st.subheader("Optimized Transfer Points")
                            transfer_df = pd.DataFrame(
                                results["results"]["transfer_points"],
                                columns=["Transfer Point", "Score"]
                            )
                            st.dataframe(
                                transfer_df.sort_values("Score", ascending=False),
                                use_container_width=True
                            )
                        
                        # Bus Allocation Tab
                        with tabs[1]:
                            st.subheader("Bus Route Allocation")
                            bus_df = pd.DataFrame(
                                list(results["results"]["bus_allocation"].items()),
                                columns=["Route", "Buses Allocated"]
                            )
                            st.bar_chart(bus_df.set_index("Route"))
                            st.dataframe(bus_df, use_container_width=True)
                        
                        # Metro Allocation Tab
                        with tabs[2]:
                            st.subheader("Metro Line Allocation")
                            metro_df = pd.DataFrame(
                                list(results["results"]["metro_allocation"].items()),
                                columns=["Line", "Trains Allocated"]
                            )
                            st.bar_chart(metro_df.set_index("Line"))
                            st.dataframe(metro_df, use_container_width=True)
                        
                        # Schedules Tab
                        with tabs[3]:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("Bus Schedules")
                                bus_sched_df = pd.DataFrame(results["results"]["bus_schedules"])
                                st.dataframe(bus_sched_df, use_container_width=True)
                                
                                st.download_button(
                                    "📥 Download Bus Schedules (CSV)",
                                    bus_sched_df.to_csv(index=False),
                                    "bus_schedules.csv",
                                    "text/csv",
                                    help="Download the complete bus schedule in CSV format"
                                )
                            
                            with col2:
                                st.subheader("Metro Schedules")
                                metro_sched_df = pd.DataFrame(results["results"]["metro_schedules"])
                                st.dataframe(metro_sched_df, use_container_width=True)
                                
                                st.download_button(
                                    "📥 Download Metro Schedules (CSV)",
                                    metro_sched_df.to_csv(index=False),
                                    "metro_schedules.csv",
                                    "text/csv",
                                    help="Download the complete metro schedule in CSV format"
                                )
                            
                            # Add summary statistics
                            st.subheader("Schedule Summary")
                            st.markdown(f"""
                            - Average bus interval: {bus_sched_df['Interval (min)'].mean():.1f} minutes
                            - Average metro interval: {metro_sched_df['Interval (min)'].mean():.1f} minutes
                            - Total transfer points served: {len(set().union(*[set(x) for x in bus_sched_df['Transfer Points']]))}
                            - Total daily capacity: {metrics['total_daily_capacity']:,} passengers
                            """)
                
                except Exception as e:
                    st.error(f"An error occurred during optimization: {str(e)}")
                    st.info("Please check the input parameters and try again.")
    
    else:
        # Get neighborhood names for dropdowns
        neighborhood_names = st.session_state.controller.get_neighborhood_names()
        
        source = st.selectbox(
            "Source Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x]
        )
        
        dest = st.selectbox(
            "Destination Point",
            options=list(neighborhood_names.keys()),
            format_func=lambda x: neighborhood_names[x]
        )
        
        time_of_day = st.selectbox(
            "Time of Day",
            ["Morning Rush", "Midday", "Evening Rush", "Night"]
        )
        
        scenario = st.text_input("Scenario Options (e.g., Road Closure ID)")
        
        col1, col2 = st.columns(2)
        consider_conditions = col1.checkbox("Consider Road Conditions")
        avoid_congestion = col2.checkbox("Avoid Congested Routes")
        
        if st.button("Run Algorithm"):
            with st.spinner("Running analysis..."):
                try:
                    # Prepare algorithm-specific parameters
                    kwargs = {
                        "consider_road_condition": consider_conditions,
                        "avoid_congestion": avoid_congestion
                    }
                    
                    results = st.session_state.controller.run_algorithm(
                        algo_type.split(" ")[0],  # Get first word of algo type
                        source,
                        dest,
                        time_of_day,
                        scenario,
                        **kwargs
                    )
                    
                    # Display results using the controller's display method
                    st.session_state.controller.display_results(results)
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

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
