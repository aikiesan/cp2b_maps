# 🗺️ CP2B Maps - Biogas Potential Analysis Platform

**Professional Streamlit application for comprehensive biogas potential analysis across São Paulo's 645 municipalities.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](#)

## 🌟 Overview

CP2B Maps is a comprehensive web-based platform for analyzing biogas potential across São Paulo state. Built with modern data science tools, it provides interactive visualizations, advanced analytics, and detailed insights for researchers, policymakers, investors, and entrepreneurs in the biogas sector.

### 🎯 Key Capabilities

- **🗺️ Interactive Mapping**: Dynamic Folium-based maps with multiple visualization styles
- **📊 Advanced Analytics**: Statistical analysis, correlations, regional comparisons, portfolio analysis  
- **🔍 Comprehensive Data Explorer**: Detailed statistics, rankings, and comparative analysis
- **🎛️ Professional UI/UX**: Hierarchical control panel with real-time feedback
- **⚡ Performance Optimized**: 7 cached functions, optimized geometries, efficient data handling
- **📱 Responsive Design**: Professional interface that works across devices

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Git (for cloning the repository)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/aikiesan/cp2b_maps.git
cd cp2b_maps
```

2. **Create virtual environment (recommended):**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up the database (optional for sample data):**
```bash
python setup.py
```

5. **Launch the application:**
```bash
streamlit run src/streamlit/app.py
```

6. **Access the application:**
   - Open your browser and navigate to `http://localhost:8501`
   - Start exploring São Paulo's biogas potential!

## 📁 Project Structure

```
CP2B_Maps/
├── 📄 Documentation
│   ├── README.md                    # Project overview (this file)
│   ├── TECHNICAL_DOCUMENTATION.md  # Technical specs and API reference
│   ├── USER_GUIDE.md               # Complete user manual
│   ├── DEVELOPER_GUIDE.md          # Development and contribution guide
│   ├── PROJECT_SUMMARY.md          # Detailed project summary
│   └── MELHORIAS_UI_IMPLEMENTADAS.md # UI improvements log
├── 💾 Source Code
│   └── src/
│       ├── streamlit/
│       │   └── app.py              # Main application (5,681 lines)
│       ├── database/
│       │   ├── data_loader.py      # Database operations
│       │   └── migrations.py       # Database migrations
│       └── raster/
│           └── raster_loader.py    # Raster data processing
├── 📊 Data Files
│   ├── data/                       # SQLite database and raw data
│   ├── shapefile/                  # Geospatial vector data
│   ├── geoparquet/                 # Optimized geometries
│   └── rasters/                    # MapBiomas land use data
├── ⚙️ Configuration
│   ├── .streamlit/config.toml      # Performance-optimized settings
│   ├── requirements.txt            # Python dependencies
│   └── setup.py                    # Installation script
└── 🛠️ Utilities
    ├── create_centroid_map_optimized.py # Map generation utilities
    ├── optimize_geometries.py      # Geometry optimization
    └── update_regions.py           # Regional data updates
```

## 🎯 Application Features

### 🗺️ **Mapa Principal (Main Map)**
- **Interactive Mapping**: Professional Folium-based maps with multiple visualization styles
- **🎛️ Hierarchical Control Panel**: Organized in collapsible sections:
  - **Visible Layers**: Biogas data, infrastructure, reference data, satellite imagery
  - **Data Filters**: Individual/multiple residue selection, municipality search
  - **Visualization Styles**: Proportional circles, heat maps, clusters, choropleth
  - **Advanced Analysis**: Proximity analysis, data classification, normalization
- **Real-time Statistics**: Instant metrics updates based on applied filters
- **Smart Layer Management**: Toggle infrastructure (biogas plants, pipelines), reference data (highways, urban areas), and MapBiomas satellite data

### 🔍 **Explorar Dados (Data Explorer)**
- **Comprehensive Statistics**: Descriptive statistics with percentiles (P10-P99)
- **📈 Multiple Visualizations**: 4 chart types (histograms, box plots, scatter plots, bar charts)
- **🏆 Flexible Rankings**: Customizable rankings by category and size (5-50 municipalities)
- **🔍 Advanced Filtering**: Compact, focused filtering options
- **📥 Export Capabilities**: Download complete datasets, filtered data, or statistical summaries

### 📊 **Análise de Resíduos (Residue Analysis)**
- **🏆 Comparative Analysis**: Direct comparison between residue types
- **🌍 Regional Analysis**: Municipality size and geographic pattern analysis  
- **🔍 Pattern Recognition**: Correlation analysis and multi-specialization identification
- **📈 Portfolio Analysis**: Diversification vs specialization insights for strategic planning

