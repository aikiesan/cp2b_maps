"""
CP2B Maps - Results Page Module
Unified Analysis Results Page with simplified map and processed data display
"""

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
from datetime import datetime
import json
import io
import base64

try:
    from .map_utils import create_enhanced_results_map, add_analysis_legend, export_map_as_html
    HAS_MAP_UTILS = True
except ImportError:
    HAS_MAP_UTILS = False

try:
    from .municipality_loader import get_municipality_geometries, get_municipality_info
    HAS_MUNICIPALITY_LOADER = True
except ImportError:
    HAS_MUNICIPALITY_LOADER = False


def render_results_page():
    """Main function to render the unified results page"""
    
    # Check if we have analysis results to display
    if not st.session_state.get('analysis_results') or not st.session_state.get('show_results_page'):
        st.error("❌ Nenhum resultado de análise encontrado. Retorne às análises e use o botão 'VER NO MAPA'.")
        
        # Button to return to main navigation
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🏠 Voltar ao Menu Principal", use_container_width=True):
                st.session_state.show_results_page = False
                st.rerun()
        return
    
    # Get analysis results from session state
    results = st.session_state.analysis_results
    
    # Header with analysis info
    render_results_header(results)
    
    # Main content layout: Map on left, Data panel on right
    col_map, col_data = st.columns([1.2, 0.8])
    
    with col_map:
        render_simplified_map(results)
    
    with col_data:
        render_processed_data_panel(results)
    
    # Navigation buttons at bottom
    render_navigation_buttons()


