from typing import Dict, Any, Optional
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
    def __init__(self):
        """Initialize the controller with data and graph."""
        self.neighborhoods, self.roads, self.facilities = load_data()
        self.base_map, self.node_positions, self.neighborhood_ids, self.graph = build_map(
            self.neighborhoods, self.roads, self.facilities
        )
        
        # Create lookup dictionaries for names
        self.neighborhood_names = {
            str(row["ID"]): row["Name"]
            for _, row in self.neighborhoods.iterrows()
        }
        self.facility_names = {
            str(row["ID"]): row["Name"]
            for _, row in self.facilities.iterrows()
        }
        # Create road name lookup
        self.road_names = {
            (str(row["FromID"]), str(row["ToID"])): row["Name"]
            for _, row in self.roads.iterrows()
        }

        # Create set of valid nodes
        self.valid_nodes = set(str(row["ID"]) for _, row in self.neighborhoods.iterrows())
        self.valid_nodes.update(str(row["ID"]) for _, row in self.facilities.iterrows())

        # Load transit data
        try:
            self.bus_routes, self.metro_lines, self.demand_data, self.transfer_points = load_transit_data(self.valid_nodes)
        except Exception as e:
            st.error(f"Could not load transit data: {str(e)}")
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
            # Load data
            bus_routes = pd.read_csv('data/bus_routes.csv')
            metro_lines = pd.read_csv('data/metro_lines.csv')
            demand_data = pd.read_csv('data/demand_data.csv')
            
            # Clean demand data
            demand_dict = defaultdict(int)
            for _, row in demand_data.iterrows():
                from_id = str(row['FromID'])
                to_id = str(row['ToID'])
                demand_dict[(from_id, to_id)] = row['DailyPassengers']
            
            # Create optimizer and run optimization
            optimizer = PublicTransitOptimizer(bus_routes, metro_lines, demand_dict)
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
            raise Exception(f"Error in scheduling optimization: {str(e)}")

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
                    st.write("Initializing transit optimization...")
                    # Verify transit data is available
                    if self.bus_routes.empty or self.metro_lines.empty:
                        raise ValueError("Transit data not available. Please check bus_routes.csv and metro_lines.csv.")

                    # Show transit data status
                    st.write("Transit Data Status:")
                    st.write(f"Bus Routes: {len(self.bus_routes)} routes")
                    st.write(f"Metro Lines: {len(self.metro_lines)} lines")
                    st.write(f"Transfer Points: {len(self.transfer_points)} points")

                    total_buses = kwargs.get("total_buses", 200)
                    total_trains = kwargs.get("total_trains", 30)
                    
                    # Create optimizer instance
                    st.write("Creating transit optimizer...")
                    optimizer = PublicTransitOptimizer()
                    
                    # Build network
                    st.write("Building integrated network...")
                    optimizer.build_integrated_network()
                    
                    # Run optimization
                    st.write("Running schedule optimization...")
                    transfer_points = optimizer.optimize_transfer_points()
                    bus_alloc, metro_alloc = optimizer.optimize_resource_allocation(
                        total_buses=total_buses,
                        total_trains=total_trains
                    )
                    
                    # Generate schedules
                    st.write("Generating transit schedules...")
                    bus_schedules, metro_schedules = optimizer.generate_schedules(bus_alloc, metro_alloc)
                    
                    # Create visualization
                    st.write("Creating network visualization...")
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
                    st.error(f"Error in transit optimization: {str(e)}")
                    # Show detailed error information
                    if st.checkbox("Show Optimization Error Details"):
                        st.error("Transit Optimization Error Details:")
                        st.write("Bus Routes Shape:", self.bus_routes.shape if not self.bus_routes.empty else "No bus routes")
                        st.write("Metro Lines Shape:", self.metro_lines.shape if not self.metro_lines.empty else "No metro lines")
                        st.write("Transfer Points:", list(self.transfer_points))
                        st.write("Error:", str(e))
                    raise
            
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
                
        except Exception as e:
            st.error(f"Algorithm error: {str(e)}")
            raise
    
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
        """Find optimal public transit route between two points."""
        try:
            # Create base map first to ensure it works
            try:
                m = folium.Map(
                    location=[30.0444, 31.2357],  # Cairo coordinates
                    zoom_start=12
                )
            except Exception as e:
                st.error(f"Error creating base map: {str(e)}")
                raise ValueError("Failed to create map visualization")

            # Convert IDs to strings and strip whitespace
            source = str(source).strip()
            destination = str(destination).strip()

            # Debug information
            st.write("Debug Info:")
            st.write(f"Source: {source} ({self.get_location_name(source)})")
            st.write(f"Destination: {destination} ({self.get_location_name(destination)})")

            # Validate input data
            if self.bus_routes.empty or self.metro_lines.empty:
                raise ValueError("Transit data not available. Please check that bus_routes.csv and metro_lines.csv exist in the data directory.")
            
            if source not in self.node_positions:
                raise ValueError(f"Source location '{source}' ({self.get_location_name(source)}) not found in the network.")
            
            if destination not in self.node_positions:
                raise ValueError(f"Destination location '{destination}' ({self.get_location_name(destination)}) not found in the network.")

            # Create a specialized graph for transit routing
            transit_graph = nx.MultiGraph()
            
            # Initialize schedules if not provided
            if schedules is None:
                # Process bus routes
                bus_schedules = []
                for _, route in self.bus_routes.iterrows():
                    try:
                        stops = [str(s).strip() for s in route["Stops"].split(",")]
                        valid_stops = []
                        for stop in stops:
                            if stop not in self.node_positions:
                                st.warning(f"Bus route {route['RouteID']}: Stop {stop} not found in network")
                            else:
                                valid_stops.append(stop)
                        
                        if len(valid_stops) >= 2:
                            bus_schedules.append({
                                "Route": route["RouteID"],
                                "Stops": valid_stops,
                                "Interval (min)": 15,  # Default interval
                                "Transfer Points": list(self.transfer_points)
                            })
                    except Exception as e:
                        st.warning(f"Error processing bus route {route['RouteID']}: {str(e)}")
                        continue

                # Process metro lines
                metro_schedules = []
                for _, line in self.metro_lines.iterrows():
                    try:
                        stations = [str(s).strip() for s in line["Stations"].split(",")]
                        valid_stations = []
                        for station in stations:
                            if station not in self.node_positions:
                                st.warning(f"Metro line {line['LineID']}: Station {station} not found in network")
                            else:
                                valid_stations.append(station)
                        
                        if len(valid_stations) >= 2:
                            metro_schedules.append({
                                "Line": line["LineID"],
                                "Stations": valid_stations,
                                "Interval (min)": 10,  # Default interval
                                "Transfer Points": list(self.transfer_points)
                            })
                    except Exception as e:
                        st.warning(f"Error processing metro line {line['LineID']}: {str(e)}")
                        continue

                schedules = {
                    "bus_schedules": bus_schedules,
                    "metro_schedules": metro_schedules
                }

            # Debug information
            st.write("Available Routes:")
            st.write("Bus Routes:", [f"{route['Route']}: {' → '.join(route['Stops'])}" for route in schedules["bus_schedules"]])
            st.write("Metro Lines:", [f"{line['Line']}: {' → '.join(line['Stations'])}" for line in schedules["metro_schedules"]])

            # Collect all stops and stations
            all_stops = set()
            for route in schedules["bus_schedules"]:
                all_stops.update(route["Stops"])
            for line in schedules["metro_schedules"]:
                all_stops.update(line["Stations"])

            # Add all nodes to the graph first
            for stop in all_stops:
                transit_graph.add_node(stop)

            # Add bus routes to transit graph
            for route in schedules["bus_schedules"]:
                stops = route["Stops"]
                for i in range(len(stops) - 1):
                    try:
                        # Get coordinates and calculate travel time
                        start_pos = self.node_positions[stops[i]]
                        end_pos = self.node_positions[stops[i + 1]]
                        distance = ((start_pos[0] - end_pos[0])**2 + 
                                  (start_pos[1] - end_pos[1])**2)**0.5 * 100
                        travel_time = max(5, (distance / 30) * 60)  # Minimum 5 minutes between stops

                        edge_data = {
                            "type": "bus",
                            "route_id": route["Route"],
                            "interval": float(route["Interval (min)"]),
                            "travel_time": float(travel_time),
                            "transfer_points": route["Transfer Points"]
                        }
                        transit_graph.add_edge(stops[i], stops[i + 1], **edge_data)
                    except Exception as e:
                        st.warning(f"Error adding bus route segment {route['Route']} ({stops[i]} → {stops[i + 1]}): {str(e)}")
                        continue

            # Add metro lines to transit graph
            for line in schedules["metro_schedules"]:
                stations = line["Stations"]
                for i in range(len(stations) - 1):
                    try:
                        # Get coordinates and calculate travel time
                        start_pos = self.node_positions[stations[i]]
                        end_pos = self.node_positions[stations[i + 1]]
                        distance = ((start_pos[0] - end_pos[0])**2 + 
                                  (start_pos[1] - end_pos[1])**2)**0.5 * 100
                        travel_time = max(3, (distance / 60) * 60)  # Minimum 3 minutes between stations

                        edge_data = {
                            "type": "metro",
                            "route_id": line["Line"],
                            "interval": float(line["Interval (min)"]),
                            "travel_time": float(travel_time),
                            "transfer_points": line["Transfer Points"]
                        }
                        transit_graph.add_edge(stations[i], stations[i + 1], **edge_data)
                    except Exception as e:
                        st.warning(f"Error adding metro line segment {line['Line']} ({stations[i]} → {stations[i + 1]}): {str(e)}")
                        continue

            # Add transfer edges between routes at transfer points
            for stop in all_stops:
                # Find all routes that include this stop
                routes_at_stop = []
                for route in schedules["bus_schedules"]:
                    if stop in route["Stops"]:
                        routes_at_stop.append(("bus", route["Route"]))
                for line in schedules["metro_schedules"]:
                    if stop in line["Stations"]:
                        routes_at_stop.append(("metro", line["Line"]))
                
                # If this stop is served by multiple routes, add transfer edges
                if len(routes_at_stop) > 1:
                    # Add edges between all connected stops in different routes
                    for i, (type1, route1) in enumerate(routes_at_stop):
                        for type2, route2 in routes_at_stop[i+1:]:
                            if type1 != type2 or route1 != route2:
                                # Add transfer edge with a time penalty
                                transit_graph.add_edge(stop, stop, 
                                    type="transfer",
                                    route_id=f"Transfer at {self.get_location_name(stop)}",
                                    interval=5,  # 5-minute transfer interval
                                    travel_time=10,  # 10-minute transfer time
                                    transfer_points=[stop]
                                )

            # Debug information about graph
            st.write("Graph Information:")
            st.write(f"Number of nodes: {len(transit_graph.nodes())}")
            st.write(f"Number of edges: {len(transit_graph.edges())}")
            st.write(f"Source node in graph: {source in transit_graph.nodes()}")
            st.write(f"Destination node in graph: {destination in transit_graph.nodes()}")
            st.write("Transfer points in graph:", [stop for stop in all_stops if transit_graph.degree(stop) > 2])

            # Check if source and destination are in the same connected component
            if not nx.has_path(transit_graph, source, destination):
                # Find connected components
                components = list(nx.connected_components(transit_graph))
                source_component = None
                dest_component = None
                
                for i, component in enumerate(components):
                    if source in component:
                        source_component = i
                    if destination in component:
                        dest_component = i
                
                error_msg = f"No transit route found between {self.get_location_name(source)} and {self.get_location_name(destination)}. "
                if source_component is None:
                    error_msg += f"Source location ({self.get_location_name(source)}) is not connected to any transit routes."
                elif dest_component is None:
                    error_msg += f"Destination location ({self.get_location_name(destination)}) is not connected to any transit routes."
                else:
                    error_msg += "These locations are in different disconnected parts of the transit network."
                
                raise ValueError(error_msg)

            # Find shortest path considering preferences
            def edge_weight(u, v, data):
                base_time = float(data[0]["travel_time"]) + float(data[0]["interval"]) / 2
                if prefer_metro and data[0]["type"] == "bus":
                    base_time *= 1.5  # Penalty for bus if metro is preferred
                if minimize_transfers and data[0]["type"] == "transfer":
                    base_time *= 2  # Higher penalty for transfers if minimizing them
                return base_time

            path = nx.shortest_path(
                transit_graph,
                source,
                destination,
                weight=edge_weight
            )
            
            # After finding the path, create the visualization
            try:
                # Add Font Awesome for icons
                m.get_root().header.add_child(folium.Element("""
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
                """))

                # Create icons
                bus_icon = folium.DivIcon(
                    html='<div style="font-size: 18px; color: blue;"><i class="fa fa-bus"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15)
                )

                metro_icon = folium.DivIcon(
                    html='<div style="font-size: 18px; color: red;"><i class="fa fa-subway"></i></div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15)
                )

                # Track added stops to avoid duplicates
                added_stops = set()

                # Draw route segments
                for i in range(len(path) - 1):
                    try:
                        edge_data = transit_graph[path[i]][path[i + 1]][0]
                        color = "red" if edge_data["type"] == "metro" else "blue"
                        
                        # Get coordinates for both stops
                        start_coords = self.node_positions.get(path[i])
                        end_coords = self.node_positions.get(path[i + 1])
                        
                        if not start_coords or not end_coords:
                            st.warning(f"Missing coordinates for segment {path[i]} → {path[i + 1]}")
                            continue

                        # Draw route line
                        folium.PolyLine(
                            locations=[start_coords, end_coords],
                            color=color,
                            weight=4,
                            opacity=0.8,
                            popup=f"{edge_data['type'].title()} {edge_data['route_id']}"
                        ).add_to(m)

                        # Add stop markers
                        for node_id, coords in [(path[i], start_coords), (path[i + 1], end_coords)]:
                            if node_id not in added_stops:
                                # Determine if this is a transfer point
                                is_transfer = node_id in self.transfer_points
                                
                                # Get transport type
                                icon = metro_icon if edge_data["type"] == "metro" else bus_icon
                                color = "red" if edge_data["type"] == "metro" else "blue"
                                
                                # Create popup content
                                popup_content = f"""
                                <div style="width: 200px;">
                                    <b>{self.get_location_name(node_id)}</b><br>
                                    {edge_data['type'].title()} Stop<br>
                                    {'Transfer Point<br>' if is_transfer else ''}
                                    Next departure: {edge_data['interval']:.0f} min
                                </div>
                                """
                                
                                # Add markers
                                folium.Marker(
                                    location=coords,
                                    icon=icon,
                                    popup=folium.Popup(popup_content, max_width=300)
                                ).add_to(m)
                                
                                if is_transfer:
                                    folium.CircleMarker(
                                        location=coords,
                                        radius=12,
                                        color="green",
                                        fill=True,
                                        fill_opacity=0.3,
                                        weight=2,
                                        popup="Transfer Point"
                                    ).add_to(m)
                                else:
                                    folium.CircleMarker(
                                        location=coords,
                                        radius=8,
                                        color=color,
                                        fill=True,
                                        fill_opacity=0.3,
                                        weight=2
                                    ).add_to(m)
                                
                                added_stops.add(node_id)
                    except Exception as e:
                        st.warning(f"Error drawing route segment: {str(e)}")
                        continue

                # Add legend
                legend_html = """
                <div style="position: fixed; 
                            bottom: 50px; right: 50px; width: 180px; 
                            border:2px solid grey; z-index:9999; font-size:14px;
                            background-color:white;
                            padding: 10px;
                            border-radius: 5px;">
                    <p style="margin-bottom: 10px;"><strong>Route Legend</strong></p>
                    <div style="margin-bottom: 5px;">
                        <i class="fa fa-bus" style="color:blue;"></i> Bus Stop
                    </div>
                    <div style="margin-bottom: 5px;">
                        <i class="fa fa-subway" style="color:red;"></i> Metro Station
                    </div>
                    <div style="margin-bottom: 5px;">
                        <hr style="border: 2px solid blue; display: inline-block; width: 30px; margin-right: 5px;">
                        Bus Route
                    </div>
                    <div style="margin-bottom: 5px;">
                        <hr style="border: 2px solid red; display: inline-block; width: 30px; margin-right: 5px;">
                        Metro Line
                    </div>
                    <div>
                        <i class="fa fa-circle" style="color:green;"></i> Transfer Point
                    </div>
                </div>
                """
                m.get_root().html.add_child(folium.Element(legend_html))

            except Exception as e:
                st.error(f"Error creating route visualization: {str(e)}")
                # Return a simple map if visualization fails
                m = folium.Map(
                    location=[30.0444, 31.2357],  # Cairo coordinates
                    zoom_start=12
                )

            # Calculate route details
            total_travel_time = 0
            total_waiting_time = 0
            total_distance = 0
            steps = []
            num_transfers = 0
            current_line = None
            wait_time = 0
            
            for i in range(len(path) - 1):
                edge_data = transit_graph[path[i]][path[i + 1]][0]
                
                # Add travel time
                segment_time = float(edge_data["travel_time"])
                total_travel_time += segment_time
                
                # Track waiting time
                if i == 0 or (current_line and current_line != edge_data["route_id"]):
                    wait_time = float(edge_data["interval"]) / 2
                    total_waiting_time += wait_time
                    if i > 0:  # Count transfers after first segment
                        num_transfers += 1
                
                current_line = edge_data["route_id"]
                
                # Calculate segment distance
                try:
                    start_pos = self.node_positions[path[i]]
                    end_pos = self.node_positions[path[i + 1]]
                    distance = ((start_pos[0] - end_pos[0])**2 + 
                              (start_pos[1] - end_pos[1])**2)**0.5 * 100
                    total_distance += distance
                except Exception:
                    pass
                
                # Add step details
                step = {
                    "mode": edge_data["type"].title(),
                    "from_stop": self.get_location_name(path[i]),
                    "to_stop": self.get_location_name(path[i + 1]),
                    "travel_time": segment_time,
                    "wait_time": wait_time if (i == 0 or (current_line != edge_data["route_id"])) else 0,
                    "next_departure": f"Every {edge_data['interval']:.0f} minutes",
                    "line_info": f"{edge_data['type'].title()} {edge_data['route_id']}",
                    "summary": f"{edge_data['type'].title()} {edge_data['route_id']}: {self.get_location_name(path[i])} → {self.get_location_name(path[i + 1])}"
                }
                
                if path[i] in self.transfer_points:
                    step["transfer_info"] = "Transfer point - Follow signs to your next line"
                    step["summary"] = f"🔄 Transfer: {step['summary']}"
                
                steps.append(step)

            return {
                "visualization": m._repr_html_(),
                "total_travel_time": total_travel_time,
                "total_waiting_time": total_waiting_time,
                "total_time": total_travel_time + total_waiting_time,
                "total_distance": total_distance,
                "num_transfers": num_transfers,
                "total_cost": (total_travel_time + total_waiting_time) * 0.5,
                "steps": steps
            }

        except Exception as e:
            st.error(f"Error finding transit route: {str(e)}")
            raise

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
