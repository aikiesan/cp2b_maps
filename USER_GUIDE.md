# 👤 CP2B Maps - User Guide

## 📋 Table of Contents
1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Main Features](#main-features)
4. [Page-by-Page Guide](#page-by-page-guide)
5. [Advanced Features](#advanced-features)
6. [Tips & Best Practices](#tips--best-practices)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### What is CP2B Maps?
CP2B Maps is an interactive web application that helps you analyze and visualize biogas potential across São Paulo's 645 municipalities. Whether you're a researcher, investor, policy maker, or entrepreneur, this tool provides comprehensive insights into organic waste resources and biogas opportunities.

### Quick Start
1. **Access the Application**: Open CP2B Maps in your web browser
2. **Navigate Pages**: Use the top navigation bar to switch between different analysis views
3. **Apply Filters**: Use the control panel to customize your analysis
4. **Explore Data**: Click on municipalities, adjust visualizations, and dive into detailed analytics

### Key Benefits
- ✅ **No Technical Knowledge Required**: Intuitive interface for non-technical users
- ✅ **Comprehensive Data**: 15 types of organic residues across all SP municipalities
- ✅ **Interactive Visualizations**: Dynamic maps, charts, and tables
- ✅ **Real-time Analysis**: Instant results as you adjust filters and parameters

---

## 🖥️ Interface Overview

### Navigation Structure
```
CP2B Maps Application
├── 🗺️ Mapa Principal          # Interactive mapping and visualization
├── 🔍 Explorar Dados          # Data exploration and statistics  
├── 📊 Análise de Resíduos     # Advanced residue analysis
└── ℹ️ Sobre                   # Project information
```

### Control Panel (Main Map Only)
The hierarchical control panel is organized into collapsible sections:

#### 🗺️ Camadas Visíveis (Visible Layers) - *Always Expanded*
- **Dados Principais**: Biogas potential visualization controls
- **Infraestrutura**: Biogas plants, gas pipelines, power infrastructure
- **Referência**: Highways, urban areas, administrative regions
- **Imagem de Satélite**: MapBiomas land use data with culture selection

#### 📊 Filtros de Dados (Data Filters) - *Collapsible*
- **Individual/Multiple Mode**: Switch between single and multiple residue analysis
- **Residue Selection**: Choose from 15 types of organic waste
- **Municipality Search**: Find specific municipalities

#### 🎨 Estilos de Visualização (Visualization Styles) - *Collapsible*
- **Map Types**: Proportional circles, heat maps, clusters, choropleth

#### 🎯 Análises Avançadas (Advanced Analysis) - *Collapsible*
- **Proximity Analysis**: Analyze municipalities within a radius
- **Data Classification**: Natural breaks classification options
- **Data Normalization**: Per capita and area-based normalizations

### Status Indicators
- **🎯 Active Filters Banner**: Shows all applied filters in real-time
- **✨ Toast Notifications**: Confirms actions like selections and data changes
- **📊 Statistics Summary**: Real-time metrics displayed below maps

---

## 🎯 Main Features

### 1. **Interactive Mapping**
- **Multiple Visualization Styles**: Choose from 4 different map types
- **Dynamic Layers**: Toggle infrastructure, reference, and satellite layers
- **Smart Clustering**: Automatic grouping for better performance
- **Detailed Popups**: Click municipalities for detailed information

### 2. **Comprehensive Data Coverage**
- **645 Municipalities**: Complete coverage of São Paulo state
- **15 Residue Types**: Agricultural, livestock, and urban waste categories
- **Historical Context**: 2022 population data and administrative regions
- **High-Quality Geospatial Data**: Professional shapefiles and optimized geometries

### 3. **Advanced Analytics**
- **Statistical Analysis**: Percentiles, correlations, distributions
- **Regional Comparisons**: Compare municipalities by region and size
- **Portfolio Analysis**: Identify diversified vs specialized municipalities
- **Opportunity Analysis**: Find investment and development opportunities

### 4. **Professional Visualizations**
- **Interactive Charts**: Histograms, scatter plots, box plots, bar charts
- **Comparative Analysis**: Side-by-side municipality comparisons
- **Ranking Tables**: Customizable rankings with multiple criteria
- **Export Capabilities**: Download filtered data and statistics

---

## 📖 Page-by-Page Guide

## 🗺️ **Mapa Principal** (Main Map)

### Purpose
The main mapping interface for visualizing and exploring biogas potential across São Paulo municipalities with full customization options.

### Key Features
- **🎛️ Hierarchical Control Panel**: Organized sections for different control types
- **🗺️ Interactive Map**: Folium-based map with multiple visualization options
- **📊 Real-time Statistics**: Instant metrics updates based on current filters
- **🎯 Filter Status**: Clear indication of all active filters

### How to Use

#### Basic Visualization
1. **Select Residue Type**: Choose from the dropdown (defaults to Total Potential)
2. **Choose Map Style**: Select visualization type (Proportional Circles recommended)  
3. **Apply Filters**: Use search or municipality selection to focus analysis
4. **Explore Results**: Click municipalities for detailed popups

#### Layer Management
1. **Expand "Camadas Visíveis"**: Already open by default
2. **Toggle Infrastructure**: Enable/disable biogas plants, pipelines, power infrastructure
3. **Add Reference Data**: Show highways, urban areas, administrative regions
4. **Satellite Overlay**: Add MapBiomas land use data with specific culture selection

#### Advanced Analysis
1. **Expand "Análises Avançadas"**: Access proximity and classification tools
2. **Proximity Analysis**: Click map to set center, adjust radius, analyze nearby municipalities
3. **Data Classification**: Apply natural breaks for better data visualization
4. **Normalization Options**: Switch between absolute values and per-capita metrics

### Tips for Main Map
- 💡 **Start Simple**: Begin with "Total Potential" to get overall picture
- 💡 **Use Layers Strategically**: Don't enable all layers at once - focus on what's relevant
- 💡 **Proximity Analysis**: Great for identifying biogas plant opportunities near waste sources
- 💡 **Filter Combinations**: Combine municipality search with specific residue types

---

## 🔍 **Explorar Dados** (Data Explorer)

### Purpose  
Comprehensive data exploration with statistical analysis, visualizations, and detailed municipality information.

### Key Features
- **📊 Comprehensive Statistics**: Descriptive statistics with percentiles
- **📈 Multiple Chart Types**: 4 different visualization tabs
- **🏆 Flexible Rankings**: Customizable rankings by any criteria
- **🔍 Advanced Filtering**: Compact, focused filtering options
- **📥 Data Export**: Download capabilities for analysis and reporting

### How to Use

#### Statistical Overview
1. **Select Residue Type**: Choose what to analyze
2. **Review Metrics**: Examine max, min, mean, median, standard deviation
3. **Check Percentiles**: Understand data distribution (P10, P25, P50, P75, P90, P95, P99)
4. **Identify Outliers**: Note municipalities with exceptional values

#### Visual Analysis (4 Tabs)
1. **📊 Histograma**: 
   - Shows distribution of values
   - Identify common ranges and outliers
   - Adjust bin count for different perspectives

2. **📦 Box Plot**:
   - Visualize quartiles and outliers
   - Compare multiple residue types
   - Identify extreme values

3. **🎯 Scatter Plot**:
   - Explore correlations between variables
   - X-axis vs Y-axis comparisons
   - Identify patterns and relationships

4. **📊 Gráfico de Barras**:
   - Top municipalities ranking
   - Customizable number of municipalities
   - Clear value comparisons

#### Municipality Comparisons
1. **Select Multiple Municipalities**: Use the multi-select dropdown
2. **Review Comparison Chart**: Automatically generated side-by-side comparison
3. **Analyze Differences**: Identify strengths and opportunities

#### Interactive Table
1. **Search Function**: Find specific municipalities by name
2. **Column Selection**: Choose which data columns to display
3. **Sorting**: Click column headers to sort data
4. **Filtering**: Apply filters to focus on specific criteria

#### Rankings & Downloads
1. **Category Rankings**: Choose from Totals, Agricultural, Livestock, Urban
2. **Ranking Size**: Adjust from 5 to 50 municipalities
3. **Export Options**: Download complete dataset, filtered data, or statistics

### Tips for Data Explorer
- 💡 **Start with Overview**: Review statistics before diving into visualizations
- 💡 **Use Multiple Charts**: Different chart types reveal different insights
- 💡 **Compare Strategically**: Select municipalities with similar characteristics for meaningful comparisons
- 💡 **Export for Analysis**: Download data for external analysis or reporting

---

## 📊 **Análise de Resíduos** (Residue Analysis)

### Purpose
Advanced analytical tools for deep-dive analysis, pattern recognition, and strategic insights.

### Key Features  
- **🏆 Comparative Analysis**: Direct residue type comparisons
- **🌍 Regional Analysis**: Municipality size and geographic analysis
- **🔍 Pattern Recognition**: Correlation and specialization analysis
- **📈 Portfolio Analysis**: Diversification vs specialization insights

### How to Use

#### A) 🏆 **Comparar Tipos de Resíduos** (Compare Residue Types)
1. **Select Category**: Choose Agricultural, Livestock, or Urban
2. **Pick Specific Types**: Select 2-4 residue types for comparison
3. **Review Metrics**: 
   - Total Potential: Overall production capacity
   - Average per Municipality: Efficiency metrics
   - Municipal Coverage: How many municipalities have this resource
4. **Analyze Charts**: Three visualization perspectives
5. **Read Insights**: Automatic analysis and recommendations

**Best Use Cases**:
- Comparing agricultural residues (Sugarcane vs Soy vs Corn)
- Livestock analysis (Cattle vs Swine vs Poultry)
- Urban waste assessment (Solid waste vs Pruning residues)

#### B) 🌍 **Analisar por Região** (Regional Analysis)
1. **Population Analysis**:
   - Groups municipalities by population size
   - Shows biogas potential distribution across different municipality sizes
   - Identifies whether large or small municipalities have more potential

2. **Top N vs Rest Analysis**:
   - Compare top municipalities against the rest of the state
   - Adjustable N value (10, 20, 50, 100)
   - Concentration metrics and distribution analysis

**Best Use Cases**:
- Investment strategy (focus on large municipalities vs distributed approach)
- Policy planning (resources concentrated vs distributed)
- Market analysis (where are the biggest opportunities)

#### C) 🔍 **Encontrar Padrões e Correlações** (Find Patterns and Correlations)
1. **Correlation Between Types**:
   - Select two residue types
   - View correlation coefficient and scatter plot
   - Identify municipalities strong in both types

2. **Population Relationships**:
   - Analyze correlation between biogas potential and population size
   - Identify per-capita leaders vs absolute volume leaders

3. **Multi-specialized Municipalities**:
   - Find municipalities with high potential across multiple categories
   - Strategic locations for diversified biogas operations

**Best Use Cases**:
- Site selection (municipalities strong in multiple areas)
- Understanding market dynamics (population vs biogas potential)
- Risk analysis (diversified vs specialized locations)

#### D) 📈 **Análise de Portfólio Municipal** (Municipal Portfolio Analysis)
1. **Diversified Municipalities**:
   - Rankings by diversity of residue types
   - Municipalities with balanced portfolios across multiple categories

2. **Specialized Municipalities**:
   - Focus on municipalities excelling in specific categories
   - High potential in fewer areas vs spread across many

3. **Diversification vs Potential**:
   - Analysis of trade-offs between diversity and total volume
   - Strategic insights for different business models

**Best Use Cases**:
- Business model planning (diversified vs specialized operations)
- Risk management (spread risk vs focused expertise)
- Partnership strategies (complementary municipality profiles)

### Tips for Residue Analysis
- 💡 **Start with Comparisons**: Begin with residue type comparisons to understand the landscape
- 💡 **Use Regional Analysis**: Understand geographic and demographic patterns
- 💡 **Look for Patterns**: Correlation analysis reveals hidden relationships
- 💡 **Consider Portfolio Approach**: Balance specialization with diversification strategies

---

## ℹ️ **Sobre** (About)

### Purpose
Project information, methodology, and technical details.

### Content
- Project overview and objectives
- Data sources and methodology
- Technical specifications
- Contact information

---

## 🚀 Advanced Features

### **Proximity Analysis**
**Location**: Main Map → Advanced Analysis → Proximity Analysis

1. **Set Center Point**: Click anywhere on the map
2. **Adjust Radius**: Use slider to set analysis radius (1-100 km)
3. **Review Results**: Automatically shows municipalities within radius
4. **Analyze Metrics**: Total potential, average values, municipality count
5. **Strategic Planning**: Ideal for biogas plant location planning

**Use Cases**:
- Biogas plant site selection
- Logistics planning (transportation distances)
- Regional development strategies
- Supply chain optimization

### **MapBiomas Integration**
**Location**: Main Map → Visible Layers → Satellite Image

1. **Enable MapBiomas**: Toggle the satellite overlay
2. **Select Cultures**: Choose specific agricultural cultures to display
3. **Combine with Data**: Overlay with biogas potential data
4. **Visual Correlation**: See relationship between land use and biogas potential

**Use Cases**:
- Agricultural analysis (crop types vs biogas potential)
- Land use planning
- Environmental impact assessment
- Investment opportunity identification

### **Data Classification**
**Location**: Main Map → Advanced Analysis → Data Classification

1. **Enable Classification**: Toggle natural breaks classification
2. **Automatic Grouping**: Data automatically classified into meaningful groups
3. **Improved Visualization**: Better color coding and data interpretation
4. **Pattern Recognition**: Easier identification of high, medium, low potential areas

**Use Cases**:
- Market segmentation
- Priority area identification
- Resource allocation planning
- Policy development

### **Export and Sharing**
**Location**: Data Explorer → Download Options

1. **Complete Dataset**: Download all municipality data
2. **Filtered Data**: Export only currently filtered data
3. **Statistics**: Download statistical summaries
4. **Format Options**: CSV format for Excel/analysis software compatibility

**Use Cases**:
- External analysis and reporting
- Integration with other tools
- Backup and archival
- Sharing with stakeholders

---

## 💡 Tips & Best Practices

### **Getting Started**
1. **🎯 Start with Overview**: Begin on Main Map with "Total Potential" to understand overall landscape
2. **🔍 Progress to Details**: Move to Data Explorer for statistical analysis
3. **📊 Deep Dive Analysis**: Use Residue Analysis for strategic insights
4. **💾 Export Key Findings**: Download relevant data for reporting

### **Effective Analysis Workflow**
1. **Define Objectives**: Clear goals (investment, research, policy, etc.)
2. **Start Broad**: Use total potential and regional views
3. **Apply Filters**: Gradually narrow focus based on criteria
4. **Cross-Reference**: Compare findings across different analysis types
5. **Document Results**: Export data and take screenshots of key insights

### **Map Visualization Tips**
- **🎨 Choose Right Style**: 
  - Proportional Circles: Best for comparing absolute values
  - Heat Map: Good for density patterns
  - Choropleth: Excellent for categorical or classified data
- **🗂️ Layer Management**: Enable only relevant layers to avoid cluttering
- **🔍 Use Zoom Strategically**: Zoom in for local analysis, out for regional patterns

### **Filter Strategy**
- **📊 Single vs Multiple**: Start with single residue analysis, progress to multiple
- **🔍 Search Function**: Use municipality search to quickly find specific locations
- **🎯 Combination Filters**: Combine residue type, population, and geographic filters

### **Performance Optimization**
- **⚡ Cache Utilization**: Repeated operations are faster due to caching
- **🗺️ Layer Selection**: Too many layers can slow map rendering
- **📊 Data Size**: Large exports may take time - be patient

---

## 🔧 Troubleshooting

### **Common Issues & Solutions**

#### **Map Not Loading**
- **Symptom**: Blank or partially loaded map
- **Solution**: 
  1. Refresh the page
  2. Check internet connection
  3. Clear browser cache
  4. Try a different browser

#### **Data Not Updating**
- **Symptom**: Filters applied but results don't change
- **Solution**:
  1. Check that filters are properly selected
  2. Look for filter status banner
  3. Try clearing all filters and reapplying
  4. Refresh the page if needed

#### **Slow Performance**
- **Symptom**: Application responds slowly
- **Solution**:
  1. Reduce number of active map layers
  2. Use smaller radius for proximity analysis
  3. Close other browser tabs
  4. Clear browser cache

#### **Export Issues**
- **Symptom**: Downloads not working or files corrupted
- **Solution**:
  1. Check browser download settings
  2. Ensure sufficient disk space
  3. Try smaller data exports
  4. Use Chrome or Firefox browsers

#### **Visualization Problems**
- **Symptom**: Charts or maps display incorrectly
- **Solution**:
  1. Refresh the page
  2. Try different visualization style
  3. Clear browser cache
  4. Check browser zoom level (use 100%)

### **Browser Compatibility**
- ✅ **Recommended**: Chrome, Firefox, Safari (latest versions)
- ⚠️ **Limited Support**: Internet Explorer, older browsers
- 📱 **Mobile**: Basic functionality available, desktop recommended for full features

### **Performance Requirements**
- **RAM**: 4GB minimum, 8GB recommended
- **Internet**: Broadband connection recommended for map layers
- **Screen**: 1024x768 minimum, 1920x1080 recommended for full interface

---

## 📞 Support & Feedback

### **Getting Help**
- **Documentation**: Refer to this guide and technical documentation
- **Project Repository**: Check GitHub for updates and issues
- **Community**: Connect with other users and developers

### **Reporting Issues**
1. **Describe the Problem**: Clear description of what's not working
2. **Steps to Reproduce**: What actions led to the issue
3. **Browser Information**: Browser type and version
4. **Screenshots**: Visual documentation helps diagnosis

### **Feature Requests**
- **GitHub Issues**: Submit enhancement requests
- **User Feedback**: Share how you use the application
- **Community Input**: Participate in development discussions

---

*This user guide is designed to help you make the most of CP2B Maps. For technical details, refer to the Technical Documentation. For project overview, see the README file.*