def render_results_header(results):
    """Render the header section with analysis summary"""
    
    analysis_type = results.get('type', 'Análise')
    timestamp = results.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    municipalities_count = len(results.get('municipalities', []))
    
    # Title and summary
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #4CAF50 0%, #2E8B57 100%); 
                color: white; padding: 1.5rem; margin: -1rem -1rem 1rem -1rem; 
                border-radius: 10px; text-align: center;'>
        <h1 style='margin: 0; font-size: 2.2em;'>📊 RESULTADO DA ANÁLISE</h1>
        <p style='margin: 0.5rem 0 0 0; font-size: 1.1em; opacity: 0.9;'>
            {get_analysis_type_name(analysis_type)} • {municipalities_count} município(s) • {timestamp}
        </p>
    </div>
    """, unsafe_allow_html=True)


def get_analysis_type_name(analysis_type):
    """Convert analysis type to display name"""
    type_names = {
        'proximity_analysis': 'Análise de Proximidade',
        'residue_analysis': 'Análise de Resíduos',
        'culture_analysis': 'Análise de Culturas',
        'biogas_potential': 'Potencial de Biogás',
        'municipal_profile': 'Perfil Municipal'
    }
    return type_names.get(analysis_type, 'Análise Customizada')


def render_simplified_map(results):
    """Render a simplified map with selected municipalities"""
    
    st.markdown("### 🗺️ Mapa dos Municípios Selecionados")
    
    try:
        municipalities = results.get('municipalities', [])
        polygons = results.get('polygons', [])
        analysis_type = results.get('type', 'analysis')
        
        # Try to load actual municipality geometries if available
        if HAS_MUNICIPALITY_LOADER and municipalities:
            try:
                st.info("🔄 Carregando geometrias dos municípios...")
                actual_geometries = get_municipality_geometries(municipalities)
                
                if actual_geometries:
                    st.success(f"✅ Carregadas {len(actual_geometries)} geometrias municipais")
                    polygons = actual_geometries
                else:
                    st.warning("⚠️ Não foi possível carregar as geometrias. Usando fallback.")
                    
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar geometrias: {e}")
        
        # Try to use enhanced map utilities if available
        if HAS_MAP_UTILS and polygons:
            try:
                # Create enhanced map
                analysis_data = results.get('data', {}).get('residues', [])
                m = create_enhanced_results_map(municipalities, polygons, analysis_data)
                
                # Add legend
                m = add_analysis_legend(m, get_analysis_type_name(analysis_type))
                
                # Display enhanced map
                map_data = st_folium(m, width=None, height=450)
                
                # Add map export option
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📄 Exportar Mapa HTML", key="export_map_html"):
                        html_content = export_map_as_html(m)
                        if html_content:
                            st.download_button(
                                label="⬇️ Download Mapa HTML",
                                data=html_content,
                                file_name=f"cp2b_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                                mime="text/html"
                            )
                            st.success("✅ Mapa exportado com sucesso!")
                
            except Exception as e:
                st.warning(f"Usando mapa básico devido a: {e}")
                # Fallback to basic map
                m = create_basic_map(municipalities, polygons)
                map_data = st_folium(m, width=None, height=400)
        
        else:
            # Use basic map
            m = create_basic_map(municipalities, polygons)
            map_data = st_folium(m, width=None, height=400)
        
        # Show municipality list
        if municipalities:
            with st.expander("📍 Lista de Municípios", expanded=False):
                for i, mun in enumerate(municipalities):
                    st.markdown(f"{i+1}. **{mun}**")
    
    except Exception as e:
        st.error(f"Erro ao renderizar o mapa: {e}")
        st.markdown("📍 **Municípios Selecionados:**")
        for mun in results.get('municipalities', []):
            st.markdown(f"• {mun}")


def create_basic_map(municipalities, polygons):
    """Create basic fallback map"""
    
    # Create base map
    map_center = [-23.5, -46.6]  # Default to São Paulo center
    
    # If we have polygon data, calculate center from geometries
    if polygons and len(polygons) > 0:
        # Calculate bounds from polygons
        all_bounds = []
        for polygon in polygons:
            if hasattr(polygon, 'bounds'):
                all_bounds.append(polygon.bounds)
        
        if all_bounds:
            min_lat = min(bounds[1] for bounds in all_bounds)
            max_lat = max(bounds[3] for bounds in all_bounds)
            min_lon = min(bounds[0] for bounds in all_bounds)
            max_lon = max(bounds[2] for bounds in all_bounds)
            
            map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    
    # Create folium map
    m = folium.Map(
        location=map_center,
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add municipality polygons
    if polygons:
        for i, polygon in enumerate(polygons):
            municipality_name = municipalities[i] if i < len(municipalities) else f"Município {i+1}"
            
            # Add polygon to map
            folium.GeoJson(
                polygon,
                style_function=lambda x: {
                    'fillColor': '#4CAF50',
                    'color': '#2E8B57',
                    'weight': 2,
                    'fillOpacity': 0.7
                },
                tooltip=folium.Tooltip(municipality_name),
                popup=folium.Popup(f"<b>{municipality_name}</b>", parse_html=True)
            ).add_to(m)
            
            # Add centroid marker
            if hasattr(polygon, 'centroid'):
                centroid = polygon.centroid
                folium.Marker(
                    [centroid.y, centroid.x],
                    popup=municipality_name,
                    tooltip=municipality_name,
                    icon=folium.Icon(color='green', icon='info-sign')
                ).add_to(m)
    
    # Fit map to show all municipalities
    if polygons:
        try:
            # Calculate bounds for all polygons
            all_bounds = []
            for polygon in polygons:
                if hasattr(polygon, 'bounds'):
                    bounds = polygon.bounds
                    all_bounds.extend([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            
            if all_bounds:
                m.fit_bounds(all_bounds)
        except Exception as e:
            pass  # Skip auto-fit on error
    
    return m


def render_processed_data_panel(results):
    """Render the processed data panel with charts and metrics"""
    
    st.markdown("### 📈 Dados Processados")
    
    # Analysis summary
    render_analysis_summary(results)
    
    # Data sections
    data = results.get('data', {})
    
    # Cultures data
    if 'cultures' in data:
        render_cultures_section(data['cultures'])
    
    # Residues data
    if 'residues' in data:
        render_residues_section(data['residues'])
    
    # Metrics
    if 'metrics' in data:
        render_metrics_section(data['metrics'])
    
    # Charts
    charts = results.get('charts', [])
    if charts:
        render_charts_section(charts)
    
    # Export functionality
    render_export_section(results)


def render_analysis_summary(results):
    """Render analysis summary section"""
    
    st.markdown("#### 📋 Resumo da Análise")
    
    summary = results.get('summary', {})
    if summary:
        # Display summary metrics in columns
        cols = st.columns(3)
        
        if 'total_area' in summary:
            with cols[0]:
                st.metric("Área Total", f"{summary['total_area']:,.0f} ha")
        
        if 'total_production' in summary:
            with cols[1]:
                st.metric("Produção Total", f"{summary['total_production']:,.0f} t")
        
        if 'biogas_potential' in summary:
            with cols[2]:
                st.metric("Potencial Biogás", f"{summary['biogas_potential']:,.0f} m³")
    
    else:
        st.info("ℹ️ Resumo detalhado não disponível para esta análise.")


def render_cultures_section(cultures_data):
    """Render cultures analysis section"""
    
    with st.expander("🌾 Análise de Culturas", expanded=True):
        if isinstance(cultures_data, list) and cultures_data:
            # Convert to DataFrame for better display
            df = pd.DataFrame(cultures_data)
            
            # Ensure we have municipality names for better charts
            df = ensure_municipality_names_in_df(df)
            
            # Display as interactive table
            st.dataframe(df, use_container_width=True)
            
            # Simple chart if we have numeric data
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) > 0:
                chart_col = st.selectbox("Selecione coluna para gráfico:", numeric_cols, key="cultures_chart")
                if chart_col and len(df) > 1:
                    # Use municipality name for x-axis
                    x_col = get_municipality_name_column(df)
                    fig = px.bar(df.head(10), x=x_col, y=chart_col, 
                               title=f"Top 10 - {format_column_name(chart_col)}")
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
        
        elif isinstance(cultures_data, dict):
            # Display dictionary data
            for key, value in cultures_data.items():
                st.markdown(f"**{key}:** {value}")
        
        else:
            st.info("Dados de culturas não disponíveis em formato estruturado.")


def render_residues_section(residues_data):
    """Render residues analysis section"""
    
    with st.expander("♻️ Análise de Resíduos", expanded=False):
        if isinstance(residues_data, list) and residues_data:
            # Convert to DataFrame for better display
            df = pd.DataFrame(residues_data)
            
            # Ensure we have municipality names for better charts
            df = ensure_municipality_names_in_df(df)
            
            # Display as interactive table
            st.dataframe(df, use_container_width=True)
            
            # Simple chart if we have numeric data
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) > 0:
                chart_col = st.selectbox("Selecione coluna para gráfico:", numeric_cols, key="residues_chart")
                if chart_col and len(df) > 1:
                    # Use municipality name for labels
                    name_col = get_municipality_name_column(df)
                    chart_type = st.radio("Tipo de gráfico:", ["Pizza", "Barras"], key="residues_chart_type")
                    
                    if chart_type == "Pizza":
                        fig = px.pie(df.head(8), values=chart_col, names=name_col,
                                   title=f"Distribuição - {format_column_name(chart_col)}")
                    else:
                        fig = px.bar(df.head(10), x=name_col, y=chart_col,
                                   title=f"Top 10 - {format_column_name(chart_col)}")
                        fig.update_layout(xaxis_tickangle=-45)
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        elif isinstance(residues_data, dict):
            # Display dictionary data
            for key, value in residues_data.items():
                st.markdown(f"**{key}:** {value}")
        
        else:
            st.info("Dados de resíduos não disponíveis em formato estruturado.")


def render_metrics_section(metrics_data):
    """Render metrics section"""
    
    with st.expander("📊 Métricas Calculadas", expanded=False):
        if isinstance(metrics_data, dict):
            # Display metrics in a nice format
            cols = st.columns(2)
            items = list(metrics_data.items())
            
            for i, (key, value) in enumerate(items):
                col = cols[i % 2]
                with col:
                    if isinstance(value, (int, float)):
                        st.metric(key.replace('_', ' ').title(), f"{value:,.2f}")
                    else:
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
        
        else:
            st.info("Métricas não disponíveis em formato estruturado.")


def render_charts_section(charts):
    """Render charts section"""
    
    with st.expander("📈 Gráficos da Análise", expanded=False):
        if charts and len(charts) > 0:
            for i, chart in enumerate(charts):
                st.markdown(f"**Gráfico {i+1}**")
                # Here you would display the actual charts
                # This depends on how charts are stored in the analysis results
                st.info(f"Gráfico {i+1}: {type(chart).__name__}")
        else:
            st.info("Nenhum gráfico disponível para esta análise.")


def render_export_section(results):
    """Render export functionality section"""
    
    st.markdown("#### 💾 Exportar Resultados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Exportar CSV", use_container_width=True):
            export_to_csv(results)
    
    with col2:
        if st.button("📊 Exportar JSON", use_container_width=True):
            export_to_json(results)
    
    with col3:
        if st.button("🗺️ Exportar GeoJSON", use_container_width=True):
            export_to_geojson(results)


def export_to_csv(results):
    """Export analysis results to CSV"""
    try:
        data = results.get('data', {})
        
        # Create a combined dataset
        export_data = {
            'municipalities': results.get('municipalities', []),
            'analysis_type': results.get('type', ''),
            'timestamp': results.get('timestamp', '')
        }
        
        # Add data from analysis
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                export_data[key] = str(value)
            else:
                export_data[key] = value
        
        # Convert to DataFrame
        df = pd.DataFrame([export_data])
        
        # Create download link
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        filename = f"cp2b_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )
        
        st.success("✅ Arquivo CSV preparado para download!")
        
    except Exception as e:
        st.error(f"Erro ao exportar CSV: {e}")


def export_to_json(results):
    """Export analysis results to JSON"""
    try:
        # Convert results to JSON-serializable format
        export_data = dict(results)
        
        # Handle non-serializable objects
        for key, value in export_data.items():
            if hasattr(value, '__dict__'):
                export_data[key] = str(value)
        
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        
        filename = f"cp2b_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        st.download_button(
            label="⬇️ Download JSON",
            data=json_data,
            file_name=filename,
            mime="application/json"
        )
        
        st.success("✅ Arquivo JSON preparado para download!")
        
    except Exception as e:
        st.error(f"Erro ao exportar JSON: {e}")


def export_to_geojson(results):
    """Export geographic data to GeoJSON"""
    try:
        polygons = results.get('polygons', [])
        municipalities = results.get('municipalities', [])
        
        if not polygons:
            st.warning("⚠️ Nenhum dado geográfico disponível para exportar.")
            return
        
        # Create GeoJSON structure
        features = []
        
        for i, polygon in enumerate(polygons):
            municipality_name = municipalities[i] if i < len(municipalities) else f"Municipality_{i}"
            
            feature = {
                "type": "Feature",
                "properties": {
                    "name": municipality_name,
                    "analysis_type": results.get('type', ''),
                    "timestamp": results.get('timestamp', '')
                },
                "geometry": polygon.__geo_interface__ if hasattr(polygon, '__geo_interface__') else str(polygon)
            }
            features.append(feature)
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        json_data = json.dumps(geojson_data, indent=2, ensure_ascii=False)
        filename = f"cp2b_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
        
        st.download_button(
            label="⬇️ Download GeoJSON",
            data=json_data,
            file_name=filename,
            mime="application/json"
        )
        
        st.success("✅ Arquivo GeoJSON preparado para download!")
        
    except Exception as e:
        st.error(f"Erro ao exportar GeoJSON: {e}")


def render_navigation_buttons():
    """Render navigation buttons at the bottom"""
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔙 Voltar às Análises", use_container_width=True):
            st.session_state.show_results_page = False
            st.rerun()
    
    with col2:
        if st.button("🏠 Menu Principal", use_container_width=True):
            st.session_state.show_results_page = False
            # Clear analysis results
            if 'analysis_results' in st.session_state:
                del st.session_state.analysis_results
            st.rerun()
    
    with col3:
        if st.button("🔄 Nova Análise", use_container_width=True):
            st.session_state.show_results_page = False
            # Clear previous results
            if 'analysis_results' in st.session_state:
                del st.session_state.analysis_results
            st.rerun()
    
    with col4:
        if st.button("🖨️ Imprimir Página", use_container_width=True):
            st.markdown("""
            <script>
            window.print();
            </script>
            """, unsafe_allow_html=True)
            st.info("📄 Use Ctrl+P ou Cmd+P para imprimir esta página")


# Helper functions for better data display
def ensure_municipality_names_in_df(df):
    """Ensure DataFrame has a readable municipality name column"""
    if df.empty:
        return df
    
    # Look for municipality name columns
    name_columns = ['nome_municipio', 'município', 'municipio', 'nome', 'city', 'municipality']
    for col in name_columns:
        if col in df.columns:
            return df
    
    # If no name column found, try to create one from index or first column
    if df.index.name and 'municipio' in df.index.name.lower():
        df = df.reset_index()
    elif len(df.columns) > 0:
        # Check if first column might be municipality names (not numeric and reasonable length)
        first_col = df.columns[0]
        if not pd.api.types.is_numeric_dtype(df[first_col]):
            sample_values = df[first_col].dropna().head(3).astype(str)
            if all(len(str(val)) > 3 and len(str(val)) < 50 for val in sample_values):
                df = df.rename(columns={first_col: 'nome_municipio'})
    
    return df


def get_municipality_name_column(df):
    """Get the column that contains municipality names"""
    name_columns = ['nome_municipio', 'município', 'municipio', 'nome', 'city', 'municipality']
    
    for col in name_columns:
        if col in df.columns:
            return col
    
    # Fallback to first non-numeric column
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return col
    
    # Last resort: use first column
    return df.columns[0] if len(df.columns) > 0 else 'index'


def format_column_name(col_name):
    """Format column names for better display in charts"""
    name_mappings = {
        'total_final_nm_ano': 'Potencial Total (m³/ano)',
        'total_agricola_nm_ano': 'Potencial Agrícola (m³/ano)',
        'total_pecuaria_nm_ano': 'Potencial Pecuária (m³/ano)',
        'biogas_cana_nm_ano': 'Biogás de Cana-de-açúcar (m³/ano)',
        'biogas_soja_nm_ano': 'Biogás de Soja (m³/ano)',
        'biogas_milho_nm_ano': 'Biogás de Milho (m³/ano)',
        'biogas_cafe_nm_ano': 'Biogás de Café (m³/ano)',
        'biogas_citros_nm_ano': 'Biogás de Citros (m³/ano)',
        'biogas_bovinos_nm_ano': 'Biogás de Bovinos (m³/ano)',
        'biogas_suino_nm_ano': 'Biogás de Suínos (m³/ano)',
        'biogas_aves_nm_ano': 'Biogás de Aves (m³/ano)',
        'biogas_piscicultura_nm_ano': 'Biogás de Piscicultura (m³/ano)',
        'rsu_total_nm_ano': 'Resíduos Urbanos (m³/ano)',
        'rpo_total_nm_ano': 'Resíduos de Poda (m³/ano)',
        'populacao_2022': 'População (2022)',
        'area_km2': 'Área (km²)',
        'potencial_biogas': 'Potencial Biogás (m³/ano)',
        'potencial_total': 'Potencial Total (m³/ano)',
        'faixa_pop': 'Faixa Populacional'
    }
    
    if col_name in name_mappings:
        return name_mappings[col_name]
    
    # Format the name nicely
    formatted = col_name.replace('_', ' ').title()
    formatted = formatted.replace('m Ano', '(m³/ano)')
    formatted = formatted.replace('Km2', '(km²)')
    
    return formatted