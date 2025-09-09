# CP2B Maps - Clean Version

**Simple and robust Streamlit application for analyzing biogas potential in São Paulo municipalities.**

## ✨ Features

- 🗺️ **Interactive Maps** with municipal biogas potential data
- 🔍 **Data Explorer** with comprehensive statistical analysis
- 📊 **Advanced Analytics** including correlations and comparisons
- 🎯 **Smart Filters** - individual or multiple residue selection
- 📥 **Data Export** - download complete or filtered datasets
- 🚀 **Simple Setup** - one command to get started

## 🚀 Quick Start

1. **Navigate to the project:**
```bash
cd "C:\Users\Lucas\Documents\CP2B\CP2B_Maps"
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run setup (creates database and loads sample data):**
```bash
python setup.py
```

4. **Launch the application:**
```bash
streamlit run src/streamlit/app.py
```

## 📁 Project Structure

```
CP2B_Maps/
├── src/
│   ├── database/           # Clean database management
│   │   ├── migrations.py   # Database setup with error handling
│   │   └── data_loader.py  # Robust data loading and cleaning
│   └── streamlit/
│       └── app.py         # Clean, simple Streamlit app
├── data/                  # Database and data files
├── .streamlit/           # Streamlit configuration
├── setup.py             # One-command setup
└── requirements.txt     # Minimal dependencies
```

## 🎯 Application Pages

### 🏠 **Mapa Principal**
- Interactive Folium map with biogas potential visualization
- Real-time filtering by residue type (individual or combined)
- Summary metrics and analysis charts below the map
- Municipality search and detailed data table

### 🔍 **Explorar Dados**
- Comprehensive statistical analysis (mean, median, std deviation)
- Top rankings by municipality and residue category
- Data download options (complete dataset, filtered data, statistics)
- Interactive exploration tools

### 📊 **Análises**
- Correlation matrix between different variables
- Multi-residue comparison charts
- Advanced statistical visualizations

### ℹ️ **Sobre**
- Project information and usage instructions

## 📊 Data Types Analyzed

- **Agricultural**: Sugar cane, soybeans, corn, coffee, citrus
- **Livestock**: Cattle, pigs, poultry, aquaculture
- **Urban**: Municipal solid waste and garden/pruning waste

## 🛠️ Technical Improvements

### Code Quality
- ✅ **Clean Architecture** - Simple, maintainable functions
- ✅ **Error Handling** - Robust error management throughout
- ✅ **Performance** - Cached data loading and optimized queries
- ✅ **Logging** - Comprehensive logging for debugging

### User Experience
- ✅ **Tab Navigation** - Clean top navigation instead of sidebar
- ✅ **Responsive Design** - Works well on different screen sizes
- ✅ **Smart Defaults** - Sensible default values and settings
- ✅ **Clear Feedback** - Progress indicators and status messages

## 🔧 Customization

The application automatically:
- Looks for data files in common locations
- Creates sample data if no real data is found
- Handles missing or malformed data gracefully
- Provides clear error messages and recovery options

## 📈 Sample Data

If no data file is found, the application creates realistic sample data for 7 major São Paulo municipalities including São Paulo, Campinas, Sorocaba, Guarulhos, Santo André, Hortolândia, and Santos.

## 🆘 Troubleshooting

**Database issues:**
```bash
python setup.py  # Recreates database and reloads data
```

**Missing dependencies:**
```bash
pip install -r requirements.txt
```

**Import errors:**
- Make sure you're running commands from the CP2B_Maps directory
- Check that Python path includes the src directory

---

**🌱 CP2B Maps** - Clean, simple, and robust biogas potential analysis for São Paulo.