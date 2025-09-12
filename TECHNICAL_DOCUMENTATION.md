# 🔧 CP2B Maps - Technical Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)  
3. [Core Technologies](#core-technologies)
4. [Project Structure](#project-structure)
5. [Data Model](#data-model)
6. [API Reference](#api-reference)
7. [Performance Features](#performance-features)
8. [Configuration](#configuration)
9. [Installation & Setup](#installation--setup)
10. [Development Guidelines](#development-guidelines)

---

## 📖 Project Overview

**CP2B Maps** is a comprehensive Streamlit-based web application for analyzing biogas potential in São Paulo municipalities. The application provides interactive visualization, advanced analytics, and detailed exploration of organic waste data across 645 municipalities.

### Key Capabilities
- **Interactive Mapping**: Dynamic Folium-based maps with multiple visualization styles
- **Multi-dimensional Analysis**: 15 types of organic residues across agricultural, livestock, and urban sectors
- **Advanced Analytics**: Statistical analysis, correlations, regional comparisons, and portfolio analysis
- **Performance Optimized**: Cached operations, optimized geometries, and efficient data handling
- **Professional UI/UX**: Modern interface with hierarchical controls and real-time feedback

---

## 🏗️ Architecture

### Application Structure
```
CP2B Maps (Streamlit Application)
├── Frontend Layer (Streamlit UI)
│   ├── Interactive Maps (Folium)
│   ├── Data Visualization (Plotly)
│   └── Control Interface (Hierarchical Sidebar)
├── Processing Layer (Python Backend)
│   ├── Data Processing (Pandas)
│   ├── Geospatial Operations (GeoPandas)
│   ├── Statistical Analysis (NumPy)
│   └── Caching System (Streamlit Cache)
├── Data Layer
│   ├── SQLite Database (Municipality Data)
│   ├── Shapefiles (Geospatial Data)
│   ├── GeoParquet (Optimized Geometries)
│   └── Raster Data (MapBiomas)
└── Configuration Layer
    ├── Streamlit Config (Performance Settings)
    ├── Environment Variables (Logging)
    └── Requirements (Dependencies)
```

### Design Patterns
- **MVC Pattern**: Clear separation between UI, processing, and data
- **Caching Strategy**: Multi-level caching for performance optimization
- **Modular Functions**: Well-defined functions for specific operations
- **Error Handling**: Comprehensive error handling with graceful degradation

---

## 💻 Core Technologies

### Primary Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| **Streamlit** | ≥1.31.0 | Web application framework |
| **Pandas** | ≥2.1.0 | Data manipulation and analysis |
| **GeoPandas** | ≥0.14.0 | Geospatial data processing |
| **Folium** | ≥0.15.0 | Interactive mapping |
| **Plotly** | ≥5.17.0 | Data visualization |
| **NumPy** | ≥1.24.0 | Numerical computing |

### Supporting Libraries
| Library | Purpose |
|---------|---------|
| **streamlit-folium** | Streamlit-Folium integration |
| **rasterio** | Raster data processing |
| **shapely** | Geometric operations |
| **matplotlib** | Additional plotting capabilities |
| **pillow** | Image processing |
| **jenkspy** | Natural breaks classification |

---

## 📁 Project Structure

```
CP2B_Maps/
├── 📄 Configuration Files
│   ├── .streamlit/
│   │   └── config.toml              # Streamlit performance settings
│   ├── requirements.txt             # Python dependencies
│   ├── packages.txt                 # System dependencies
│   └── setup.py                     # Installation script
├── 📊 Data Files
│   ├── data/
│   │   ├── cp2b_maps.db            # SQLite database (645 municipalities)
│   │   └── Dados_Por_Municipios_SP.xls # Raw data source
│   ├── shapefile/                   # Geospatial vector data
│   │   ├── APPs_Hidrografia.*       # Hydrography APPs
│   │   ├── ETEs_2019_SP.*           # Wastewater treatment plants
│   │   ├── Linhas_De_Transmissao_Energia.* # Power transmission lines
│   │   └── Subestacoes_Energia.*    # Power substations
│   ├── geoparquet/                  # Optimized geometries
│   │   └── Areas_Urbanas_SP.parquet # Urban areas (optimized)
│   └── rasters/                     # Raster data
│       └── MapBiomas_SP_2024_*.tif  # MapBiomas land use data
├── 💾 Source Code
│   └── src/
│       ├── streamlit/
│       │   └── app.py               # Main application (5,681 lines)
│       ├── database/
│       │   ├── data_loader.py       # Database operations
│       │   └── migrations.py        # Database migrations
│       └── raster/
│           └── raster_loader.py     # Raster data processing
├── 🛠️ Utility Scripts
│   ├── create_centroid_map_optimized.py # Map generation utilities
│   ├── optimize_geometries.py       # Geometry optimization
│   └── update_regions.py            # Regional data updates
└── 📚 Documentation
    ├── README.md                    # Project overview
    ├── PROJECT_SUMMARY.md           # Detailed project summary
    ├── MELHORIAS_UI_IMPLEMENTADAS.md # UI improvements documentation
    ├── CONTEXTO_CLAUDE_CODE.md      # Claude Code context
    └── DEVELOPMENT_ROADMAP.md       # Future development plans
```

---

## 🗄️ Data Model

### Municipality Database Schema
```sql
Table: municipalities
├── id (INTEGER PRIMARY KEY)
├── nome_municipio (TEXT)           -- Municipality name
├── regiao_administrativa (TEXT)    -- Administrative region
├── latitude (REAL)                 -- Latitude coordinate
├── longitude (REAL)                -- Longitude coordinate
├── populacao_2022 (INTEGER)        -- 2022 population
├── total_final_nm_ano (REAL)       -- Total biogas potential (Nm³/year)
├── total_agricola_nm_ano (REAL)    -- Agricultural total
├── total_pecuaria_nm_ano (REAL)    -- Livestock total
├── total_urbano_nm_ano (REAL)      -- Urban total
├── biogas_cana_nm_ano (REAL)       -- Sugarcane biogas potential
├── biogas_soja_nm_ano (REAL)       -- Soybean biogas potential
├── biogas_milho_nm_ano (REAL)      -- Corn biogas potential
├── biogas_cafe_nm_ano (REAL)       -- Coffee biogas potential
├── biogas_citros_nm_ano (REAL)     -- Citrus biogas potential
├── biogas_bovinos_nm_ano (REAL)    -- Cattle biogas potential
├── biogas_suino_nm_ano (REAL)      -- Swine biogas potential
├── biogas_aves_nm_ano (REAL)       -- Poultry biogas potential
├── biogas_piscicultura_nm_ano (REAL) -- Aquaculture biogas potential
├── rsu_total_nm_ano (REAL)         -- Urban solid waste
└── rpo_total_nm_ano (REAL)         -- Pruning residues
```

### Residue Classification System
```python
RESIDUE_CATEGORIES = {
    'Agricultural': [
        'biogas_cana_nm_ano',      # Sugarcane
        'biogas_soja_nm_ano',      # Soybean  
        'biogas_milho_nm_ano',     # Corn
        'biogas_cafe_nm_ano',      # Coffee
        'biogas_citros_nm_ano'     # Citrus
    ],
    'Livestock': [
        'biogas_bovinos_nm_ano',   # Cattle
        'biogas_suino_nm_ano',     # Swine
        'biogas_aves_nm_ano',      # Poultry
        'biogas_piscicultura_nm_ano' # Aquaculture
    ],
    'Urban': [
        'rsu_total_nm_ano',        # Urban solid waste
        'rpo_total_nm_ano'         # Pruning residues
    ],
    'Totals': [
        'total_final_nm_ano',      # Overall total
        'total_agricola_nm_ano',   # Agricultural total
        'total_pecuaria_nm_ano',   # Livestock total
        'total_urbano_nm_ano'      # Urban total
    ]
}
```

---

## 🔌 API Reference

### Core Functions

#### Data Loading & Caching
```python
@st.cache_data(ttl=3600)
def load_municipalities() -> pd.DataFrame
    """Load municipality data from database with error handling"""
    
@st.cache_data(ttl=3600) 
def prepare_layer_data() -> dict
    """Pre-load all layer data with caching"""
    
@st.cache_data(ttl=3600)
def load_shapefile_cached(shapefile_path: str, simplify_tolerance: float = 0.001) -> gpd.GeoDataFrame
    """Load shapefile with caching and optional simplification"""
```

#### Map Generation
```python
def create_centroid_map_optimized(
    df: pd.DataFrame,
    display_col: str,
    filters: dict = None,
    get_legend_only: bool = False,
    search_term: str = "",
    viz_type: str = "Círculos Proporcionais",
    **layer_options
) -> folium.Map
    """Ultra-optimized map creation with customizable layers"""
```

#### Utility Functions
```python
@st.cache_data
def get_residue_label(column_name: str) -> str
    """Convert column name to readable label with caching"""
    
@st.cache_data
def format_number(value: float, unit: str = "Nm³/ano", scale: int = 1) -> str
    """Format numbers with proper scaling and caching"""
    
def safe_divide(numerator: float, denominator: float, default: float = 0) -> float
    """Safe division with default value"""
```

#### Analysis Functions
```python
def analyze_municipalities_in_radius(
    df_municipalities: pd.DataFrame,
    center_lat: float, 
    center_lon: float,
    radius_km: float
) -> pd.DataFrame
    """Analyze municipalities within specified radius"""
    
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float
    """Calculate distance between two points using Haversine formula"""
```

---

## ⚡ Performance Features

### Caching System
- **7 Cached Functions**: Strategic caching of expensive operations
- **Cache Coverage**: 15.9% of functions cached for optimal performance
- **TTL Strategy**: 1-hour TTL for data that changes infrequently
- **Memory Efficient**: Cached utility functions reduce repetitive calculations

### Streamlit Optimizations
```toml
[global]
enableStaticServing = true      # Better static resource handling
showErrorDetails = true         # Development error details

[server]  
fastReruns = true              # Faster app reruns
enableCORS = false             # Reduced network overhead
maxUploadSize = 200            # Support for larger datasets (200MB)
```

### Data Optimizations
- **GeoParquet Format**: 89-99% file size reduction for geometries
- **Geometry Simplification**: Tolerance-based simplification for different zoom levels
- **Intelligent Detail Levels**: Automatic detail selection based on municipality count

### Logging System
```python
# Environment-configurable logging
LOG_LEVEL = os.getenv('CP2B_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

## ⚙️ Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `CP2B_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Streamlit Configuration (.streamlit/config.toml)
```toml
[global]
dataFrameSerialization = "legacy"
showErrorDetails = true
enableStaticServing = true

[server]
runOnSave = true
port = 8501
fastReruns = true
enableCORS = false
maxUploadSize = 200

[theme]
primaryColor = "#2E8B57"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- Git

### Installation Steps
```bash
# 1. Clone repository
git clone https://github.com/aikiesan/cp2b_maps.git
cd cp2b_maps

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install system dependencies (if needed)
# On Ubuntu/Debian: sudo apt-get install gdal-bin libgdal-dev

# 5. Set environment variables (optional)
export CP2B_LOG_LEVEL=DEBUG  # For development

# 6. Run application
streamlit run src/streamlit/app.py
```

### Docker Setup (Alternative)
```dockerfile
# Dockerfile example
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "src/streamlit/app.py"]
```

---

## 🔧 Development Guidelines

### Code Style
- **PEP 8 Compliance**: Follow Python style guidelines
- **Import Organization**: Standard library → Third-party → Local imports
- **Function Documentation**: Comprehensive docstrings for all functions
- **Error Handling**: Graceful error handling with user-friendly messages

### Performance Best Practices
1. **Use Caching**: Add `@st.cache_data` to expensive functions
2. **Optimize Geometries**: Use appropriate simplification tolerances
3. **Batch Operations**: Process data in batches when possible
4. **Monitor Memory**: Use efficient data structures

### Testing Approach
```python
# Test syntax
python -m py_compile src/streamlit/app.py

# Test configuration
python -c "import toml; toml.load('.streamlit/config.toml')"

# Test cached functions
python -c "from src.streamlit.app import format_number; print(format_number(1000))"
```

### Git Workflow
```bash
# Feature development
git checkout -b feature/new-feature
git add .
git commit -m "feat: description"
git push origin feature/new-feature

# Create pull request for review
```

---

## 📊 Metrics & Monitoring

### Application Metrics
- **Total Functions**: 44
- **Cached Functions**: 7 (15.9% coverage)
- **Application Size**: 271.4KB
- **Dependencies**: 14 well-managed packages
- **Configuration Lines**: 25

### Performance Targets
- **Map Loading**: < 2 seconds
- **Data Filtering**: < 500ms  
- **Cache Hit Ratio**: > 80%
- **Memory Usage**: < 500MB

---

## 🚀 Future Enhancements

### Planned Features
1. **Real-time Data Updates**: Integration with live data sources
2. **Advanced Analytics**: Machine learning predictions
3. **Export Capabilities**: PDF report generation
4. **API Endpoints**: REST API for external integrations
5. **Mobile Optimization**: Responsive design improvements

### Technical Improvements
1. **Database Migration**: PostgreSQL with PostGIS
2. **Microservices**: Separate analytics and visualization services
3. **Container Orchestration**: Kubernetes deployment
4. **Monitoring**: Application performance monitoring (APM)

---

*This technical documentation is maintained alongside the codebase and should be updated with any architectural changes or new features.*