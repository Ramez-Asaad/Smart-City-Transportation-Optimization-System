import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import networkx as nx
from datetime import datetime, timedelta

class TrafficSimulator:
    def __init__(self, graph: nx.Graph, node_positions: Dict, roads_data: pd.DataFrame):
        """
        Initialize traffic simulator with network data.
        
        Args:
            graph: NetworkX graph of the road network
            node_positions: Dictionary mapping node IDs to coordinates
            roads_data: DataFrame containing road information
        """
        self.graph = graph
        self.node_positions = node_positions
        self.roads_data = roads_data
        self.vehicles = {}  # Will store active vehicles
        self.traffic_state = {}  # Current traffic state for each road
        self.current_time_period = "Morning Rush"  # Default time period
        
        # Initialize traffic states
        self._initialize_traffic_states()
        # Generate initial traffic state
        self.update_traffic_state(self.current_time_period)
        
    def _initialize_traffic_states(self):
        """Initialize traffic states for all roads."""
        for _, row in self.roads_data.iterrows():
            from_id = str(row["FromID"])
            to_id = str(row["ToID"])
            
            if from_id in self.graph and to_id in self.graph:
                # Create unique road ID in both directions
                road_id_forward = f"{from_id}-{to_id}"
                road_id_reverse = f"{to_id}-{from_id}"
                
                # Initialize with base capacity and no current traffic
                base_capacity = float(row["Current Capacity(vehicles/hour)"])
                
                self.traffic_state[road_id_forward] = {
                    "current_load": 0,
                    "capacity": base_capacity,
                    "vehicles": [],
                    "congestion_level": 0.0
                }
                
                self.traffic_state[road_id_reverse] = {
                    "current_load": 0,
                    "capacity": base_capacity,
                    "vehicles": [],
                    "congestion_level": 0.0
                }
    
    def generate_traffic_load(self, time_of_day: str) -> Dict[str, float]:
        """
        Generate traffic load factors based on time of day.
        
        Args:
            time_of_day: String indicating time period
            
        Returns:
            Dictionary mapping road IDs to load factors
        """
        # Define base load factors for different times
        load_factors = {
            "Morning Rush": (0.7, 0.9),
            "Midday": (0.3, 0.6),
            "Evening Rush": (0.8, 1.0),
            "Night": (0.1, 0.3)
        }
        
        min_load, max_load = load_factors.get(time_of_day, (0.3, 0.6))
        
        traffic_loads = {}
        for road_id in self.traffic_state:
            # Generate random load within the time-appropriate range
            base_load = np.random.uniform(min_load, max_load)
            
            # Add some randomness for realism
            noise = np.random.normal(0, 0.1)
            load = max(0, min(1, base_load + noise))
            
            traffic_loads[road_id] = load
            
        return traffic_loads
    
    def update_traffic_state(self, time_of_day: str):
        """
        Update traffic state based on time of day and current conditions.
        
        Args:
            time_of_day: String indicating time period
        """
        self.current_time_period = time_of_day
        traffic_loads = self.generate_traffic_load(time_of_day)
        
        for road_id, load_factor in traffic_loads.items():
            if road_id in self.traffic_state:
                capacity = self.traffic_state[road_id]["capacity"]
                current_load = int(capacity * load_factor)
                
                self.traffic_state[road_id].update({
                    "current_load": current_load,
                    "congestion_level": load_factor
                })
    
    def get_road_speed(self, from_id: str, to_id: str) -> float:
        """
        Calculate current road speed based on congestion.
        
        Args:
            from_id: Starting node ID
            to_id: Ending node ID
            
        Returns:
            float: Current speed factor (0-1)
        """
        road_id = f"{from_id}-{to_id}"
        road_state = self.traffic_state.get(road_id)
        
        if road_state:
            # Speed decreases as congestion increases
            congestion = road_state["congestion_level"]
            return max(0.2, 1 - congestion)  # Minimum 20% of max speed
        
        return 1.0  # Default to max speed if no data
    
    def get_congestion_color(self, congestion_level: float) -> str:
        """Get color for visualization based on congestion level."""
        if congestion_level < 0.3:
            return "green"
        elif congestion_level < 0.6:
            return "yellow"
        elif congestion_level < 0.8:
            return "orange"
        else:
            return "red"
    
    def get_traffic_metrics(self) -> Dict:
        """Get current traffic metrics for the network."""
        metrics = {
            "total_vehicles": sum(state["current_load"] for state in self.traffic_state.values()),
            "avg_congestion": np.mean([state["congestion_level"] for state in self.traffic_state.values()]),
            "congested_roads": sum(1 for state in self.traffic_state.values() if state["congestion_level"] > 0.7),
            "free_flowing_roads": sum(1 for state in self.traffic_state.values() if state["congestion_level"] < 0.3)
        }
        
        return metrics 