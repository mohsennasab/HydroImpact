"""Module for building footprint analysis"""

import pandas as pd
import geopandas as gpd
import numpy as np
from shapely import geometry
import mercantile
from typing import Dict, Optional, Tuple
import tempfile
import os
import requests
from tqdm import tqdm
import streamlit as st
import folium
from folium import plugins
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from utils.raster_utils import create_flood_extent_polygon, extract_raster_stats_for_polygon
from utils.vector_utils import load_shapefile
from app.config import BUILDINGS_DATASET_URL


def download_building_footprints(aoi_polygon, progress_callback=None) -> gpd.GeoDataFrame:
    """Download building footprints from Microsoft dataset for AOI"""
    
    # Get bounding box
    minx, miny, maxx, maxy = aoi_polygon.bounds
    
    # Determine which tiles intersect our AOI
    quad_keys = set()
    for tile in list(mercantile.tiles(minx, miny, maxx, maxy, zooms=9)):
        quad_keys.add(mercantile.quadkey(tile))
    quad_keys = list(quad_keys)
    
    if progress_callback:
        progress_callback(0.1, f"Found {len(quad_keys)} tiles to download")
    
    # Download dataset links
    df = pd.read_csv(BUILDINGS_DATASET_URL, dtype=str)
    
    # Download and merge building footprints
    combined_gdf = gpd.GeoDataFrame()
    idx = 0
    
    for i, quad_key in enumerate(quad_keys):
        if progress_callback:
            progress_callback((i + 1) / len(quad_keys) * 0.8 + 0.1, 
                            f"Processing tile {i+1}/{len(quad_keys)}")
        
        rows = df[df["QuadKey"] == quad_key]
        if rows.shape[0] == 1:
            try:
                url = rows.iloc[0]["Url"]
                df2 = pd.read_json(url, lines=True)
                df2["geometry"] = df2["geometry"].apply(geometry.shape)
                
                gdf = gpd.GeoDataFrame(df2, crs=4326)
                
                # Filter geometries within the AOI
                #gdf = gdf[gdf.geometry.within(aoi_polygon)]
                gdf = gdf[gdf.geometry.intersects(aoi_polygon)]
                gdf['building_id'] = range(idx, idx + len(gdf))
                idx += len(gdf)
                
                combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)
            except Exception as e:
                st.warning(f"Error processing tile {quad_key}: {str(e)}")
    
    if progress_callback:
        progress_callback(1.0, "Download complete!")
    
    return combined_gdf


def analyze_buildings(
    building_gdf: gpd.GeoDataFrame,
    raster_paths: Dict[str, str],
    id_column: str = "building_id"
) -> pd.DataFrame:
    """Extract raster statistics for each building"""
    
    results = []
    
    total_buildings = len(building_gdf)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, building in building_gdf.iterrows():
        if idx % 10 == 0:
            progress = idx / total_buildings
            progress_bar.progress(progress)
            status_text.text(f"Processing building {idx}/{total_buildings}")
        
        result = {id_column: building[id_column]}
        
        # Add geometry info
        result['geometry_wkt'] = building.geometry.wkt
        #result['area_m2'] = building.geometry.area * 111000 * 111000  # Approximate for lat/lon
        result['area_ft2'] = building.geometry.area * 111000 * 111000 * 10.7639  # Approximate area in ft² from lat/lon degrees

        # Extract stats from each raster
        for raster_name, raster_path in raster_paths.items():
            if raster_path:
                stats = extract_raster_stats_for_polygon(raster_path, building.geometry)
                for stat_name, stat_value in stats.items():
                    result[f"{raster_name}_{stat_name}"] = stat_value
        
        results.append(result)
    
    progress_bar.progress(1.0)
    status_text.text("Analysis complete!")
    
    return pd.DataFrame(results)


def create_building_analysis_map(
    buildings_gdf: gpd.GeoDataFrame,
    wse_path: str,
    map_height: int = 600
) -> folium.Map:
    """Create an interactive map with buildings and WSE overlay"""
    
    # Get center point from buildings
    bounds = buildings_gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles='OpenStreetMap'
    )
    
    # Add WSE raster as overlay
    try:
        with rasterio.open(wse_path) as src:
            # Read the raster data
            wse_data = src.read(1)
            
            # Get bounds
            bounds = src.bounds
            
            # Normalize data for visualization (0-1)
            valid_data = wse_data[wse_data != src.nodata] if src.nodata is not None else wse_data[wse_data > 0]
            if len(valid_data) > 0:
                vmin, vmax = np.percentile(valid_data, [2, 98])  # Use percentiles to handle outliers
                normalized = np.clip((wse_data - vmin) / (vmax - vmin), 0, 1)
                
                # Apply colormap
                cmap = cm.get_cmap('Blues')
                colored = cmap(normalized)
                
                # Convert to RGBA image
                rgba = (colored * 255).astype(np.uint8)
                
                # Set transparency for nodata values
                if src.nodata is not None:
                    rgba[wse_data == src.nodata] = [0, 0, 0, 0]
                else:
                    rgba[wse_data <= 0] = [0, 0, 0, 0]
                
                # Create a temporary PNG file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    plt.imsave(tmp.name, rgba)
                    
                    # Add to map with 50% opacity
                    folium.raster_layers.ImageOverlay(
                        image=tmp.name,
                        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
                        opacity=0.5,
                        name='Water Surface Elevation'
                    ).add_to(m)
                    
                # Clean up temp file
                os.unlink(tmp.name)
                
    except Exception as e:
        st.warning(f"Could not add WSE overlay to map: {str(e)}")
    
    # Add building footprints
    folium.GeoJson(
        buildings_gdf.to_json(),
        name='Building Footprints',
        style_function=lambda feature: {
            'fillColor': 'red',
            'color': 'darkred',
            'weight': 1,
            'fillOpacity': 0.7
        }
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Fit bounds
    sw = [bounds[1], bounds[0]]
    ne = [bounds[3], bounds[2]]
    m.fit_bounds([sw, ne])
    
    return m


def run_building_analysis(
    dem_path: str,
    wse_path: str,
    other_rasters: Dict[str, str],
    existing_buildings_path: Optional[str] = None,
    id_column: str = "building_id"
) -> Tuple[pd.DataFrame, gpd.GeoDataFrame]:
    """Main function to run building analysis - now returns both results and GeoDataFrame"""
    
    st.info("Creating flood extent polygon...")
    flood_extent = create_flood_extent_polygon(wse_path)
    
    if existing_buildings_path:
        st.info("Loading existing building footprints...")
        buildings_gdf = load_shapefile(existing_buildings_path)
        # Filter to flood extent
        buildings_gdf = buildings_gdf[buildings_gdf.geometry.intersects(flood_extent.geometry.iloc[0])]
    else:
        st.info("Downloading building footprints from Microsoft dataset...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(progress, message):
            progress_bar.progress(progress)
            status_text.text(message)
        
        buildings_gdf = download_building_footprints(
            flood_extent.geometry.iloc[0],
            progress_callback
        )
    
    st.success(f"Found {len(buildings_gdf)} buildings in flood extent")
    
    # Prepare raster paths - include DEM for analysis
    all_rasters = {"dem": dem_path, "wse": wse_path, **other_rasters}
    
    # Analyze buildings
    st.info("Analyzing buildings...")
    results_df = analyze_buildings(buildings_gdf, all_rasters, id_column)
    
    return results_df, buildings_gdf



