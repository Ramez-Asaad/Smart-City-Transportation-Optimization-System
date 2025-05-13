import pandas as pd
import folium
import math
import time
import random
from typing import Dict, List, Tuple, Optional
from pathlib import Path

def load_traffic_lights_data():
    """
    Load traffic light data from CSV file.
    
    Returns:
        pd.DataFrame: Traffic light data
    """
    try:
        # Get the absolute path to the data directory
        current_dir = Path(__file__).parent.parent
        data_path = current_dir / "data" / "traffic_lights.csv"

        # Load the data with explicit encoding
        traffic_lights = pd.read_csv(
            data_path,
            skipinitialspace=True,
            encoding='utf-8'
        )
        
        # Clean column names and convert ID columns to string
        traffic_lights.columns = traffic_lights.columns.str.strip()
        id_columns = ['ID', 'FromID', 'ToID', 'IntersectionID']
        for col in id_columns:
            if col in traffic_lights.columns:
                traffic_lights[col] = traffic_lights[col].astype(str).str.strip()
        
        return traffic_lights
    except Exception as e:
        print(f"Error loading traffic lights data: {str(e)}")
        # Return empty DataFrame if file not found
        return pd.DataFrame()

def create_traffic_light_map(node_positions, traffic_lights, roads, current_time=None):
    """
    Add traffic light markers to a map.
    
    Args:
        node_positions: Dictionary of node coordinates
        traffic_lights: DataFrame of traffic light data
        roads: DataFrame of road data
        current_time: Optional current time for determining light state
    
    Returns:
        dict: Dictionary mapping intersection IDs to traffic light states
    """
    # If no time provided, use current system time
    if current_time is None:
        current_time = int(time.time())
    
    intersection_states = {}
    
    # Process each traffic light
    for _, light in traffic_lights.iterrows():
        from_id = light['FromID']
        to_id = light['ToID']
        cycle_time = int(light['CycleTime'])
        green_time = int(light['GreenTime'])
        yellow_time = int(light['YellowTime'])
        
        # Calculate current position in cycle
        cycle_position = current_time % cycle_time
        
        # Determine light state
        if cycle_position < green_time:
            state = "green"
        elif cycle_position < (green_time + yellow_time):
            state = "yellow"
        else:
            state = "red"
        
        # Store intersection state
        intersection_id = light['IntersectionID']
        intersection_states[f"{from_id}-{to_id}"] = {
            "state": state,
            "remaining_time": get_remaining_time(cycle_position, state, green_time, yellow_time, cycle_time)
        }
    
    return intersection_states

def get_remaining_time(cycle_position, state, green_time, yellow_time, cycle_time):
    """
    Calculate remaining time for the current light state.
    
    Args:
        cycle_position: Current position in the cycle (seconds)
        state: Current state ("green", "yellow", "red")
        green_time: Duration of green light (seconds)
        yellow_time: Duration of yellow light (seconds)
        cycle_time: Total cycle time (seconds)
    
    Returns:
        int: Remaining time in current state (seconds)
    """
    if state == "green":
        return green_time - cycle_position
    elif state == "yellow":
        return green_time + yellow_time - cycle_position
    else:  # red
        return cycle_time - cycle_position

def calculate_traffic_light_delay(from_id, to_id, traffic_lights, current_time=None):
    """
    Calculate delay due to traffic light at an intersection.
    
    Args:
        from_id: Starting node ID
        to_id: Ending node ID
        traffic_lights: DataFrame of traffic light data
        current_time: Optional current time
    
    Returns:
        float: Estimated delay in minutes
    """
    if current_time is None:
        current_time = int(time.time())
    
    # Find traffic light for this road segment
    light = traffic_lights[(traffic_lights['FromID'] == from_id) & 
                          (traffic_lights['ToID'] == to_id)]
    
    if light.empty:
        # Check reverse direction (undirected graph)
        light = traffic_lights[(traffic_lights['FromID'] == to_id) & 
                              (traffic_lights['ToID'] == from_id)]
    
    if light.empty:
        # No traffic light at this intersection
        return 0.0
    
    # Get the first matching traffic light
    light = light.iloc[0]
    
    cycle_time = int(light['CycleTime'])
    green_time = int(light['GreenTime'])
    yellow_time = int(light['YellowTime'])
    
    # Calculate current position in cycle
    cycle_position = current_time % cycle_time
    
    # Determine light state
    if cycle_position < green_time:
        # Green light, minimal delay
        return 0.1  # Small delay for slowing down
    elif cycle_position < (green_time + yellow_time):
        # Yellow light, moderate delay
        return 0.5  # Half a minute delay on average
    else:
        # Red light, calculate average wait time
        # On average, you'll wait half the remaining red time
        red_time = cycle_time - green_time - yellow_time
        remaining_red = cycle_time - cycle_position
        return min(remaining_red / 2, red_time / 2) / 60.0  # Convert to minutes
        
