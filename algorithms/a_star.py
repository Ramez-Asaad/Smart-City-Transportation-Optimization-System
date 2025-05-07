import pandas as pd
import heapq
import streamlit as st

# A* zx
def load_graph_from_csv(path):
    df = pd.read_csv(path)  # Expected columns: FromID, ToID, Cost
    graph = {}
    for _, row in df.iterrows():
        src = str(row['FromID'])
        dst = str(row['ToID'])
        cost = row['Cost']

        if src not in graph:
            graph[src] = []
        graph[src].append((dst, cost))

        if dst not in graph:
            graph[dst] = []
        graph[dst].append((src, cost))

    return graph

def heuristic(node, goal):
    return 0  # Replace later with coordinates-based distance

def a_star(graph, start, goal):
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path, g_score[goal]

        for neighbor, cost in graph.get(current, []):
            tentative_g = g_score[current] + cost
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None, float('inf')

def find_nearest_hospital(start_id, graph, hospitals):
    best_path = None
    min_cost = float('inf')
    best_hospital = None

    for _, row in hospitals.iterrows():
        hospital_id = str(row['FacilityID'])
        path, cost = a_star(graph, start_id, hospital_id)
        if cost < min_cost:
            min_cost = cost
            best_path = path
            best_hospital = row['Name']

    return best_path, min_cost, best_hospital

# Streamlit frontend integration
def run_emergency_routing(source_id):
    graph = load_graph_from_csv('data/graph.csv')
    facilities_df = pd.read_csv('data/facilities.csv')
    hospitals = facilities_df[facilities_df['Type'].str.lower() == 'hospital']

    path, cost, hospital = find_nearest_hospital(source_id, graph, hospitals)

    if path:
        st.success(f"Nearest hospital: {hospital}")
        st.markdown(f"**Path:** {' → '.join(path)}")
        st.metric("Total Travel Cost / Time", f"{cost:.2f} units")
        st.dataframe(pd.DataFrame({
            "Step": range(1, len(path) + 1),
            "Node": path,
            "Action": ["Start"] + ["Move"] * (len(path) - 2) + ["Arrive"]
        }))
    else:
        st.error("No valid path found to any hospital.")
