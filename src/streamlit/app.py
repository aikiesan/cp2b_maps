"""
CP2B Maps - Clean Multi-Page Streamlit Application
Simple and robust biogas potential analysis for São Paulo municipalities
"""

import streamlit as st

# Configure page layout for wide mode
st.set_page_config(
    page_title="CP2B Maps",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)
import pandas as pd
import folium
from streamlit_folium import st_folium
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Constants
RESIDUE_OPTIONS = {
    'Potencial Total': 'total_final_nm_ano',
    'Total Agrícola': 'total_agricola_nm_ano',
    'Total Pecuária': 'total_pecuaria_nm_ano',
    'Cana-de-açúcar': 'biogas_cana_nm_ano',
    'Soja': 'biogas_soja_nm_ano',
    'Milho': 'biogas_milho_nm_ano',
    'Café': 'biogas_cafe_nm_ano',
    'Citros': 'biogas_citros_nm_ano',
    'Bovinos': 'biogas_bovinos_nm_ano',
    'Suínos': 'biogas_suino_nm_ano',
    'Aves': 'biogas_aves_nm_ano',
    'Piscicultura': 'biogas_piscicultura_nm_ano',
    'Resíduos Urbanos': 'rsu_potencial_nm_habitante_ano',
    'Resíduos Poda': 'rpo_potencial_nm_habitante_ano'
}

# Database functions
@st.cache_data
def get_database_path():
    """Get database path"""
    return Path(__file__).parent.parent.parent / "data" / "cp2b_maps.db"

@st.cache_data
def load_municipalities():
    """Load municipality data from database with error handling"""
    try:
        db_path = get_database_path()
        
        if not db_path.exists():
            logger.warning("Database not found")
            return pd.DataFrame()
        
        with sqlite3.connect(db_path) as conn:
            query = "SELECT * FROM municipalities ORDER BY total_final_nm_ano DESC"
            df = pd.read_sql_query(query, conn)
            logger.info(f"Loaded {len(df)} municipalities")
            return df
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()

def safe_divide(numerator, denominator, default=0):
    """Safe division with default value"""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default

def format_number(value, unit="Nm³/ano", scale=1):
    """Format numbers with proper scaling"""
    try:
        if pd.isna(value) or value == 0:
            return f"0 {unit}"
        
        scaled_value = value / scale
        if scale >= 1_000_000:
            return f"{scaled_value:.1f}M {unit}"
        elif scale >= 1_000:
            return f"{scaled_value:.0f}K {unit}"
        else:
            return f"{value:,.0f} {unit}"
    except:
        return f"0 {unit}"

# Navigation functions
def render_header():
    """Render application header"""
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2E8B57 0%, #228B22 50%, #32CD32 100%); 
                color: white; padding: 1.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 0 0 15px 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h1 style='margin: 0; font-size: 2.2rem; font-weight: 700;'>🌱 CP2B Maps</h1>
        <p style='margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>
            Análise de Potencial de Biogás em São Paulo
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_navigation():
    """Simple tab-based navigation"""
    tabs = st.tabs([
        "🏠 Mapa Principal",
        "🔍 Explorar Dados",
        "📊 Análises",
        "ℹ️ Sobre"
    ])
    
    return tabs

# Filter functions
def render_sidebar_filters():
    """Render sidebar filters (deprecated - kept for compatibility)"""
    # Simple navigation-only sidebar
    st.sidebar.markdown("""
    <div style='background: #2E8B57; color: white; padding: 0.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 8px;'>
        <h4 style='margin: 0;'>📊 CP2B Maps</h4>
        <p style='margin: 0; font-size: 0.8em;'>Use as abas para navegar</p>
    </div>
    """, unsafe_allow_html=True)
    
    return {
        'residues': [RESIDUE_OPTIONS["Potencial Total"]],
        'display_name': "Potencial Total",
        'search': "",
        'show_zeros': False,
        'max_count': 50
    }

