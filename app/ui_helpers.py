"""UI helper functions for Streamlit"""

import streamlit as st
import tempfile
import os
from typing import Dict, Optional, Tuple
import geopandas as gpd
import pandas as pd

from app.config import RASTER_TYPES


def create_file_uploader_section() -> Tuple[Dict[str, any], Dict[str, any]]:
    """Create file upload section and return uploaded files"""
    
    st.header("📁 File Upload")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Raster Files (GeoTIFF)")
        raster_files = {}
        
        # Required rasters
        dem_file = st.file_uploader("DEM *", type=['tif', 'tiff'], key="dem")
        wse_file = st.file_uploader("Water Surface Elevation *", type=['tif', 'tiff'], key="wse")
        
        raster_files['dem'] = dem_file
        raster_files['wse'] = wse_file
        
        # Optional rasters
        st.write("**Optional Rasters:**")
        velocity_file = st.file_uploader("Velocity", type=['tif', 'tiff'], key="velocity")
        depth_file = st.file_uploader("Depth", type=['tif', 'tiff'], key="depth")
        arrival_file = st.file_uploader("Arrival Time", type=['tif', 'tiff'], key="arrival")
        
        raster_files['velocity'] = velocity_file
        raster_files['depth'] = depth_file
        raster_files['arrival_time'] = arrival_file
    
    with col2:
        st.subheader("Vector Files (Shapefile)")
        vector_files = {}
        
        # Note about shapefiles
        st.info("📌 Upload all shapefile components (.shp, .shx, .dbf, .prj)")
        
        # Function to handle shapefile uploads
        def upload_shapefile_components(name: str, label: str):
            shp_file = st.file_uploader(f"{label} (.shp)", type=['shp'], key=f"{name}_shp")
            
            if shp_file:
                # Request associated files
                with st.expander(f"Upload {label} associated files"):
                    shx_file = st.file_uploader(f"{label} (.shx)", type=['shx'], key=f"{name}_shx")
                    dbf_file = st.file_uploader(f"{label} (.dbf)", type=['dbf'], key=f"{name}_dbf")
                    prj_file = st.file_uploader(f"{label} (.prj)", type=['prj'], key=f"{name}_prj")
                    
                    # Store associated files in session state
                    if shx_file:
                        st.session_state[f"{name}_.shx"] = shx_file
                    if dbf_file:
                        st.session_state[f"{name}_.dbf"] = dbf_file
                    if prj_file:
                        st.session_state[f"{name}_.prj"] = prj_file
                
                return shp_file
            return None
        
        cross_sections = upload_shapefile_components("cross_sections", "Cross Sections")
        points = upload_shapefile_components("points", "Points of Interest")
        buildings = upload_shapefile_components("buildings", "Building Footprints (optional)")
        
        vector_files['cross_sections'] = cross_sections
        vector_files['points'] = points
        vector_files['buildings'] = buildings
    
    return raster_files, vector_files


def save_uploaded_files(uploaded_files: Dict[str, any], file_type: str = "raster") -> Dict[str, str]:
    """Save uploaded files to temporary directory and return paths"""
    
    saved_paths = {}
    
    for name, file_obj in uploaded_files.items():
        if file_obj is not None:
            suffix = '.tif' if file_type == "raster" else '.shp'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_obj.getvalue())
                saved_paths[name] = tmp.name
                
                # For shapefiles, also save associated files
                if file_type == "vector" and suffix == '.shp':
                    # Save associated files from session state
                    for ext in ['.shx', '.dbf', '.prj']:
                        associated_key = f"{name}_{ext}"
                        if associated_key in st.session_state:
                            associated_file = st.session_state[associated_key]
                            if associated_file:
                                associated_path = tmp.name[:-4] + ext
                                with open(associated_path, 'wb') as f:
                                    f.write(associated_file.getvalue())
    
    return saved_paths


def create_id_column_selector(gdf: gpd.GeoDataFrame, feature_type: str) -> str:
    """Create a selectbox for choosing ID column"""
    
    columns = gdf.columns.tolist()
    columns.remove('geometry')
    
    default_cols = ['id', 'ID', 'FID', 'OBJECTID', 'name', 'Name']
    default_choice = next((col for col in default_cols if col in columns), columns[0])
    
    return st.selectbox(
        f"Select ID column for {feature_type}",
        columns,
        index=columns.index(default_choice) if default_choice in columns else 0
    )


def create_download_button(df: pd.DataFrame, filename: str, key: str):
    """Create a download button for dataframe as CSV"""
    
    csv = df.to_csv(index=False)
    st.download_button(
        label=f"📥 Download {filename}",
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=key
    )