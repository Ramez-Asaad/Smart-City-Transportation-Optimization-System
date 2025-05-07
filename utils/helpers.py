import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os

#
def load_data():
    neighborhoods = pd.DataFrame({
        "ID": [1, 2, 3],
        "Name": ["A", "B", "C"],
        "Y-coordinate": [30.1, 30.2, 30.3],
        "X-coordinate": [31.1, 31.2, 31.3],
        "Population": [1000, 2000, 3000]
    })
    roads = pd.DataFrame({
        "FromID": [1, 2],
        "ToID": [2, 3],
        "Distance(km)": [5, 10]
    })
    facilities = pd.DataFrame({
        "ID": [1, 2],
        "Name": ["Hospital", "School"],
        "Type": ["Health", "Education"],
        "Y-coordinate": [30.15, 30.25],
        "X-coordinate": [31.15, 31.25]
    })
    return neighborhoods, roads, facilities