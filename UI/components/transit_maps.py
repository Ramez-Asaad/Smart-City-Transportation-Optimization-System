import streamlit as st
import folium
from folium import plugins
import pandas as pd
import random

def generate_distinct_colors(n):
    """Generate n visually distinct colors."""
    colors = [
        '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', 
        '#FFFF33', '#A65628', '#F781BF', '#999999', '#66C2A5',
        '#FC8D62', '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F'
    ]
    # If we need more colors than in our predefined list, generate them randomly
    while len(colors) < n:
        color = '#{:06x}'.format(random.randint(0, 0xFFFFFF))
        if color not in colors:  # Avoid duplicates
            colors.append(color)
    return colors[:n]

def create_bus_routes_map(controller, neighborhoods, bus_routes) -> str:
    """Create a map showing all bus routes with different colors."""
    # Create base map centered on Cairo
    m = folium.Map(
        location=[30.0444, 31.2357],
        zoom_start=11
    )
    
    # Get colors for routes
    route_colors = generate_distinct_colors(len(bus_routes))
    
    # Create a legend HTML
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                border:2px solid grey; z-index:9999; 
                background-color:white;
                padding: 10px;
                border-radius: 5px;
                max-height: 300px;
                overflow-y: auto;">
        <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
            Bus Routes
        </div>
    """
    
    # Add each route to the map
    for idx, route in bus_routes.iterrows():
        color = route_colors[idx]
        stops = [str(s.strip()) for s in route['Stops'].split(',')]
        route_name = f"Route {route['RouteID']}"
        
        # Add to legend
        legend_html += f"""
        <div style="margin-bottom: 5px;">
            <span style="background-color: {color}; 
                        display: inline-block; 
                        width: 20px; 
                        height: 10px; 
                        margin-right: 5px;"></span>
            {route_name}
        </div>
        """
        
        # Draw route on map
        for i in range(len(stops)-1):
            start_pos = controller.node_positions[stops[i]]
            end_pos = controller.node_positions[stops[i+1]]
            
            # Draw route line
            folium.PolyLine(
                locations=[start_pos, end_pos],
                color=color,
                weight=3,
                opacity=0.8,
                popup=f"Bus {route['RouteID']}"
            ).add_to(m)
            
            # Add stop markers
            folium.CircleMarker(
                location=start_pos,
                radius=5,
                color=color,
                fill=True,
                popup=controller.get_location_name(stops[i])
            ).add_to(m)
            
        # Add final stop marker
        folium.CircleMarker(
            location=controller.node_positions[stops[-1]],
            radius=5,
            color=color,
            fill=True,
            popup=controller.get_location_name(stops[-1])
        ).add_to(m)
    
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m._repr_html_()

def create_metro_map(controller, neighborhoods, metro_lines) -> str:
    """Create a map showing all metro lines with their designated colors."""
    # Create base map centered on Cairo
    m = folium.Map(
        location=[30.0444, 31.2357],
        zoom_start=11
    )
    
    # Standard metro line colors
    metro_colors = {
        'M1': '#FF0000',  # Red Line
        'M2': '#0000FF',  # Blue Line
        'M3': '#00FF00',  # Green Line
    }
    
    # Create a legend HTML
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                border:2px solid grey; z-index:9999; 
                background-color:white;
                padding: 10px;
                border-radius: 5px;">
        <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
            Metro Lines
        </div>
    """
    
    # Add each metro line to the map
    for _, line in metro_lines.iterrows():
        line_id = line['LineID']
        color = metro_colors.get(line_id, '#000000')  # Default to black if color not defined
        stations = [str(s.strip()) for s in line['Stations'].split(',')]
        
        # Add to legend
        legend_html += f"""
        <div style="margin-bottom: 5px;">
            <span style="background-color: {color}; 
                        display: inline-block; 
                        width: 20px; 
                        height: 10px; 
                        margin-right: 5px;"></span>
            Line {line_id}
        </div>
        """
        
        # Draw metro line
        for i in range(len(stations)-1):
            start_pos = controller.node_positions[stations[i]]
            end_pos = controller.node_positions[stations[i+1]]
            
            # Draw line
            folium.PolyLine(
                locations=[start_pos, end_pos],
                color=color,
                weight=5,
                opacity=0.8,
                popup=f"Metro {line_id}"
            ).add_to(m)
            
            # Add station markers
            folium.CircleMarker(
                location=start_pos,
                radius=7,
                color=color,
                fill=True,
                fillOpacity=0.7,
                popup=f"Station: {controller.get_location_name(stations[i])}"
            ).add_to(m)
            
            # Add metro icon
            folium.DivIcon(
                html=f'<div style="font-size: 12px; color: {color};"><i class="fa fa-subway"></i></div>',
                icon_size=(20, 20),
                icon_anchor=(10, 10)
            ).add_to(folium.Marker(
                location=start_pos,
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 14px; color: {color};"><i class="fa fa-subway"></i></div>'
                )
            ).add_to(m))
        
        # Add final station marker and icon
        folium.CircleMarker(
            location=controller.node_positions[stations[-1]],
            radius=7,
            color=color,
            fill=True,
            fillOpacity=0.7,
            popup=f"Station: {controller.get_location_name(stations[-1])}"
        ).add_to(m)
        
        folium.DivIcon(
            html=f'<div style="font-size: 12px; color: {color};"><i class="fa fa-subway"></i></div>',
            icon_size=(20, 20),
            icon_anchor=(10, 10)
        ).add_to(folium.Marker(
            location=controller.node_positions[stations[-1]],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 14px; color: {color};"><i class="fa fa-subway"></i></div>'
            )
        ).add_to(m))
    
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add Font Awesome for metro icons
    m.get_root().header.add_child(folium.Element("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    """))
    
    return m._repr_html_() 