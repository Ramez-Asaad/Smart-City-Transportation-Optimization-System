import pandas as pd
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st
import json
import folium
from streamlit_folium import st_folium

class PublicTransitOptimizer:
    def __init__(self, bus_routes, metro_lines, demand_data):
        self.bus_routes = bus_routes
        self.metro_lines = metro_lines
        self.demand_data = demand_data
        self.network = nx.Graph()
        self.transfer_points = set()
        
    def build_integrated_network(self):
        """Builds a multimodal transportation network combining bus and metro systems"""
        # Add bus routes to network
        for _, route in self.bus_routes.iterrows():
            stops = self._parse_stops(route['Stops'])
            for i in range(len(stops)-1):
                self.network.add_edge(stops[i], stops[i+1], 
                                     type='bus', 
                                     route=route['RouteID'],
                                     capacity=route.get('DailyPassengers', 10000))
        
        # Add metro lines to network
        for _, line in self.metro_lines.iterrows():
            stations = self._parse_stops(line['Stations'])
            for i in range(len(stations)-1):
                self.network.add_edge(stations[i], stations[i+1], 
                                    type='metro', 
                                    route=line['LineID'],
                                    capacity=line.get('DailyPassengers', 500000))
        
        # Identify transfer points
        self._identify_transfer_points()
        
    def _parse_stops(self, stops):
        """Helper to parse stops whether they're strings or lists"""
        if isinstance(stops, str):
            return [s.strip() for s in stops.split(',')]
        return stops
    
    def _identify_transfer_points(self):
        """Finds all nodes where bus and metro systems intersect"""
        bus_nodes = set()
        metro_nodes = set()
        
        for u, v, data in self.network.edges(data=True):
            if data['type'] == 'bus':
                bus_nodes.update([u, v])
            elif data['type'] == 'metro':
                metro_nodes.update([u, v])
        
        self.transfer_points = bus_nodes.intersection(metro_nodes)
    
    def optimize_transfer_points(self):
        """Optimizes transfer points based on demand and connectivity"""
        transfer_scores = []
        
        for point in self.transfer_points:
            # Calculate connectivity score
            degree = self.network.degree(point)
            
            # Calculate demand score
            demand_in = sum(self.demand_data.get((src, point), 0) for src in self.network.nodes())
            demand_out = sum(self.demand_data.get((point, dest), 0) for dest in self.network.nodes())
            
            # Calculate transfer efficiency (connections between different modes)
            transfer_efficiency = 0
            neighbors = list(self.network.neighbors(point))
            for i in range(len(neighbors)):
                for j in range(i+1, len(neighbors)):
                    if self.network[point][neighbors[i]]['type'] != self.network[point][neighbors[j]]['type']:
                        transfer_efficiency += 1
            
            score = 0.4*(degree) + 0.3*(demand_in + demand_out)/1000 + 0.3*transfer_efficiency
            transfer_scores.append((point, score))
        
        # Sort by score descending
        return sorted(transfer_scores, key=lambda x: x[1], reverse=True)
    
    def optimize_resource_allocation(self, total_buses=200, total_trains=30):
        """Optimizes vehicle allocation using modified DP approach"""
        # Precompute route values
        bus_values = self._compute_route_values('bus')
        metro_values = self._compute_route_values('metro')
        
        # Optimize bus allocation
        bus_allocation = self._dp_allocate(
            values=bus_values,
            max_units=total_buses,
            min_units=5,  # Minimum buses per route
            max_per_route=25  # Maximum buses per route
        )
        
        # Optimize metro allocation
        metro_allocation = self._dp_allocate(
            values=metro_values,
            max_units=total_trains,
            min_units=2,  # Minimum trains per line
            max_per_route=10  # Maximum trains per line
        )
        
        return bus_allocation, metro_allocation
    
    def _compute_route_values(self, transport_type):
        """Computes value scores for each route based on demand and connectivity"""
        routes = self.bus_routes if transport_type == 'bus' else self.metro_lines
        values = []
        
        for _, route in routes.iterrows():
            stops = self._parse_stops(route['Stops'] if transport_type == 'bus' else route['Stations'])
            
            # Base value from existing passengers
            value = route.get('DailyPassengers', 10000 if transport_type == 'bus' else 500000)
            
            # Add value from demand matrix
            for i in range(len(stops)):
                for j in range(i+1, len(stops)):
                    value += self.demand_data.get((stops[i], stops[j]), 0) // 2
            
            # Add transfer point bonus
            transfer_bonus = sum(10000 for stop in stops if stop in self.transfer_points)
            value += transfer_bonus
            
            values.append((route['RouteID'] if transport_type == 'bus' else route['LineID'], value))
        
        return values
    
