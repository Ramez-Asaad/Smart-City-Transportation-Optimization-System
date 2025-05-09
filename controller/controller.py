from typing import Dict, Any, Optional, List
import streamlit as st
import folium
import pandas as pd
import numpy as np
from algorithms.mst import run_mst
from algorithms.time_dijkstra import run_time_dijkstra, calculate_time_weight
from algorithms.a_star import find_nearest_hospital, run_emergency_routing
from utils.helpers import load_data, build_map, load_transit_data
from collections import defaultdict
from algorithms.dp_schedule import PublicTransitOptimizer
import networkx as nx
import os
from pathlib import Path

class TransportationController:
    """
    Main controller class for the Smart City Transportation System.
    Handles data loading, route planning, and network management.
    """
    def __init__(self):
        """Initialize the controller with data and graph structures."""
        # Load base network data
        self.neighborhoods, self.roads, self.facilities = load_data()
        self.base_map, self.node_positions, self.neighborhood_ids, self.graph = build_map(
            self.neighborhoods, self.roads, self.facilities
        )
        
        # Create lookup dictionaries for efficient name resolution
        self.neighborhood_names = {
            str(row["ID"]): row["Name"]
            for _, row in self.neighborhoods.iterrows()
        }
        self.facility_names = {
            str(row["ID"]): row["Name"]
            for _, row in self.facilities.iterrows()
        }
        self.road_names = {
            (str(row["FromID"]), str(row["ToID"])): row["Name"]
            for _, row in self.roads.iterrows()
        }

        # Create set of valid nodes for validation
        self.valid_nodes = set(str(row["ID"]) for _, row in self.neighborhoods.iterrows())
        self.valid_nodes.update(str(row["ID"]) for _, row in self.facilities.iterrows())

        # Load public transit data
        try:
            self.bus_routes, self.metro_lines, self.demand_data, self.transfer_points = load_transit_data(self.valid_nodes)
        except Exception as e:
            self.bus_routes = pd.DataFrame()
            self.metro_lines = pd.DataFrame()
            self.demand_data = {}
            self.transfer_points = set()
        
    def get_location_name(self, location_id: str) -> str:
        """Get the name of a location (neighborhood or facility) from its ID."""
        if location_id in self.neighborhood_names:
            return self.neighborhood_names[location_id]
        elif location_id in self.facility_names:
            return self.facility_names[location_id]
        return location_id
    
    def get_road_name(self, from_id: str, to_id: str) -> str:
        """Get the name of a road from its endpoint IDs."""
        # Try both directions as roads are undirected
        if (from_id, to_id) in self.road_names:
            return self.road_names[(from_id, to_id)]
        elif (to_id, from_id) in self.road_names:
            return self.road_names[(to_id, from_id)]
        return f"{from_id} → {to_id}"

    def analyze_path(self, path: list, time_of_day: str) -> Dict[str, Any]:
        """Analyze a path and return detailed metrics."""
        if not path or len(path) < 2:
            return {}

        analysis = {
            "total_distance": 0,
            "total_time": 0,
            "avg_condition": 0,
            "road_segments": [],
            "time_comparisons": {},
            "bottlenecks": []
        }

        # Analyze each segment
        conditions = []
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            edge_data = self.graph[from_id][to_id]
            road_name = self.get_road_name(from_id, to_id)

            # Basic metrics
            distance = edge_data["weight"]
            condition = edge_data["condition"]
            capacity = edge_data["capacity"]
            
            # Calculate times for different periods
            times = {
                "Morning Rush": calculate_time_weight(edge_data, "Morning Rush"),
                "Midday": calculate_time_weight(edge_data, "Midday"),
                "Evening Rush": calculate_time_weight(edge_data, "Evening Rush"),
                "Night": calculate_time_weight(edge_data, "Night")
            }
            
            current_time = times[time_of_day]

            # Segment analysis
            segment = {
                "road_name": road_name,
                "distance": distance,
                "condition": condition,
                "capacity": capacity,
                "current_time": current_time,
                "times": times
            }
            
            # Update totals
            analysis["total_distance"] += distance
            analysis["total_time"] += current_time
            conditions.append(condition)
            
            # Check for bottlenecks (high time difference or poor condition)
            is_bottleneck = False
            time_variance = max(times.values()) - min(times.values())
            if time_variance > 10 or condition < 6:  # More than 10 min variance or poor condition
                is_bottleneck = True
                analysis["bottlenecks"].append({
                    "road": road_name,
                    "reason": "High traffic variance" if time_variance > 10 else "Poor condition",
                    "condition": condition,
                    "time_variance": time_variance
                })

            segment["is_bottleneck"] = is_bottleneck
            analysis["road_segments"].append(segment)

        # Calculate averages and overall metrics
        analysis["avg_condition"] = sum(conditions) / len(conditions)
        
        # Calculate time comparisons
        total_times = {
            period: sum(seg["times"][period] for seg in analysis["road_segments"])
            for period in ["Morning Rush", "Midday", "Evening Rush", "Night"]
        }
        analysis["time_comparisons"] = total_times
        
        # Calculate best time to travel
        best_time = min(total_times.items(), key=lambda x: x[1])
        worst_time = max(total_times.items(), key=lambda x: x[1])
        analysis["best_time"] = {
            "period": best_time[0],
            "duration": best_time[1],
            "saving": worst_time[1] - best_time[1]
        }

        return analysis
        
    def run_dp_scheduling(self, total_buses: int = 200, total_trains: int = 30) -> Dict[str, Any]:
        """Run the DP scheduling optimization and return results."""
        try:
            # Verify transit data is available
            if self.bus_routes.empty or self.metro_lines.empty:
                raise ValueError("Transit data not available")
            
            # Create optimizer with valid nodes
            optimizer = PublicTransitOptimizer()
            optimizer.valid_nodes = self.valid_nodes
            optimizer.bus_routes = optimizer._validate_routes(self.bus_routes, "bus")
            optimizer.metro_lines = optimizer._validate_routes(self.metro_lines, "metro")
            optimizer.demand_data = self.demand_data
            optimizer._identify_transfer_points()
            
            # Build network and run optimization
            optimizer.build_integrated_network()
            transfer_points = optimizer.optimize_transfer_points()
            bus_alloc, metro_alloc = optimizer.optimize_resource_allocation(
                total_buses=total_buses,
                total_trains=total_trains
            )
            
            # Generate schedules and visualization
            bus_schedules, metro_schedules = optimizer.generate_schedules(bus_alloc, metro_alloc)
            map_html = optimizer.create_visualization()
            
            # Return comprehensive results
            return {
                "visualization": map_html,
                "results": {
                    "transfer_points": transfer_points,
                    "bus_allocation": bus_alloc,
                    "metro_allocation": metro_alloc,
                    "bus_schedules": bus_schedules,
                    "metro_schedules": metro_schedules,
                    "metrics": {
                        "total_buses_allocated": sum(bus_alloc.values()),
                        "total_trains_allocated": sum(metro_alloc.values()),
                        "num_transfer_points": len(transfer_points),
                        "total_daily_capacity": sum(s['Daily Capacity'] for s in bus_schedules + metro_schedules)
                    }
                },
                "type": "schedule"
            }
        except Exception as e:
            raise Exception(f"Error in transit optimization: {str(e)}")

    def run_algorithm(
        self,
        algorithm: str,
        source: str,
        dest: str,
        time_of_day: str,
        scenario: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run the specified algorithm and return results."""
        try:
            if algorithm == "MST":
                algo_name = kwargs.get("mst_algorithm", "Prim")
                visualization, results = run_mst(source, dest, time_of_day, scenario, algo_name)
                return {
                    "visualization": visualization,
                    "results": results,
                    "type": "network"
                }
                
            elif algorithm == "Dijkstra":
                avoid_congestion = kwargs.get("avoid_congestion", False)
                visualization, results = run_time_dijkstra(
                    source, dest, time_of_day, scenario, avoid_congestion
                )
                
                # Add path analysis if path exists
                if results["path"]:
                    results["analysis"] = self.analyze_path(results["path"], time_of_day)
                
                return {
                    "visualization": visualization,
                    "results": results,
                    "type": "path"
                }
                
            elif algorithm == "A*":
                hospitals = self.facilities[self.facilities["Type"].str.lower() == "medical"]
                visualization, results = run_emergency_routing(source)
                
                # Add path analysis if path exists
                if "path" in results and results["path"]:
                    results["analysis"] = self.analyze_path(results["path"], time_of_day)
                
                return {
                    "visualization": visualization,
                    "results": results,
                    "type": "emergency"
                }
            
            elif algorithm == "DP":
                try:
                    # Verify transit data is available
                    if self.bus_routes.empty or self.metro_lines.empty:
                        raise ValueError("Transit data not available")

                    total_buses = kwargs.get("total_buses", 200)
                    total_trains = kwargs.get("total_trains", 30)
                    
                    # Create optimizer instance
                    optimizer = PublicTransitOptimizer()
                    
                    # Build network and run optimization
                    optimizer.build_integrated_network()
                    transfer_points = optimizer.optimize_transfer_points()
                    bus_alloc, metro_alloc = optimizer.optimize_resource_allocation(
                        total_buses=total_buses,
                        total_trains=total_trains
                    )
                    
                    # Generate schedules and visualization
                    bus_schedules, metro_schedules = optimizer.generate_schedules(bus_alloc, metro_alloc)
                    map_html = optimizer.create_visualization()
                    
                    # Return comprehensive results
                    return {
                        "visualization": map_html,
                        "results": {
                            "transfer_points": transfer_points,
                            "bus_allocation": bus_alloc,
                            "metro_allocation": metro_alloc,
                            "bus_schedules": bus_schedules,
                            "metro_schedules": metro_schedules,
                            "metrics": {
                                "total_buses_allocated": sum(bus_alloc.values()),
                                "total_trains_allocated": sum(metro_alloc.values()),
                                "num_transfer_points": len(transfer_points),
                                "total_daily_capacity": sum(s['Daily Capacity'] for s in bus_schedules + metro_schedules)
                            }
                        },
                        "type": "schedule"
                    }
                except Exception as e:
                    raise ValueError(f"Error in transit optimization: {str(e)}")
            
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
                
        except Exception as e:
            raise ValueError(str(e))
    
    def display_results(self, results: Dict[str, Any]):
        """
        Display algorithm results in Streamlit.
        
        Args:
            results: Dictionary containing visualization and results
        """
        # Display visualization
        st.subheader("Network Visualization")
        st.components.v1.html(results["visualization"], height=600)
        
        # Display metrics based on result type
        if results["type"] == "network":
            if "warning" in results["results"]:
                st.warning(results["results"]["warning"])
            else:
                st.success("Network analysis completed successfully!")
                col1, col2 = st.columns(2)
                col1.metric("Total Distance", f"{results['results']['total_distance']:.2f} km")
                col2.metric("Network Segments", str(results['results']['num_edges']))
                
                # Display roads in MST
                if "roads" in results["results"]:
                    st.subheader("Roads in Minimum Spanning Tree")
                    for road_name in results["results"]["roads"]:
                        st.write(f"• {road_name}")
                
        elif results["type"] in ["path", "emergency"]:
            if "error" in results["results"]:
                st.error(results["results"]["error"])
            else:
                path = results["results"]["path"]
                analysis = results["results"].get("analysis", {})
                
                # Display success message and basic metrics
                st.success("Route found successfully!")
                
                # Basic metrics
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "Total Distance",
                    f"{analysis.get('total_distance', 0):.1f} km"
                )
                col2.metric(
                    "Total Time",
                    f"{analysis.get('total_time', 0):.1f} min"
                )
                col3.metric(
                    "Road Condition",
                    f"{analysis.get('avg_condition', 0):.1f}/10"
                )

                # Route Details
                st.subheader("Route Details")
                
                # Display start location
                st.write(f"🚩 Starting from: **{self.get_location_name(path[0])}**")
                
                # Display each road segment with analytics
                for i, segment in enumerate(analysis.get("road_segments", [])):
                    to_id = path[i + 1]
                    
                    # Create segment details
                    details = f"""
                    ↠ Take **{segment['road_name']}** to **{self.get_location_name(to_id)}**
                    - Distance: {segment['distance']:.1f} km
                    - Estimated Time: {segment['current_time']:.1f} min
                    - Road Condition: {segment['condition']}/10
                    """
                    
                    if segment['is_bottleneck']:
                        details += "\n    ⚠️ **Potential bottleneck!**"
                    
                    st.markdown(details)
                
                # Display destination/hospital reached
                if results["type"] == "emergency":
                    st.write(f"🏥 Hospital reached: **{results['results']['hospital']}**")
                else:
                    st.write(f"🏁 Destination reached: **{self.get_location_name(path[-1])}**")
                
                # Time Analysis
                if analysis.get("time_comparisons"):
                    st.subheader("Time Analysis")
                    
                    # Time comparison chart
                    time_data = pd.DataFrame(
                        list(analysis["time_comparisons"].items()),
                        columns=["Period", "Duration"]
                    )
                    st.bar_chart(time_data.set_index("Period"))
                    
                    # Best time to travel
                    best_time = analysis["best_time"]
                    st.info(
                        f"📊 Best time to travel: **{best_time['period']}** "
                        f"({best_time['duration']:.1f} min)\n\n"
                        f"Potential time saving: {best_time['saving']:.1f} min"
                    )
                
                # Bottleneck Analysis
                if analysis.get("bottlenecks"):
                    st.subheader("⚠️ Potential Bottlenecks")
                    for bottleneck in analysis["bottlenecks"]:
                        st.warning(
                            f"**{bottleneck['road']}**\n"
                            f"- Issue: {bottleneck['reason']}\n"
                            f"- Condition: {bottleneck['condition']}/10\n"
                            f"- Time Variance: {bottleneck['time_variance']:.1f} min"
                        )
    
    def get_neighborhood_names(self) -> Dict[str, str]:
        """Get mapping of neighborhood IDs to names for UI."""
        return self.neighborhood_names

    def find_transit_route(
        self,
        source: str,
        destination: str,
        time_of_day: str,
        prefer_metro: bool = True,
        minimize_transfers: bool = True,
        schedules: Dict = None
    ) -> Dict[str, Any]:
        """
        Find optimal public transit route between two points.
        
        Args:
            source: Starting location ID
            destination: Destination location ID
            time_of_day: Time period for the journey
            prefer_metro: Whether to prefer metro over bus routes
            minimize_transfers: Whether to minimize number of transfers
            schedules: Optional pre-computed schedules
            
        Returns:
            Dictionary containing route details, visualization, and metrics
        """
        try:
            # Initialize base map for visualization
            m = folium.Map(
                location=[30.0444, 31.2357],  # Cairo coordinates
                zoom_start=12
            )

            # Validate input parameters
            source = str(source).strip()
            destination = str(destination).strip()
            
            if source not in self.node_positions:
                raise ValueError(f"Source location '{source}' not found in network")
            if destination not in self.node_positions:
                raise ValueError(f"Destination location '{destination}' not found in network")
            if self.bus_routes.empty or self.metro_lines.empty:
                raise ValueError("Transit data not available")

            # Create specialized transit graph
            transit_graph = nx.MultiGraph()
            
            # Initialize schedules if not provided
            if schedules is None:
                schedules = self._generate_default_schedules()

            # Build transit network
            all_stops = self._build_transit_network(transit_graph, schedules)
            
            # Verify route exists
            if not nx.has_path(transit_graph, source, destination):
                raise ValueError(f"No route available between {self.get_location_name(source)} and {self.get_location_name(destination)}")

            # Find optimal path
            path = self._find_optimal_path(transit_graph, source, destination, prefer_metro, minimize_transfers)
            
            if not path:
                raise ValueError("Failed to find a valid path")
            
            if len(path) < 2:
                raise ValueError("Path must contain at least 2 stops")
            
            # Verify all path nodes are in the graph
            for node in path:
                if node not in transit_graph:
                    raise ValueError(f"Invalid node in path: {node}")
                if node not in self.node_positions:
                    raise ValueError(f"Missing coordinates for node: {node}")
            
            # Verify all consecutive nodes are connected
            for i in range(len(path) - 1):
                if not transit_graph.has_edge(path[i], path[i + 1]):
                    raise ValueError(f"Missing edge between {path[i]} and {path[i + 1]}")
            
            # Create visualization
            map_html = self._create_route_visualization(m, transit_graph, path)
            
            # Calculate route details
            route_details = self._calculate_route_details(transit_graph, path)
            
            return {
                "visualization": map_html,
                **route_details
            }

        except Exception as e:
            raise ValueError(str(e))

    def _generate_default_schedules(self) -> Dict:
        """Generate default schedules for bus routes and metro lines."""
        bus_schedules = []
        for _, route in self.bus_routes.iterrows():
            stops = [str(s).strip() for s in route["Stops"].split(",")]
            valid_stops = [stop for stop in stops if stop in self.node_positions]
            
            if len(valid_stops) >= 2:
                bus_schedules.append({
                    "Route": route["RouteID"],
                    "Stops": valid_stops,
                    "Interval (min)": 15,
                    "Transfer Points": list(self.transfer_points)
                })

        metro_schedules = []
        for _, line in self.metro_lines.iterrows():
            stations = [str(s).strip() for s in line["Stations"].split(",")]
            valid_stations = [station for station in stations if station in self.node_positions]
            
            if len(valid_stations) >= 2:
                metro_schedules.append({
                    "Line": line["LineID"],
                    "Stations": valid_stations,
                    "Interval (min)": 10,
                    "Transfer Points": list(self.transfer_points)
                })

        return {
            "bus_schedules": bus_schedules,
            "metro_schedules": metro_schedules
        }

    def _build_transit_network(self, transit_graph: nx.MultiGraph, schedules: Dict) -> set:
        """Build the transit network graph with bus routes and metro lines."""
        # Collect all stops and stations
        all_stops = set()
        
        # Add bus routes
        for route in schedules["bus_schedules"]:
            stops = route["Stops"]
            all_stops.update(stops)
            
            # Add edges between consecutive stops
            for i in range(len(stops) - 1):
                start_pos = self.node_positions[stops[i]]
                end_pos = self.node_positions[stops[i + 1]]
                distance = ((start_pos[0] - end_pos[0])**2 + 
                          (start_pos[1] - end_pos[1])**2)**0.5 * 100
                travel_time = max(5, (distance / 30) * 60)

                edge_data = {
                    "type": "bus",
                    "route_id": route["Route"],
                    "interval": float(route["Interval (min)"]),
                    "travel_time": float(travel_time),
                    "transfer_points": route["Transfer Points"]
                }
                
                # Add edge in both directions since it's an undirected graph
                transit_graph.add_edge(stops[i], stops[i + 1], **edge_data)
                transit_graph.add_edge(stops[i + 1], stops[i], **edge_data)
        
        # Add metro lines
        for line in schedules["metro_schedules"]:
            stations = line["Stations"]
            all_stops.update(stations)
            
            # Add edges between consecutive stations
            for i in range(len(stations) - 1):
                start_pos = self.node_positions[stations[i]]
                end_pos = self.node_positions[stations[i + 1]]
                distance = ((start_pos[0] - end_pos[0])**2 + 
                          (start_pos[1] - end_pos[1])**2)**0.5 * 100
                travel_time = max(3, (distance / 60) * 60)

                edge_data = {
                    "type": "metro",
                    "route_id": line["Line"],
                    "interval": float(line["Interval (min)"]),
                    "travel_time": float(travel_time),
                    "transfer_points": line["Transfer Points"]
                }
                
                # Add edge in both directions since it's an undirected graph
                transit_graph.add_edge(stations[i], stations[i + 1], **edge_data)
                transit_graph.add_edge(stations[i + 1], stations[i], **edge_data)
        
        # Add transfer edges
        for stop in all_stops:
            # Find all routes that include this stop
            routes_at_stop = []
            for route in schedules["bus_schedules"]:
                if stop in route["Stops"]:
                    routes_at_stop.append(("bus", route["Route"]))
            for line in schedules["metro_schedules"]:
                if stop in line["Stations"]:
                    routes_at_stop.append(("metro", line["Line"]))
            
            # Add transfer edges if stop serves multiple routes
            if len(routes_at_stop) > 1:
                edge_data = {
                    "type": "transfer",
                    "route_id": f"Transfer at {self.get_location_name(stop)}",
                    "interval": 5,
                    "travel_time": 10,
                    "transfer_points": [stop]
                }
                transit_graph.add_edge(stop, stop, **edge_data)
        
        return all_stops

    def _find_optimal_path(
        self, 
        graph: nx.MultiGraph, 
        source: str, 
        destination: str,
        prefer_metro: bool,
        minimize_transfers: bool
    ) -> List[str]:
        """Find the optimal path considering preferences."""
        def edge_weight(u, v, data):
            base_time = float(data["travel_time"]) + float(data["interval"]) / 2
            if prefer_metro and data["type"] == "bus":
                base_time *= 1.5
            if minimize_transfers and data["type"] == "transfer":
                base_time *= 2
            return base_time

        try:
            # Find shortest path considering weights
            path = nx.shortest_path(
                graph,
                source,
                destination,
                weight=lambda u, v, d: edge_weight(u, v, d[0])
            )
            
            # Verify path is valid
            for i in range(len(path) - 1):
                if not graph.has_edge(path[i], path[i + 1]):
                    raise nx.NetworkXNoPath(f"Invalid path segment between {path[i]} and {path[i + 1]}")
            
            return path
            
        except nx.NetworkXNoPath:
            raise ValueError(f"No route found between {self.get_location_name(source)} and {self.get_location_name(destination)}")
        except Exception as e:
            raise ValueError(f"Error finding path: {str(e)}")

    def _create_route_visualization(self, m: folium.Map, graph: nx.MultiGraph, path: List[str]) -> str:
        """Create an interactive map visualization of the route."""
        if not path or len(path) < 2:
            raise ValueError("Invalid path for visualization")

        # Add Font Awesome icons
        m.get_root().header.add_child(folium.Element("""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        """))

        # Create icons for stops
        bus_icon = folium.DivIcon(
            html='<div style="font-size: 24px; color: blue;"><i class="fa fa-bus"></i></div>',
            icon_size=(40, 40),
            icon_anchor=(20, 20)
        )
        metro_icon = folium.DivIcon(
            html='<div style="font-size: 24px; color: red;"><i class="fa fa-subway"></i></div>',
            icon_size=(40, 40),
            icon_anchor=(20, 20)
        )
        start_icon = folium.DivIcon(
            html='<div style="font-size: 28px; color: green;"><i class="fa fa-play-circle"></i></div>',
            icon_size=(40, 40),
            icon_anchor=(20, 20)
        )
        end_icon = folium.DivIcon(
            html='<div style="font-size: 28px; color: red;"><i class="fa fa-stop-circle"></i></div>',
            icon_size=(40, 40),
            icon_anchor=(20, 20)
        )

        # Draw all route segments first
        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]
            
            # Get edge data
            edge_data = graph[start_node][end_node][0]
            transport_type = edge_data["type"]
            
            # Get coordinates
            start_coords = self.node_positions[start_node]
            end_coords = self.node_positions[end_node]
            
            # Draw route line
            color = "red" if transport_type == "metro" else "blue"
            weight = 8 if transport_type == "metro" else 6  # Increased thickness
            
            folium.PolyLine(
                locations=[start_coords, end_coords],
                color=color,
                weight=weight,
                opacity=0.8,
                popup=f"{transport_type.title()} {edge_data['route_id']}"
            ).add_to(m)

        # Then add all stop markers
        for i, node_id in enumerate(path):
            coords = self.node_positions[node_id]
            is_transfer = node_id in self.transfer_points
            is_start = i == 0
            is_end = i == len(path) - 1
            
            # Get edge data for popup
            if i < len(path) - 1:
                edge_data = graph[node_id][path[i + 1]][0]
            else:
                edge_data = graph[path[i - 1]][node_id][0]
            
            # Choose icon
            if is_start:
                icon = start_icon
            elif is_end:
                icon = end_icon
            else:
                icon = metro_icon if edge_data["type"] == "metro" else bus_icon
            
            # Add marker
            folium.Marker(
                location=coords,
                icon=icon,
                popup=folium.Popup(self._create_stop_popup(
                    node_id, edge_data, is_transfer, is_start, is_end
                ), max_width=300)
            ).add_to(m)
            
            # Add transfer point circle if needed
            if is_transfer:
                folium.CircleMarker(
                    location=coords,
                    radius=15,
                    color="green",
                    fill=True,
                    fill_opacity=0.3,
                    weight=3,
                    popup="Transfer Point"
                ).add_to(m)

            # Add special circle for start/end points
            if is_start or is_end:
                color = "green" if is_start else "red"
                folium.CircleMarker(
                    location=coords,
                    radius=18,
                    color=color,
                    fill=False,
                    weight=3,
                    opacity=0.8,
                    popup="Start Point" if is_start else "End Point"
                ).add_to(m)

        # Fit map bounds to route with padding
        route_coords = [self.node_positions[node_id] for node_id in path]
        min_lat = min(coord[0] for coord in route_coords)
        max_lat = max(coord[0] for coord in route_coords)
        min_lon = min(coord[1] for coord in route_coords)
        max_lon = max(coord[1] for coord in route_coords)
        
        # Add padding (about 10% of the route span)
        lat_padding = (max_lat - min_lat) * 0.1
        lon_padding = (max_lon - min_lon) * 0.1
        
        # Set bounds with padding
        m.fit_bounds([
            [min_lat - lat_padding, min_lon - lon_padding],
            [max_lat + lat_padding, max_lon + lon_padding]
        ])

        # Add legend
        m.get_root().html.add_child(folium.Element(self._create_legend_html()))
        
        return m._repr_html_()

    def _create_stop_popup(self, node_id: str, edge_data: Dict, is_transfer: bool, is_start: bool = False, is_end: bool = False) -> str:
        """Create HTML content for stop popup."""
        location_name = self.get_location_name(node_id)
        stop_type = "Start" if is_start else "End" if is_end else edge_data['type'].title()
        
        content = f"""
        <div style="width: 200px; padding: 10px;">
            <h4 style="margin: 0 0 10px 0; color: {'green' if is_start else 'red' if is_end else 'black'};">
                {location_name}
            </h4>
            <div style="margin-bottom: 5px;">
                <strong>Type:</strong> {stop_type} Stop
            </div>
        """
        
        if not (is_start or is_end):
            content += f"""
            <div style="margin-bottom: 5px;">
                <strong>Line:</strong> {edge_data['route_id']}
            </div>
            <div style="margin-bottom: 5px;">
                <strong>Next departure:</strong> {edge_data['interval']:.0f} min
            </div>
            """
            
        if is_transfer:
            content += """
            <div style="margin-top: 10px; padding: 5px; background-color: #e8f5e9; border-radius: 5px;">
                <i class="fa fa-exchange"></i> Transfer Point
            </div>
            """
            
        content += "</div>"
        return content

    def _create_legend_html(self) -> str:
        """Create HTML content for map legend."""
        return """
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 200px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <h4 style="margin: 0 0 10px 0;">Route Legend</h4>
            <div style="margin-bottom: 8px;">
                <i class="fa fa-play-circle" style="color:green; font-size: 18px;"></i>
                <span style="margin-left: 8px;">Start Point</span>
            </div>
            <div style="margin-bottom: 8px;">
                <i class="fa fa-stop-circle" style="color:red; font-size: 18px;"></i>
                <span style="margin-left: 8px;">End Point</span>
            </div>
            <div style="margin-bottom: 8px;">
                <i class="fa fa-bus" style="color:blue; font-size: 18px;"></i>
                <span style="margin-left: 8px;">Bus Stop</span>
            </div>
            <div style="margin-bottom: 8px;">
                <i class="fa fa-subway" style="color:red; font-size: 18px;"></i>
                <span style="margin-left: 8px;">Metro Station</span>
            </div>
            <div style="margin-bottom: 8px;">
                <hr style="border: 6px solid blue; display: inline-block; width: 30px; margin-right: 8px;">
                <span>Bus Route</span>
            </div>
            <div style="margin-bottom: 8px;">
                <hr style="border: 8px solid red; display: inline-block; width: 30px; margin-right: 8px;">
                <span>Metro Line</span>
            </div>
            <div>
                <i class="fa fa-exchange" style="color:green; font-size: 18px;"></i>
                <span style="margin-left: 8px;">Transfer Point</span>
            </div>
        </div>
        """

    def _calculate_route_details(self, graph: nx.MultiGraph, path: List[str]) -> Dict[str, Any]:
        """Calculate detailed metrics for the route."""
        total_travel_time = 0
        total_waiting_time = 0
        total_distance = 0
        total_cost = 0
        steps = []
        num_transfers = 0
        current_line = None
        current_mode = None
        stops_in_current_metro_journey = 0
        
        for i in range(len(path) - 1):
            edge_data = graph[path[i]][path[i + 1]][0]
            transport_mode = edge_data["type"]
            
            # Calculate times
            segment_time = float(edge_data["travel_time"])
            total_travel_time += segment_time
            
            wait_time = 0
            if i == 0 or (current_line and current_line != edge_data["route_id"]):
                wait_time = float(edge_data["interval"]) / 2
                total_waiting_time += wait_time
                if i > 0:
                    num_transfers += 1
                    # Add fare for new segment
                    if transport_mode == "bus":
                        total_cost += 12  # Average bus fare in Cairo
                    elif transport_mode == "metro":
                        # Reset metro stops counter and add base fare
                        if current_mode != "metro":
                            stops_in_current_metro_journey = 0
                            total_cost += 8  # Base metro fare
            
            current_line = edge_data["route_id"]
            
            # For first segment, add initial fare
            if i == 0:
                if transport_mode == "bus":
                    total_cost += 12  # Average bus fare
                elif transport_mode == "metro":
                    total_cost += 8  # Base metro fare
            
            # Count stops for metro fare calculation
            if transport_mode == "metro":
                stops_in_current_metro_journey += 1
                # Update metro fare based on number of stops
                if stops_in_current_metro_journey == 10:
                    total_cost += 2  # Additional fare for 10+ stops
                elif stops_in_current_metro_journey == 17:
                    total_cost += 5  # Additional fare for 17+ stops
                elif stops_in_current_metro_journey == 24:
                    total_cost += 5  # Additional fare for 24+ stops
            
            current_mode = transport_mode
            
            # Calculate distance
            start_pos = self.node_positions[path[i]]
            end_pos = self.node_positions[path[i + 1]]
            distance = ((start_pos[0] - end_pos[0])**2 + 
                      (start_pos[1] - end_pos[1])**2)**0.5 * 100
            total_distance += distance
            
            # Create step details
            step = {
                "mode": transport_mode.title(),
                "from_stop": self.get_location_name(path[i]),
                "to_stop": self.get_location_name(path[i + 1]),
                "travel_time": segment_time,
                "wait_time": wait_time,
                "next_departure": f"Every {edge_data['interval']:.0f} minutes",
                "line_info": f"{transport_mode.title()} {edge_data['route_id']}",
                "summary": f"{transport_mode.title()} {edge_data['route_id']}: {self.get_location_name(path[i])} → {self.get_location_name(path[i + 1])}"
            }
            
            if path[i] in self.transfer_points:
                step["transfer_info"] = "Transfer point - Follow signs to your next line"
                step["summary"] = f"🔄 Transfer: {step['summary']}"
            
            steps.append(step)

        return {
            "total_travel_time": total_travel_time,
            "total_waiting_time": total_waiting_time,
            "total_time": total_travel_time + total_waiting_time,
            "total_distance": total_distance,
            "num_transfers": num_transfers,
            "total_cost": total_cost,
            "steps": steps
        }

    def get_network_status(self) -> Dict[str, Any]:
        """Get current status of the public transit network."""
        try:
            # In a real system, this would fetch live data
            # Here we'll generate sample status data
            
            # Metro lines status
            metro_lines = []
            if not self.metro_lines.empty:
                for _, line in self.metro_lines.iterrows():
                    metro_lines.append({
                        "Line": f"Metro {line['LineID']}",
                        "Status": "Operating Normally",
                        "Next Train": "2 minutes",
                        "Crowding": "Moderate",
                        "Delays": "None"
                    })
            else:
                metro_lines.append({
                    "Line": "No metro lines available",
                    "Status": "N/A",
                    "Next Train": "N/A",
                    "Crowding": "N/A",
                    "Delays": "N/A"
                })
            
            # Bus routes status
            bus_routes = []
            if not self.bus_routes.empty:
                for _, route in self.bus_routes.iterrows():
                    bus_routes.append({
                        "Route": f"Bus {route['RouteID']}",
                        "Status": "Operating Normally",
                        "Next Bus": "5 minutes",
                        "Crowding": "Light",
                        "Delays": "None"
                    })
            else:
                bus_routes.append({
                    "Route": "No bus routes available",
                    "Status": "N/A",
                    "Next Bus": "N/A",
                    "Crowding": "N/A",
                    "Delays": "N/A"
                })
            
            # Transfer points status
            transfer_points = []
            if self.transfer_points:
                for point in self.transfer_points:
                    point_name = self.get_location_name(point)
                    transfer_points.append({
                        "Location": point_name if point_name else point,
                        "Status": "Open",
                        "Crowding": "Moderate",
                        "Facilities": "All Operating",
                        "Next Connections": "< 5 minutes"
                    })
            else:
                transfer_points.append({
                    "Location": "No transfer points available",
                    "Status": "N/A",
                    "Crowding": "N/A",
                    "Facilities": "N/A",
                    "Next Connections": "N/A"
                })
            
            return {
                "metro_lines": metro_lines,
                "bus_routes": bus_routes,
                "transfer_points": transfer_points,
                "last_updated": "Just now"
            }
            
        except Exception as e:
            print(f"Error getting network status: {str(e)}")
            # Return a default error status
            return {
                "metro_lines": [{
                    "Line": "Error loading metro lines",
                    "Status": "Error",
                    "Next Train": "Unknown",
                    "Crowding": "Unknown",
                    "Delays": str(e)
                }],
                "bus_routes": [{
                    "Route": "Error loading bus routes",
                    "Status": "Error",
                    "Next Bus": "Unknown",
                    "Crowding": "Unknown",
                    "Delays": str(e)
                }],
                "transfer_points": [{
                    "Location": "Error loading transfer points",
                    "Status": "Error",
                    "Crowding": "Unknown",
                    "Facilities": "Unknown",
                    "Next Connections": "Unknown"
                }],
                "last_updated": "Error"
            }
