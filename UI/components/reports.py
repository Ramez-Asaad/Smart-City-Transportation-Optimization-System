import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
import folium

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

def render_transit_report(controller) -> None:
    """Render comprehensive public transit system report with interactive visualizations."""
    st.subheader("Public Transit System Analytics")
    
    # Get data from controller
    bus_routes = controller.bus_routes
    metro_lines = controller.metro_lines
    transfer_points = controller.transfer_points
    
    if bus_routes.empty or metro_lines.empty:
        st.warning("No transit data available. Please ensure bus routes and metro lines data is loaded.")
        return
    
    # Calculate high-level transit metrics
    bus_stops = set()
    metro_stops = set()
    
    # Process bus data
    for _, route in bus_routes.iterrows():
        stops = [stop.strip() for stop in route['Stops'].split(',')]
        bus_stops.update(stops)
    
    # Process metro data
    for _, line in metro_lines.iterrows():
        stations = [station.strip() for station in line['Stations'].split(',')]
        metro_stops.update(stations)
    
    # Calculate metrics
    total_transit_stops = len(bus_stops.union(metro_stops))
    total_interchanges = len(transfer_points)
    
    # Calculate total route kilometers - approximate using node positions
    total_bus_km = 0
    bus_daily_capacity = 0
    for _, route in bus_routes.iterrows():
        stops = [stop.strip() for stop in route['Stops'].split(',')]
        for i in range(len(stops) - 1):
            if stops[i] in controller.node_positions and stops[i+1] in controller.node_positions:
                pos1 = controller.node_positions[stops[i]]
                pos2 = controller.node_positions[stops[i+1]]
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5 * 100
                total_bus_km += distance
        # Each bus carries ~50 passengers and makes ~20 trips
        bus_daily_capacity += int(route.get('DailyPassengers', 5000))
    
    total_metro_km = 0
    metro_daily_capacity = 0
    for _, line in metro_lines.iterrows():
        stations = [station.strip() for station in line['Stations'].split(',')]
        for i in range(len(stations) - 1):
            if stations[i] in controller.node_positions and stations[i+1] in controller.node_positions:
                pos1 = controller.node_positions[stations[i]]
                pos2 = controller.node_positions[stations[i+1]]
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5 * 100
                total_metro_km += distance
        # Each metro carries ~500 passengers and makes ~20 trips daily
        metro_daily_capacity += int(line.get('DailyPassengers', 10000))
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "Transit Network Coverage",
        f"{total_transit_stops} stops",
        f"{len(bus_routes)} bus routes, {len(metro_lines)} metro lines"
    )
    
    col2.metric(
        "Transfer Points",
        f"{total_interchanges}",
        "Interchange stations"
    )
    
    col3.metric(
        "Total Network Length",
        f"{total_bus_km + total_metro_km:.1f} km",
        f"Bus: {total_bus_km:.1f} km, Metro: {total_metro_km:.1f} km"
    )
    
    col4.metric(
        "Daily Passenger Capacity",
        f"{(bus_daily_capacity + metro_daily_capacity):,}",
        f"{((bus_daily_capacity + metro_daily_capacity) * 365 / 1000000):.1f}M yearly"
    )
    
    # Create transit network diagram
    st.subheader("Transit Network Visualization")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create transit network map
        transit_map = create_transit_network_map(controller)
        st.components.v1.html(transit_map, height=500)
    
    with col2:
        # Transit mode split
        mode_data = pd.DataFrame([
            {"Mode": "Bus", "Stops": len(bus_stops), "Routes": len(bus_routes), "Distance": total_bus_km, "Capacity": bus_daily_capacity},
            {"Mode": "Metro", "Stops": len(metro_stops), "Routes": len(metro_lines), "Distance": total_metro_km, "Capacity": metro_daily_capacity}
        ])
        
        fig = px.pie(
            mode_data,
            values="Capacity",
            names="Mode",
            title="Transit Capacity by Mode",
            color="Mode",
            color_discrete_map={"Bus": "#C08A38", "Metro": "#8C6D3F"},
            hole=0.4
        )
        
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=0),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display route density stats
        st.info(f"**Network Density**: {total_transit_stops / (total_bus_km + total_metro_km):.2f} stops per km")
        
        # User sentiment analysis (simulated)
        st.markdown("### User Satisfaction")
        
        satisfaction_data = {
            "Very Satisfied": 42,
            "Satisfied": 38,
            "Neutral": 12,
            "Dissatisfied": 6,
            "Very Dissatisfied": 2
        }
        
        # Create a satisfaction gauge
        satisfaction_score = sum([
            5 * satisfaction_data["Very Satisfied"],
            4 * satisfaction_data["Satisfied"],
            3 * satisfaction_data["Neutral"],
            2 * satisfaction_data["Dissatisfied"],
            1 * satisfaction_data["Very Dissatisfied"]
        ]) / sum(satisfaction_data.values()) / 5 * 100
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=satisfaction_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "User Satisfaction", 'font': {'size': 16}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': "#C08A38"},
                'steps': [
                    {'range': [0, 20], 'color': '#ffcccb'},
                    {'range': [20, 40], 'color': '#ffb347'},
                    {'range': [40, 60], 'color': '#FFFBF0'},
                    {'range': [60, 80], 'color': '#E5D3A9'},
                    {'range': [80, 100], 'color': '#8C6D3F'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 3},
                    'thickness': 0.75,
                    'value': satisfaction_score
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)

