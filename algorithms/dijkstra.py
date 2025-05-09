import networkx as nx
from typing import Dict, List, Tuple, Optional
import heapq
import folium
from utils.helpers import load_data, build_map

def dijkstra_shortest_path(
    graph: nx.Graph,
    start: str,
    end: str,
    consider_road_condition: bool = False,
    condition_weight: float = 0.3
) -> Tuple[List[str], float]:
    """
    Basic Dijkstra's algorithm for finding shortest path based on distance.
    
    Args:
        graph: NetworkX graph
        start: Starting node ID
        end: Destination node ID
        consider_road_condition: Whether to factor in road conditions
        condition_weight: Weight factor for road conditions (0-1)
    
    Returns:
        Tuple[List[str], float]: Path and total distance
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
            
            # Calculate weight based on distance and optionally road condition
            weight = edge_data.get('weight', 1.0)  # Base distance
            if consider_road_condition:
                condition = edge_data.get('condition', 10)
                condition_factor = (11 - condition) * condition_weight
                weight *= (1 + condition_factor)
            
            distance = distances[current] + weight
            
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

def run_dijkstra(
    source: str,
    dest: str,
    scenario: Optional[str] = None,
    consider_road_condition: bool = False,
    condition_weight: float = 0.3
) -> Tuple[str, Dict]:
    """
    Run Dijkstra's algorithm and return visualization.
    
    Args:
        source: Starting point ID
        dest: Destination ID
        scenario: Optional scenario (e.g., road closures)
        consider_road_condition: Whether to factor in road conditions
        condition_weight: Weight factor for road conditions
    
    Returns:
        Tuple[str, Dict]: HTML string of map visualization and results dict
    """
    # Load and build the graph
    neighborhoods, roads, facilities = load_data()
    m, node_positions, _, graph = build_map(neighborhoods, roads, facilities, scenario)
    
    # Run the algorithm
    path, total_distance = dijkstra_shortest_path(
        graph, source, dest, consider_road_condition, condition_weight
    )
    
    results = {
        "total_distance": total_distance,
        "path": path,
        "num_segments": len(path) - 1 if path else 0,
        "considered_conditions": consider_road_condition
    }
    
    if path:
        # Draw the path on the map
        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]
            
            # Get edge data for popup information
            edge_data = graph[start_node][end_node]
            distance = edge_data.get('weight', 0)
            condition = edge_data.get('condition', 10) if consider_road_condition else None
            
            # Create detailed popup text
            popup_text = f"""
            <b>{edge_data['name']}</b><br>
            Distance: {distance:.1f} km
            """
            
            if condition:
                popup_text += f"<br>Road Condition: {condition}/10"
            
            folium.PolyLine(
                [node_positions[start_node], node_positions[end_node]],
                color="blue", weight=3,
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
