# This script loads various datasets related to Cairo's neighborhoods, roads, traffic, metro lines, and bus routes.
import csv
import json

def load_neighborhoods(path='data/neighborhoods.csv'):
    with open(path, newline='') as csvfile:
        return list(csv.DictReader(csvfile))

def load_roads(path='data/roads.csv'):
    with open(path, newline='') as csvfile:
        return list(csv.DictReader(csvfile))

def load_traffic(path='data/traffic.csv'):
    with open(path, newline='') as csvfile:
        return list(csv.DictReader(csvfile))

def load_metro_lines(path='data/metro_lines.json'):
    with open(path) as f:
        return json.load(f)

def load_bus_routes(path='data/bus_routes.json'):
    with open(path) as f:
        return json.load(f)