def create_transit_network_map(controller) -> str:
    """Create a transit network map visualization."""
    # Create a map centered on Cairo
    m = folium.Map(
        location=[30.0444, 31.2357],
        zoom_start=11,
        tiles="cartodbpositron"
    )
    
    # Add Font Awesome for icons
    m.get_root().header.add_child(folium.Element("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    """))
    
    # Generate colors for bus routes and metro lines
    bus_colors = {route['RouteID']: f"#{hash(route['RouteID']) % 0xffffff:06x}" 
                  for _, route in controller.bus_routes.iterrows()}
    
    metro_colors = {
        'M1': '#E74C3C',  # Red
        'M2': '#3498DB',  # Blue
        'M3': '#2ECC71',  # Green
    }
    
    # Add metro lines (first as base layer)
    for _, line in controller.metro_lines.iterrows():
        line_id = line['LineID']
        color = metro_colors.get(line_id, '#000000')
        stations = [station.strip() for station in line['Stations'].split(',')]
        
        # Draw the line segments
        for i in range(len(stations) - 1):
            if stations[i] in controller.node_positions and stations[i+1] in controller.node_positions:
                # Get coordinates
                pos1 = controller.node_positions[stations[i]]
                pos2 = controller.node_positions[stations[i+1]]
                
                # Calculate distance for popup
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5 * 100
                
                # Draw the metro line
                folium.PolyLine(
                    locations=[pos1, pos2],
                    color=color,
                    weight=5,
                    opacity=0.7,
                    popup=f"Metro Line {line_id}: {distance:.1f} km"
                ).add_to(m)
    
    # Add bus routes on top
    for _, route in controller.bus_routes.iterrows():
        route_id = route['RouteID']
        color = bus_colors.get(route_id, '#C08A38')
        stops = [stop.strip() for stop in route['Stops'].split(',')]
        
        # Draw the line segments
        for i in range(len(stops) - 1):
            if stops[i] in controller.node_positions and stops[i+1] in controller.node_positions:
                # Get coordinates
                pos1 = controller.node_positions[stops[i]]
                pos2 = controller.node_positions[stops[i+1]]
                
                # Calculate distance for popup
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5 * 100
                
                # Draw the bus route
                folium.PolyLine(
                    locations=[pos1, pos2],
                    color=color,
                    weight=3,
                    opacity=0.7,
                    popup=f"Bus Route {route_id}: {distance:.1f} km"
                ).add_to(m)
    
    # Add metro stations
    metro_stations = set()
    for _, line in controller.metro_lines.iterrows():
        stations = [station.strip() for station in line['Stations'].split(',')]
        metro_stations.update(stations)
    
    for station in metro_stations:
        if station in controller.node_positions:
            is_transfer = station in controller.transfer_points
            icon_html = f'<i class="fas fa-subway" style="color:#E74C3C;"></i>'
            
            folium.Marker(
                location=controller.node_positions[station],
                popup=f"Metro Station: {controller.get_location_name(station)}",
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 18px; {"color:#8C6D3F; background-color:#F5ECD9; padding:6px; border-radius:50%; border:2px solid #C08A38;" if is_transfer else ""}">{icon_html}</div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15)
                )
            ).add_to(m)
    
    # Add bus stops (only those not already covered by metro)
    bus_stops = set()
    for _, route in controller.bus_routes.iterrows():
        stops = [stop.strip() for stop in route['Stops'].split(',')]
        bus_stops.update(stops)
    
    # Remove stops that are already metro stations
    bus_only_stops = bus_stops - metro_stations
    
    for stop in bus_only_stops:
        if stop in controller.node_positions:
            is_transfer = stop in controller.transfer_points
            icon_html = f'<i class="fas fa-bus" style="color:#C08A38;"></i>'
            
            folium.Marker(
                location=controller.node_positions[stop],
                popup=f"Bus Stop: {controller.get_location_name(stop)}",
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 16px; {"color:#8C6D3F; background-color:#F5ECD9; padding:6px; border-radius:50%; border:2px solid #C08A38;" if is_transfer else ""}">{icon_html}</div>',
                    icon_size=(28, 28),
                    icon_anchor=(14, 14)
                )
            ).add_to(m)
    
    # Add legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 30px; right: 30px; width: 220px; 
                border: 2px solid #C08A38; z-index: 9999; 
                background-color: #FFFBF0;
                padding: 10px;
                border-radius: 6px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);">
        <div style="font-size: 16px; font-weight: bold; color: #5A4214; margin-bottom: 10px; border-bottom: 1px solid #E5D3A9; padding-bottom: 5px;">
            Transit Network
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #E74C3C; width: 20px; height: 5px; margin-right: 10px;"></div>
            <span style="color: #5A4214;">Metro Line</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #C08A38; width: 20px; height: 3px; margin-right: 10px;"></div>
            <span style="color: #5A4214;">Bus Route</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <i class="fas fa-subway" style="color: #E74C3C; margin-right: 10px;"></i>
            <span style="color: #5A4214;">Metro Station</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <i class="fas fa-bus" style="color: #C08A38; margin-right: 10px;"></i>
            <span style="color: #5A4214;">Bus Stop</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="padding: 2px; border-radius: 50%; border: 2px solid #C08A38; margin-right: 10px; width: 16px; height: 16px;"></div>
            <span style="color: #5A4214;">Transfer Point</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m._repr_html_()