### ℹ️ **Sobre (About)**
- Project information, methodology, and technical specifications

## 📊 Comprehensive Data Coverage

### **645 Municipalities** across São Paulo State
- **15 Residue Types** analyzed in detail:

#### 🌾 **Agricultural Residues**
- Sugarcane (*Cana-de-açúcar*)
- Soybean (*Soja*) 
- Corn (*Milho*)
- Coffee (*Café*)
- Citrus (*Citros*)

#### 🐄 **Livestock Residues**  
- Cattle (*Bovinos*)
- Swine (*Suínos*)
- Poultry (*Aves*)
- Aquaculture (*Piscicultura*)

#### 🏙️ **Urban Residues**
- Urban Solid Waste (*Resíduos Sólidos Urbanos*)
- Pruning Residues (*Resíduos de Poda*)

#### 📊 **Aggregate Categories**
- Total Agricultural (*Total Agrícola*)
- Total Livestock (*Total Pecuária*)  
- Total Urban (*Total Urbano*)
- **Total Biogas Potential** (*Potencial Total*)

## ⚡ Technical Excellence

### 🏗️ **Architecture & Performance**
- **✅ Professional Architecture**: Clean MVC pattern with modular functions
- **✅ Advanced Caching System**: 7 cached functions (15.9% coverage) for optimal performance
- **✅ Memory Optimization**: GeoParquet format with 89-99% size reduction
- **✅ Smart Data Loading**: Intelligent detail levels based on municipality count
- **✅ Performance Optimized**: Streamlit configuration tuned for speed and efficiency

### 💻 **Code Quality & Standards**
- **✅ PEP 8 Compliant**: Clean, organized import structure following Python standards
- **✅ Comprehensive Error Handling**: Robust error management with graceful degradation
- **✅ Environment-based Logging**: Configurable logging levels for development and production
- **✅ Type Safety**: Well-documented functions with clear parameter types
- **✅ Modular Design**: Separation of concerns with database, raster, and UI modules

### 🎨 **User Experience Design**
- **✅ Professional UI/UX**: Hierarchical control panel that transforms from "shopping list" to "control panel"
- **✅ Real-time Feedback**: Toast notifications and active filter status indicators  
- **✅ Responsive Layout**: Optimized for different screen sizes and devices
- **✅ Intuitive Navigation**: Clear page structure with logical workflow
- **✅ Smart Defaults**: Sensible default values and automatic optimizations

### 🔧 **Developer Experience**
- **✅ Comprehensive Documentation**: Technical docs, user guide, and developer guide
- **✅ Easy Setup**: One-command installation and database setup
- **✅ Hot Reload**: Development mode with automatic refresh
- **✅ Extensible Architecture**: Clear extension points for new features
- **✅ Testing Ready**: Structure prepared for comprehensive testing

## 🌐 Technology Stack

### **Core Technologies**
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Backend processing and analysis |
| **Streamlit** | ≥1.31.0 | Web application framework |
| **Pandas** | ≥2.1.0 | Data manipulation and analysis |
| **GeoPandas** | ≥0.14.0 | Geospatial data processing |
| **Folium** | ≥0.15.0 | Interactive mapping |
| **Plotly** | ≥5.17.0 | Advanced data visualization |

### **Geospatial & Analytics**
- **SQLite**: Efficient local database with 645 municipalities
- **Shapefiles**: Professional geospatial data for infrastructure and reference
- **GeoParquet**: Optimized geometries for fast rendering
- **MapBiomas**: Satellite imagery integration for land use analysis
- **Rasterio**: Raster data processing capabilities

## 🎯 Use Cases & Applications

### **🔬 Research & Academic**
- Municipal biogas potential assessment
- Regional development planning
- Environmental impact studies
- Academic research and publications

### **💼 Business & Investment**
- Biogas plant site selection
- Investment opportunity identification
- Market analysis and sizing
- Supply chain optimization

### **🏛️ Policy & Government**
- Municipal policy development
- Regional planning initiatives
- Environmental compliance planning
- Resource allocation strategies

### **🌱 Environmental & Sustainability**
- Waste-to-energy project planning
- Carbon footprint reduction analysis
- Circular economy implementation
- Sustainable development goal tracking

## 📈 Data Quality & Sources

### **Data Characteristics**
- **Coverage**: Complete São Paulo state (645 municipalities)
- **Temporal Scope**: 2022 population data with biogas potential projections
- **Spatial Resolution**: Municipality-level analysis with coordinate precision
- **Data Validation**: Comprehensive validation and error checking

### **Quality Assurance**
- ✅ **Data Integrity**: Automated validation of coordinates and value ranges
- ✅ **Completeness**: 100% municipality coverage with no missing critical data
- ✅ **Accuracy**: Professional data sources and validated calculations
- ✅ **Consistency**: Standardized units (Nm³/year) and measurement methodologies

