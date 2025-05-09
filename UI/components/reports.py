import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

def render_infrastructure_report(neighborhoods: pd.DataFrame, roads: pd.DataFrame, facilities: pd.DataFrame) -> None:
    """Render infrastructure analysis report."""
    st.subheader("Infrastructure Analysis")
    
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    
    # Road Condition Analysis
    avg_condition = roads["Condition(1-10)"].mean()
    poor_roads = len(roads[roads["Condition(1-10)"] < 6])
    col1.metric(
        "Average Road Condition",
        f"{avg_condition:.1f}/10",
        f"{poor_roads} roads need maintenance"
    )
    
    # Network Capacity
    total_capacity = roads["Current Capacity(vehicles/hour)"].sum()
    avg_capacity = roads["Current Capacity(vehicles/hour)"].mean()
    col2.metric(
        "Total Network Capacity",
        f"{total_capacity:,.0f} vehicles/hour",
        f"Avg: {avg_capacity:,.0f} per road"
    )
    
    # Population Coverage
    total_pop = neighborhoods["Population"].sum()
    col3.metric(
        "Total Population Served",
        f"{total_pop:,.0f}",
        f"{len(facilities)} service points"
    )
    
    # Road Conditions Distribution
    st.subheader("Road Infrastructure Quality")
    col1, col2 = st.columns(2)
    
    with col1:
        # Road Conditions Histogram
        fig_condition = px.histogram(
            roads,
            x="Condition(1-10)",
            title="Road Conditions Distribution",
            labels={"Condition(1-10)": "Condition Score", "count": "Number of Roads"},
            color_discrete_sequence=['#1f77b4']
        )
        fig_condition.update_layout(bargap=0.2)
        st.plotly_chart(fig_condition, use_container_width=True)
    
    with col2:
        # Road Capacity vs Condition Scatter
        fig_scatter = px.scatter(
            roads,
            x="Condition(1-10)",
            y="Current Capacity(vehicles/hour)",
            title="Road Capacity vs Condition",
            labels={
                "Condition(1-10)": "Road Condition",
                "Current Capacity(vehicles/hour)": "Capacity (vehicles/hour)"
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

def render_population_report(neighborhoods: pd.DataFrame) -> None:
    """Render population distribution analysis."""
    st.subheader("Population Distribution Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Population by Area Type
        fig_pop_type = px.pie(
            neighborhoods,
            values="Population",
            names="Type",
            title="Population Distribution by Area Type"
        )
        st.plotly_chart(fig_pop_type, use_container_width=True)
    
    with col2:
        # Top 10 Most Populated Areas
        top_areas = neighborhoods.nlargest(10, "Population")
        fig_top = px.bar(
            top_areas,
            x="Name",
            y="Population",
            title="Top 10 Most Populated Areas",
            labels={"Name": "Area", "Population": "Population"}
        )
        fig_top.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_top, use_container_width=True)
    
    # Population Density Map
    st.subheader("Population Density Map")
    fig_density = px.scatter_mapbox(
        neighborhoods,
        lat="Y-coordinate",
        lon="X-coordinate",
        size="Population",
        color="Type",
        hover_name="Name",
        hover_data=["Population"],
        title="Population Density Distribution",
        zoom=10,
        mapbox_style="carto-positron"
    )
    st.plotly_chart(fig_density, use_container_width=True)

def render_connectivity_report(roads: pd.DataFrame, neighborhoods: pd.DataFrame) -> None:
    """Render network connectivity analysis."""
    st.subheader("Network Connectivity Analysis")
    
    # Create connectivity metrics
    # Convert FromID to string type before grouping
    roads_copy = roads.copy()
    roads_copy["FromID"] = roads_copy["FromID"].astype(str)
    connectivity_data = pd.DataFrame(roads_copy.groupby("FromID").size()).reset_index()
    connectivity_data.columns = ["Area", "Connections"]
    
    # Convert ID to string in neighborhoods data for consistent merging
    neighborhoods_copy = neighborhoods.copy()
    neighborhoods_copy["ID"] = neighborhoods_copy["ID"].astype(str)
    
    # Merge with neighborhood names
    connectivity_data = connectivity_data.merge(
        neighborhoods_copy[["ID", "Name"]],
        left_on="Area",
        right_on="ID",
        how="left"
    )
    
    # Calculate summary statistics
    avg_connections = connectivity_data["Connections"].mean()
    max_connections = connectivity_data["Connections"].max()
    min_connections = connectivity_data["Connections"].min()
    
    # Display key metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Average Connections", f"{avg_connections:.1f}")
    col2.metric("Most Connected", f"{max_connections}")
    col3.metric("Least Connected", f"{min_connections}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Network Connectivity Distribution
        fig_connect = px.histogram(
            connectivity_data,
            x="Connections",
            title="Network Connectivity Distribution",
            labels={"Connections": "Number of Connections", "count": "Number of Areas"},
            color_discrete_sequence=['#2ecc71']
        )
        fig_connect.update_layout(
            bargap=0.2,
            showlegend=False,
            xaxis_title="Number of Connections",
            yaxis_title="Number of Areas"
        )
        st.plotly_chart(fig_connect, use_container_width=True)
    
    with col2:
        # Top Connected Areas
        top_connected = connectivity_data.nlargest(10, "Connections")
        fig_top = px.bar(
            top_connected,
            x="Name",
            y="Connections",
            title="Top 10 Most Connected Areas",
            labels={"Name": "Area", "Connections": "Number of Connections"},
            color="Connections",
            color_continuous_scale="Viridis"
        )
        fig_top.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            xaxis_title="Area",
            yaxis_title="Number of Connections"
        )
        st.plotly_chart(fig_top, use_container_width=True)
    
    # Add connectivity map
    st.subheader("Network Connectivity Map")
    
    # Create a function to safely get coordinates
    def get_coordinate(row, coord_type):
        matching_area = neighborhoods_copy[neighborhoods_copy["ID"] == row["Area"]]
        if matching_area.empty:
            return None
        return float(matching_area[f"{coord_type}-coordinate"].iloc[0])
    
    # Add coordinates to connectivity data
    connectivity_data["latitude"] = connectivity_data.apply(lambda x: get_coordinate(x, "Y"), axis=1)
    connectivity_data["longitude"] = connectivity_data.apply(lambda x: get_coordinate(x, "X"), axis=1)
    
    # Filter out rows with missing coordinates
    valid_data = connectivity_data.dropna(subset=["latitude", "longitude"])
    
    if len(valid_data) > 0:
        fig_map = px.scatter_mapbox(
            valid_data,
            lat="latitude",
            lon="longitude",
            size="Connections",
            color="Connections",
            hover_name="Name",
            hover_data=["Connections"],
            title="Area Connectivity Distribution",
            color_continuous_scale="Viridis",
            zoom=10,
            mapbox_style="carto-positron"
        )
        fig_map.update_layout(
            mapbox=dict(
                center=dict(
                    lat=30.0444,
                    lon=31.2357
                )
            )
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("No valid coordinate data available for the connectivity map.")

def render_facility_report(facilities: pd.DataFrame, neighborhoods: pd.DataFrame) -> None:
    """Render facility distribution analysis."""
    st.subheader("Facility Distribution Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Facility Types Distribution
        fig_types = px.pie(
            facilities,
            names="Type",
            title="Distribution of Facility Types"
        )
        st.plotly_chart(fig_types, use_container_width=True)
    
    with col2:
        # Facilities per Area Type
        facility_counts = pd.DataFrame(facilities.groupby("Type").size()).reset_index()
        facility_counts.columns = ["Type", "Count"]
        fig_area = px.bar(
            facility_counts,
            x="Type",
            y="Count",
            title="Number of Facilities by Type",
            labels={"Type": "Facility Type", "Count": "Number of Facilities"}
        )
        fig_area.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_area, use_container_width=True)
    
    # Facility Location Map
    st.subheader("Facility Locations")
    fig_locations = px.scatter_mapbox(
        facilities,
        lat="Y-coordinate",
        lon="X-coordinate",
        color="Type",
        hover_name="Name",
        title="Facility Locations Map",
        zoom=10,
        mapbox_style="carto-positron"
    )
    st.plotly_chart(fig_locations, use_container_width=True)

def render_reports(neighborhoods: pd.DataFrame, roads: pd.DataFrame, facilities: pd.DataFrame) -> None:
    """Render the main reports section with all analyses."""
    st.title("Network Analysis Reports")
    
    # Create tabs for different report types
    report_tabs = st.tabs([
        "Infrastructure",
        "Population",
        "Connectivity",
        "Facilities"
    ])
    
    # Infrastructure Report
    with report_tabs[0]:
        render_infrastructure_report(neighborhoods, roads, facilities)
    
    # Population Report
    with report_tabs[1]:
        render_population_report(neighborhoods)
    
    # Connectivity Report
    with report_tabs[2]:
        render_connectivity_report(roads, neighborhoods)
    
    # Facilities Report
    with report_tabs[3]:
        render_facility_report(facilities, neighborhoods) 