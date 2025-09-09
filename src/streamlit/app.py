"""
CP2B Maps - Clean Multi-Page Streamlit Application
Simple and robust biogas potential analysis for São Paulo municipalities
"""

import streamlit as st
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

# Page configuration
st.set_page_config(
    page_title="CP2B Maps",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    """Render sidebar filters"""
    st.sidebar.markdown("""
    <div style='background: #2E8B57; color: white; padding: 1rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 8px;'>
        <h3 style='margin: 0;'>🔍 Filtros</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Selection mode
    mode = st.sidebar.radio(
        "Modo de Seleção:",
        ["Individual", "Múltiplos"],
        help="Individual: um tipo por vez. Múltiplos: soma vários tipos."
    )
    
    if mode == "Individual":
        selected = st.sidebar.selectbox("Tipo de Resíduo:", list(RESIDUE_OPTIONS.keys()))
        residues = [RESIDUE_OPTIONS[selected]]
        display_name = selected
    else:
        selected_list = st.sidebar.multiselect(
            "Tipos de Resíduos:",
            list(RESIDUE_OPTIONS.keys()),
            default=["Potencial Total"]
        )
        residues = [RESIDUE_OPTIONS[item] for item in selected_list]
        display_name = f"Soma de {len(residues)} tipos" if len(residues) > 1 else (selected_list[0] if selected_list else "Nenhum")
    
    # Additional filters
    st.sidebar.markdown("---")
    search = st.sidebar.text_input("🔍 Buscar município:")
    show_zeros = st.sidebar.checkbox("Mostrar valores zero")
    max_count = st.sidebar.slider("Máximo de municípios:", 10, 200, 50)
    
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
def create_map(df, display_col):
    """Create simple folium map"""
    m = folium.Map(location=[-22.5, -48.5], zoom_start=7)
    
    if df.empty:
        return m
    
    # Get value range for colors
    max_val = df[display_col].max()
    min_val = df[display_col].min()
    
    if max_val == min_val:
        max_val = min_val + 1  # Avoid division by zero
    
    # Add markers
    for _, row in df.iterrows():
        if pd.notna(row.get('lat')) and pd.notna(row.get('lon')):
            # Calculate color intensity
            intensity = (row[display_col] - min_val) / (max_val - min_val)
            
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
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=max(4, min(15, intensity * 15)),
                popup=f"""
                <b>{row['nome_municipio']}</b><br>
                Potencial: {format_number(row[display_col])}<br>
                População: {row.get('populacao_2022', 'N/A'):,}
                """,
                color='black',
                fillColor=color,
                fillOpacity=0.7,
                weight=1
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
    
    # Get filters
    filters = render_sidebar_filters()
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
    st_folium(folium_map, width=None, height=500)
    
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
    
    filters = render_sidebar_filters()
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