## 🔧 Configuration & Customization

### **Environment Variables**
```bash
# Logging configuration
export CP2B_LOG_LEVEL=DEBUG    # Development: DEBUG, Production: INFO

# Development mode
export STREAMLIT_ENV=development
```

### **Performance Tuning**
The application includes optimized Streamlit configuration:
- **Fast Reruns**: Enabled for responsive development
- **Static Serving**: Optimized asset loading
- **Memory Efficiency**: 200MB upload limit with compression
- **Cache Optimization**: Strategic caching of expensive operations

### **Data Customization**
- **Automatic Data Discovery**: Looks for data files in standard locations
- **Graceful Fallbacks**: Creates sample data if real data unavailable
- **Flexible Data Sources**: Supports Excel, SQLite, and CSV formats
- **Validation & Recovery**: Comprehensive error handling with recovery options

## 🆘 Troubleshooting

### **Common Issues & Solutions**

#### **Installation Problems**
```bash
# Missing system dependencies (Ubuntu/Debian)
sudo apt-get install gdal-bin libgdal-dev

# Virtual environment issues
python -m venv venv --clear  # Recreate if corrupted

# Permission errors (Linux/Mac)
chmod +x setup.py
```

#### **Runtime Issues**
```bash
# Database corruption/issues
python setup.py  # Recreates database and reloads data

# Missing dependencies
pip install -r requirements.txt --force-reinstall

# Cache issues during development
# Clear Streamlit cache: Ctrl+C in terminal, then restart
```

#### **Performance Issues**
- **Slow Loading**: Reduce active map layers, use smaller analysis radius
- **Memory Issues**: Close other browser tabs, restart application
- **Display Problems**: Use Chrome/Firefox, check browser zoom (100%)

### **Development Debugging**
```bash
# Enable debug logging
export CP2B_LOG_LEVEL=DEBUG
streamlit run src/streamlit/app.py

# Run with hot reload
streamlit run src/streamlit/app.py --server.runOnSave true
```

## 📚 Documentation

### **Complete Documentation Suite**
- **📖 [USER_GUIDE.md](USER_GUIDE.md)**: Comprehensive user manual with step-by-step instructions
- **🔧 [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)**: Technical specifications, API reference, and architecture
- **👨‍💻 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**: Development setup, contribution guidelines, and advanced features
- **📋 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**: Detailed project overview and feature summary

### **Quick Reference Links**
- **🚀 Quick Start**: See installation section above
- **🎯 Feature Overview**: See application features section
- **⚡ Performance**: See technical excellence section
- **🔧 API Reference**: See [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

## 🤝 Contributing

We welcome contributions to improve CP2B Maps! Please see our [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for:

- **Development Environment Setup**
- **Code Style Guidelines** 
- **Testing Procedures**
- **Pull Request Process**
- **Architecture Guidelines**

### **Quick Contribution Setup**
```bash
# Fork and clone your fork
git clone https://github.com/your-username/cp2b_maps.git
cd cp2b_maps

# Set up development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, test, commit, and create pull request
```

## 📄 License & Acknowledgments

### **License**
This project is licensed under the MIT License - see the LICENSE file for details.

### **Acknowledgments**
- **MapBiomas Project**: Satellite imagery and land use data
- **São Paulo Government**: Municipal data and administrative boundaries  
- **Streamlit Community**: Framework and ecosystem
- **Open Source GIS Community**: Geospatial libraries and tools

## 📞 Support & Contact

### **Getting Help**
- **📚 Documentation**: Start with our comprehensive guides above
- **🐛 Issues**: Report bugs or request features on [GitHub Issues](https://github.com/aikiesan/cp2b_maps/issues)
- **💬 Discussions**: General questions and community support
- **📧 Contact**: For business inquiries and partnerships

### **Project Status**
- **✅ Production Ready**: Stable and fully functional
- **🔄 Active Development**: Regular updates and improvements
- **🌟 Feature Complete**: Core functionality implemented
- **📈 Performance Optimized**: Efficient and scalable

---

## 🌟 **CP2B Maps** - *Professional Biogas Potential Analysis Platform*

**Empowering data-driven decisions in São Paulo's biogas sector through interactive visualization, advanced analytics, and comprehensive municipal analysis.**

[![GitHub Stars](https://img.shields.io/github/stars/aikiesan/cp2b_maps?style=social)](https://github.com/aikiesan/cp2b_maps)
[![Made with Streamlit](https://img.shields.io/badge/Made%20with-Streamlit-red.svg)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)

---

*Built with 💚 for sustainable energy development in Brazil*