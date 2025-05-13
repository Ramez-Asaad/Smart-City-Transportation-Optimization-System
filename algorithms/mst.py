import streamlit as st
import pandas as pd
import folium
import networkx as nx
from utils.helpers import load_data, build_map

def prim_mst(graph, start):
    """
    Compute the Minimum Spanning Tree (MST) of a graph using Prim's algorithm.
    Args:
        graph: A NetworkX-like graph object with .nodes() and .edges(data=True)
        start: The starting node ID
    Returns:
        mst_edges: List of (u, v, data) tuples representing the MST edges
    """
    import heapq

    visited = set([start])
    edges = []
    mst_edges = []

    # Add all edges from the start node to the heap
    for neighbor in graph.neighbors(start):
        data = graph[start][neighbor]
        heapq.heappush(edges, (data['weight'], start, neighbor, data))

    while edges and len(visited) < len(graph.nodes()):
        weight, u, v, data = heapq.heappop(edges)
        if v in visited:
            continue
        # Add edge to MST
        mst_edges.append((u, v, data))
        visited.add(v)
        # Add new edges from the newly visited node
        for neighbor in graph.neighbors(v):
            if neighbor not in visited:
                ndata = graph[v][neighbor]
                heapq.heappush(edges, (ndata['weight'], v, neighbor, ndata))

    return mst_edges

def run_mst(source, dest, time_of_day, scenario):
    """
    Run Minimum Spanning Tree algorithm on the transportation network.
    
    Args:
        source: Starting point ID
        dest: Destination ID
        time_of_day: Time period for analysis
        scenario: Optional scenario for road closures
        algo: Algorithm to use ('Prim' or 'Kruskal')
        
    Returns:
        Tuple[str, Dict]: HTML string of map visualization and results dictionary
    """
    # Load data
    neighborhoods, roads, facilities, traffic_lights = load_data()
    
    # Build base map and get graph components
    m, node_positions, neighborhood_ids_str, base_graph = build_map(
        neighborhoods, roads, facilities, scenario
    )

    mst_results = {}
    if len(base_graph.edges()) > 0:
        # Run the MST algorithm "prim"
        mst = prim_mst(base_graph, source)

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
        mst_results["roads"] = [base_graph[u][v]['name'] for u, v in mst.edges()]
    else:
        mst_results["warning"] = "No valid roads between neighborhoods!"

    # Return the map as an HTML string
    return m._repr_html_(), mst_results