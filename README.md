
# 🌊 HydroImpact: Dam Breach Post Processing Toolkit

A Streamlit application for processing and analyzing hydrodynamic modeling outputs from HEC-RAS dam breach simulations. This tool automates the extraction of flood impact data for buildings, cross-sections, and points of interest.

---

## 📋 Features

### 🏢 Building Footprint Analysis
- **Automatic Building Detection** from Microsoft’s Global Buildings dataset
- **Custom Building Import** using shapefiles
- **Statistics Extraction** (mean, min, max, std) from rasters
- **Interactive Map** with WSE overlay and building highlights
- **Export Options**: CSV + zipped shapefile

### 📊 Cross Section Visualization
- Terrain (DEM) and water surface elevation (WSE) profiles
- Plotly-based interactive visuals
- Batch cross-section processing
- Export all plots as a single HTML report

### 📍 Point-Based Analysis
- Extracts raster values at specific points
- Flexible column selection for IDs
- Includes calculated depth above ground
- CSV output

### 🔄 Automatic CRS Management
- Checks coordinate system consistency
- One-click reprojection to EPSG:4326
- Reprojects only the needed files

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- `pip` package manager

### Setup
```bash
git clone https://github.com/mohsennasab/HydroImpact.git
cd hydro-toolkit

# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 📁 Required Input Files

### Raster Files (GeoTIFF)
- ✅ DEM (Digital Elevation Model) – Required  
- ✅ WSE (Max Water Surface Elevation) – Required  
- ➕ Max Velocity – Optional  
- ➕ Max Depth – Optional  
- ➕ Arrival Time – Optional  

### Vector Files (Shapefile)
- ✅ Cross-section polylines – For elevation profiles  
- ✅ Points of interest – For point-based values  
- ➕ Building footprints – Optional (can auto-download)

*Note: Files will be automatically reprojected to EPSG:4326 if needed.*

---

## 🎯 Usage

### Start the App
```bash
# Option 1: With launcher script
python run.py

# Option 2: Direct Streamlit call
streamlit run app/main.py
```

App will open at: [http://localhost:8502](http://localhost:8502)

### Workflow

1. **Upload Files**
   - Upload DEM and WSE (required)
   - Upload vector shapefiles (.shp, .shx, .dbf, .prj)

2. **Check/Reproject CRS**
   - Click 🔍 "Check CRS"
   - Click 🔄 "Auto-Reproject" if needed

3. **Run Analysis**
   - Choose a tab (Buildings, Cross Sections, or Points)
   - Configure inputs and run

4. **View Results & Export**
   - View tables and plots in-app
   - Download CSVs, shapefiles, or HTML reports

---

## 📊 Output Files

| File Name | Description |
|-----------|-------------|
| `building_analysis_results.csv` | Building-level stats |
| `building_footprints.zip` | Zipped shapefile of buildings |
| `cross_section_profiles.html` | Interactive cross-section plots |
| `point_analysis_results.csv` | Raster values at point locations |

---

## 🏗️ Project Structure

```
hydro_toolkit/
├── app/
│   ├── main.py              # Streamlit app interface
│   ├── config.py            # Configuration constants
│   └── ui_helpers.py        # UI components
├── modules/
│   ├── crs_check.py         # CRS validation and reprojection
│   ├── building_analysis.py # Building analysis logic
│   ├── cross_section_plot.py # Cross-section plotting
│   └── point_analysis.py    # Point-based raster extraction
├── utils/
│   ├── raster_utils.py      # Raster helpers
│   └── vector_utils.py      # Vector helpers
├── requirements.txt         # Dependency list
├── run.py                   # Launch script
└── README.md                # You’re reading it!
```

---

## 🛠️ Technical Details

**Technologies Used**
- Streamlit
- GeoPandas
- Rasterio
- Plotly
- Folium
- Mercantile (for building tiles)

**CRS Handling**
- Enforced EPSG:4326
- Auto-reprojection included

**Building Footprints**
- From Microsoft’s ML Global Building Footprints when not provided

---

## 🤝 Contributing

Contributions are welcome!  
Please open an issue for major changes before submitting a pull request.

---

## 📝 License

This project is licensed under the MIT License – see the `LICENSE` file for details.

---

## 📧 Contact

Questions? 
Contact Mohsen: www.hydromohsen.com
