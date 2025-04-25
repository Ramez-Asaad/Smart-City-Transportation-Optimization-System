import heapq
from collections import defaultdict
from datetime import datetime, timedelta
from collections import defaultdict

# === Scheduling Bus and Metro using DP ===
def generate_bus_schedule(graph, bus_data, start_time="06:00", end_time="22:00"):
    """
    Dynamic programming to optimize bus schedules across the day
    Arguments:
      graph: dictionary of bus stops and connections (frontend will send it)
      bus_data: list of bus routes and buses assigned
    Returns:
      Dictionary of schedules
    """
    schedule = {}
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)

    for bus in bus_data:
        route_id = bus['RouteID']
        buses = bus['BusesAssigned']
        interval = total_minutes // buses
        current_time = start_dt
        route_schedule = []

        while current_time <= end_dt:
            route_schedule.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=interval)

        schedule[route_id] = route_schedule
    return schedule

def generate_metro_schedule(graph, metro_data, start_time="05:00", end_time="00:00", trains_per_line=40):
    """
    Dynamic programming to optimize metro schedules across the day
    Arguments:
      graph: dictionary of metro stations and connections (frontend will send it)
      metro_data: list of metro lines
    Returns:
      Dictionary of schedules
    """
    schedule = {}
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)

    for metro in metro_data:
        line_name = metro['Name']
        interval = total_minutes // trains_per_line
        current_time = start_dt
        line_schedule = []

        while current_time <= end_dt:
            line_schedule.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=interval)

        schedule[line_name] = line_schedule
    return schedule

# === Resource Allocation (Road Maintenance using DP) ===
def resource_allocation_dp(graph, budget):
    """
    Allocate transportation resources efficiently to maintain roads
    Arguments:
      graph: dictionary of roads and properties
      budget: total budget for maintenance
    Returns:
      List of roads to prioritize
    """
    roads = []
    for node in graph:
        for neighbor, properties in graph[node]:
            cost = (10 - properties['Condition']) * 10
            benefit = properties['Capacity'] * properties['Condition']
            roads.append((cost, benefit, node, neighbor))

    n = len(roads)
    dp = [[0 for _ in range(budget + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        cost, benefit, _, _ = roads[i - 1]
        for b in range(budget + 1):
            if b >= cost:
                dp[i][b] = max(dp[i-1][b], dp[i-1][b - int(cost)] + benefit)
            else:
                dp[i][b] = dp[i-1][b]

    chosen = []
    b = budget
    for i in range(n, 0, -1):
        if dp[i][b] != dp[i-1][b]:
            cost, _, from_node, to_node = roads[i - 1]
            chosen.append((from_node, to_node))
            b -= int(cost)

    return chosen


def build_integrated_network(road_graph, bus_data, metro_data):
    """
    Create an integrated transportation network connecting bus stops, metro stations, and roads
    Arguments:
        road_graph: Dictionary of roads {node: [(neighbor, properties)]}
        bus_data: List of bus routes [{RouteID, Stops, BusesAssigned}]
        metro_data: List of metro lines [{Name, Stations, DailyPassengers}]
    Returns:
        integrated_graph: A combined graph with buses, metros, and roads
    """
    integrated_graph = defaultdict(list)

    # Add all road connections
    for node, neighbors in road_graph.items():
        for neighbor, properties in neighbors:
            integrated_graph[node].append((neighbor, properties))

    # Add bus routes (consider bus stops as connections too)
    for bus in bus_data:
        stops = list(map(str.strip, bus['Stops'].split(',')))
        for i in range(len(stops) - 1):
            from_stop = stops[i]
            to_stop = stops[i + 1]
            integrated_graph[from_stop].append((to_stop, {'type': 'bus_route'}))
            integrated_graph[to_stop].append((from_stop, {'type': 'bus_route'}))

    # Add metro lines (connect stations)
    for metro in metro_data:
        stations = list(map(str.strip, metro['Stations'].split(',')))
        for i in range(len(stations) - 1):
            from_station = stations[i]
            to_station = stations[i + 1]
            integrated_graph[from_station].append((to_station, {'type': 'metro_line'}))
            integrated_graph[to_station].append((from_station, {'type': 'metro_line'}))

    return integrated_graph

def find_transfer_points(bus_data, metro_data):
    """
    Analyze transfer points between bus and metro stops
    Arguments:
        bus_data: List of bus routes
        metro_data: List of metro lines
    Returns:
        List of optimal transfer points
    """
    bus_stops = set()
    metro_stations = set()

    # Gather all bus stops
    for bus in bus_data:
        stops = list(map(str.strip, bus['Stops'].split(',')))
        bus_stops.update(stops)

    # Gather all metro stations
    for metro in metro_data:
        stations = list(map(str.strip, metro['Stations'].split(',')))
        metro_stations.update(stations)

    # Find intersections (good transfer points)
    transfer_points = bus_stops.intersection(metro_stations)

    return list(transfer_points)