def render_transit_performance_metrics(controller) -> None:
    """Render transit performance metrics including service reliability and environmental impact."""
    
    st.subheader("Transit Performance Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Service Reliability Analysis (simulated data)
        st.markdown("### Service Reliability")
        
        reliability_data = pd.DataFrame({
            "Mode": ["Bus", "Bus", "Bus", "Metro", "Metro", "Metro"],
            "Metric": ["On Time", "Delayed", "Cancelled", "On Time", "Delayed", "Cancelled"],
            "Percentage": [78, 19, 3, 92, 7, 1]
        })
        
        fig = px.bar(
            reliability_data,
            x="Mode",
            y="Percentage",
            color="Metric",
            title="Service Reliability Analysis",
            color_discrete_map={
                "On Time": "#8C6D3F",
                "Delayed": "#E5B660", 
                "Cancelled": "#C08A38"
            }
        )
        
        fig.update_layout(
            xaxis_title="Transport Mode",
            yaxis_title="Percentage of Services",
            legend_title="Service Status",
            barmode="stack"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Congestion Impact Analysis
        if not controller.bus_routes.empty:
            st.markdown("### Traffic Congestion Reduction")
            
            # Calculate total ridership
            total_ridership = sum(
                int(route.get('DailyPassengers', 5000))
                for _, route in controller.bus_routes.iterrows()
            ) + sum(
                int(line.get('DailyPassengers', 10000))
                for _, line in controller.metro_lines.iterrows()
            )
            
            # Assume each passenger would otherwise generate 0.05 hours of congestion
            congestion_reduction = total_ridership * 0.05
            
            # Create congestion reduction visualization
            fig = go.Figure()
            
            fig.add_trace(go.Indicator(
                mode="number+delta",
                value=congestion_reduction,
                title={
                    "text": "Daily Congestion Hours Reduced"},
                delta={"reference": congestion_reduction * 0.9, "relative": True},
                domain={"x": [0, 1], "y": [0, 1]}
            ))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add context
            st.markdown(f"""
            By serving {total_ridership:,} daily passengers, the transit system reduces approximately 
            **{congestion_reduction:,.0f} hours** of traffic congestion daily, equivalent to about 
            **{congestion_reduction/24:,.0f} days** of continuous traffic.
            """)
    
    with col2:
        # Environmental Impact Analysis
        st.markdown("### Environmental Impact")
        
        # Calculate daily CO2 emission reduction
        if not controller.bus_routes.empty and not controller.metro_lines.empty:
            # Assumptions:
            # - Average car emits 120g CO2 per passenger-km
            # - Bus emits 65g CO2 per passenger-km
            # - Metro emits 35g CO2 per passenger-km
            # - Average trip length is 8km
            
            bus_passengers = sum(
                int(route.get('DailyPassengers', 5000))
                for _, route in controller.bus_routes.iterrows()
            )
            
            metro_passengers = sum(
                int(line.get('DailyPassengers', 10000))
                for _, line in controller.metro_lines.iterrows()
            )
            
            avg_trip_length = 8  # km
            
            # CO2 saved compared to cars (in tons)
            bus_co2_saved = bus_passengers * avg_trip_length * (120 - 65) / 1000000
            metro_co2_saved = metro_passengers * avg_trip_length * (120 - 35) / 1000000
            total_co2_saved = bus_co2_saved + metro_co2_saved
            
            # Create environmental impact chart
            impact_data = pd.DataFrame([
                {"Mode": "Bus", "CO2 Reduction (tons)": bus_co2_saved, "Trees Equivalent": bus_co2_saved * 45},
                {"Mode": "Metro", "CO2 Reduction (tons)": metro_co2_saved, "Trees Equivalent": metro_co2_saved * 45}
            ])
            
            fig = px.bar(
                impact_data,
                x="Mode",
                y="CO2 Reduction (tons)",
                color="Mode",
                title="Daily CO2 Emissions Reduction",
                color_discrete_map={"Bus": "#C08A38", "Metro": "#8C6D3F"}
            )
            
            fig.update_layout(
                xaxis_title="Transport Mode",
                yaxis_title="CO2 Reduction (tons/day)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Annual environmental impact
            annual_co2_saved = total_co2_saved * 365
            trees_equivalent = annual_co2_saved * 45  # Approx. 45 trees absorb 1 ton of CO2 annually
            
            col1, col2 = st.columns(2)
            col1.metric(
                "Annual CO2 Reduction",
                f"{annual_co2_saved:,.0f} tons",
                f"{annual_co2_saved/1000:,.1f}K tons CO2"
            )
            
            col2.metric(
                "Equivalent Trees",
                f"{trees_equivalent:,.0f} trees",
                "Annual absorption"
            )
        
        # Accessibility Analysis
        st.markdown("### Transit Accessibility")
        
        # Calculate population within 500m of transit
        neighborhoods = controller.neighborhoods
        transit_stops = set()
        
        for _, route in controller.bus_routes.iterrows():
            stops = [stop.strip() for stop in route['Stops'].split(',')]
            transit_stops.update(stops)
        
        for _, line in controller.metro_lines.iterrows():
            stations = [station.strip() for station in line['Stations'].split(',')]
            transit_stops.update(stations)
        
        # For demonstration, simulate some coverage statistics
        coverage_data = pd.DataFrame({
            "Walking Time": ["<5 min", "5-10 min", "10-15 min", ">15 min"],
            "Population": [350000, 480000, 320000, 150000]
        })
        
        fig = px.pie(
            coverage_data,
            values="Population",
            names="Walking Time",
            title="Population Access to Transit",
            color="Walking Time",
            color_discrete_map={
                "<5 min": "#8C6D3F",
                "5-10 min": "#C08A38",
                "10-15 min": "#E5B660",
                ">15 min": "#F5ECD9"
            }
        )
        
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

def render_transit_future_planning(controller) -> None:
    """Render future transit planning scenarios and expansion recommendations."""
    
    st.subheader("Future Transit Planning")
    
    # Expansion Recommendations
    st.markdown("### Network Expansion Recommendations")
    
    # Get existing connectivity data
    neighborhoods = controller.neighborhoods
    
    # Create a DataFrame with neighborhood data
    neighborhood_data = pd.DataFrame({
        "ID": [str(row["ID"]) for _, row in neighborhoods.iterrows()],
        "Name": [row["Name"] for _, row in neighborhoods.iterrows()],
        "Population": [row["Population"] for _, row in neighborhoods.iterrows()],
        "Type": [row["Type"] for _, row in neighborhoods.iterrows()],
        "Latitude": [row["Y-coordinate"] for _, row in neighborhoods.iterrows()],
        "Longitude": [row["X-coordinate"] for _, row in neighborhoods.iterrows()]
    })
    
    # Get all transit stops
    all_transit_stops = set()
    
    for _, route in controller.bus_routes.iterrows():
        stops = [stop.strip() for stop in route['Stops'].split(',')]
        all_transit_stops.update(stops)
    
    for _, line in controller.metro_lines.iterrows():
        stations = [station.strip() for station in line['Stations'].split(',')]
        all_transit_stops.update(stations)
    
    # Add transit coverage to neighborhood data
    neighborhood_data["HasTransit"] = neighborhood_data["ID"].apply(
        lambda x: "Yes" if x in all_transit_stops else "No"
    )
    
    # Create an underserved index based on population and transit coverage
    neighborhood_data["UnderservedIndex"] = neighborhood_data.apply(
        lambda row: row["Population"] / 10000 if row["HasTransit"] == "No" else 0,
        axis=1
    )
    
    # Get top underserved neighborhoods for expansion recommendations
    top_underserved = neighborhood_data.nlargest(5, "UnderservedIndex")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Create map showing underserved areas
        m = folium.Map(
            location=[30.0444, 31.2357],
            zoom_start=11,
            tiles="cartodbpositron"
        )
        
        # Add existing transit network (simplified)
        for _, route in controller.bus_routes.iterrows():
            stops = [stop.strip() for stop in route['Stops'].split(',')]
            for i in range(len(stops) - 1):
                if stops[i] in controller.node_positions and stops[i+1] in controller.node_positions:
                    folium.PolyLine(
                        locations=[controller.node_positions[stops[i]], controller.node_positions[stops[i+1]]],
                        color="#C08A38",
                        weight=2,
                        opacity=0.5
                    ).add_to(m)
        
        for _, line in controller.metro_lines.iterrows():
            stations = [station.strip() for station in line['Stations'].split(',')]
            for i in range(len(stations) - 1):
                if stations[i] in controller.node_positions and stations[i+1] in controller.node_positions:
                    folium.PolyLine(
                        locations=[controller.node_positions[stations[i]], controller.node_positions[stations[i+1]]],
                        color="#8C6D3F",
                        weight=3,
                        opacity=0.6
                    ).add_to(m)
        
        # Add neighborhoods with color indicating service level
        for _, row in neighborhood_data.iterrows():
            # Determine color based on underserved index
            if row["UnderservedIndex"] > 10:
                color = "#C12F39"  # High priority
            elif row["UnderservedIndex"] > 5:
                color = "#EF8D32"  # Medium priority
            elif row["UnderservedIndex"] > 0:
                color = "#FFCC00"  # Low priority
            else:
                color = "#8C6D3F"  # Already served
                
            # Add circle marker
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=8,
                fill=True,
                color=color,
                fill_opacity=0.7,
                popup=f"{row['Name']}<br>Population: {row['Population']:,}<br>Priority: {'High' if row['UnderservedIndex'] > 10 else 'Medium' if row['UnderservedIndex'] > 5 else 'Low' if row['UnderservedIndex'] > 0 else 'Already Served'}"
            ).add_to(m)
            
        # Add proposed expansion lines for top 3 underserved areas
        for i, row in top_underserved.head(3).iterrows():
            # Find nearest transit stop for connection
            min_dist = float('inf')
            nearest_stop = None
            
            for stop in all_transit_stops:
                if stop in controller.node_positions:
                    dist = ((row["Latitude"] - controller.node_positions[stop][0])**2 + 
                           (row["Longitude"] - controller.node_positions[stop][1])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_stop = stop
            
            if nearest_stop:
                folium.PolyLine(
                    locations=[[row["Latitude"], row["Longitude"]], controller.node_positions[nearest_stop]],
                    color="#C12F39",
                    weight=3,
                    opacity=0.9,
                    dash_array="5,8",
                    popup=f"Proposed connection: {row['Name']} to {controller.get_location_name(nearest_stop)}"
                ).add_to(m)
        
        # Add legend
        legend_html = """
        <div style="position: fixed; 
                    bottom: 30px; right: 30px; width: 180px; 
                    border: 2px solid #C08A38; z-index: 9999; 
                    background-color: #FFFBF0;
                    padding: 10px;
                    border-radius: 6px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            <div style="font-size: 16px; font-weight: bold; color: #5A4214; margin-bottom: 10px; border-bottom: 1px solid #E5D3A9; padding-bottom: 5px;">
                Expansion Priority
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="background-color: #C12F39; width: 16px; height: 16px; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: #5A4214;">High Priority</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="background-color: #EF8D32; width: 16px; height: 16px; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: #5A4214;">Medium Priority</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="background-color: #FFCC00; width: 16px; height: 16px; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: #5A4214;">Low Priority</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="background-color: #8C6D3F; width: 16px; height: 16px; border-radius: 50%; margin-right: 10px;"></div>
                <span style="color: #5A4214;">Already Served</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="border-top: 3px dashed #C12F39; width: 30px; margin-right: 10px;"></div>
                <span style="color: #5A4214;">Proposed Line</span>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Display the map
        st.components.v1.html(m._repr_html_(), height=500)
    
    with col2:
        # Show expansion recommendations table
        st.markdown("#### Top Expansion Priorities")
        
        st.table(top_underserved[["Name", "Population", "Type"]].reset_index(drop=True))
        
        # Add ridership projections
        st.markdown("#### Ridership Projections")
        
        # Simulate ridership projections
        years = list(range(2024, 2029))
        base_ridership = sum(
            int(route.get('DailyPassengers', 5000))
            for _, route in controller.bus_routes.iterrows()
        ) + sum(
            int(line.get('DailyPassengers', 10000))
            for _, line in controller.metro_lines.iterrows()
        )
        
        # Simulate growth scenarios
        conservative_growth = [base_ridership * (1 + 0.03 * y) for y, _ in enumerate(years)]
        moderate_growth = [base_ridership * (1 + 0.05 * y) for y, _ in enumerate(years)]
        aggressive_growth = [base_ridership * (1 + 0.08 * y) for y, _ in enumerate(years)]
        
        # Create projection chart
        projection_df = pd.DataFrame({
            'Year': years * 3,
            'Scenario': ['Conservative'] * 5 + ['Moderate'] * 5 + ['Aggressive'] * 5,
            'Daily Ridership': conservative_growth + moderate_growth + aggressive_growth
        })
        
        fig = px.line(
            projection_df,
            x="Year",
            y="Daily Ridership",
            color="Scenario",
            title="Transit Ridership Projections",
            color_discrete_map={
                "Conservative": "#8C6D3F", 
                "Moderate": "#C08A38",
                "Aggressive": "#E5B660"
            }
        )
        
        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Daily Ridership",
            legend_title="Growth Scenario"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Project funding requirements
        st.markdown("#### Funding Requirements")
        
        # Estimate costs based on proposed extensions
        est_km_extension = sum(
            ((row["Latitude"] - controller.node_positions[all_transit_stops.pop()][0])**2 + 
             (row["Longitude"] - controller.node_positions[all_transit_stops.pop()][1])**2)**0.5 * 100
            for _, row in top_underserved.head(3).iterrows()
        ) if all_transit_stops else 15  # Default if no stops
        
        # Cost per km (in millions)
        bus_cost_per_km = 2  # $2M per km for bus routes
        metro_cost_per_km = 80  # $80M per km for metro
        
        st.info(f"""
        **Estimated extension:** {est_km_extension:.1f} km
        
        **Bus-based solution:** ${est_km_extension * bus_cost_per_km:.1f}M
        
        **Metro-based solution:** ${est_km_extension * metro_cost_per_km:.1f}M
        
        **Recommendation:** Mixed approach with BRT (Bus Rapid Transit) corridors
        """)

def render_reports(neighborhoods: pd.DataFrame, roads: pd.DataFrame, facilities: pd.DataFrame) -> None:
    """Render the main reports section with all analyses."""
    st.title("Network Analysis Reports")
    
    # Create tabs for different report types
    report_tabs = st.tabs([
        "Infrastructure",
        "Population",
        "Connectivity",
        "Facilities",
        "Public Transit"
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
    
    # Public Transit Report
    with report_tabs[4]:
        # Get transit controller
        if 'controller' in st.session_state:
            controller = st.session_state.controller
            
            # Create subtabs for transit reports
            transit_tabs = st.tabs(["Network Overview", "Performance Metrics", "Future Planning"])
            
            with transit_tabs[0]:
                render_transit_report(controller)
                
            with transit_tabs[1]:
                render_transit_performance_metrics(controller)
                
            with transit_tabs[2]:
                render_transit_future_planning(controller)
        else:
            st.warning("Transit controller not available. Please navigate to the Dashboard first to initialize the application.") 