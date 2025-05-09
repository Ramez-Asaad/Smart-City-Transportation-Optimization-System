import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional
import json
import os

class TransportationGraphBuilder:
    def __init__(self):
        self.graph = nx.Graph()
        self.node_metadata = {}
        self.edge_metadata = {}
        
    def add_node(self, node_id: str, **attributes):
        """Add a node with its attributes to the graph."""
        self.graph.add_node(node_id)
        self.node_metadata[node_id] = attributes
        
    def add_edge(self, from_id: str, to_id: str, **attributes):
        """Add an edge with its attributes to the graph."""
        self.graph.add_edge(from_id, to_id)
        self.edge_metadata[(from_id, to_id)] = attributes
        
    def load_neighborhoods(self, filepath: str):
        """Load neighborhoods from CSV file."""
        neighborhoods = pd.read_csv(filepath)
        for _, row in neighborhoods.iterrows():
            self.add_node(
                str(row["ID"]),
                type="neighborhood",
                name=row["Name"],
                population=row["Population"],
                coordinates=(row["Y-coordinate"], row["X-coordinate"])
            )
            
    def load_facilities(self, filepath: str):
        """Load facilities from CSV file."""
        facilities = pd.read_csv(filepath)
        for _, row in facilities.iterrows():
            self.add_node(
                str(row["ID"]),
                type="facility",
                name=row["Name"],
                facility_type=row["Type"],
                coordinates=(row["Y-coordinate"], row["X-coordinate"])
            )
            
    def load_roads(self, filepath: str):
        """Load roads from CSV file."""
        roads = pd.read_csv(filepath)
        for _, row in roads.iterrows():
            self.add_edge(
                str(row["FromID"]),
                str(row["ToID"]),
                distance=row["Distance(km)"],
                capacity=row.get("Current Capacity(vehicles/hour)", 0),
                condition=row.get("Condition(1-10)", 10)
            )
            
    def apply_traffic_data(self, filepath: str, time_of_day: Optional[str] = None):
        """Apply traffic data to edges, optionally filtered by time of day."""
        traffic = pd.read_csv(filepath)
        if time_of_day:
            traffic = traffic[traffic["TimeOfDay"] == time_of_day]
            
        for _, row in traffic.iterrows():
            edge = (str(row["FromID"]), str(row["ToID"]))
            if edge in self.edge_metadata:
                self.edge_metadata[edge].update({
                    "traffic_flow": row["TrafficFlow"],
                    "congestion_level": row["CongestionLevel"],
                    "average_speed": row["AverageSpeed"]
                })
                
    def get_node_attribute(self, node_id: str, attribute: str):
        """Get a specific attribute of a node."""
        return self.node_metadata.get(node_id, {}).get(attribute)
        
    def get_edge_attribute(self, from_id: str, to_id: str, attribute: str):
        """Get a specific attribute of an edge."""
        return self.edge_metadata.get((from_id, to_id), {}).get(attribute)
        
    def get_neighbors(self, node_id: str) -> List[str]:
        """Get all neighbors of a node."""
        return list(self.graph.neighbors(node_id))
        
    def get_shortest_path(self, start: str, end: str, weight: str = "distance") -> Tuple[List[str], float]:
        """Find shortest path between two nodes using specified weight attribute."""
        try:
            path = nx.shortest_path(self.graph, start, end, weight=weight)
            length = nx.shortest_path_length(self.graph, start, end, weight=weight)
            return path, length
        except nx.NetworkXNoPath:
            return [], float('inf')
            
    def save_graph(self, filepath: str):
        """Save the graph data to a JSON file."""
        data = {
            "nodes": self.node_metadata,
            "edges": {f"{k[0]}-{k[1]}": v for k, v in self.edge_metadata.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_graph(self, filepath: str):
        """Load the graph data from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.graph = nx.Graph()
        self.node_metadata = data["nodes"]
        self.edge_metadata = {
            tuple(k.split("-")): v 
            for k, v in data["edges"].items()
        }
        
        # Rebuild the graph
        for node in self.node_metadata:
            self.graph.add_node(node)
        for (from_id, to_id) in self.edge_metadata:
            self.graph.add_edge(from_id, to_id)
            
    def get_subgraph(self, node_type: Optional[str] = None) -> nx.Graph:
        """Get a subgraph containing only nodes of a specific type."""
        if node_type:
            nodes = [
                node for node in self.graph.nodes()
                if self.node_metadata[node].get("type") == node_type
            ]
            return self.graph.subgraph(nodes)
        return self.graph
