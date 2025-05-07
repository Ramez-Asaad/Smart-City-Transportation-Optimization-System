import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import numpy as np
from algorithms.mst import run_mst
from streamlit_folium import st_folium
import streamlit.components.v1 as components

st.set_page_config("Cairo Smart City", layout="wide")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize session state for network visualization and results
if "network_visualization" not in st.session_state:
    st.session_state["network_visualization"] = None
if "mst_results" not in st.session_state:
    st.session_state["mst_results"] = None
if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False

# Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["Dashboard", "Data", "Algorithms", "Reports"])

# ------ DASHBOARD ------
if menu == "Dashboard":
    st.title("Smart City Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Nodes", "120", "Network Points")
    col2.metric("Edges", "340", "Connections")
    col3.metric("Traffic", "2,500", "Records Today")

    st.subheader("Run Analysis")

    with st.form("run_analysis"):
        col1, col2 = st.columns(2)
        source = col1.selectbox("Source Point", ["A1", "B2", "C3", "D4"])
        dest = col2.selectbox("Destination Point", ["D4", "C3", "B2", "A1"])
        time_of_day = st.selectbox("Time of Day", ["Morning Rush", "Midday", "Evening"])
        scenario = st.text_input("Scenario Options", "e.g., Road Closure")
        algo = st.selectbox("Algorithm", ["Dijkstra", "A*", "Greedy", "DP"])
        submitted = st.form_submit_button("Run Algorithm")
        print("Form Submitted:", submitted)

    # Run the MST algorithm only if the form is submitted and not already processed
    if submitted and not st.session_state["form_submitted"]:
        print("Running MST Algorithm...")
        visualization, results = run_mst(
            source=source,
            dest=dest,
            time_of_day=time_of_day,
            scenario=scenario,
            algo=algo
        )
        st.session_state["network_visualization"] = visualization
        st.session_state["mst_results"] = results
        st.session_state["form_submitted"] = True

    # Display the visualization and results if they exist in session state
    if st.session_state["network_visualization"]:
        st.subheader("Network Visualization")
        # Render the Folium map as an HTML component
        components.html(st.session_state["network_visualization"], height=600)

    if st.session_state["mst_results"]:
        results = st.session_state["mst_results"]
        if "warning" in results:
            st.warning(results["warning"])
        else:
            st.subheader("Minimum Spanning Tree Results")
            st.markdown(f"**Total MST Distance:** `{results['total_distance']:.2f} km`")
            st.markdown(f"**Roads in MST:** `{results['num_edges']}`")

    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cost", "EGP 1,200", "Estimated Route Cost")
    col2.metric("Travel Time", "35 min")
    col3.metric("Coverage", "+12% Improvement")

    st.subheader("Results Table")
    df = pd.DataFrame({
        "Step": [1, 2, 3, 4],
        "Node": ["A1", "B2", "C3", "D4"],
        "Action": ["Start", "Move", "Move", "Arrive"],
        "Cost": [0, 200, 400, 1200]
    })
    st.table(df)

    st.subheader("Congestion Chart")
    st.bar_chart(np.random.randint(5, 20, size=12))

# ------ DATA MANAGEMENT ------
elif menu == "Data":
    st.title("Data Management")

    st.subheader("Upload Files")
    net_file = st.file_uploader("Network Data")
    traffic_file = st.file_uploader("Traffic Data")

    st.subheader("Data Overview")
    st.markdown("**Network:** 120 Nodes, 340 Edges")
    st.markdown("**Traffic:** 2,500 Records Today")

    st.subheader("Sample Data Table")
    st.dataframe(pd.DataFrame({
        "Node": ["A1", "B2", "C3"],
        "Type": ["Intersection", "Station", "Intersection"],
        "Degree": [4, 2, 3],
        "Status": ["Active", "Active", "Inactive"]
    }))

    st.subheader("Traffic Volume Chart")
    st.line_chart(np.random.randint(10, 30, size=12))

# ------ ALGORITHMS ------
elif menu == "Algorithms":
    st.title("Algorithm Selection")

    algo_type = st.selectbox("Choose Algorithm", ["Dijkstra", "A*", "Greedy", "DP"])

    st.text_input("Source Point", "e.g., A1")
    st.text_input("Destination Point", "e.g., D4")
    st.selectbox("Time of Day", ["Morning Rush", "Evening", "Night"])
    st.checkbox("Simulate Road Closure")
    st.checkbox("Enable Emergency Mode")

    if st.button("Run Algorithm"):
        st.success("Algorithm executed!")

        col1, col2, col3 = st.columns(3)
        col1.metric("Travel Time", "15 min")
        col2.metric("Cost", "EGP 25")
        col3.metric("Coverage", "98%")

        st.subheader("Network Visualization")
        st.info("[Mock Graph Placeholder]")

        st.subheader("Result Table")
        st.table(pd.DataFrame({
            "Step": [1, 2, 3, 4],
            "Node": ["A1", "B2", "C3", "D4"],
            "Action": ["Start", "Move", "Move", "Arrive"],
            "Cost": [0, 5, 10, 15]
        }))

        st.subheader("Congestion Chart")
        st.bar_chart(np.random.randint(10, 50, size=12))

# ------ REPORTS ------
elif menu == "Reports":
    st.title("Reports Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trips", "18,200", "Last 24 hours")
    col2.metric("Avg. Travel Time", "32 min")
    col3.metric("Congestion", "High", "Peak hours")

    st.subheader("Congestion by Area")
    st.bar_chart({
        "Downtown": [80], "Zamalek": [50], "Nasr City": [90],
        "Maadi": [65], "6th Oct": [70]
    })

    st.subheader("Recent Algorithm Runs")
    st.dataframe(pd.DataFrame({
        "Algorithm": ["Dijkstra", "A*", "Greedy"],
        "Source": ["A1", "C3", "E5"],
        "Destination": ["B2", "D4", "F6"],
        "Result Time": ["12 min", "Emergency", "Optimized"],
        "Time": ["09:10", "08:45", "07:30"]
    }))
