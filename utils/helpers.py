import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os
from pathlib import Path
from typing import Dict, Tuple, Set

@st.cache_data
def load_data():
    """Load and clean the data from CSV files."""
    try:
        # Get the absolute path to the data directory
        current_dir = Path(__file__).parent.parent
        data_dir = current_dir / "data"

        # Verify data files exist
        required_files = ["neighborhoods.csv", "roads.csv", "facilities.csv"]
        for file in required_files:
            if not (data_dir / file).exists():
                raise FileNotFoundError(f"Required data file not found: {file}")

        # Load the data from CSV files with explicit handling of whitespace
        neighborhoods = pd.read_csv(
            data_dir / "neighborhoods.csv",
            skipinitialspace=True
        )
        roads = pd.read_csv(
            data_dir / "roads.csv",
            skipinitialspace=True
        )
        facilities = pd.read_csv(
            data_dir / "facilities.csv",
            skipinitialspace=True
        )
        
        # Clean column names and data
        for df in [neighborhoods, roads, facilities]:
            df.columns = df.columns.str.strip()
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()
        
        return neighborhoods, roads, facilities
    except FileNotFoundError as e:
        st.error(f"Data file not found: {str(e)}")
        raise
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        raise

@st.cache_data
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
            if not (data_dir / file).exists():
                raise FileNotFoundError(f"Transit data file not found: {file}")

        # Load and clean bus routes
        bus_routes = pd.read_csv(data_dir / "bus_routes.csv", skipinitialspace=True)
        bus_routes.columns = bus_routes.columns.str.strip()

        # Load and clean metro lines
        metro_lines = pd.read_csv(data_dir / "metro_lines.csv", skipinitialspace=True)
        metro_lines.columns = metro_lines.columns.str.strip()

        # Load and clean demand data
        demand_data = pd.read_csv(data_dir / "demand_data.csv", skipinitialspace=True)
        demand_data.columns = demand_data.columns.str.strip()

        # Convert demand data to dictionary
        demand_dict = {
            (str(row['FromID']).strip(), str(row['ToID']).strip()): row['DailyPassengers']
            for _, row in demand_data.iterrows()
        }

        # Validate and collect stops/stations
        bus_stops = set()
        metro_stations = set()

        # Process bus routes
        valid_bus_routes = []
        for _, route in bus_routes.iterrows():
            stops = [str(s).strip() for s in route['Stops'].split(',')]
            if valid_nodes:
                stops = [stop for stop in stops if stop in valid_nodes]
            if len(stops) >= 2:  # Only keep routes with at least 2 valid stops
                route_copy = route.copy()
                route_copy['Stops'] = ','.join(stops)
                valid_bus_routes.append(route_copy)
                bus_stops.update(stops)

        # Process metro lines
        valid_metro_lines = []
        for _, line in metro_lines.iterrows():
            stations = [str(s).strip() for s in line['Stations'].split(',')]
            if valid_nodes:
                stations = [station for station in stations if station in valid_nodes]
            if len(stations) >= 2:  # Only keep lines with at least 2 valid stations
                line_copy = line.copy()
                line_copy['Stations'] = ','.join(stations)
                valid_metro_lines.append(line_copy)
                metro_stations.update(stations)

        # Create DataFrames from valid routes
        validated_bus_routes = pd.DataFrame(valid_bus_routes)
        validated_metro_lines = pd.DataFrame(valid_metro_lines)

        # Find transfer points (intersections between bus and metro)
        transfer_points = bus_stops.intersection(metro_stations)

        if validated_bus_routes.empty:
            st.warning("No valid bus routes found after validation.")
        if validated_metro_lines.empty:
            st.warning("No valid metro lines found after validation.")

        return validated_bus_routes, validated_metro_lines, demand_dict, transfer_points

    except FileNotFoundError as e:
        st.error(f"Transit data file not found: {str(e)}")
        raise
    except Exception as e:
        st.error(f"Error loading transit data: {str(e)}")
        raise

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