def render_compact_filters(page_key="default"):
    """Render compact filters on main page"""
    # Create compact filter container
    with st.container():
        st.markdown("""
        <div style='background: rgba(255,255,255,0.95); padding: 1rem; border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 1rem;'>
        </div>
        """, unsafe_allow_html=True)
        
        # Use columns for horizontal layout
        col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
        
        with col1:
            # Selection mode
            mode = st.radio(
                "Modo:",
                ["Individual", "Múltiplos"],
                horizontal=True,
                key=f"{page_key}_selection_mode"
            )
        
        with col2:
            if mode == "Individual":
                selected = st.selectbox("Tipo de Resíduo:", list(RESIDUE_OPTIONS.keys()), key=f"{page_key}_residue_select")
                residues = [RESIDUE_OPTIONS[selected]]
                display_name = selected
            else:
                selected_list = st.multiselect(
                    "Tipos:",
                    list(RESIDUE_OPTIONS.keys()),
                    default=["Potencial Total"],
                    key=f"{page_key}_residue_multi"
                )
                residues = [RESIDUE_OPTIONS[item] for item in selected_list]
                display_name = f"Soma de {len(residues)} tipos" if len(residues) > 1 else (selected_list[0] if selected_list else "Nenhum")
        
        with col3:
            search = st.text_input("🔍 Buscar:", placeholder="Nome do município", key=f"{page_key}_search")
        
        with col4:
            show_zeros = st.checkbox("Valores zero", key=f"{page_key}_zeros")
            max_count = st.slider("Max:", 10, 200, 50, key=f"{page_key}_max")
    
    return {
        'residues': residues,
        'display_name': display_name,
        'search': search,
        'show_zeros': show_zeros,
        'max_count': max_count
    }

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    if df.empty:
        return df, 'total_final_nm_ano'
    
    df_filtered = df.copy()
    
    # Calculate display column
    if len(filters['residues']) == 1:
        display_col = filters['residues'][0]
    else:
        display_col = 'combined_potential'
        available_residues = [col for col in filters['residues'] if col in df_filtered.columns]
        if available_residues:
            df_filtered[display_col] = df_filtered[available_residues].fillna(0).sum(axis=1)
        else:
            df_filtered[display_col] = 0
    
    # Apply search filter
    if filters['search']:
        mask = df_filtered['nome_municipio'].str.contains(
            filters['search'], case=False, na=False
        )
        df_filtered = df_filtered[mask]
    
    # Filter zeros
    if not filters['show_zeros']:
        df_filtered = df_filtered[df_filtered[display_col] > 0]
    
    # Limit results
    df_filtered = df_filtered.nlargest(filters['max_count'], display_col)
    
    return df_filtered, display_col

# Map functions
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_optimized_geometries(detail_level="medium_detail"):
    """Load optimized municipality geometries from GeoParquet"""
    import geopandas as gpd
    from pathlib import Path
    
    try:
        parquet_path = Path(__file__).parent.parent.parent / "shapefile" / f"municipalities_{detail_level}.parquet"
        
        if parquet_path.exists():
            return gpd.read_parquet(parquet_path)
        else:
            # Fallback to original shapefile
            shapefile_path = Path(__file__).parent.parent.parent / "shapefile" / "Municipios_SP_shapefile.shp"
            if shapefile_path.exists():
                gdf = gpd.read_file(shapefile_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
                return gdf
    except Exception as e:
        st.error(f"Error loading geometries: {e}")
    
    return None

def create_map(df, display_col):
    """Create optimized folium map with municipality boundaries"""
    import geopandas as gpd
    from pathlib import Path
    
    # Center map on São Paulo state
    m = folium.Map(
        location=[-22.5, -48.5], 
        zoom_start=7,
        tiles='OpenStreetMap',
        attr='OpenStreetMap'
    )
    
    if df.empty:
        return m
    
    try:
        # Load optimized geometries based on data size
        municipality_count = len(df)
        
        if municipality_count > 200:
            detail_level = "low_detail"  # Fast for large datasets
        elif municipality_count > 50:
            detail_level = "medium_detail"  # Balanced
        else:
            detail_level = "high_detail"  # Detailed for small datasets
        
        gdf = load_optimized_geometries(detail_level)
        
        if gdf is None:
            return create_simple_map(df, display_col)
        
        # Merge geometries with data
        df_merged = gdf.merge(df, on='cd_mun', how='inner')
        
        if df_merged.empty:
            st.warning("⚠️ Nenhum município encontrado nos dados geométricos.")
            return create_simple_map(df, display_col)
        
        # Get value range for colors
        max_val = df_merged[display_col].max()
        min_val = df_merged[display_col].min()
        
        if max_val == min_val:
            max_val = min_val + 1
        
        # Create optimized GeoJson layer
        def style_function(feature):
            # Get municipality value
            cd_mun = feature['properties']['cd_mun']
            mun_data = df_merged[df_merged['cd_mun'] == cd_mun]
            
            if not mun_data.empty:
                value = mun_data.iloc[0][display_col]
                intensity = (value - min_val) / (max_val - min_val)
                
                if intensity > 0.8:
                    color = '#d73027'
                elif intensity > 0.6:
                    color = '#fc8d59'
                elif intensity > 0.4:
                    color = '#fee08b'
                elif intensity > 0.2:
                    color = '#d9ef8b'
                else:
                    color = '#91bfdb'
            else:
                color = '#cccccc'
            
            return {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7,
            }
        
        # Add optimized GeoJson layer
        folium.GeoJson(
            df_merged,
            style_function=style_function,
            popup=folium.GeoJsonPopup(
                fields=['nome_municipio', display_col],
                aliases=['Município:', 'Potencial:'],
                localize=True,
                labels=True,
                style="background-color: white;",
            ),
            tooltip=folium.GeoJsonTooltip(
                fields=['nome_municipio', display_col],
                aliases=['Município:', 'Potencial:'],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=800,
            )
        ).add_to(m)
        
        # Add performance info
        st.info(f"📊 Renderizando {len(df_merged)} municípios com nível de detalhe: {detail_level}")
        
        return m
        
    except Exception as e:
        st.error(f"❌ Erro ao criar mapa: {e}")
        return create_simple_map(df, display_col)

def create_simple_map(df, display_col):
    """Fallback simple map creation"""
    m = folium.Map(location=[-22.5, -48.5], zoom_start=7)
    
    # Simple grid-based visualization as fallback
    import random
    random.seed(42)
    
    for idx, row in df.iterrows():
        intensity = random.uniform(0, 1)  # Simplified for fallback
        
        lat = -22.5 + random.uniform(-2, 2)
        lon = -48.5 + random.uniform(-4, 4)
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=f"<b>{row['nome_municipio']}</b>",
            color='blue',
            fillColor='lightblue',
            fillOpacity=0.6
        ).add_to(m)
    
    return m

