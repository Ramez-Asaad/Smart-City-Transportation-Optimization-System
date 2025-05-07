import pandas as pd
import streamlit as st
import folium
import networkx as nx
import os

#
def load_data():
    # Load the data from CSV files
    neighborhoods = pd.read_csv(os.path.join("data", "neighborhoods.csv"))
    roads = pd.read_csv(os.path.join("data", "roads.csv"))
    facilities = pd.read_csv(os.path.join("data", "facilities.csv"))

    return neighborhoods, roads, facilities