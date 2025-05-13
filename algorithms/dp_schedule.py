import pandas as pd
import networkx as nx
import folium
from utils.helpers import load_data, build_map, load_transit_data, simple_shortest_path_length
from typing import Dict, List, Tuple, Any
from collections import defaultdict

class PublicTransitOptimizer:
    """
    Optimizes public transit schedules using dynamic programming.
    Handles bus routes, metro lines, and transfer points.
    """
    def __init__(self, bus_routes: pd.DataFrame = None, metro_lines: pd.DataFrame = None, demand_data: Dict = None):
        """
        Initialize the optimizer with transit data.
        
        Args:
            bus_routes: DataFrame containing bus route information
            metro_lines: DataFrame containing metro line information
            demand_data: Dictionary mapping (from_id, to_id) to daily passenger count
        """
        # Load base network data
        self.neighborhoods, self.roads, self.facilities = load_data()
        self.base_map, self.node_positions, _, self.base_graph = build_map(
            self.neighborhoods, self.roads, self.facilities
        )
        
        # Create set of valid nodes from neighborhoods and facilities
        self.valid_nodes = set(str(row["ID"]).strip() for _, row in self.neighborhoods.iterrows())
        self.valid_nodes.update(str(row["ID"]).strip() for _, row in self.facilities.iterrows())
        
        # Load transit data if not provided
        if bus_routes is None or metro_lines is None or demand_data is None:
            try:
                self.bus_routes, self.metro_lines, self.demand_data, self.transfer_points = load_transit_data(self.valid_nodes)
            except Exception as e:
                raise Exception(f"Failed to load transit data: {str(e)}")
        else:
            # Store provided transit data
            self.bus_routes = self._validate_routes(bus_routes, "bus")
            self.metro_lines = self._validate_routes(metro_lines, "metro")
            self.demand_data = {
                (str(k[0]).strip(), str(k[1]).strip()): int(v)
                for k, v in demand_data.items()
            }
            self.transfer_points = set()
            self._identify_transfer_points()
        
        # Initialize the network graph
        self.network = nx.MultiGraph()
        
    def _validate_routes(self, routes: pd.DataFrame, route_type: str) -> pd.DataFrame:
        """
        Validate and clean route data.
        
        Args:
            routes: DataFrame containing route information
            route_type: Type of route ('bus' or 'metro')
            
        Returns:
            DataFrame containing validated routes
        """
        valid_routes = []
        for _, route in routes.iterrows():
            try:
                # Get stops/stations and clean IDs
                stops_col = 'Stations' if route_type == 'metro' else 'Stops'
                stops = [str(s).strip() for s in str(route[stops_col]).split(',')]
                
                # Filter valid stops
                valid_stops = [stop for stop in stops if stop in self.valid_nodes]
                
                if len(valid_stops) >= 2:  # Only keep routes with at least 2 valid stops
                    route_dict = route.to_dict()
                    route_dict[stops_col] = ','.join(valid_stops)
                    # Clean string values
                    for key in route_dict:
                        if isinstance(route_dict[key], str):
                            route_dict[key] = route_dict[key].strip()
                    valid_routes.append(route_dict)
            except Exception:
                continue
                
        return pd.DataFrame(valid_routes)
        
    def _identify_transfer_points(self):
        """Find intersections between bus and metro networks."""
        bus_stops = set()
        metro_stations = set()
        
        # Collect bus stops
        for _, route in self.bus_routes.iterrows():
            stops = [str(s.strip()) for s in route['Stops'].split(',')]
            bus_stops.update(stop for stop in stops if stop in self.valid_nodes)
        
        # Collect metro stations
        for _, line in self.metro_lines.iterrows():
            stations = [str(s.strip()) for s in line['Stations'].split(',')]
            metro_stations.update(station for station in stations if station in self.valid_nodes)
        
        # Find intersections
        self.transfer_points = bus_stops.intersection(metro_stations)
    
    def build_integrated_network(self):
        """Build a multimodal transportation network."""
        # Start with the base road network, ensuring string IDs
        self.network = nx.Graph()
        
        # Add base graph edges
        for u, v, data in self.base_graph.edges(data=True):
            self.network.add_edge(str(u), str(v), **data)
        
        # Add bus routes
        for _, route in self.bus_routes.iterrows():
            stops = [str(s.strip()) for s in route['Stops'].split(',')]
            
            for i in range(len(stops)-1):
                # Skip if either stop is not in valid nodes
                if stops[i] not in self.valid_nodes or stops[i+1] not in self.valid_nodes:
                    continue
                
                # Get coordinates for visualization
                start_pos = self.node_positions.get(stops[i])
                end_pos = self.node_positions.get(stops[i+1])
                
                if start_pos and end_pos:
                    try:
                        # Calculate distance using existing road network if possible
                        distance = simple_shortest_path_length(self.base_graph, stops[i], stops[i+1], weight='weight')
                    
                    except Exception:
                        # If no road path exists, use direct distance
                        distance = ((start_pos[0] - end_pos[0])**2 + 
                                  (start_pos[1] - end_pos[1])**2)**0.5
                    
                    self.network.add_edge(
                        stops[i],
                        stops[i+1],
                        type='bus',
                        route=route['RouteID'],
                        weight=distance,
                        capacity=route['DailyPassengers']
                    )
        
        # Add metro lines
        for _, line in self.metro_lines.iterrows():
            stations = [str(s.strip()) for s in line['Stations'].split(',')]
            
            for i in range(len(stations)-1):
                # Skip if either station is not in valid nodes
                if stations[i] not in self.valid_nodes or stations[i+1] not in self.valid_nodes:
                    continue
                
                # Get coordinates for visualization
                start_pos = self.node_positions.get(stations[i])
                end_pos = self.node_positions.get(stations[i+1])
                
                if start_pos and end_pos:
                    # Calculate direct distance for metro (doesn't follow roads)
                    distance = ((start_pos[0] - end_pos[0])**2 + 
                              (start_pos[1] - end_pos[1])**2)**0.5
                    
                    self.network.add_edge(
                        stations[i],
                        stations[i+1],
                        type='metro',
                        route=line['LineID'],
                        weight=distance,
                        capacity=line['DailyPassengers']
                    )
    
    def optimize_transfer_points(self) -> List[Tuple[str, float]]:
        """
        Optimize transfer points based on demand and connectivity.
        
        Returns:
            List of tuples (point_id, score) sorted by score in descending order
        """
        transfer_scores = []
        
        for point in self.transfer_points:
            # Calculate connectivity score
            degree = self.network.degree(point)
            
            # Calculate demand score
            demand_in = sum(self.demand_data.get((src, point), 0) 
                          for src in self.network.nodes())
            demand_out = sum(self.demand_data.get((point, dest), 0) 
                           for dest in self.network.nodes())
            
            # Calculate transfer efficiency
            transfer_efficiency = 0
            neighbors = list(self.network.neighbors(point))
            for i in range(len(neighbors)):
                for j in range(i+1, len(neighbors)):
                    if (self.network[point][neighbors[i]].get('type') != 
                        self.network[point][neighbors[j]].get('type')):
                        transfer_efficiency += 1
            
            # Calculate final score
            score = (0.4 * degree + 
                    0.3 * (demand_in + demand_out)/1000 + 
                    0.3 * transfer_efficiency)
            
            transfer_scores.append((point, score))
        
        return sorted(transfer_scores, key=lambda x: x[1], reverse=True)
    
    def _dp_allocate(
        self,
        values: List[Tuple[str, float]],
        max_units: int,
        min_units: int,
        max_per_route: int
    ) -> Dict[str, int]:
        """Optimize resource allocation using dynamic programming."""
        n = len(values)
        dp = [[0] * (max_units + 1) for _ in range(n + 1)]
        allocation = {}

        # Build DP table
        for i in range(1, n + 1):
            route_id, value = values[i-1]
            for u in range(max_units + 1):
                max_possible = min(u, max_per_route)
                for alloc in range(min_units, max_possible + 1):
                    # Apply diminishing returns
                    current_value = value * min(alloc, 10)
                    if dp[i-1][u-alloc] + current_value > dp[i][u]:
                        dp[i][u] = dp[i-1][u-alloc] + current_value

        # Backtrack to find allocation
        remaining = max_units
        for i in range(n, 0, -1):
            route_id, value = values[i-1]
            for alloc in range(min(remaining, max_per_route), min_units-1, -1):
                if dp[i][remaining] == dp[i-1][remaining-alloc] + value * min(alloc, 10):
                    allocation[route_id] = alloc
                    remaining -= alloc
                    break
            else:
                allocation[route_id] = min_units
                remaining -= min_units

        return allocation
    
    def optimize_resource_allocation(
        self,
        total_buses: int = 200,
        total_trains: int = 30
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Optimize allocation of buses and trains."""
        # Calculate route values
        bus_values = []
        for _, route in self.bus_routes.iterrows():
            stops = [s.strip() for s in route['Stops'].split(',')]
            
            # Base value from existing passengers
            value = route['DailyPassengers']
            
            # Add value from demand matrix
            for i in range(len(stops)):
                for j in range(i+1, len(stops)):
                    value += self.demand_data.get((stops[i], stops[j]), 0) // 2
            
            # Add transfer point bonus
            transfer_bonus = sum(10000 for stop in stops 
                               if stop in self.transfer_points)
            value += transfer_bonus
            
            bus_values.append((route['RouteID'], value))
        
        # Calculate metro values
        metro_values = []
        for _, line in self.metro_lines.iterrows():
            stations = [s.strip() for s in line['Stations'].split(',')]
            
            # Base value from existing passengers
            value = line['DailyPassengers']
            
            # Add value from demand matrix
            for i in range(len(stations)):
                for j in range(i+1, len(stations)):
                    value += self.demand_data.get((stations[i], stations[j]), 0) // 2
            
            # Add transfer point bonus
            transfer_bonus = sum(10000 for station in stations 
                               if station in self.transfer_points)
            value += transfer_bonus
            
            metro_values.append((line['LineID'], value))
        
        # Optimize allocations
        bus_allocation = self._dp_allocate(
            values=bus_values,
            max_units=total_buses,
            min_units=5,  # Minimum buses per route
            max_per_route=25  # Maximum buses per route
        )
        
        metro_allocation = self._dp_allocate(
            values=metro_values,
            max_units=total_trains,
            min_units=2,  # Minimum trains per line
            max_per_route=10  # Maximum trains per line
        )
        
        return bus_allocation, metro_allocation
    
    def generate_schedules(
        self,
        bus_allocation: Dict[str, int],
        metro_allocation: Dict[str, int]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Generate optimized schedules with transfer information."""
        bus_schedules = []
        metro_schedules = []
        
        # Generate bus schedules
        for _, route in self.bus_routes.iterrows():
            route_id = route['RouteID']
            assigned = bus_allocation.get(route_id, 5)
            stops = [s.strip() for s in route['Stops'].split(',')]
            
            # Find transfer points on this route
            transfers = [stop for stop in stops if stop in self.transfer_points]
            
            bus_schedules.append({
                'Route': route_id,
                'Stops': stops,
                'Assigned Vehicles': assigned,
                'Interval (min)': max(5, 1080 // assigned),  # 18 operating hours
                'Transfer Points': transfers,
                'Daily Capacity': assigned * 50 * 20  # 50 passengers, 20 trips
            })
        
        # Generate metro schedules
        for _, line in self.metro_lines.iterrows():
            line_id = line['LineID']
            assigned = metro_allocation.get(line_id, 2)
            stations = [s.strip() for s in line['Stations'].split(',')]
            
            # Find transfer points on this line
            transfers = [station for station in stations 
                        if station in self.transfer_points]
            
            metro_schedules.append({
                'Line': line_id,
                'Stations': stations,
                'Assigned Trains': assigned,
                'Interval (min)': max(3, 1080 // assigned),  # 18 operating hours
                'Transfer Points': transfers,
                'Daily Capacity': assigned * 500 * 20  # 500 passengers, 20 trips
            })
        
        return bus_schedules, metro_schedules
    
    def create_visualization(self) -> str:
        """Create an interactive map visualization."""
        # Create base map
        m = folium.Map(
            location=[30.0444, 31.2357],  # Cairo coordinates
            zoom_start=12
        )
        
        # Add bus routes
        for _, route in self.bus_routes.iterrows():
            stops = [s.strip() for s in route['Stops'].split(',')]
            for i in range(len(stops)-1):
                if (stops[i] in self.node_positions and 
                    stops[i+1] in self.node_positions):
                    # Draw route line
                    folium.PolyLine(
                        locations=[
                            self.node_positions[stops[i]],
                            self.node_positions[stops[i+1]]
                        ],
                        color='blue',
                        weight=2,
                        opacity=0.7,
                        popup=f"Bus Route {route['RouteID']}"
                    ).add_to(m)
        
        # Add metro lines
        for _, line in self.metro_lines.iterrows():
            stations = [s.strip() for s in line['Stations'].split(',')]
            for i in range(len(stations)-1):
                if (stations[i] in self.node_positions and 
                    stations[i+1] in self.node_positions):
                    # Draw metro line
                    folium.PolyLine(
                        locations=[
                            self.node_positions[stations[i]],
                            self.node_positions[stations[i+1]]
                        ],
                        color='red',
                        weight=4,
                        opacity=0.9,
                        popup=f"Metro Line {line['LineID']}"
                    ).add_to(m)
        
        # Add transfer points
        for point in self.transfer_points:
            if point in self.node_positions:
                folium.CircleMarker(
                    location=self.node_positions[point],
                    radius=5,
                    color='green',
                    fill=True,
                    fill_color='green',
                    popup=f"Transfer Point: {point}"
                ).add_to(m)
        
        return m._repr_html_()