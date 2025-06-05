"""Configuration constants and defaults for the hydro toolkit"""

# Coordinate Reference System
REQUIRED_CRS = "EPSG:4326"

# File type mappings
RASTER_EXTENSIONS = ['.tif', '.tiff', '.geotiff']
VECTOR_EXTENSIONS = ['.shp']

# Raster names
RASTER_TYPES = {
    'dem': 'Digital Elevation Model (DEM)',
    'wse': 'Maximum Water Surface Elevation (WSE)',
    'velocity': 'Maximum Velocity',
    'depth': 'Maximum Depth',
    'arrival_time': 'Arrival Time'
}

# Default column names
DEFAULT_ID_COLUMN = 'id'

# Plot settings
PLOT_HEIGHT = 600
PLOT_WIDTH = 1000

# Map settings
MAP_ZOOM_START = 12

# Microsoft Buildings dataset URL
BUILDINGS_DATASET_URL = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"