def add_traffic_lights_to_map(m, traffic_lights, node_positions, current_time=None):
    """
    Add traffic light visualizations to a folium map.
    
    Args:
        m: Folium map object
        traffic_lights: DataFrame of traffic light data
        node_positions: Dictionary of node coordinates
        current_time: Optional current time
    """
    if current_time is None:
        current_time = int(time.time())
    
    # Group traffic lights by intersection
    intersections = traffic_lights.groupby('IntersectionID')
    
    for intersection_id, group in intersections:
        # Calculate intersection position (average of connected nodes)
        positions = []
        valid_nodes = []
        
        for _, light in group.iterrows():
            from_id = light['FromID']
            to_id = light['ToID']
            
            # Check if both nodes have positions
            if from_id in node_positions and to_id in node_positions:
                positions.append(node_positions[from_id])
                positions.append(node_positions[to_id])
                valid_nodes.append(from_id)
                valid_nodes.append(to_id)
        
        # Only proceed if we have valid positions
        if positions:
            # Calculate average position
            avg_lat = sum(pos[0] for pos in positions) / len(positions)
            avg_lon = sum(pos[1] for pos in positions) / len(positions)
            
            # Calculate midpoint between intersecting roads for more accuracy
            if len(valid_nodes) >= 2:
                # Use the first two valid nodes for midpoint calculation
                mid_lat = (node_positions[valid_nodes[0]][0] + node_positions[valid_nodes[1]][0]) / 2
                mid_lon = (node_positions[valid_nodes[0]][1] + node_positions[valid_nodes[1]][1]) / 2
                
                # Use the midpoint position unless it's too far from the average (which might happen with complex intersections)
                if abs(mid_lat - avg_lat) < 0.01 and abs(mid_lon - avg_lon) < 0.01:
                    avg_lat, avg_lon = mid_lat, mid_lon
            
            # Determine the state of traffic lights at this intersection
            # For visualization, we'll use the state of the first light
            first_light = group.iloc[0]
            cycle_time = int(first_light['CycleTime'])
            green_time = int(first_light['GreenTime'])
            yellow_time = int(first_light['YellowTime'])
            
            cycle_position = current_time % cycle_time
            
            if cycle_position < green_time:
                color = "green"
                icon = "fa-traffic-light"
            elif cycle_position < (green_time + yellow_time):
                color = "orange"
                icon = "fa-traffic-light"
            else:
                color = "red"
                icon = "fa-traffic-light"
            
            # Create popup content
            popup_content = f"""
            <div style="width: 200px;">
                <h4>Traffic Light {intersection_id}</h4>
                <p><strong>Current State:</strong> <span style="color: {color};">{color.upper()}</span></p>
                <p><strong>Cycle Time:</strong> {cycle_time}s</p>
                <p><strong>Green Time:</strong> {green_time}s</p>
                <p><strong>Yellow Time:</strong> {yellow_time}s</p>
                <p><strong>Red Time:</strong> {cycle_time - green_time - yellow_time}s</p>
                <p><strong>Connected Roads:</strong> {', '.join(valid_nodes)}</p>
            </div>
            """
            
            # Add marker with improved Font Awesome icon
            folium.Marker(
                location=[avg_lat, avg_lon],
                icon=folium.DivIcon(
                    html=f'''
                    <div style="
                        font-size: 22px; 
                        color: {color}; 
                        background-color: rgba(255,255,255,0.8);
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid {color};
                        box-shadow: 0 0 5px rgba(0,0,0,0.3);
                    ">
                        <i class="fas fa-traffic-light"></i>
                    </div>
                    ''',
                    icon_size=(40, 40),
                    icon_anchor=(20, 20)
                ),
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)

def get_traffic_light_for_segment(from_id, to_id, traffic_lights):
    """
    Find traffic light for a specific road segment.
    
    Args:
        from_id: Starting node ID
        to_id: Ending node ID
        traffic_lights: DataFrame of traffic light data
    
    Returns:
        pd.DataFrame row or None: Traffic light data if exists
    """
    # Check direct match
    light = traffic_lights[(traffic_lights['FromID'] == from_id) & 
                          (traffic_lights['ToID'] == to_id)]
    
    if not light.empty:
        return light.iloc[0]
    
    # Check reverse direction
    light = traffic_lights[(traffic_lights['FromID'] == to_id) & 
                          (traffic_lights['ToID'] == from_id)]
    
    if not light.empty:
        return light.iloc[0]
    
    # No traffic light found
    return None 