"""Utility functions for vector operations"""

import geopandas as gpd
import pandas as pd
from typing import Optional, List


def load_shapefile(shapefile_path: str, target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """Load shapefile and ensure it's in the target CRS"""
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        raise ValueError(f"Shapefile {shapefile_path} has no CRS defined")
    
    if gdf.crs.to_string() != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    return gdf


def save_shapefile_with_crs(gdf: gpd.GeoDataFrame, output_path: str, target_crs: str = "EPSG:4326"):
    """Save shapefile ensuring it has the target CRS"""
    if gdf.crs is None:
        gdf.crs = target_crs
    elif gdf.crs.to_string() != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    gdf.to_file(output_path)


def get_numeric_columns(gdf: gpd.GeoDataFrame) -> List[str]:
    """Get list of numeric columns from GeoDataFrame"""
    return gdf.select_dtypes(include=['number']).columns.tolist()


def get_string_columns(gdf: gpd.GeoDataFrame) -> List[str]:
    """Get list of string columns from GeoDataFrame"""
    return gdf.select_dtypes(include=['object']).columns.tolist()


def extract_point_coordinates(gdf: gpd.GeoDataFrame) -> List[tuple]:
    """Extract coordinates from point geometries"""
    if not all(gdf.geometry.type == 'Point'):
        raise ValueError("All geometries must be points")
    
    return [(geom.x, geom.y) for geom in gdf.geometry]