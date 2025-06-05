"""Module for point-based analysis"""

import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, List
import streamlit as st

from utils.raster_utils import sample_raster_at_points
from utils.vector_utils import load_shapefile, extract_point_coordinates


def analyze_points(
    points_gdf: gpd.GeoDataFrame,
    raster_paths: Dict[str, str],
    id_column: str
) -> pd.DataFrame:
    """Extract raster values at point locations"""
    
    # Extract coordinates
    coordinates = extract_point_coordinates(points_gdf)
    
    # Start with point IDs and coordinates
    results = {
        id_column: points_gdf[id_column].tolist(),
        'longitude': [coord[0] for coord in coordinates],
        'latitude': [coord[1] for coord in coordinates]
    }
    
    # Sample each raster
    for raster_name, raster_path in raster_paths.items():
        if raster_path:
            st.info(f"Sampling {raster_name}...")
            values = sample_raster_at_points(raster_path, coordinates)
            results[raster_name] = values
    
    return pd.DataFrame(results)


def format_results_table(df: pd.DataFrame, ground_elevation_col: str = 'dem') -> pd.DataFrame:
    """Format results similar to the reference table"""
    
    # Calculate depth above ground if we have both DEM and WSE
    if ground_elevation_col in df.columns and 'wse' in df.columns:
        df['depth_above_ground'] = df['wse'] - df[ground_elevation_col]
        df['depth_above_ground'] = df['depth_above_ground'].apply(
            lambda x: x if x > 0 else 0
        )
    
    # Round numerical columns
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    df[numeric_columns] = df[numeric_columns].round(2)
    
    # Rename columns for clarity
    column_mapping = {
        'dem': 'Ground Elevation (ft)',
        'wse': 'Max Water Surface Elevation (ft)',
        'velocity': 'Velocity (ft/s)',
        'depth': 'Max Depth (ft)',
        'arrival_time': 'Arrival Time (hrs)',
        'depth_above_ground': 'Depth Above Ground (ft)'
    }
    
    df = df.rename(columns=column_mapping)
    
    return df