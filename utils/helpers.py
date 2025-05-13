import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os
from pathlib import Path
from typing import Dict, Tuple, Set

def load_data():
    """
    Load and clean the data from CSV files.
    
    Returns:
        Tuple containing:
        - neighborhoods: DataFrame of neighborhood data
        - roads: DataFrame of road network data
        - facilities: DataFrame of facility locations
    """
    try:
        # Get the absolute path to the data directory
        current_dir = Path(__file__).parent.parent
        data_dir = current_dir / "data"

        # Verify data files exist
        required_files = ["neighborhoods.csv", "roads.csv", "facilities.csv"]
        for file in required_files:
            if not (data_dir / file).exists():
                raise FileNotFoundError(f"Required data file not found: {file}")

        # Load the data from CSV files with explicit encoding
        neighborhoods = pd.read_csv(
            data_dir / "neighborhoods.csv",
            skipinitialspace=True,
            encoding='utf-8'
        )
        roads = pd.read_csv(
            data_dir / "roads.csv",
            skipinitialspace=True,
            encoding='utf-8'
        )
        facilities = pd.read_csv(
            data_dir / "facilities.csv",
            skipinitialspace=True,
            encoding='utf-8'
        )
        
        # Clean column names and data
        for df in [neighborhoods, roads, facilities]:
            df.columns = df.columns.str.strip()
            # Convert ID columns to string and strip whitespace
            id_columns = ['ID', 'FromID', 'ToID']
            for col in id_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            # Clean other string columns
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()
        
        return neighborhoods, roads, facilities
    except Exception as e:
        raise Exception(f"Error loading data: {str(e)}")