# Chart functions
def create_top_chart(df, display_col, title, limit=15):
    """Create top municipalities chart"""
    if df.empty:
        return None
    
    top_data = df.nlargest(limit, display_col)
    
    fig = px.bar(
        top_data,
        x='nome_municipio',
        y=display_col,
        title=f'Top {limit} Municípios - {title}',
        labels={display_col: 'Potencial (Nm³/ano)', 'nome_municipio': 'Município'}
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=False
    )
    
    return fig

def create_distribution_chart(df, display_col, title):
    """Create distribution chart"""
    if df.empty:
        return None
    
    fig = px.histogram(
        df,
        x=display_col,
        title=f'Distribuição - {title}',
        nbins=20,
        labels={display_col: 'Potencial (Nm³/ano)'}
    )
    fig.update_layout(height=400)
    
    return fig

# Page functions
def page_main():
    """Main map page"""
    st.markdown("## 🗺️ Mapa Principal")
    
    # Load data
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados. Execute o setup primeiro.")
        st.code("python setup.py")
        return
    
    # Get filters - compact version on main page
    filters = render_compact_filters("main")
    df_filtered, display_col = apply_filters(df, filters)
    
    if df_filtered.empty:
        st.warning("⚠️ Nenhum município encontrado com os filtros aplicados.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Municípios", len(df_filtered))
    with col2:
        total = df_filtered[display_col].sum()
        st.metric("Total", format_number(total, scale=1_000_000))
    with col3:
        avg = df_filtered[display_col].mean()
        st.metric("Média", format_number(avg, scale=1_000))
    with col4:
        max_val = df_filtered[display_col].max()
        st.metric("Máximo", format_number(max_val, scale=1_000_000))
    
    # Map
    st.markdown("---")
    folium_map = create_map(df_filtered, display_col)
    st_folium(folium_map, width=None, height=700)
    
    # Analysis charts
    st.markdown("---")
    st.markdown("### 📊 Análises")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chart1 = create_top_chart(df_filtered, display_col, filters['display_name'])
        if chart1:
            st.plotly_chart(chart1, use_container_width=True)
    
    with col2:
        chart2 = create_distribution_chart(df_filtered, display_col, filters['display_name'])
        if chart2:
            st.plotly_chart(chart2, use_container_width=True)
    
    # Data table
    with st.expander("📋 Dados Detalhados"):
        cols = ['nome_municipio', 'cd_mun', display_col]
        available_cols = [col for col in cols if col in df_filtered.columns]
        st.dataframe(df_filtered[available_cols], use_container_width=True)