def _dp_allocate(self, values, max_units, min_units, max_per_route):
    """Simplified DP allocation with constraints"""
    n = len(values)
    # dp[i][u] = max benefit for first i routes using u units
    dp = [[0] * (max_units + 1) for _ in range(n + 1)]
    allocation = {}

    # Build DP table
    for i in range(1, n + 1):
        route_id, value = values[i-1]
        for u in range(max_units + 1):
            # Try all possible allocations for this route
            max_possible = min(u, max_per_route)
            for alloc in range(min_units, max_possible + 1):
                current_value = value * min(alloc, 10)  # Diminishing returns
                if dp[i-1][u-alloc] + current_value > dp[i][u]:
                    dp[i][u] = dp[i-1][u-alloc] + current_value

    # Backtrack to find allocation
    remaining = max_units
    for i in range(n, 0, -1):
        route_id, value = values[i-1]
        # Find the allocation that gave us this DP value
        for alloc in range(min(remaining, max_per_route), min_units-1, -1):
            if dp[i][remaining] == dp[i-1][remaining-alloc] + value * min(alloc, 10):
                allocation[route_id] = alloc
                remaining -= alloc
                break
        else:  # No allocation found (shouldn't happen if constraints are valid)
            allocation[route_id] = min_units
            remaining -= min_units

    return allocation

    def generate_schedules(self, bus_allocation, metro_allocation):
        """Generates optimized schedules with transfer information"""
        bus_schedules = []
        metro_schedules = []
        
        # Generate bus schedules
        for _, route in self.bus_routes.iterrows():
            route_id = route['RouteID']
            assigned = bus_allocation.get(route_id, 5)
            stops = self._parse_stops(route['Stops'])
            
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
            stations = self._parse_stops(line['Stations'])
            
            # Find transfer points on this line
            transfers = [station for station in stations if station in self.transfer_points]
            
            metro_schedules.append({
                'Line': line_id,
                'Stations': stations,
                'Assigned Trains': assigned,
                'Interval (min)': max(3, 1080 // assigned),  # 18 operating hours
                'Transfer Points': transfers,
                'Daily Capacity': assigned * 500 * 20  # 500 passengers, 20 trips
            })
        
        return bus_schedules, metro_schedules
    
    def visualize_network_map(self):
        """Creates an interactive Folium map visualization"""
        # Create base map
        m = folium.Map(location=[30.0444, 31.2357], zoom_start=12)  # Cairo coordinates
        
        # Add bus routes
        for _, route in self.bus_routes.iterrows():
            stops = self._parse_stops(route['Stops'])
            for i in range(len(stops)-1):
                folium.PolyLine(
                    locations=[[i+30.0, i+31.0] for i in range(len(stops))],  # Simplified coordinates
                    color='blue',
                    weight=2,
                    opacity=0.7,
                    popup=f"Bus Route {route['RouteID']}"
                ).add_to(m)
        
        # Add metro lines
        for _, line in self.metro_lines.iterrows():
            stations = self._parse_stops(line['Stations'])
            for i in range(len(stations)-1):
                folium.PolyLine(
                    locations=[[i+30.0, i+30.9] for i in range(len(stations))],  # Simplified coordinates
                    color='red',
                    weight=4,
                    opacity=0.9,
                    popup=f"Metro Line {line['LineID']}"
                ).add_to(m)
        
        # Add transfer points
        for point in self.transfer_points:
            folium.CircleMarker(
                location=[30.0444, 31.2357],  # Simplified coordinate
                radius=5,
                color='green',
                fill=True,
                fill_color='green',
                popup=f"Transfer Point: {point}"
            ).add_to(m)
        
        return m._repr_html_()

def run_public_transit_optimization():
    """Main function to run the optimization and return results for Streamlit"""
    # Load sample data (in a real app, this would come from file uploads)
    bus_routes = pd.DataFrame({
        'RouteID': ['B1', 'B2', 'B3'],
        'Stops': ['A1,B1,C1,D1', 'A2,B2,C2,D2', 'A3,B3,C3,D3'],
        'DailyPassengers': [8000, 12000, 5000]
    })
    
    metro_lines = pd.DataFrame({
        'LineID': ['M1', 'M2'],
        'Stations': ['A1,B1,C1', 'A2,B2,C2'],
        'DailyPassengers': [300000, 250000]
    })
    
    demand_data = pd.DataFrame({
        'FromID': ['A1', 'B1', 'C1', 'A2', 'B2'],
        'ToID': ['B1', 'C1', 'D1', 'B2', 'C2'],
        'DailyPassengers': [500, 300, 200, 400, 350]
    })
    
    # Clean demand data
    demand_dict = defaultdict(int)
    for _, row in demand_data.iterrows():
        demand_dict[(str(row['FromID']), str(row['ToID']))] = row['DailyPassengers']
    
    # Create optimizer instance
    optimizer = PublicTransitOptimizer(bus_routes, metro_lines, demand_dict)
    
    # Build integrated network
    optimizer.build_integrated_network()
    
    # Optimize transfer points
    transfer_points = optimizer.optimize_transfer_points()
    
    # Optimize resource allocation
    bus_alloc, metro_alloc = optimizer.optimize_resource_allocation()
    
    # Generate schedules
    bus_schedules, metro_schedules = optimizer.generate_schedules(bus_alloc, metro_alloc)
    
    # Create visualization
    map_html = optimizer.visualize_network_map()
    
    # Prepare results for Streamlit
    results = {
        'transfer_points': transfer_points,
        'bus_allocation': bus_alloc,
        'metro_allocation': metro_alloc,
        'bus_schedules': bus_schedules,
        'metro_schedules': metro_schedules,
        'network_visualization': map_html
    }
    
    return results

# Streamlit integration
def show_public_transit_analysis():
    st.title("Public Transit Optimization")
    
    with st.form("transit_optimization"):
        st.subheader("Input Parameters")
        col1, col2 = st.columns(2)
        total_buses = col1.number_input("Total Available Buses", min_value=50, max_value=500, value=200)
        total_trains = col2.number_input("Total Available Trains", min_value=10, max_value=100, value=30)
        
        submitted = st.form_submit_button("Run Optimization")
    
    if submitted:
        with st.spinner("Optimizing public transit network..."):
            results = run_public_transit_optimization()
            
            st.success("Optimization complete!")
            
            # Display visualization
            st.subheader("Network Visualization")
            st.components.v1.html(results['network_visualization'], height=500)
            
            # Display transfer points
            st.subheader("Optimized Transfer Points (Ranked)")
            transfer_df = pd.DataFrame(results['transfer_points'], columns=['Transfer Point', 'Score'])
            st.dataframe(transfer_df.sort_values('Score', ascending=False))
            
            # Display resource allocation
            st.subheader("Bus Allocation")
            bus_df = pd.DataFrame(list(results['bus_allocation'].items()), columns=['Route', 'Buses Allocated'])
            st.bar_chart(bus_df.set_index('Route'))
            
            st.subheader("Metro Allocation")
            metro_df = pd.DataFrame(list(results['metro_allocation'].items()), columns=['Line', 'Trains Allocated'])
            st.bar_chart(metro_df.set_index('Line'))
            
            # Display schedules
            st.subheader("Optimized Bus Schedules")
            bus_sched_df = pd.DataFrame(results['bus_schedules'])
            st.dataframe(bus_sched_df)
            
            st.subheader("Optimized Metro Schedules")
            metro_sched_df = pd.DataFrame(results['metro_schedules'])
            st.dataframe(metro_sched_df)

# Add to your existing Streamlit navigation
if menu == "Algorithms":
    st.title("Algorithm Selection")
    
    algo_type = st.selectbox("Choose Algorithm", ["Dijkstra", "A*", "Greedy", "DP", "Public Transit Optimization"])
    
    if algo_type == "Public Transit Optimization":
        show_public_transit_analysis()
    else:
        # Your existing algorithm selection code
        st.text_input("Source Point", "e.g., A1")
        st.text_input("Destination Point", "e.g., D4")
        st.selectbox("Time of Day", ["Morning Rush", "Evening", "Night"])
        st.checkbox("Simulate Road Closure")
        st.checkbox("Enable Emergency Mode")

        if st.button("Run Algorithm"):
            st.success("Algorithm executed!")

            col1, col2, col3 = st.columns(3)
            col1.metric("Travel Time", "15 min")
            col2.metric("Cost", "EGP 25")
            col3.metric("Coverage", "98%")

            st.subheader("Network Visualization")
            st.info("[Mock Graph Placeholder]")

            st.subheader("Result Table")
            st.table(pd.DataFrame({
                "Step": [1, 2, 3, 4],
                "Node": ["A1", "B2", "C3", "D4"],
                "Action": ["Start", "Move", "Move", "Arrive"],
                "Cost": [0, 5, 10, 15]
            }))