def load_transit_data(valid_nodes: Set[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[Tuple[str, str], int], Set[str]]:
    """
    Load and validate transit data including bus routes, metro lines, and demand data.
    
    Args:
        valid_nodes: Set of valid node IDs to validate against
    
    Returns:
        Tuple containing:
        - bus_routes: DataFrame of validated bus routes
        - metro_lines: DataFrame of validated metro lines
        - demand_data: Dictionary of demand between node pairs
        - transfer_points: Set of transfer points (intersections between bus and metro)
    """
    try:
        # Get the absolute path to the data directory
        current_dir = Path(__file__).parent.parent
        data_dir = current_dir / "data"

        # Load transit data files
        transit_files = ["bus_routes.csv", "metro_lines.csv", "demand_data.csv"]
        for file in transit_files:
            file_path = data_dir / file
            if not file_path.exists():
                raise FileNotFoundError(f"Transit data file not found: {file_path}")

        # Load and clean data with explicit encoding
        bus_routes = pd.read_csv(data_dir / "bus_routes.csv", skipinitialspace=True, encoding='utf-8')
        bus_routes.columns = bus_routes.columns.str.strip()

        metro_lines = pd.read_csv(data_dir / "metro_lines.csv", skipinitialspace=True, encoding='utf-8')
        metro_lines.columns = metro_lines.columns.str.strip()

        demand_data = pd.read_csv(data_dir / "demand_data.csv", skipinitialspace=True, encoding='utf-8')
        demand_data.columns = demand_data.columns.str.strip()

        # Load neighborhoods for name-to-ID mapping
        neighborhoods = pd.read_csv(data_dir / "neighborhoods.csv", skipinitialspace=True, encoding='utf-8')
        name_to_id = {
            str(row['Name']).strip(): str(row['ID']).strip()
            for _, row in neighborhoods.iterrows()
        }

        # Convert demand data to dictionary with consistent string IDs
        demand_dict = {}
        for _, row in demand_data.iterrows():
            from_id = str(row['FromID']).strip()
            to_id = str(row['ToID']).strip()
            
            # Convert neighborhood names to IDs if needed
            if from_id in name_to_id:
                from_id = name_to_id[from_id]
            if to_id in name_to_id:
                to_id = name_to_id[to_id]
                
            # Only add if both IDs are valid
            if valid_nodes is None or (from_id in valid_nodes and to_id in valid_nodes):
                demand_dict[(from_id, to_id)] = int(row['DailyPassengers'])

        # Process bus routes
        valid_bus_routes = []
        bus_stops = set()
        for _, route in bus_routes.iterrows():
            try:
                stops = [str(s).strip() for s in str(route['Stops']).split(',')]
                
                # Filter valid stops
                if valid_nodes:
                    stops = [stop for stop in stops if stop in valid_nodes]
                    
                if len(stops) >= 2:  # Only keep routes with at least 2 valid stops
                    route_dict = route.to_dict()
                    route_dict['Stops'] = ','.join(stops)
                    # Clean string values
                    for key in route_dict:
                        if isinstance(route_dict[key], str):
                            route_dict[key] = route_dict[key].strip()
                    valid_bus_routes.append(route_dict)
                    bus_stops.update(stops)
            except Exception:
                continue

        # Process metro lines
        valid_metro_lines = []
        metro_stations = set()
        for _, line in metro_lines.iterrows():
            try:
                stations = [str(s).strip() for s in str(line['Stations']).split(',')]
                
                # Filter valid stations
                if valid_nodes:
                    stations = [station for station in stations if station in valid_nodes]
                    
                if len(stations) >= 2:  # Only keep lines with at least 2 valid stations
                    line_dict = line.to_dict()
                    line_dict['Stations'] = ','.join(stations)
                    # Clean string values
                    for key in line_dict:
                        if isinstance(line_dict[key], str):
                            line_dict[key] = line_dict[key].strip()
                    valid_metro_lines.append(line_dict)
                    metro_stations.update(stations)
            except Exception:
                continue

        # Create DataFrames from valid routes
        validated_bus_routes = pd.DataFrame(valid_bus_routes)
        validated_metro_lines = pd.DataFrame(valid_metro_lines)

        # Find transfer points (intersections between bus and metro)
        transfer_points = bus_stops.intersection(metro_stations)

        if validated_bus_routes.empty or validated_metro_lines.empty:
            raise ValueError("No valid transit routes found after validation")

        return validated_bus_routes, validated_metro_lines, demand_dict, transfer_points

    except Exception as e:
        raise Exception(f"Error loading transit data: {str(e)}")

def calculate_distance(pos1, pos2):
    """Calculate Euclidean distance between two coordinates."""
    return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5

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
        
        # Convert neighborhood IDs to strings and strip whitespace
        neighborhood_ids_str = [str(id).strip() for id in neighborhoods["ID"].tolist()]

        # Create the base map using mean coordinates
        center_y = neighborhoods["Y-coordinate"].mean()
        center_x = neighborhoods["X-coordinate"].mean()
        m = folium.Map(location=[center_y, center_x], zoom_start=12)
        
        # Initialize graph
        graph = nx.Graph()
        
        # Add nodes to graph
        for node_id in node_positions:
            graph.add_node(node_id)
            
        # Filter roads based on scenario if provided
        filtered_roads = roads
        if scenario:
            # Add scenario-specific road filtering here
            pass
            
        # Add road connections with validation
        for _, row in filtered_roads.iterrows():
            try:
                from_id = str(row["FromID"]).strip()
                to_id = str(row["ToID"]).strip()
                
                if from_id in node_positions and to_id in node_positions:
                    # Add edge to graph with all attributes
                    graph.add_edge(
                        from_id, to_id,
                        name=str(row["Name"]).strip(),
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

        # Add markers for neighborhoods
        for _, row in neighborhoods.iterrows():
            try:
                node_id = str(row['ID']).strip()
                if node_id in node_positions:
                    folium.CircleMarker(
                        location=node_positions[node_id],
                        radius=8,
                        color='blue',
                        fill=True,
                        popup=f"{row['Name']}<br>Population: {row['Population']}"
                    ).add_to(m)
            except Exception:
                continue

        # Add markers for facilities if requested
        if show_facilities:
            for _, row in facilities.iterrows():
                try:
                    node_id = str(row['ID']).strip()
                    if node_id in node_positions:
                        folium.CircleMarker(
                            location=node_positions[node_id],
                            radius=6,
                            color='red',
                            fill=True,
                            popup=f"{row['Name']}<br>Type: {row['Type']}"
                        ).add_to(m)
                except Exception:
                    continue

        return m, node_positions, neighborhood_ids_str, graph
        
    except Exception as e:
        raise Exception(f"Error building map: {str(e)}")
    
def simple_shortest_path_length(graph, start, end, weight='weight'):
    import heapq
    distances = {node: float('inf') for node in graph.nodes()}
    distances[start] = 0
    pq = [(0, start)]
    while pq:
        dist, node = heapq.heappop(pq)
        if node == end:
            return dist
        if dist > distances[node]:
            continue
        for neighbor in graph.neighbors(node):
            edge_weight = graph[node][neighbor].get(weight, 1)
            new_dist = dist + edge_weight
            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                heapq.heappush(pq, (new_dist, neighbor))
    return float('inf')