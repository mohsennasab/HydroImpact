"""Module for checking and enforcing CRS consistency"""

import os
import tempfile
from typing import Dict, Tuple, Optional
import streamlit as st
from utils.raster_utils import check_raster_crs, reproject_raster
from utils.vector_utils import load_shapefile, save_shapefile_with_crs
import geopandas as gpd
import shutil


def check_all_inputs_crs(
    raster_files: Dict[str, any],
    vector_files: Dict[str, any],
    target_crs: str = "EPSG:4326"
) -> Tuple[bool, Dict[str, str]]:
    """
    Check all input files for CRS consistency
    Returns: (all_match, messages_dict)
    """
    messages = {}
    all_match = True
    
    # Check rasters
    for name, file_obj in raster_files.items():
        if file_obj is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp:
                tmp.write(file_obj.getvalue())
                tmp_path = tmp.name
            
            try:
                if not check_raster_crs(tmp_path, target_crs):
                    messages[name] = f"❌ {name} is not in {target_crs}"
                    all_match = False
                else:
                    messages[name] = f"✅ {name} is in {target_crs}"
            finally:
                os.unlink(tmp_path)
    
    # Check vectors
    for name, file_obj in vector_files.items():
        if file_obj is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.shp') as tmp:
                tmp.write(file_obj.getvalue())
                tmp_path = tmp.name
            
            try:
                # Save associated files (.shx, .dbf, .prj)
                base_name = file_obj.name[:-4]
                for ext in ['.shx', '.dbf', '.prj']:
                    associated_key = f"{name}_{ext}"
                    if associated_key in st.session_state:
                        associated_file = st.session_state[associated_key]
                        if associated_file:
                            associated_path = tmp_path[:-4] + ext
                            with open(associated_path, 'wb') as f:
                                f.write(associated_file.getvalue())
                
                gdf = gpd.read_file(tmp_path)
                if gdf.crs is None:
                    messages[name] = f"⚠️ {name} has no CRS defined"
                    all_match = False
                elif gdf.crs.to_string() != target_crs:
                    messages[name] = f"❌ {name} is in {gdf.crs.to_string()}, not {target_crs}"
                    all_match = False
                else:
                    messages[name] = f"✅ {name} is in {target_crs}"
            except Exception as e:
                messages[name] = f"❌ {name} error: {str(e)}"
                all_match = False
            finally:
                # Clean up all associated files
                for ext in ['.shp', '.shx', '.dbf', '.prj']:
                    if os.path.exists(tmp_path[:-4] + ext):
                        os.unlink(tmp_path[:-4] + ext)
    
    return all_match, messages


def reproject_all_files(
    raster_files: Dict[str, any],
    vector_files: Dict[str, any],
    target_crs: str = "EPSG:4326",
    progress_callback=None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Reproject all files to target CRS and return paths to reprojected files
    """
    reprojected_rasters = {}
    reprojected_vectors = {}
    total_files = len([f for f in raster_files.values() if f]) + len([f for f in vector_files.values() if f])
    current_file = 0
    
    # Create a temporary directory for reprojected files
    temp_dir = tempfile.mkdtemp(prefix="hydro_toolkit_reprojected_")
    
    # Reproject rasters
    for name, file_obj in raster_files.items():
        if file_obj is not None:
            current_file += 1
            if progress_callback:
                progress_callback(current_file / total_files, f"Reprojecting {name}...")
            
            # Save original file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp:
                tmp.write(file_obj.getvalue())
                src_path = tmp.name
            
            # Check if reprojection is needed
            try:
                if check_raster_crs(src_path, target_crs):
                    # Just copy the file
                    dst_path = os.path.join(temp_dir, f"{name}_4326.tif")
                    shutil.copy2(src_path, dst_path)
                    reprojected_rasters[name] = dst_path
                else:
                    # Reproject the file
                    dst_path = os.path.join(temp_dir, f"{name}_4326.tif")
                    reproject_raster(src_path, dst_path, target_crs)
                    reprojected_rasters[name] = dst_path
            finally:
                os.unlink(src_path)
    
    # Reproject vectors
    for name, file_obj in vector_files.items():
        if file_obj is not None:
            current_file += 1
            if progress_callback:
                progress_callback(current_file / total_files, f"Reprojecting {name}...")
            
            # Save original file with associated files
            with tempfile.NamedTemporaryFile(delete=False, suffix='.shp') as tmp:
                tmp.write(file_obj.getvalue())
                src_path = tmp.name
            
            try:
                # Save associated files
                base_name = file_obj.name[:-4]
                for ext in ['.shx', '.dbf', '.prj']:
                    associated_key = f"{name}_{ext}"
                    if associated_key in st.session_state:
                        associated_file = st.session_state[associated_key]
                        if associated_file:
                            associated_path = src_path[:-4] + ext
                            with open(associated_path, 'wb') as f:
                                f.write(associated_file.getvalue())
                
                # Load and reproject
                gdf = gpd.read_file(src_path)
                
                if gdf.crs is None:
                    # Assume WGS84 if no CRS is defined
                    gdf.crs = target_crs
                elif gdf.crs.to_string() != target_crs:
                    gdf = gdf.to_crs(target_crs)
                
                # Save reprojected file
                dst_path = os.path.join(temp_dir, f"{name}_4326.shp")
                gdf.to_file(dst_path)
                reprojected_vectors[name] = dst_path
                
            finally:
                # Clean up original files
                for ext in ['.shp', '.shx', '.dbf', '.prj']:
                    if os.path.exists(src_path[:-4] + ext):
                        os.unlink(src_path[:-4] + ext)
    
    if progress_callback:
        progress_callback(1.0, "Reprojection complete!")
    
    # Store temp directory in session state for cleanup later
    st.session_state['temp_reprojected_dir'] = temp_dir
    
    return reprojected_rasters, reprojected_vectors


def display_crs_check_results(messages: Dict[str, str]):
    """Display CRS check results in Streamlit"""
    st.subheader("CRS Check Results")
    for name, message in messages.items():
        st.write(message)


def cleanup_temp_files():
    """Clean up temporary reprojected files"""
    if 'temp_reprojected_dir' in st.session_state:
        temp_dir = st.session_state['temp_reprojected_dir']
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        del st.session_state['temp_reprojected_dir']