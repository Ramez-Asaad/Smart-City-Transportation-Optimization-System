import pandas as pd
import heapq
import folium
import math
from utils.helpers import load_data, build_map

def calculate_distance(coord1, coord2):
    """Calculate Euclidean distance between two coordinates."""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)

def heuristic(node_pos, goal_pos):
    """
    Calculate heuristic distance between two nodes using their coordinates.
    Uses Euclidean distance scaled by a factor to ensure admissibility.
    
    Args:
        node_pos: Tuple of (y, x) coordinates for current node
        goal_pos: Tuple of (y, x) coordinates for goal node
        
    Returns:
        float: Estimated distance to goal
    """
    if not node_pos or not goal_pos:
        return 0
    return calculate_distance(node_pos, goal_pos) * 50  # Scale factor based on average speed

def a_star(graph, start, goal, node_positions):
    """
    A* pathfinding algorithm using geographical distances as heuristic.
    
    Args:
        graph: NetworkX graph
        start: Starting node ID
        goal: Goal node ID
        node_positions: Dictionary of node coordinates
        
    Returns:
        Tuple[List[str], float]: Path and total cost, or (None, inf) if no path exists
    """
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(node_positions.get(start), node_positions.get(goal))}
    
    while open_set:
        current_f, current = heapq.heappop(open_set)
        
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path, g_score[goal]
        
        for neighbor in graph.neighbors(current):
            # Get the edge data
            edge_data = graph[current][neighbor]
            # Use distance as the cost
            cost = edge_data['weight']
            
            # Calculate the cost to reach the neighbor node from the start node via the current node
            tentative_g = g_score[current] + cost
            
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(
                    node_positions.get(neighbor),
                    node_positions.get(goal)
                )
                heapq.heappush(open_set, (f_score, neighbor))
    
    return None, float('inf')

def create_emergency_map(neighborhoods, facilities, roads, node_positions, path=None, source=None, hospitals=None):
    """
    Create a map visualization for emergency routing.
    
    Args:
        neighborhoods: DataFrame of neighborhoods
        facilities: DataFrame of facilities
        roads: DataFrame of roads
        node_positions: Dictionary of node coordinates
        path: Optional list of node IDs in the path
        source: Optional source node ID
        hospitals: Optional DataFrame of hospitals
        
    Returns:
        str: HTML string of the map visualization
    """
    # Create base map
    m = folium.Map(
        location=[
            neighborhoods["Y-coordinate"].mean(),
            neighborhoods["X-coordinate"].mean()
        ],
        zoom_start=12
    )
    
    # Add neighborhood markers
    for _, row in neighborhoods.iterrows():
        folium.CircleMarker(
            location=[row["Y-coordinate"], row["X-coordinate"]],
            radius=6,
            color="blue",
            fill=True,
            fill_opacity=0.8,
            popup=f"{row['Name']}<br>Population: {row['Population']}"
        ).add_to(m)

    # Add facility markers (excluding hospitals)
    for _, row in facilities.iterrows():
        if row["Type"].lower() != "medical":
            folium.Marker(
                location=[row["Y-coordinate"], row["X-coordinate"]],
                icon=folium.Icon(color="red", icon="info-sign"),
                popup=f"{row['Name']}<br>Type: {row['Type']}"
            ).add_to(m)

    # Add all roads as background
    for _, row in roads.iterrows():
        from_id = str(row["FromID"])
        to_id = str(row["ToID"])
        if from_id in node_positions and to_id in node_positions:
            folium.PolyLine(
                [node_positions[from_id], node_positions[to_id]],
                color="gray",
                weight=1,
                opacity=0.4,
                popup=row["Name"]
            ).add_to(m)

    # If we have a path, draw it and add markers
    if path and source and hospitals is not None:
        # Draw the emergency path
        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]
            
            # Get road name from the roads DataFrame
            road_info = roads[
                ((roads["FromID"].astype(str) == start_node) & (roads["ToID"].astype(str) == end_node)) |
                ((roads["FromID"].astype(str) == end_node) & (roads["ToID"].astype(str) == start_node))
            ].iloc[0]
            
            # Create detailed popup
            popup_text = f"""
            <b>{road_info['Name']}</b><br>
            Distance: {road_info['Distance(km)']:.1f} km<br>
            Road Condition: {road_info['Condition(1-10)']}/10<br>
            Capacity: {road_info['Current Capacity(vehicles/hour)']} vehicles/hour
            """
            
            folium.PolyLine(
                [node_positions[start_node], node_positions[end_node]],
                color="red",
                weight=4,
                popup=popup_text
            ).add_to(m)

        # Mark start point
        start_name = neighborhoods[neighborhoods["ID"].astype(str) == source]["Name"].iloc[0]
        folium.Marker(
            location=node_positions[source],
            icon=folium.Icon(color="green", icon="flag"),
            popup=f"Start: {start_name}"
        ).add_to(m)

        # Mark all hospitals
        for _, row in hospitals.iterrows():
            hospital_id = str(row["ID"])
            is_target = hospital_id == path[-1]
            
            folium.Marker(
                location=[row["Y-coordinate"], row["X-coordinate"]],
                icon=folium.Icon(
                    color="red" if is_target else "lightgray",
                    icon="plus",
                    prefix='fa'
                ),
                popup=f"{'🏥 Nearest ' if is_target else ''}{row['Name']}"
            ).add_to(m)

    return m._repr_html_()

def find_nearest_hospital(start_id: str, graph, hospitals, node_positions):
    """
    Find the nearest hospital using A* algorithm.
    
    Args:
        start_id: Starting location ID
        graph: NetworkX graph
        hospitals: DataFrame of hospitals
        node_positions: Dictionary of node coordinates
        
    Returns:
        Tuple[List[str], float, str]: Best path, minimum cost, and hospital name
    """
    best_path = None
    min_cost = float('inf')
    best_hospital = None

    # Try to find path to each hospital
    for _, row in hospitals.iterrows():
        hospital_id = str(row["ID"])
        
        # Skip if either node is not in graph
        if hospital_id not in graph or start_id not in graph:
            continue
        
        path, cost = a_star(graph, start_id, hospital_id, node_positions)
        
        if path and cost < min_cost:
            min_cost = cost
            best_path = path
            best_hospital = row["Name"]

    return best_path, min_cost, best_hospital

def run_emergency_routing(source_id):
    """
    Run emergency routing to find nearest hospital.
    
    Args:
        source_id: Starting location ID
        
    Returns:
        Tuple[str, Dict]: HTML string of map visualization and results dictionary
    """
    # Load and build the graph
    neighborhoods, roads, facilities, traffic_lights = load_data()
    m, node_positions, _, graph = build_map(neighborhoods, roads, facilities)
    
    # Filter for hospitals
    hospitals = facilities[facilities["Type"].str.lower() == "medical"]
    
    if hospitals.empty:
        return m._repr_html_(), {"error": "No hospitals found in the data"}
    
    path, cost, hospital = find_nearest_hospital(source_id, graph, hospitals, node_positions)

    if path:
        # Create visualization
        visualization = create_emergency_map(
            neighborhoods, facilities, roads, node_positions,
            path=path, source=source_id, hospitals=hospitals
        )
        
        results = {
            "path": path,
            "cost": cost,
            "hospital": hospital
        }
        
        return visualization, results
    else:
        # Return base map with error
        visualization = create_emergency_map(
            neighborhoods, facilities, roads, node_positions
        )
        return visualization, {"error": "No valid path found to any hospital"}