from typing import Dict, Any, Optional
import streamlit as st
import folium
import pandas as pd
import numpy as np
from algorithms.mst import run_mst
from algorithms.time_dijkstra import run_time_dijkstra, calculate_time_weight
from algorithms.a_star import find_nearest_hospital, run_emergency_routing
from utils.helpers import load_data, build_map
from collections import defaultdict
from algorithms.dp_schedule import PublicTransitOptimizer
import networkx as nx
import os

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

        # Load transit data
        try:
            bus_routes_path = os.path.join('data', 'bus_routes.csv')
            metro_lines_path = os.path.join('data', 'metro_lines.csv')
            
            if os.path.exists(bus_routes_path) and os.path.exists(metro_lines_path):
                self.bus_routes = pd.read_csv(bus_routes_path)
                self.metro_lines = pd.read_csv(metro_lines_path)
                
                # Initialize transfer points (intersections between bus and metro)
                self.transfer_points = set()
                bus_stops = set()
                metro_stations = set()
                
                # Collect all bus stops
                for _, route in self.bus_routes.iterrows():
                    stops = [s.strip() for s in route['Stops'].split(',')]
                    bus_stops.update(stops)
                
                # Collect all metro stations
                for _, line in self.metro_lines.iterrows():
                    stations = [s.strip() for s in line['Stations'].split(',')]
                    metro_stations.update(stations)
                
                # Find intersections
                self.transfer_points = bus_stops.intersection(metro_stations)
            else:
                print("Warning: Transit data files not found")
                self.bus_routes = pd.DataFrame()
                self.metro_lines = pd.DataFrame()
                self.transfer_points = set()
                
        except Exception as e:
            print(f"Warning: Could not load transit data: {str(e)}")
            # Initialize with empty data if files not found
            self.bus_routes = pd.DataFrame()
            self.metro_lines = pd.DataFrame()
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
            total_buses = kwargs.get("total_buses", 200)
            total_trains = kwargs.get("total_trains", 30)
            return self.run_dp_scheduling(total_buses, total_trains)
        
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
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
            # Create a specialized graph for transit routing
            transit_graph = nx.MultiGraph()
            
            # Add bus routes
            bus_schedules = schedules.get("bus_schedules", [])
            for route in bus_schedules:
                stops = route["Stops"]
                for i in range(len(stops) - 1):
                    try:
                        # Get coordinates and calculate travel time
                        start_pos = self.node_positions[stops[i]]
                        end_pos = self.node_positions[stops[i + 1]]
                        distance = ((start_pos[0] - end_pos[0])**2 + 
                                  (start_pos[1] - end_pos[1])**2)**0.5 * 100
                        travel_time = max(5, (distance / 30) * 60)  # Minimum 5 minutes between stops
                    except Exception:
                        travel_time = 15  # Default time if coordinates not found
                    
                    edge_data = {
                        "type": "bus",
                        "route_id": route["Route"],
                        "interval": float(route["Interval (min)"]),
                        "travel_time": float(travel_time),
                        "transfer_points": route["Transfer Points"]
                    }
                    transit_graph.add_edge(stops[i], stops[i + 1], **edge_data)
            
            # Add metro lines
            metro_schedules = schedules.get("metro_schedules", [])
            for line in metro_schedules:
                stations = line["Stations"]
                for i in range(len(stations) - 1):
                    try:
                        # Get coordinates and calculate travel time
                        start_pos = self.node_positions[stations[i]]
                        end_pos = self.node_positions[stations[i + 1]]
                        distance = ((start_pos[0] - end_pos[0])**2 + 
                                  (start_pos[1] - end_pos[1])**2)**0.5 * 100
                        travel_time = max(3, (distance / 60) * 60)  # Minimum 3 minutes between stations
                    except Exception:
                        travel_time = 10  # Default time if coordinates not found
                    
                    edge_data = {
                        "type": "metro",
                        "route_id": line["Line"],
                        "interval": float(line["Interval (min)"]),
                        "travel_time": float(travel_time),
                        "transfer_points": line["Transfer Points"]
                    }
                    transit_graph.add_edge(stations[i], stations[i + 1], **edge_data)
            
            # Find shortest path considering preferences
            def edge_weight(u, v, data):
                base_time = float(data[0]["travel_time"]) + float(data[0]["interval"]) / 2
                if prefer_metro and data[0]["type"] == "bus":
                    base_time *= 1.5  # Penalty for bus if metro is preferred
                if minimize_transfers and u in data[0]["transfer_points"]:
                    base_time += 10  # Transfer time penalty
                return base_time
            
            path = nx.shortest_path(
                transit_graph,
                source,
                destination,
                weight=edge_weight
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
                
                if path[i] in edge_data["transfer_points"]:
                    step["transfer_info"] = "Transfer point - Follow signs to your next line"
                    step["summary"] = f"🔄 Transfer: {step['summary']}"
                
                steps.append(step)
            
            # Create visualization
            m = folium.Map(
                location=[30.0444, 31.2357],  # Cairo coordinates
                zoom_start=12
            )

            # Add Font Awesome
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

            # Track added stops
            added_stops = set()

            # Draw route segments
            for i in range(len(path) - 1):
                edge_data = transit_graph[path[i]][path[i + 1]][0]
                color = "red" if edge_data["type"] == "metro" else "blue"
                
                # Draw route line
                folium.PolyLine(
                    locations=[self.node_positions[path[i]], self.node_positions[path[i + 1]]],
                    color=color,
                    weight=4,
                    opacity=0.8,
                    popup=f"{edge_data['type'].title()} {edge_data['route_id']}"
                ).add_to(m)

                # Add stop markers
                for node_id in [path[i], path[i + 1]]:
                    if node_id not in added_stops:
                        coords = self.node_positions[node_id]
                        
                        # Determine if this is a transfer point
                        is_transfer = False
                        if i > 0 and i < len(path) - 1:
                            prev_type = transit_graph[path[i-1]][path[i]][0]["type"]
                            next_type = transit_graph[path[i]][path[i+1]][0]["type"]
                            is_transfer = prev_type != next_type
                        
                        # Get transport type
                        if i < len(path) - 1:
                            edge_data = transit_graph[node_id][path[i + 1]][0]
                        else:
                            edge_data = transit_graph[path[i-1]][node_id][0]
                        
                        # Choose icon and color
                        icon = metro_icon if edge_data["type"] == "metro" else bus_icon
                        color = "red" if edge_data["type"] == "metro" else "blue"
                        
                        # Create popup
                        popup_content = f"""
                        <div style="width: 200px;">
                            <b>{self.get_location_name(node_id)}</b><br>
                            {edge_data['type'].title()} Stop<br>
                            Line: {edge_data['route_id']}<br>
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
                        
                        folium.CircleMarker(
                            location=coords,
                            radius=10,
                            color=color,
                            fill=True,
                            fill_opacity=0.3,
                            weight=2
                        ).add_to(m)
                        
                        added_stops.add(node_id)

            # Add destination marker
            final_coords = self.node_positions[path[-1]]
            folium.CircleMarker(
                location=final_coords,
                radius=12,
                color="green",
                fill=True,
                fill_opacity=0.5,
                weight=3,
                popup="Destination: " + self.get_location_name(path[-1])
            ).add_to(m)

            # Add legend
            legend_html = """
            <div style="position: fixed; 
                        bottom: 50px; right: 50px; width: 180px; 
                        border:2px solid grey; z-index:9999; font-size:14px;
                        background-color:white;
                        padding: 10px;
                        border-radius: 5px;
                        ">
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
                    <i class="fa fa-circle" style="color:green;"></i> Destination
                </div>
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))
            
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
            raise Exception(f"Error finding transit route: {str(e)}")

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
