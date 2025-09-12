# 👨‍💻 CP2B Maps - Developer Guide

## 📋 Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Code Structure & Conventions](#code-structure--conventions)
4. [API Reference & Extension Points](#api-reference--extension-points)
5. [Database Schema & Migrations](#database-schema--migrations)
6. [Performance Optimization](#performance-optimization)
7. [Testing & Quality Assurance](#testing--quality-assurance)
8. [Deployment & Production](#deployment--production)
9. [Contributing Guidelines](#contributing-guidelines)
10. [Troubleshooting Development Issues](#troubleshooting-development-issues)

---

## 🔧 Development Environment Setup

### Prerequisites
```bash
# Required versions
Python 3.8+
Git 2.25+
Node.js 16+ (optional, for frontend tools)
```

### Local Development Setup
```bash
# 1. Clone and navigate
git clone https://github.com/aikiesan/cp2b_maps.git
cd cp2b_maps

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .  # Development installation

# 4. Set development environment variables
export CP2B_LOG_LEVEL=DEBUG
export STREAMLIT_ENV=development

# 5. Run in development mode
streamlit run src/streamlit/app.py --server.runOnSave true
```

### Development Tools Setup
```bash
# Code quality tools (optional)
pip install black isort flake8 mypy
pip install pre-commit

# Set up pre-commit hooks
pre-commit install
```

### IDE Configuration (VS Code)
```json
// .vscode/settings.json
{
    "python.defaultInterpreter": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

---

## 🏗️ Architecture Deep Dive

### Application Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
├─────────────────────────────────────────────────────────────┤
│  Navigation Layer    │  UI Components  │  State Management  │
│  ├── Navigation      │  ├── Maps       │  ├── Session State │
│  ├── Page Routing    │  ├── Charts     │  ├── Cache        │
│  └── Layout Control  │  └── Controls   │  └── Filters      │
├─────────────────────────────────────────────────────────────┤
│                    Processing Layer                          │
├─────────────────────────────────────────────────────────────┤
│  Data Processing     │  Geospatial     │  Analysis Engine   │
│  ├── Data Loading    │  ├── Geometry   │  ├── Statistics    │
│  ├── Filtering       │  ├── Mapping    │  ├── Correlations  │
│  ├── Transformations │  ├── Projections│  └── Classifications│
│  └── Caching         │  └── Simplify   │                    │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                             │
├─────────────────────────────────────────────────────────────┤
│  SQLite Database     │  Shapefiles     │  Raster Data       │
│  ├── Municipalities  │  ├── Infra      │  ├── MapBiomas     │
│  ├── Statistics      │  ├── Reference  │  └── Land Use      │
│  └── Metadata        │  └── Boundaries │                    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow
```python
# Simplified data flow diagram
User Input → Filter State → Data Loading → Processing → Caching → Visualization
    ↓              ↓            ↓             ↓           ↓          ↓
Navigation → Session State → Database → Pandas/GeoPandas → Streamlit Cache → Folium/Plotly
```

### Module Dependencies
```python
# Core dependency structure
src/streamlit/app.py
├── Standard Library
│   ├── logging, os, pickle, re, sqlite3, sys
│   ├── functools (lru_cache)
│   └── pathlib (Path)
├── Third-party Libraries
│   ├── streamlit (core framework)
│   ├── pandas, numpy (data processing)
│   ├── geopandas, shapely (geospatial)
│   ├── folium (mapping)
│   └── plotly (visualization)
└── Local Modules
    ├── database/ (data operations)
    ├── raster/ (raster processing)
    └── utilities (helper functions)
```

---

## 📝 Code Structure & Conventions

### File Organization
```
src/
├── streamlit/
│   ├── app.py                 # Main application (5,681 lines)
│   └── __init__.py
├── database/
│   ├── __init__.py
│   ├── data_loader.py         # Database operations
│   └── migrations.py          # Schema migrations
├── raster/
│   ├── __init__.py
│   └── raster_loader.py       # Raster data processing
└── __init__.py
```

### Coding Conventions

#### Import Organization (PEP 8)
```python
# Standard library imports
import logging
import os
import sqlite3
from pathlib import Path

# Third-party imports
import pandas as pd
import streamlit as st
import folium

# Local imports
from database import load_data
from raster import process_raster
```

#### Function Naming & Documentation
```python
@st.cache_data(ttl=3600)
def load_municipalities() -> pd.DataFrame:
    """
    Load municipality data from database with error handling.
    
    Returns:
        pd.DataFrame: DataFrame containing municipality data with columns:
            - nome_municipio (str): Municipality name
            - latitude, longitude (float): Coordinates
            - total_final_nm_ano (float): Total biogas potential
            - ... (other biogas potential columns)
            
    Raises:
        ConnectionError: If database connection fails
        ValueError: If data validation fails
    """
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query("SELECT * FROM municipalities", conn)
    except Exception as e:
        logger.error(f"Failed to load municipalities: {e}")
        return pd.DataFrame()
```

#### Error Handling Pattern
```python
def safe_operation(data, operation_name="operation"):
    """Standard error handling pattern for data operations."""
    try:
        # Operation logic here
        result = perform_operation(data)
        logger.info(f"{operation_name} completed successfully")
        return result
    except SpecificError as e:
        logger.warning(f"{operation_name} failed with specific error: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error in {operation_name}: {e}")
        return fallback_value
```

### Performance-Critical Functions

#### Caching Strategy
```python
# High-frequency utility functions
@st.cache_data
def get_residue_label(column_name: str) -> str:
    """Cached dictionary lookup for residue labels."""

@st.cache_data  
def format_number(value: float, unit: str = "Nm³/ano", scale: int = 1) -> str:
    """Cached number formatting with scaling."""

# Data loading functions
@st.cache_data(ttl=3600)  # 1-hour TTL
def load_shapefile_cached(shapefile_path: str, simplify_tolerance: float = 0.001) -> gpd.GeoDataFrame:
    """Cached shapefile loading with simplification."""

@st.cache_data(ttl=3600)
def prepare_layer_data() -> dict:
    """Pre-load all geospatial layers with caching."""
```

#### Memory Management
```python
def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame memory usage."""
    # Convert object columns to category where appropriate
    for col in df.select_dtypes(include=['object']):
        if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique values
            df[col] = df[col].astype('category')
    
    # Downcast numeric types
    df = df.select_dtypes(include=['int']).apply(pd.to_numeric, downcast='integer')
    df = df.select_dtypes(include=['float']).apply(pd.to_numeric, downcast='float')
    
    return df
```

---

## 🔌 API Reference & Extension Points

### Core Data Loading API
```python
# Primary data access functions
def load_municipalities() -> pd.DataFrame:
    """Load all municipality data."""

def load_shapefile_cached(path: str, tolerance: float = 0.001) -> gpd.GeoDataFrame:
    """Load and cache shapefile with optional simplification."""

def prepare_layer_data() -> dict:
    """Pre-load all geospatial layers."""
```

### Filtering & Analysis API
```python
def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply user-defined filters to municipality data."""

def analyze_municipalities_in_radius(
    df: pd.DataFrame, 
    center_lat: float, 
    center_lon: float, 
    radius_km: float
) -> pd.DataFrame:
    """Spatial proximity analysis."""

def calculate_correlations(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Calculate correlation matrix for specified columns."""
```

### Visualization Extension Points
```python
def create_custom_map_layer(gdf: gpd.GeoDataFrame, style_function: callable) -> folium.FeatureGroup:
    """Create custom map layer for additional data visualization."""

def add_custom_analysis_tab(df: pd.DataFrame, analysis_function: callable) -> None:
    """Add custom analysis tab to the interface."""
```

### Adding New Residue Types
```python
# 1. Update RESIDUE_OPTIONS constant
RESIDUE_OPTIONS = {
    # Existing options...
    'New Residue Type': 'new_residue_column_name',
}

# 2. Update database schema (if needed)
# 3. Add to appropriate category in analysis functions
# 4. Update documentation and user guide
```

### Custom Visualization Styles
```python
def create_custom_visualization_style(df: pd.DataFrame, display_col: str) -> dict:
    """
    Create custom visualization parameters.
    
    Args:
        df: Municipality data
        display_col: Column to visualize
        
    Returns:
        dict: Visualization parameters including colors, sizes, opacity
    """
    # Custom logic here
    return {
        'colors': color_scheme,
        'sizes': size_mapping,
        'opacity': opacity_values
    }
```

---

## 🗄️ Database Schema & Migrations

### Current Schema (SQLite)
```sql
-- Municipality data table
CREATE TABLE municipalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_municipio TEXT NOT NULL,
    regiao_administrativa TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    populacao_2022 INTEGER,
    
    -- Biogas potential columns (Nm³/year)
    total_final_nm_ano REAL,
    total_agricola_nm_ano REAL,
    total_pecuaria_nm_ano REAL,
    total_urbano_nm_ano REAL,
    
    -- Agricultural residues
    biogas_cana_nm_ano REAL,
    biogas_soja_nm_ano REAL,
    biogas_milho_nm_ano REAL,
    biogas_cafe_nm_ano REAL,
    biogas_citros_nm_ano REAL,
    
    -- Livestock residues
    biogas_bovinos_nm_ano REAL,
    biogas_suino_nm_ano REAL,
    biogas_aves_nm_ano REAL,
    biogas_piscicultura_nm_ano REAL,
    
    -- Urban residues
    rsu_total_nm_ano REAL,
    rpo_total_nm_ano REAL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_municipalities_name ON municipalities(nome_municipio);
CREATE INDEX idx_municipalities_coords ON municipalities(latitude, longitude);
CREATE INDEX idx_municipalities_total ON municipalities(total_final_nm_ano);
```

### Migration System
```python
# src/database/migrations.py
class Migration:
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
    
    def up(self, connection: sqlite3.Connection) -> None:
        """Apply migration."""
        raise NotImplementedError
    
    def down(self, connection: sqlite3.Connection) -> None:
        """Rollback migration."""
        raise NotImplementedError

class Migration_001_AddIndexes(Migration):
    def __init__(self):
        super().__init__("001", "Add performance indexes")
    
    def up(self, conn):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_municipalities_name ON municipalities(nome_municipio)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_municipalities_coords ON municipalities(latitude, longitude)")
```

### Data Validation
```python
def validate_municipality_data(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """
    Validate municipality data integrity.
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    # Required columns check
    required_cols = ['nome_municipio', 'latitude', 'longitude', 'total_final_nm_ano']
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
    
    # Data range validation
    if 'latitude' in df.columns:
        if not df['latitude'].between(-34, -19).all():
            errors.append("Latitude values outside São Paulo state range")
    
    if 'longitude' in df.columns:  
        if not df['longitude'].between(-53, -44).all():
            errors.append("Longitude values outside São Paulo state range")
    
    # Non-negative biogas potential values
    biogas_cols = [col for col in df.columns if 'nm_ano' in col]
    for col in biogas_cols:
        if (df[col] < 0).any():
            errors.append(f"Negative values found in {col}")
    
    return len(errors) == 0, errors
```

---

## ⚡ Performance Optimization

### Caching Strategy
```python
# Current caching implementation (7 cached functions)
CACHE_COVERAGE = 15.9%  # 7 out of 44 functions

# Cache hierarchy
L1_CACHE = "@st.cache_data"           # Fast, memory-based
L2_CACHE = "@st.cache_data(ttl=3600)" # Time-based expiration
L3_CACHE = "File system cache"        # Persistent storage
```

### Optimization Checklist
```python
def performance_optimization_checklist():
    """Development checklist for performance optimization."""
    return {
        'data_loading': {
            'use_parquet_format': True,      # ✅ Implemented for geometries
            'cache_expensive_operations': True, # ✅ 7 cached functions
            'optimize_query_filters': True,   # ✅ Database indexes
            'batch_operations': True,        # ⚠️ Could be improved
        },
        'visualization': {
            'simplify_geometries': True,     # ✅ Implemented
            'use_clustering': True,          # ✅ Map clustering
            'optimize_layer_loading': True,  # ✅ On-demand loading
            'cache_map_tiles': False,        # ❌ Could be added
        },
        'memory_management': {
            'dataframe_optimization': False, # ❌ Could be implemented
            'garbage_collection': False,    # ❌ Could be added
            'memory_profiling': False,      # ❌ Development tool
        }
    }
```

### Profiling & Monitoring
```python
# Development profiling
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    """Decorator to profile function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # Top 10 functions
        
        return result
    return wrapper

# Memory monitoring
def monitor_memory_usage():
    """Monitor current memory usage."""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024,  # MB
        'percent': process.memory_percent()
    }
```

### Database Optimization
```python
# Query optimization
def optimized_municipality_query(filters: dict) -> str:
    """Generate optimized SQL query based on filters."""
    base_query = "SELECT * FROM municipalities"
    where_clauses = []
    
    # Use indexes effectively
    if 'nome_municipio' in filters:
        where_clauses.append("nome_municipio LIKE ?")
    
    if 'min_total' in filters:
        where_clauses.append("total_final_nm_ano >= ?")
    
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    return base_query + " ORDER BY total_final_nm_ano DESC"
```

---

## 🧪 Testing & Quality Assurance

### Testing Framework
```python
# Test structure
tests/
├── unit/
│   ├── test_data_loading.py
│   ├── test_filtering.py
│   ├── test_calculations.py
│   └── test_utilities.py
├── integration/
│   ├── test_map_generation.py
│   ├── test_analysis_workflows.py
│   └── test_data_pipeline.py
├── performance/
│   ├── test_caching.py
│   ├── test_memory_usage.py
│   └── test_load_times.py
└── conftest.py
```

### Unit Testing Examples
```python
# tests/unit/test_utilities.py
import pytest
import pandas as pd
from src.streamlit.app import format_number, safe_divide, get_residue_label

class TestUtilityFunctions:
    def test_format_number_basic(self):
        assert format_number(1000) == "1,000 Nm³/ano"
        assert format_number(5000000, "test", 1000000) == "5.0M test"
        assert format_number(0) == "0 Nm³/ano"
    
    def test_safe_divide(self):
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0  # Default value
        assert safe_divide(10, 0, -1) == -1  # Custom default
    
    def test_get_residue_label(self):
        assert get_residue_label('total_final_nm_ano') == 'Potencial Total'
        assert get_residue_label('unknown_column') == 'unknown_column'

# tests/unit/test_data_loading.py  
import pytest
from unittest.mock import patch, MagicMock
from src.streamlit.app import load_municipalities

class TestDataLoading:
    @patch('src.streamlit.app.sqlite3.connect')
    def test_load_municipalities_success(self, mock_connect):
        # Mock database connection
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        # Mock pandas read_sql_query
        with patch('pandas.read_sql_query') as mock_read_sql:
            expected_df = pd.DataFrame({'nome_municipio': ['Test City']})
            mock_read_sql.return_value = expected_df
            
            result = load_municipalities()
            
            assert not result.empty
            assert 'nome_municipio' in result.columns
```

### Integration Testing
```python
# tests/integration/test_analysis_workflows.py
import pytest
import streamlit as st
from src.streamlit.app import apply_filters, create_centroid_map_optimized

class TestAnalysisWorkflows:
    @pytest.fixture
    def sample_municipality_data(self):
        return pd.DataFrame({
            'nome_municipio': ['City A', 'City B', 'City C'],
            'latitude': [-23.5, -23.6, -23.7],
            'longitude': [-46.6, -46.7, -46.8],
            'total_final_nm_ano': [1000, 2000, 3000]
        })
    
    def test_filtering_workflow(self, sample_municipality_data):
        filters = {'search_term': 'City A'}
        result = apply_filters(sample_municipality_data, filters)
        
        assert len(result) == 1
        assert result.iloc[0]['nome_municipio'] == 'City A'
    
    def test_map_generation_workflow(self, sample_municipality_data):
        # Test map generation doesn't crash
        map_obj = create_centroid_map_optimized(
            sample_municipality_data,
            'total_final_nm_ano'
        )
        
        assert map_obj is not None
        assert hasattr(map_obj, '_name')  # Folium map object
```

### Performance Testing
```python
# tests/performance/test_caching.py
import time
import pytest
from src.streamlit.app import load_municipalities, format_number

class TestCachingPerformance:
    def test_municipality_loading_cache(self):
        """Test that repeated calls are faster due to caching."""
        # First call (cache miss)
        start_time = time.time()
        df1 = load_municipalities()
        first_call_time = time.time() - start_time
        
        # Second call (cache hit)
        start_time = time.time()
        df2 = load_municipalities()
        second_call_time = time.time() - start_time
        
        # Cache hit should be significantly faster
        assert second_call_time < first_call_time * 0.1  # At least 10x faster
        assert df1.equals(df2)  # Same data
    
    def test_format_number_cache_performance(self):
        """Test cached utility function performance."""
        # Test data
        test_values = [1000, 5000, 10000] * 100
        
        # Measure performance
        start_time = time.time()
        results = [format_number(val) for val in test_values]
        total_time = time.time() - start_time
        
        # Should complete quickly due to caching
        assert total_time < 1.0  # Less than 1 second
        assert len(results) == len(test_values)
```

### Quality Assurance Tools
```bash
# Code quality commands
black src/ tests/                    # Code formatting
isort src/ tests/                    # Import sorting  
flake8 src/ tests/                   # Linting
mypy src/                           # Type checking
pytest tests/ -v                    # Run tests
pytest tests/ --cov=src --cov-report=html  # Coverage report
```

---

## 🚀 Deployment & Production

### Production Configuration
```bash
# Production environment variables
export CP2B_LOG_LEVEL=INFO
export STREAMLIT_ENV=production
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user
RUN useradd -m -u 1001 streamlit
USER streamlit

EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Start command
CMD ["streamlit", "run", "src/streamlit/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  cp2b-maps:
    build: .
    ports:
      - "8501:8501"
    environment:
      - CP2B_LOG_LEVEL=INFO
      - STREAMLIT_ENV=production
    volumes:
      - ./data:/app/data:ro
      - ./shapefile:/app/shapefile:ro
      - ./geoparquet:/app/geoparquet:ro
      - ./rasters:/app/rasters:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Nginx Configuration
```nginx
# nginx.conf for reverse proxy
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

### Monitoring & Logging
```python
# Production logging configuration
import logging
from logging.handlers import RotatingFileHandler

def setup_production_logging():
    """Setup production-grade logging."""
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/cp2b_maps.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        'logs/cp2b_maps_errors.log',
        maxBytes=10485760,
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
```

---

## 🤝 Contributing Guidelines

### Git Workflow
```bash
# Feature development workflow
git checkout -b feature/feature-name
git add .
git commit -m "feat: add new feature"
git push origin feature/feature-name

# Create pull request
# After review and approval:
git checkout main
git pull origin main
git branch -d feature/feature-name
```

### Commit Message Convention
```bash
# Format: type(scope): description
feat(map): add new visualization style
fix(data): resolve caching issue
docs(api): update function documentation
style(ui): improve button layout
refactor(core): optimize data loading
test(unit): add utility function tests
chore(deps): update streamlit version
```

### Code Review Checklist
- [ ] Code follows PEP 8 style guidelines
- [ ] Functions have proper docstrings
- [ ] Error handling is implemented
- [ ] Performance considerations addressed
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No sensitive data exposed
- [ ] Caching used appropriately

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

---

## 🔧 Troubleshooting Development Issues

### Common Development Issues

#### **Import Errors**
```python
# Problem: Module not found errors
ModuleNotFoundError: No module named 'src.database'

# Solution: Check Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

#### **Caching Issues**
```python
# Problem: Cache not updating with new data
# Solution: Clear cache during development
st.cache_data.clear()

# Or restart with cache clearing
streamlit run app.py --server.runOnSave true
```

#### **Performance Issues**
```python
# Problem: Slow map rendering
# Solution: Check layer count and data size
logger.info(f"Rendering {len(active_layers)} layers with {len(df)} municipalities")

# Problem: High memory usage
# Solution: Monitor and optimize DataFrames
import psutil
memory_percent = psutil.virtual_memory().percent
logger.warning(f"Memory usage: {memory_percent}%")
```

#### **Database Issues**
```python
# Problem: Database locked error
sqlite3.OperationalError: database is locked

# Solution: Ensure proper connection management
try:
    with sqlite3.connect(db_path) as conn:
        # Operations here
        pass  # Connection automatically closed
except sqlite3.OperationalError as e:
    logger.error(f"Database error: {e}")
```

### Development Tools & Debugging

#### **Streamlit Debugging**
```python
# Enable development mode
streamlit run app.py --server.runOnSave true --server.port 8502

# Debug session state
st.write("Session State:", st.session_state)

# Debug dataframe
st.dataframe(df.describe())

# Performance debugging
import time
start_time = time.time()
# ... operation ...
st.write(f"Operation took {time.time() - start_time:.2f} seconds")
```

#### **Data Validation in Development**
```python
def debug_data_issues(df: pd.DataFrame, operation: str):
    """Debug common data issues during development."""
    logger.debug(f"=== {operation} Debug Info ===")
    logger.debug(f"DataFrame shape: {df.shape}")
    logger.debug(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    logger.debug(f"Null values:\n{df.isnull().sum()}")
    logger.debug(f"Data types:\n{df.dtypes}")
    
    # Check for common issues
    if df.empty:
        logger.warning("DataFrame is empty!")
    
    # Check coordinate validity for geo data
    if 'latitude' in df.columns and 'longitude' in df.columns:
        invalid_coords = df[
            (df['latitude'] < -34) | (df['latitude'] > -19) |
            (df['longitude'] < -53) | (df['longitude'] > -44)
        ]
        if not invalid_coords.empty:
            logger.warning(f"Found {len(invalid_coords)} rows with invalid coordinates")
```

### Environment-Specific Issues

#### **Windows Development**
```bash
# Path separator issues
# Use pathlib.Path instead of os.path
from pathlib import Path
data_path = Path("data") / "file.csv"  # Works on all platforms

# Encoding issues
# Always specify encoding
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
```

#### **Linux/Mac Development**
```bash
# Permission issues
chmod +x scripts/*.py

# Virtual environment activation
source venv/bin/activate  # Not venv\Scripts\activate
```

---

## 📚 Additional Resources

### Documentation Links
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [GeoPandas Documentation](https://geopandas.org/)
- [Folium Documentation](https://python-visualization.github.io/folium/)

### Development Tools
- **VS Code Extensions**: Python, Pylance, GitLens
- **Browser Tools**: Chrome DevTools for debugging
- **Database Tools**: DB Browser for SQLite
- **GIS Tools**: QGIS for geospatial data inspection

### Community & Support
- **GitHub Repository**: Issues and discussions
- **Streamlit Community**: Forums and examples
- **Python GIS Community**: Geospatial development resources

---

*This developer guide should be updated as the project evolves. New features, patterns, and best practices should be documented here for future developers.*