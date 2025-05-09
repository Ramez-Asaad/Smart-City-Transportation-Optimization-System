import networkx as nx
from typing import Dict, List, Tuple, Optional
import heapq
import folium
from utils.helpers import load_data, build_map

def calculate_time_weight(edge_data: Dict, time_of_day: str) -> float:
    """
    Calculate the time-based weight of an edge considering traffic conditions.
    
    Args:
        edge_data: Edge attributes including distance, capacity, and traffic data
        time_of_day: Current time period (e.g., "Morning Rush", "Evening", etc.)
    
    Returns:
        float: Estimated travel time in minutes
    """
    base_speed = 60.0  # km/h
    
    # Get traffic multiplier based on time of day
    traffic_multipliers = {
        "Morning Rush": 0.5,  # Heavy traffic, speed reduced by 50%
        "Evening Rush": 0.4,  # Very heavy traffic, speed reduced by 60%
        "Midday": 0.8,      # Moderate traffic, speed reduced by 20%
        "Night": 1.0        # Light traffic, no reduction
    }
    
    traffic_mult = traffic_multipliers.get(time_of_day, 0.7)  # Default to moderate traffic
    
    # Consider road condition (1-10 scale)
    condition = edge_data.get('condition', 10)
    condition_mult = condition / 10.0
    
    # Consider current capacity vs max capacity
    capacity = edge_data.get('capacity', 1000)
    current_flow = edge_data.get('traffic_flow', capacity * 0.5)  # Default to 50% if no data
    capacity_mult = max(0.3, 1.0 - (current_flow / capacity))
    
    # Calculate actual speed
    actual_speed = base_speed * traffic_mult * condition_mult * capacity_mult
    
    # Convert distance to time (hours), then to minutes
    distance = edge_data.get('weight', 1.0)  # Default to 1km if no distance
    time = (distance / actual_speed) * 60
    
    return time

def time_dijkstra(
    graph: nx.Graph,
    start: str,
    end: str,
    time_of_day: str,
    avoid_congestion: bool = False
) -> Tuple[List[str], float]:
    """
    Modified Dijkstra's algorithm that considers time-based weights.
    
    Args:
        graph: NetworkX graph
        start: Starting node ID
        end: Destination node ID
        time_of_day: Current time period
        avoid_congestion: Whether to heavily penalize congested routes
    
    Returns:
        Tuple[List[str], float]: Path and total time
    """
    distances = {node: float('infinity') for node in graph.nodes()}
    distances[start] = 0
    pq = [(0, start)]
    previous = {node: None for node in graph.nodes()}
    
    while pq:
        current_distance, current = heapq.heappop(pq)
        
        if current == end:
            break
            
        if current_distance > distances[current]:
            continue
            
        for neighbor in graph.neighbors(current):
            edge_data = graph[current][neighbor]
            
            # Calculate time-based weight
            time = calculate_time_weight(edge_data, time_of_day)
            
            # Add congestion penalty if requested
            if avoid_congestion:
                congestion = edge_data.get('congestion_level', 0.5)
                time *= (1 + congestion)
            
            distance = distances[current] + time
            
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current
                heapq.heappush(pq, (distance, neighbor))
    
    # Reconstruct path
    path = []
    current = end
    while current is not None:
        path.append(current)
        current = previous[current]
    path.reverse()
    
    return path, distances[end] if end in distances else float('infinity')

def run_time_dijkstra(
    source: str,
    dest: str,
    time_of_day: str,
    scenario: Optional[str] = None,
    avoid_congestion: bool = False
) -> Tuple[str, Dict]:
    """
    Run the time-aware Dijkstra algorithm and return visualization.
    
    Args:
        source: Starting point ID
        dest: Destination ID
        time_of_day: Time period
        scenario: Optional scenario (e.g., road closures)
        avoid_congestion: Whether to avoid congested routes
    
    Returns:
        Tuple[str, Dict]: HTML string of map visualization and results dict
    """
    # Load and build the graph
    neighborhoods, roads, facilities = load_data()
    m, node_positions, _, graph = build_map(neighborhoods, roads, facilities, scenario)
    
    # Run the algorithm
    path, total_time = time_dijkstra(graph, source, dest, time_of_day, avoid_congestion)
    
    results = {
        "total_time": total_time,
        "path": path,
        "num_segments": len(path) - 1 if path else 0
    }
    
    if path:
        # Draw the path on the map
        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]
            
            # Get edge data for popup information
            edge_data = graph[start_node][end_node]
            time = calculate_time_weight(edge_data, time_of_day)
            
            # Create detailed popup text
            popup_text = f"""
            <b>{edge_data['name']}</b><br>
            Estimated Time: {time:.1f} min<br>
            Distance: {edge_data['weight']:.1f} km<br>
            Traffic Level: {time_of_day}
            """
            
            folium.PolyLine(
                [node_positions[start_node], node_positions[end_node]],
                color="red", weight=3,
                popup=popup_text
            ).add_to(m)
        
        # Mark start and end points
        folium.Marker(
            location=node_positions[source],
            icon=folium.Icon(color="green", icon="flag"),
            popup=f"Start: {source}"
        ).add_to(m)
        
        folium.Marker(
            location=node_positions[dest],
            icon=folium.Icon(color="red", icon="flag"),
            popup=f"Destination: {dest}"
        ).add_to(m)
    
    return m._repr_html_(), results 