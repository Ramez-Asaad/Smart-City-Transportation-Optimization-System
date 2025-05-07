import streamlit as st
import pandas as pd
import folium
import networkx as nx
from utils.helpers import load_data

@st.cache_data
def run_mst(source, dest, time_of_day, scenario, algo):
    neighborhoods, roads, facilities = load_data()

    node_positions = {
        str(row["ID"]): (row["Y-coordinate"], row["X-coordinate"])
        for _, row in neighborhoods.iterrows()
    }
    neighborhood_ids_str = neighborhoods["ID"].astype(str).str.strip().tolist()

    # Create the base map
    m = folium.Map(location=[
        neighborhoods["Y-coordinate"].mean(),
        neighborhoods["X-coordinate"].mean()
    ], zoom_start=12)

    # Add neighborhood markers
    for _, row in neighborhoods.iterrows():
        folium.CircleMarker(
            location=[row["Y-coordinate"], row["X-coordinate"]],
            radius=6, color="blue", fill=True, fill_opacity=0.8,
            popup=f"{row['Name']}<br>Population: {row['Population']}"
        ).add_to(m)

    # Add facility markers
    for _, row in facilities.iterrows():
        folium.Marker(
            location=[row["Y-coordinate"], row["X-coordinate"]],
            icon=folium.Icon(color="red", icon="info-sign"),
            popup=f"{row['Name']} ({row['Type']})"
        ).add_to(m)

    # Filter roads based on the scenario (e.g., road closures)
    if scenario:
        roads = roads[~roads["FromID"].astype(str).str.contains(scenario, case=False)]
        roads = roads[~roads["ToID"].astype(str).str.contains(scenario, case=False)]

    # Add road connections
    roads["FromID"] = roads["FromID"].astype(str).str.strip()
    roads["ToID"] = roads["ToID"].astype(str).str.strip()

    for _, row in roads.iterrows():
        from_id, to_id = row["FromID"], row["ToID"]
        if from_id in node_positions and to_id in node_positions:
            folium.PolyLine(
                [node_positions[from_id], node_positions[to_id]],
                color="gray", weight=1, opacity=0.4
            ).add_to(m)

    # Create the MST graph
    mst_graph = nx.Graph()
    for _, row in roads.iterrows():
        from_id, to_id = row["FromID"], row["ToID"]
        if from_id in neighborhood_ids_str and to_id in neighborhood_ids_str:
            mst_graph.add_edge(from_id, to_id, weight=row["Distance(km)"])

    mst_results = {}
    if len(mst_graph.edges()) > 0:
        # Run the MST algorithm based on the selected algorithm
        if algo == "Prim":
            prim_mst = nx.minimum_spanning_tree(mst_graph, algorithm="prim")
        elif algo == "Kruskal":
            prim_mst = nx.minimum_spanning_tree(mst_graph, algorithm="kruskal")
        else:
            prim_mst = nx.minimum_spanning_tree(mst_graph, algorithm="prim")  # Default to Prim

        # Add MST edges to the map
        for u, v in prim_mst.edges():
            folium.PolyLine(
                [node_positions[u], node_positions[v]],
                color="green", weight=3,
                tooltip=f"MST: {u} — {v}"
            ).add_to(m)

        total_dist = sum(mst_graph[u][v]['weight'] for u, v in prim_mst.edges())

        mst_results["total_distance"] = total_dist
        mst_results["num_edges"] = len(prim_mst.edges())
    else:
        mst_results["warning"] = "⚠️ No valid roads between neighborhoods!"

    # Return the map as an HTML string
    return m._repr_html_(), mst_results