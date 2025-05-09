import streamlit as st
import pandas as pd
import folium
import networkx as nx
from utils.helpers import load_data, build_map

@st.cache_data
def run_mst(source, dest, time_of_day, scenario, algo):
    # Load data
    neighborhoods, roads, facilities = load_data()
    
    # Build base map and get graph components
    m, node_positions, neighborhood_ids_str, base_graph = build_map(
        neighborhoods, roads, facilities, scenario
    )

    mst_results = {}
    if len(base_graph.edges()) > 0:
        # Run the MST algorithm based on the selected algorithm
        if algo == "Prim":
            mst = nx.minimum_spanning_tree(base_graph, algorithm="prim")
        elif algo == "Kruskal":
            mst = nx.minimum_spanning_tree(base_graph, algorithm="kruskal")
        else:
            mst = nx.minimum_spanning_tree(base_graph, algorithm="prim")  # Default to Prim

        # Add MST edges to the map
        for u, v in mst.edges():
            # Get edge data for popup information
            edge_data = base_graph[u][v]
            
            # Create detailed popup text
            popup_text = f"""
            <b>{edge_data['name']}</b><br>
            Distance: {edge_data['weight']:.1f} km<br>
            Capacity: {edge_data['capacity']} vehicles/hour<br>
            Condition: {edge_data['condition']}/10
            """
            
            folium.PolyLine(
                [node_positions[u], node_positions[v]],
                color="green", weight=3,
                popup=popup_text
            ).add_to(m)

        total_dist = sum(base_graph[u][v]['weight'] for u, v in mst.edges())

        mst_results["total_distance"] = total_dist
        mst_results["num_edges"] = len(mst.edges())
        
        # Add list of roads in MST
        mst_results["roads"] = [base_graph[u][v]['name'] for u, v in mst.edges()]
    else:
        mst_results["warning"] = "⚠️ No valid roads between neighborhoods!"

    # Return the map as an HTML string
    return m._repr_html_(), mst_results