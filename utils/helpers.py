import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os

#
@st.cache_data
def load_data():
    """Load and clean the data from CSV files."""
    try:
        # Load the data from CSV files with explicit handling of whitespace
        neighborhoods = pd.read_csv(
            os.path.join("data", "neighborhoods.csv"),
            skipinitialspace=True  # Handle spaces after commas
        )
        roads = pd.read_csv(
            os.path.join("data", "roads.csv"),
            skipinitialspace=True
        )
        facilities = pd.read_csv(
            os.path.join("data", "facilities.csv"),
            skipinitialspace=True
        )
        
        # Clean column names
        for df in [neighborhoods, roads, facilities]:
            # Remove any whitespace from column names
            df.columns = df.columns.str.strip()
            # Clean data in string columns
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()
        
        # Print DataFrame info for debugging
        print("Neighborhoods columns:", neighborhoods.columns.tolist())
        print("Roads columns:", roads.columns.tolist())
        print("Facilities columns:", facilities.columns.tolist())
        
        return neighborhoods, roads, facilities
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise

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
        # Print first few rows of each DataFrame for debugging
        print("\nNeighborhoods head:")
        print(neighborhoods.head())
        print("\nRoads head:")
        print(roads.head())
        print("\nFacilities head:")
        print(facilities.head())
        
        # Build node positions
        node_positions = {}
        for _, row in neighborhoods.iterrows():
            try:
                node_id = str(row['ID']).strip()
                y_coord = float(row['Y-coordinate'])
                x_coord = float(row['X-coordinate'])
                node_positions[node_id] = (y_coord, x_coord)
            except Exception as e:
                print(f"Error processing neighborhood {row['ID']}: {str(e)}")
                print("Row data:", row)
                continue
        
        # Add facility positions
        for _, row in facilities.iterrows():
            try:
                node_id = str(row['ID']).strip()
                y_coord = float(row['Y-coordinate'])
                x_coord = float(row['X-coordinate'])
                node_positions[node_id] = (y_coord, x_coord)
            except Exception as e:
                print(f"Error processing facility {row['ID']}: {str(e)}")
                continue
        
        neighborhood_ids_str = neighborhoods["ID"].astype(str).str.strip().tolist()

        # Create the base map using mean coordinates
        center_y = neighborhoods["Y-coordinate"].mean()
        center_x = neighborhoods["X-coordinate"].mean()
        m = folium.Map(location=[center_y, center_x], zoom_start=12)

        # Add neighborhood markers
        for _, row in neighborhoods.iterrows():
            try:
                folium.CircleMarker(
                    location=[float(row["Y-coordinate"]), float(row["X-coordinate"])],
                    radius=6,
                    color="blue",
                    fill=True,
                    fill_opacity=0.8,
                    popup=f"{row['Name']}<br>Population: {row['Population']}<br>Type: {row['Type']}"
                ).add_to(m)
            except Exception as e:
                print(f"Error adding neighborhood marker: {str(e)}")
                continue

        # Add facility markers if requested
        if show_facilities:
            for _, row in facilities.iterrows():
                try:
                    folium.Marker(
                        location=[float(row["Y-coordinate"]), float(row["X-coordinate"])],
                        icon=folium.Icon(color="red", icon="info-sign"),
                        popup=f"{row['Name']}<br>Type: {row['Type']}"
                    ).add_to(m)
                except Exception as e:
                    print(f"Error adding facility marker: {str(e)}")
                    continue

        # Filter roads based on the scenario
        if scenario:
            roads = roads[~roads["FromID"].astype(str).str.contains(scenario, case=False)]
            roads = roads[~roads["ToID"].astype(str).str.contains(scenario, case=False)]

        # Clean road IDs
        roads["FromID"] = roads["FromID"].astype(str).str.strip()
        roads["ToID"] = roads["ToID"].astype(str).str.strip()

        # Create the graph for algorithms
        graph = nx.Graph()
        
        # Add road connections
        for _, row in roads.iterrows():
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
                    
                    # Create detailed popup text
                    popup_text = f"""
                    <b>{row['Name']}</b><br>
                    Distance: {row['Distance(km)']} km<br>
                    Capacity: {row['Current Capacity(vehicles/hour)']} vehicles/hour<br>
                    Condition: {row['Condition(1-10)']} / 10
                    """
                    
                    # Draw road on map
                    folium.PolyLine(
                        [node_positions[from_id], node_positions[to_id]],
                        color="gray",
                        weight=1,
                        opacity=0.4,
                        popup=popup_text
                    ).add_to(m)
            except Exception as e:
                print(f"Error processing road {from_id} -> {to_id}: {str(e)}")
                continue

        return m, node_positions, neighborhood_ids_str, graph
        
    except Exception as e:
        print(f"Error building map: {str(e)}")
        raise