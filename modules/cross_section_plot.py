"""Module for cross section visualization"""

import plotly.graph_objects as go
import plotly.offline as pyo  # Move this import to the top
from plotly.subplots import make_subplots
import geopandas as gpd
import streamlit as st
from typing import Dict, List, Optional

from utils.raster_utils import extract_elevation_profile
from utils.vector_utils import load_shapefile


def create_cross_section_plot(
    line_geometry,
    dem_path: str,
    wse_path: str,
    section_id: str
) -> go.Figure:
    """Create a Plotly figure for a single cross section"""
    
    # Extract elevation profiles
    distances_dem, elevations_dem = extract_elevation_profile(dem_path, line_geometry)
    distances_wse, elevations_wse = extract_elevation_profile(wse_path, line_geometry)
    
    # Create figure
    fig = go.Figure()
    
    # Add terrain profile
    fig.add_trace(go.Scatter(
        x=distances_dem,
        y=elevations_dem,
        mode='lines',
        name='Terrain (DEM)',
        line=dict(color='brown', width=2),
        fill='tonexty',
        fillcolor='rgba(139, 69, 19, 0.3)'
    ))
    
    # Add water surface elevation
    fig.add_trace(go.Scatter(
        x=distances_wse,
        y=elevations_wse,
        mode='lines',
        name='Water Surface Elevation',
        line=dict(color='blue', width=2),
        #ill='tonexty',
        #fillcolor='rgba(0, 0, 255, 0.3)'
    ))
    
    # Update layout
    y_min = min(elevations_dem) - 10 
    y_max = max(elevations_dem) + 10
    
    fig.update_layout(
        title=f"Cross Section: {section_id}",
        xaxis_title="Station (ft)",
        yaxis_title="Elevation (ft)",
        yaxis=dict(range=[y_min, y_max]),  # Use None for auto max
        hovermode='x unified',
        width=1000,
        height=600,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        )
    )

    
    return fig


def create_all_cross_sections_plot(
    cross_sections_gdf: gpd.GeoDataFrame,
    dem_path: str,
    wse_path: str,
    id_column: str
) -> List[go.Figure]:
    """Create plots for all cross sections"""
    
    figures = []
    total_sections = len(cross_sections_gdf)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, section in cross_sections_gdf.iterrows():
        progress = (idx + 1) / total_sections
        progress_bar.progress(progress)
        status_text.text(f"Processing cross section {idx + 1}/{total_sections}")
        
        section_id = section[id_column] if id_column in section else f"Section {idx}"
        
        try:
            fig = create_cross_section_plot(
                section.geometry,
                dem_path,
                wse_path,
                str(section_id)
            )
            figures.append((str(section_id), fig))
        except Exception as e:
            st.warning(f"Error processing section {section_id}: {str(e)}")
    
    progress_bar.progress(1.0)
    status_text.text("All cross sections processed!")
    
    return figures


def save_plots_to_html(figures: List[tuple], output_path: str):
    """Save all plots to a single HTML file"""
    
    # Create HTML content
    html_content = """
    <html>
    <head>
        <title>Cross Section Profiles</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .section { margin-bottom: 50px; }
            h2 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Cross Section Profiles</h1>
    """
    
    for section_id, fig in figures:
        fig.update_layout(yaxis_autorange=False) 
        # Convert figure to HTML div

        div = pyo.plot(fig, output_type='div', include_plotlyjs=False)
        html_content += f'<div class="section"><h2>{section_id}</h2>{div}</div>'
    
    html_content += """
    </body>
    </html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html_content)