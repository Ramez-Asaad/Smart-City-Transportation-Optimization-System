import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os

@st.cache_data
def load_data():
    """Load and clean the data from CSV files."""
    try:
        # Load the data from CSV files with explicit handling of whitespace
        neighborhoods = pd.read_csv(
            os.path.join("data", "neighborhoods.csv"),
            skipinitialspace=True
        )
        roads = pd.read_csv(
            os.path.join("data", "roads.csv"),
            skipinitialspace=True
        )
        facilities = pd.read_csv(
            os.path.join("data", "facilities.csv"),
            skipinitialspace=True
        )
        
        # Clean column names and data
        for df in [neighborhoods, roads, facilities]:
            df.columns = df.columns.str.strip()
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()
        
        return neighborhoods, roads, facilities
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}")

def calculate_distance(pos1, pos2):
    """Calculate Euclidean distance between two coordinates."""
    return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5

@st.cache_data
def build_map(neighborhoods, roads, facilities, scenario=None, show_facilities=True):
    """
    Builds a base map with all components that can be reused across different algorithms.
    
    Args:
        neighborhoods (pd.DataFrame): Neighborhoods data
        roads (pd.DataFrame): Roads data
        facilities (pd.DataFrame): Facilities data
        scenario (str, optional): Scenario for road closures
        show_facilities (bool): Whether to show facilities on the map
    
    Returns:
        tuple: (folium.Map, dict, list, dict) - The map object, node positions, neighborhood IDs, and graph
    """
    try:
        # Build node positions from neighborhoods
        node_positions = {}
        for _, row in neighborhoods.iterrows():
            try:
                node_id = str(row['ID']).strip()
                node_positions[node_id] = (float(row['Y-coordinate']), float(row['X-coordinate']))
            except Exception:
                continue
        
        # Add facility positions if needed for routing
        if show_facilities:
            for _, row in facilities.iterrows():
                try:
                    node_id = str(row['ID']).strip()
                    node_positions[node_id] = (float(row['Y-coordinate']), float(row['X-coordinate']))
                except Exception:
                    continue
        
        neighborhood_ids_str = neighborhoods["ID"].astype(str).str.strip().tolist()

        # Create the base map using mean coordinates
        center_y = neighborhoods["Y-coordinate"].mean()
        center_x = neighborhoods["X-coordinate"].mean()
        m = folium.Map(location=[center_y, center_x], zoom_start=12)

        # Add neighborhood markers
        for _, row in neighborhoods.iterrows():
            folium.CircleMarker(
                location=[row["Y-coordinate"], row["X-coordinate"]],
                radius=6,
                color="blue",
                fill=True,
                fill_opacity=0.8,
                popup=f"{row['Name']}<br>Population: {row['Population']}<br>Type: {row['Type']}"
            ).add_to(m)

        # Add facility markers if requested
        if show_facilities:
            for _, row in facilities.iterrows():
                folium.Marker(
                    location=[row["Y-coordinate"], row["X-coordinate"]],
                    icon=folium.Icon(color="red", icon="info-sign"),
                    popup=f"{row['Name']}<br>Type: {row['Type']}"
                ).add_to(m)

        # Filter roads based on scenario and facilities
        filtered_roads = roads.copy()
        if scenario:
            filtered_roads = filtered_roads[~filtered_roads["FromID"].astype(str).str.contains(scenario, case=False)]
            filtered_roads = filtered_roads[~filtered_roads["ToID"].astype(str).str.contains(scenario, case=False)]
        
        if not show_facilities:
            # Filter out roads connected to facilities
            facility_ids = facilities["ID"].astype(str).str.strip().tolist()
            filtered_roads = filtered_roads[
                ~filtered_roads["FromID"].astype(str).str.strip().isin(facility_ids) &
                ~filtered_roads["ToID"].astype(str).str.strip().isin(facility_ids)
            ]

        # Create the graph for algorithms
        graph = nx.Graph()
        
        # Add nodes to graph
        for node_id in node_positions:
            graph.add_node(node_id)
        
        # Add road connections
        for _, row in filtered_roads.iterrows():
            try:
                from_id = str(row["FromID"]).strip()
                to_id = str(row["ToID"]).strip()
                
                if from_id in node_positions and to_id in node_positions:
                    # Add edge to graph with all attributes
                    graph.add_edge(
                        from_id, to_id,
                        name=row["Name"],
                        weight=float(row["Distance(km)"]),
                        capacity=float(row["Current Capacity(vehicles/hour)"]),
                        condition=float(row["Condition(1-10)"])
                    )
                    
                    # Draw road on map
                    folium.PolyLine(
                        [node_positions[from_id], node_positions[to_id]],
                        color="gray",
                        weight=1,
                        opacity=0.4,
                        popup=f"{row['Name']}<br>Distance: {row['Distance(km)']} km<br>Capacity: {row['Current Capacity(vehicles/hour)']} vehicles/hour<br>Condition: {row['Condition(1-10)']} / 10"
                    ).add_to(m)
            except Exception:
                continue

        return m, node_positions, neighborhood_ids_str, graph
        
    except Exception as e:
        raise Exception(f"Error building map: {str(e)}")