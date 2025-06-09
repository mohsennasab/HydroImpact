"""Main Streamlit application"""

import streamlit as st
import os
import sys
import tempfile
from pathlib import Path
import folium
from streamlit_folium import st_folium
import zipfile

# Add the parent directory to Python path to fix imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import REQUIRED_CRS, RASTER_TYPES
from app.ui_helpers import (
    create_file_uploader_section, 
    save_uploaded_files,
    create_id_column_selector,
    create_download_button
)
from modules.crs_check import (
    check_all_inputs_crs, 
    display_crs_check_results,
    reproject_all_files,
    cleanup_temp_files
)
from modules.building_analysis import run_building_analysis
from modules.cross_section_plot import (
    create_all_cross_sections_plot,
    save_plots_to_html
)
from modules.point_analysis import analyze_points, format_results_table
from utils.vector_utils import load_shapefile


# Page config
st.set_page_config(
    page_title="HydroImpact",
    page_icon="🌊",
    layout="wide"
)

# Title and description
st.title("🌊 HydroImpact: Dam Breach Post Processing Toolkit")
st.markdown("""
Developed by [Mohsen Tahmasebi Nasab, PhD](https://www.hydromohsen.com)  
This tool processes HEC-RAS modeling outputs to extract summaries for:
- 🏢 Building footprints within flood extent
- 📊 Cross-section elevation and WSE profiles  
- 📍 Point-based raster value extraction

**Note:** All inputs will be automatically reprojected to EPSG:4326 (WGS84) if needed.  
<br>
<span style="color:red"><b>Disclaimer:</b> The app is provided as is, without warranty of any kind. The author is not liable for any damages or claims arising from use.</span>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = {}

# File upload section
raster_files, vector_files = create_file_uploader_section()

# CRS Check and Reprojection
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Check CRS"):
            with st.spinner("Checking coordinate systems..."):
                all_match, messages = check_all_inputs_crs(raster_files, vector_files, REQUIRED_CRS)
                display_crs_check_results(messages)
                
                if all_match:
                    st.success("✅ All files have consistent CRS!")
                else:
                    st.warning("⚠️ Some files need reprojection")
    
    with col2:
        if st.button("🔄 Auto-Reproject All Files"):
            # First check CRS
            all_match, messages = check_all_inputs_crs(raster_files, vector_files, REQUIRED_CRS)
            
            if all_match:
                st.success("✅ All files already in EPSG:4326!")
            else:
                # Show what needs reprojection
                st.write("Files needing reprojection:")
                for name, msg in messages.items():
                    if "❌" in msg:
                        st.write(f"  - {name}")
                
                # Reproject files
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(progress, message):
                    progress_bar.progress(progress)
                    status_text.text(message)
                
                with st.spinner("Reprojecting files..."):
                    reprojected_rasters, reprojected_vectors = reproject_all_files(
                        raster_files, 
                        vector_files,
                        REQUIRED_CRS,
                        progress_callback
                    )
                    
                    # Store reprojected paths in session state
                    st.session_state['reprojected_rasters'] = reprojected_rasters
                    st.session_state['reprojected_vectors'] = reprojected_vectors
                    
                st.success("✅ All files reprojected to EPSG:4326!")

# Create tabs for different analyses
tab1, tab2, tab3 = st.tabs(["🏢 Building Analysis", "📊 Cross Sections", "📍 Point Analysis"])

# Helper function to get the correct file paths
def get_file_paths(files_dict, file_type):
    """Get file paths, using reprojected versions if available"""
    if file_type == "raster" and 'reprojected_rasters' in st.session_state:
        reprojected = st.session_state['reprojected_rasters']
        return {k: reprojected.get(k, None) for k in files_dict.keys()}
    elif file_type == "vector" and 'reprojected_vectors' in st.session_state:
        reprojected = st.session_state['reprojected_vectors']
        return {k: reprojected.get(k, None) for k in files_dict.keys()}
    else:
        # Save original uploaded files
        return save_uploaded_files(files_dict, file_type)

# Tab 1: Building Analysis
with tab1:
    st.header("Building Footprint Analysis")
    
    if raster_files['dem'] and raster_files['wse']:
        # Get file paths (reprojected if available)
        with st.spinner("Preparing files..."):
            raster_paths = get_file_paths(raster_files, "raster")
            
        # Check if user provided building footprints
        building_source = st.radio(
            "Building footprint source:",
            ["Download from Microsoft Global Buildings", "Use uploaded shapefile"]
        )
        
        use_existing = (building_source == "Use uploaded shapefile" and vector_files.get('buildings'))
        
        if use_existing:
            vector_paths = get_file_paths({'buildings': vector_files['buildings']}, "vector")
            buildings_gdf = load_shapefile(vector_paths['buildings'])
            id_column = create_id_column_selector(buildings_gdf, "buildings")
        else:
            id_column = "building_id"
            vector_paths = {}
        
        if st.button("🏃 Run Building Analysis", key="run_building"):
            with st.spinner("Running analysis..."):
                results_df, buildings_gdf = run_building_analysis(
                    raster_paths['dem'],
                    raster_paths['wse'],
                    {k: v for k, v in raster_paths.items() if k not in ['dem', 'wse'] and v is not None},
                    vector_paths.get('buildings'),
                    id_column
                )
                
                st.session_state.building_results = results_df
                st.session_state.buildings_gdf = buildings_gdf
                st.success(f"✅ Analysis complete! Processed {len(results_df)} buildings")
        
        # Display results
        if 'building_results' in st.session_state:
            st.subheader("Results")
            
            # Create columns for downloads
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("📊 **Analysis Results**")
                st.dataframe(st.session_state.building_results.head(10))
                create_download_button(
                    st.session_state.building_results,
                    "building_analysis_results.csv",
                    "download_buildings_csv"
                )
            
            with col2:
                st.write("🏢 **Building Footprints**")
                st.info(f"Total buildings: {len(st.session_state.buildings_gdf)}")
                
                # Download building footprint shapefile
                with tempfile.TemporaryDirectory() as tmpdir:
                    shp_path = os.path.join(tmpdir, "building_footprints.shp")
                    st.session_state.buildings_gdf.to_file(shp_path)
                    
                    # Create a zip file with all shapefile components
                    import zipfile
                    zip_path = os.path.join(tmpdir, "building_footprints.zip")
                    with zipfile.ZipFile(zip_path, 'w') as zipf:
                        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                            file_path = shp_path.replace('.shp', ext)
                            if os.path.exists(file_path):
                                zipf.write(file_path, f"building_footprints{ext}")
                    
                    with open(zip_path, 'rb') as f:
                        st.download_button(
                            label="📥 Download Building Footprints (Shapefile)",
                            data=f.read(),
                            file_name="building_footprints.zip",
                            mime="application/zip",
                            key="download_buildings_shp"
                        )
            
            # Interactive Map
            st.subheader("🗺️ Interactive Map")
            with st.spinner("Creating map..."):
                from modules.building_analysis import create_building_analysis_map
                
                # Create the map
                building_map = create_building_analysis_map(
                    st.session_state.buildings_gdf,
                    raster_paths['wse']
                )
                
                # Display the map
                from streamlit_folium import st_folium
                st_folium(building_map, height=600, width=None, returned_objects=[])
                
    else:
        st.warning("⚠️ Please upload both DEM and WSE rasters")

# Tab 2: Cross Section Analysis
with tab2:
    st.header("Cross Section Visualization")
    
    if raster_files['dem'] and raster_files['wse'] and vector_files.get('cross_sections'):
        with st.spinner("Preparing files..."):
            raster_paths = get_file_paths(
                {'dem': raster_files['dem'], 'wse': raster_files['wse']}, 
                "raster"
            )
            vector_paths = get_file_paths(
                {'cross_sections': vector_files['cross_sections']}, 
                "vector"
            )
            
            # Load cross sections
            cross_sections_gdf = load_shapefile(vector_paths['cross_sections'])
            id_column = create_id_column_selector(cross_sections_gdf, "cross sections")
        
        if st.button("📊 Generate Cross Section Plots", key="run_cross"):
            with st.spinner("Creating visualizations..."):
                figures = create_all_cross_sections_plot(
                    cross_sections_gdf,
                    raster_paths['dem'],
                    raster_paths['wse'],
                    id_column
                )
                
                st.session_state.cross_section_figures = figures
                st.success(f"✅ Generated {len(figures)} cross section plots")
        
        # Display results
        if 'cross_section_figures' in st.session_state:
            st.subheader("Cross Section Profiles")
            
            # Show plots in app
            for section_id, fig in st.session_state.cross_section_figures[:3]:
                st.plotly_chart(fig, use_container_width=True)
            
            if len(st.session_state.cross_section_figures) > 3:
                st.info(f"Showing first 3 of {len(st.session_state.cross_section_figures)} plots. Download HTML for all plots.")
            
            # Save to HTML
            if st.button("💾 Save All Plots to HTML"):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
                    save_plots_to_html(st.session_state.cross_section_figures, tmp.name)
                    
                    with open(tmp.name, 'r') as f:
                        html_content = f.read()
                    
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=html_content,
                        file_name="cross_section_profiles.html",
                        mime="text/html"
                    )
    else:
        st.warning("⚠️ Please upload DEM, WSE rasters and cross section shapefile")

# Tab 3: Point Analysis  
with tab3:
    st.header("Point-Based Analysis")
    
    if vector_files.get('points'):
        with st.spinner("Preparing files..."):
            raster_paths = get_file_paths(raster_files, "raster")
            vector_paths = get_file_paths({'points': vector_files['points']}, "vector")
            
            # Load points
            points_gdf = load_shapefile(vector_paths['points'])
            id_column = create_id_column_selector(points_gdf, "points")
        
        if st.button("📍 Extract Point Values", key="run_points"):
            with st.spinner("Extracting raster values..."):
                # Filter out None values from raster_paths
                valid_raster_paths = {k: v for k, v in raster_paths.items() if v is not None}
                
                results_df = analyze_points(
                    points_gdf,
                    valid_raster_paths,
                    id_column
                )
                
                # Format results
                formatted_df = format_results_table(results_df)
                
                st.session_state.point_results = formatted_df
                st.success(f"✅ Extracted values for {len(formatted_df)} points")
        
        # Display results
        if 'point_results' in st.session_state:
            st.subheader("Results")
            st.dataframe(st.session_state.point_results)
            
            create_download_button(
                st.session_state.point_results,
                "point_analysis_results.csv",
                "download_points"
            )
    else:
        st.warning("⚠️ Please upload points shapefile")

# Footer
st.markdown("---")
st.markdown("🌊 HydroImpact v1.0 | Built with Streamlit")

# Cleanup temporary files when app is done
if st.button("🗑️ Clean Up Temporary Files", key="cleanup"):
    cleanup_temp_files()
    st.success("Temporary files cleaned up!")
