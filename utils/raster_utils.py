"""Utility functions for raster operations"""

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import shapes
from rasterio.mask import mask
from shapely.geometry import shape, Point
import geopandas as gpd
from typing import Tuple, List, Union, Dict
import tempfile
import os


def check_raster_crs(raster_path: str, target_crs: str = "EPSG:4326") -> bool:
    """Check if raster has the target CRS"""
    with rasterio.open(raster_path) as src:
        return src.crs.to_string() == target_crs


def reproject_raster(src_path: str, dst_path: str, target_crs: str = "EPSG:4326"):
    """Reproject raster to target CRS"""
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        
        with rasterio.open(dst_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )


def sample_raster_at_points(raster_path: str, points: List[Tuple[float, float]]) -> List[float]:
    """Sample raster values at given points"""
    with rasterio.open(raster_path) as src:
        # Sample returns an iterator, so we convert to list
        values = list(src.sample(points))
        return [float(val[0]) if val[0] != src.nodata else np.nan for val in values]


def extract_raster_stats_for_polygon(raster_path: str, polygon) -> Dict[str, float]:
    """Extract raster statistics for a polygon"""
    with rasterio.open(raster_path) as src:
        # Get the raster data and transform
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        
        # Create a mask for the polygon
        out_image, out_transform = mask(src, [polygon], crop=True)
        out_image = out_image[0]
        
        # Filter out nodata values
        valid_data = out_image[out_image != nodata] if nodata is not None else out_image.flatten()
        
        if len(valid_data) == 0:
            return {
                'mean': np.nan,
                'min': np.nan,
                'max': np.nan,
                'std': np.nan
            }
        
        return {
            'mean': float(np.mean(valid_data)),
            'min': float(np.min(valid_data)),
            'max': float(np.max(valid_data)),
            'std': float(np.std(valid_data))
        }


def create_flood_extent_polygon(wse_path: str, dem_path: str = None) -> gpd.GeoDataFrame:
    """
    Create polygon from WSE extent (where WSE has valid values)
    If dem_path is provided, creates polygon where WSE > DEM
    """
    with rasterio.open(wse_path) as wse_src:
        wse_data = wse_src.read(1)
        
        if dem_path:
            # Original behavior: WSE > DEM
            with rasterio.open(dem_path) as dem_src:
                # Check if rasters have same dimensions
                if wse_data.shape != dem_src.shape or wse_src.bounds != dem_src.bounds:
                    raise ValueError(
                        f"DEM and WSE rasters must have same dimensions and extent. "
                        f"DEM: {dem_src.shape}, WSE: {wse_data.shape}"
                    )
                
                dem_data = dem_src.read(1)
                # Create flood mask (WSE > DEM)
                flood_mask = (wse_data > dem_data) & (wse_data != wse_src.nodata) & (dem_data != dem_src.nodata)
        else:
            # Simplified: just use WSE extent (where WSE has valid values)
            if wse_src.nodata is not None:
                flood_mask = (wse_data != wse_src.nodata) & (wse_data > 0)
            else:
                # If no nodata value is set, assume any positive value is valid
                flood_mask = wse_data > 0
        
        # Convert to polygons
        shapes_generator = shapes(
            flood_mask.astype(np.uint8),
            mask=flood_mask,
            transform=wse_src.transform
        )
        
        polygons = []
        for geom, value in shapes_generator:
            if value == 1:  # Flooded areas
                polygons.append(shape(geom))
        
        if not polygons:
            raise ValueError("No flood extent found in WSE raster")
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({'flooded': [1] * len(polygons)}, geometry=polygons, crs=wse_src.crs)
        
        # Dissolve all polygons into one
        gdf = gdf.dissolve()
        
        return gdf


def extract_elevation_profile(raster_path: str, line_geometry) -> Tuple[List[float], List[float]]:
    """Extract elevation profile along a line"""
    with rasterio.open(raster_path) as src:
        # Sample points along the line
        distances = []
        elevations = []
        
        # Get points along the line at regular intervals
        num_points = int(line_geometry.length * 111000)  # Approximate meters for lat/lon
        num_points = max(100, min(num_points, 1000))  # Limit number of points
        
        for i in range(num_points):
            point = line_geometry.interpolate(i / (num_points - 1), normalized=True)
            distances.append(i / (num_points - 1) * line_geometry.length * 111000)  # Convert to approx meters
            
            # Sample raster at this point
            val = list(src.sample([(point.x, point.y)]))[0]
            elevations.append(float(val[0]) if val[0] != src.nodata else np.nan)
        
        return distances, elevations