def page_explorer():
    """Data explorer page"""
    st.markdown("## 🔍 Explorar Dados")
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    filters = render_compact_filters("explorer")
    df_filtered, display_col = apply_filters(df, filters)
    
    if df_filtered.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Statistics
    st.markdown("### 📈 Estatísticas")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Contagem", len(df_filtered))
    with col2:
        st.metric("Média", format_number(df_filtered[display_col].mean()))
    with col3:
        st.metric("Mediana", format_number(df_filtered[display_col].median()))
    with col4:
        st.metric("Desvio Padrão", format_number(df_filtered[display_col].std()))
    
    # Rankings by category
    st.markdown("---")
    st.markdown("### 🏆 Rankings por Categoria")
    
    for label, column in RESIDUE_OPTIONS.items():
        if column in df.columns:
            top_5 = df.nlargest(5, column)
            if not top_5.empty and top_5[column].sum() > 0:
                with st.expander(f"Top 5 - {label}"):
                    for _, row in top_5.iterrows():
                        st.write(f"**{row['nome_municipio']}**: {format_number(row[column])}")
    
    # Download section
    st.markdown("---")
    st.markdown("### 📥 Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Dataset Completo"):
            csv = df.to_csv(index=False)
            st.download_button(
                "💾 Baixar CSV",
                csv,
                "cp2b_completo.csv",
                "text/csv"
            )
    
    with col2:
        if st.button("🔍 Dados Filtrados"):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                "💾 Baixar Filtrados",
                csv,
                "cp2b_filtrados.csv",
                "text/csv"
            )

def page_analysis():
    """Analysis page"""
    st.markdown("## 📊 Análises Avançadas")
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    st.markdown("### 📈 Correlações")
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) > 1:
        # Select columns for correlation
        selected_cols = st.multiselect(
            "Selecione colunas para correlação:",
            numeric_cols,
            default=numeric_cols[:5]
        )
        
        if len(selected_cols) > 1:
            corr_matrix = df[selected_cols].corr()
            
            fig = px.imshow(
                corr_matrix,
                title="Matriz de Correlação",
                color_continuous_scale="RdBu_r"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Comparação Entre Tipos")
    
    # Multiple residue comparison
    comparison_types = st.multiselect(
        "Selecione tipos para comparar:",
        list(RESIDUE_OPTIONS.keys()),
        default=list(RESIDUE_OPTIONS.keys())[:3]
    )
    
    if comparison_types:
        comparison_data = []
        for municipality in df.nlargest(10, 'total_final_nm_ano')['nome_municipio']:
            muni_data = df[df['nome_municipio'] == municipality].iloc[0]
            for res_type in comparison_types:
                col_name = RESIDUE_OPTIONS[res_type]
                if col_name in df.columns:
                    comparison_data.append({
                        'Município': municipality,
                        'Tipo': res_type,
                        'Potencial': muni_data[col_name]
                    })
        
        if comparison_data:
            df_comp = pd.DataFrame(comparison_data)
            
            fig = px.bar(
                df_comp,
                x='Município',
                y='Potencial',
                color='Tipo',
                title='Comparação por Tipo de Resíduo (Top 10)',
                barmode='group'
            )
            fig.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig, use_container_width=True)

def page_about():
    """About page"""
    st.markdown("## ℹ️ Sobre o CP2B Maps")
    
    st.markdown("""
    ### 🎯 Objetivo
    
    Plataforma para análise do potencial de biogás nos municípios de São Paulo.
    
    ### 📊 Dados
    
    - **Agrícolas**: Cana, soja, milho, café, citros
    - **Pecuários**: Bovinos, suínos, aves, piscicultura
    - **Urbanos**: RSU e resíduos de poda
    
    ### 🛠️ Tecnologias
    
    - Streamlit, Folium, Plotly, SQLite, Pandas
    
    ### 📝 Como Usar
    
    1. Use as abas para navegar
    2. Ajuste filtros na barra lateral
    3. Explore mapas e dados
    4. Baixe dados quando necessário
    
    ### 🔗 Desenvolvimento
    
    Baseado no repositório cp2b_maps com foco em simplicidade e robustez.
    """)

def main():
    """Main application"""
    render_header()
    
    # Navigation
    tabs = render_navigation()
    
    with tabs[0]:
        page_main()
    
    with tabs[1]:
        page_explorer()
    
    with tabs[2]:
        page_analysis()
    
    with tabs[3]:
        page_about()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 1rem;'>"
        "<small>CP2B Maps - Análise de Potencial de Biogás</small>"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()