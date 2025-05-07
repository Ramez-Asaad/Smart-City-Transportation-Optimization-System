import pandas as pd
from collections import defaultdict

# Load data
bus_routes = pd.read_json('data/bus_routes.json')
metro_lines = pd.read_json('data/metro_lines.json')
public_transportation_demand = pd.read_csv('data/public_transportation_demand.csv')
public_transportation_demand.columns = public_transportation_demand.columns.str.strip()
traffic_flow_patterns = pd.read_csv('data/traffic.csv')

# =======================
# Demand Matrix Builder
# =======================
def build_demand_matrix(demand_df):
    """
    Converts the transportation demand CSV into a dictionary for quick lookup.
    Returns a dictionary with keys as (from_id, to_id) and values as daily passengers.
    """
    demand_matrix = {}
    for _, row in demand_df.iterrows():
        demand_matrix[(str(row['FromID']), str(row['ToID']))] = row['DailyPassengers']
    return demand_matrix

# =======================
# Dynamic Programming Optimizer
# =======================
def optimize_schedule_dp(routes, demand_matrix, max_units, transport_type):
    """
    Optimizes vehicle allocation across routes using dynamic programming.
    
    Args:
        routes: List of dictionaries representing bus or metro lines.
        demand_matrix: Dict mapping (from_id, to_id) to passenger counts.
        max_units: Maximum number of buses or trains to allocate.
        transport_type: 'bus' or 'metro'

    Returns:
        allocation: Dict mapping route/line ID to allocated units.
    """
    n = len(routes)
    dp = [[0] * (max_units + 1) for _ in range(n + 1)]
    route_ids = [r['RouteID'] if transport_type == "bus" else r['LineID'] for r in routes]

    def route_demand(route):
        stops = list(map(str.strip, route['Stops'].split(','))) if transport_type == 'bus' else list(map(str.strip, route['Stations'].split(',')))
        total = 0
        for i in range(len(stops)):
            for j in range(i + 1, len(stops)):
                total += demand_matrix.get((stops[i], stops[j]), 0)
        return total

    route_demand_list = [route_demand(r) for r in routes]

    for i in range(1, n + 1):
        for u in range(max_units + 1):
            for alloc in range(u + 1):
                benefit = route_demand_list[i - 1] * alloc
                dp[i][u] = max(dp[i][u], dp[i - 1][u - alloc] + benefit)

    allocation = dict()
    units_left = max_units
    for i in range(n, 0, -1):
        for alloc in range(units_left + 1):
            if dp[i][units_left] == dp[i - 1][units_left - alloc] + route_demand_list[i - 1] * alloc:
                allocation[route_ids[i - 1]] = alloc
                units_left -= alloc
                break

    return allocation

# =======================
# Schedule Generators
# =======================
def generate_optimized_schedule(routes, allocation, transport_type):
    """
    Creates readable schedules using optimal allocations.

    Args:
        routes: DataFrame of bus or metro data.
        allocation: Dict of assigned units.
        transport_type: 'bus' or 'metro'

    Returns:
        schedule: List of dicts summarizing schedule per route
    """
    schedule = []
    for _, row in routes.iterrows():
        route_id = row['RouteID'] if transport_type == 'bus' else row['LineID']
        name = f"Bus Route" if transport_type == 'bus' else "Metro Line"
        stops_key = 'Stops' if transport_type == 'bus' else 'Stations'
        assigned_units = allocation.get(route_id, 1)
        interval = 1440 // assigned_units if assigned_units else 0

        schedule.append({
            name: route_id,
            'Stops/Stations': row[stops_key],
            'Assigned Units': assigned_units,
            'Estimated Interval (min)': interval
        })
    return schedule

# =======================
# Integrated Network Builder
# =======================
def build_integrated_network(bus_data, metro_data):
    """
    Creates an integrated network graph combining bus routes and metro lines.
    Helps visualize and connect transportation options.
    """
    network = defaultdict(list)

    for bus in bus_data:
        stops = list(map(str.strip, bus['Stops'].split(',')))
        for i in range(len(stops) - 1):
            network[stops[i]].append((stops[i+1], 'bus'))
            network[stops[i+1]].append((stops[i], 'bus'))

    for metro in metro_data:
        stations = list(map(str.strip, metro['Stations'].split(',')))
        for i in range(len(stations) - 1):
            network[stations[i]].append((stations[i+1], 'metro'))
            network[stations[i+1]].append((stations[i], 'metro'))

    return network

# =======================
# Transfer Point Analyzer
# =======================
def find_transfer_points(bus_data, metro_data):
    """
    Finds optimal transfer points where bus stops intersect with metro stations.
    These points are key for designing efficient multimodal transportation.
    """
    bus_stops = set()
    metro_stations = set()

    for bus in bus_data:
        bus_stops.update(map(str.strip, bus['Stops'].split(',')))
    for metro in metro_data:
        metro_stations.update(map(str.strip, metro['Stations'].split(',')))

    transfer_points = bus_stops.intersection(metro_stations)
    return list(transfer_points)

# =======================
# Main Execution
# =======================

# Build demand
bus_demand_matrix = build_demand_matrix(public_transportation_demand)
metro_demand_matrix = bus_demand_matrix  # Same dataset used for metro as well

# Optimize allocations
optimized_bus_alloc = optimize_schedule_dp(bus_routes.to_dict('records'), bus_demand_matrix, max_units=200, transport_type="bus")
optimized_metro_alloc = optimize_schedule_dp(metro_lines.to_dict('records'), metro_demand_matrix, max_units=30, transport_type="metro")

# Generate schedules
bus_schedule = generate_optimized_schedule(bus_routes, optimized_bus_alloc, 'bus')
metro_schedule = generate_optimized_schedule(metro_lines, optimized_metro_alloc, 'metro')

# Display schedules
print("\nOptimized Bus Schedule:")
for bus in bus_schedule:
    print(bus)

print("\nOptimized Metro Schedule:")
for metro in metro_schedule:
    print(metro)

# Build and display integrated network
integrated_network = build_integrated_network(bus_routes.to_dict('records'), metro_lines.to_dict('records'))
print("\nIntegrated Network Nodes:")
for node, edges in integrated_network.items():
    print(f"{node}: {edges}")

# Analyze and display transfer points
transfer_points = find_transfer_points(bus_routes.to_dict('records'), metro_lines.to_dict('records'))
print("\nOptimal Transfer Points:")
print(transfer_points)