"""
Visualization Styles Page for CP2B Maps
Dedicated page for map visualization style selection
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from typing import Dict, Any, Optional, Tuple
import logging

from .data_service import get_data_service, load_municipalities, load_optimized_geometries
from .memory_utils import monitor_memory_usage
from .integrated_map import create_integrated_map

logger = logging.getLogger(__name__)

def render_visualization_styles_page():
    """
    Main function to render the visualization styles selection page
    """
    st.header("🎨 Estilos de Visualização")
    st.markdown("### 🎯 Escolha o estilo de visualização dos dados no mapa")

    # Load data
    df = load_municipalities()
    if df.empty:
        st.error("❌ Dados não encontrados")
        return

    # Monitor memory usage
    monitor_memory_usage(threshold_mb=600)

    # Visualization type selection with enhanced styling
    st.markdown("#### 🗺️ Tipo de Mapa:")

    viz_options = {
        "Círculos Proporcionais": {
            "icon": "🔵",
            "description": "O tamanho dos círculos representa o valor dos dados. Maior potencial = círculo maior.",
            "recommended": True
        },
        "Mapa de Calor (Heatmap)": {
            "icon": "🔥",
            "description": "Mostra densidade e intensidade dos dados usando gradientes de cores quentes.",
            "recommended": False
        },
        "Agrupamentos (Clusters)": {
            "icon": "🌐",
            "description": "Agrupa pontos próximos para melhor visualização em diferentes escalas de zoom.",
            "recommended": False
        },
        "Mapa de Preenchimento (Coroplético)": {
            "icon": "🎨",
            "description": "Preenche as áreas dos municípios com cores baseadas nos valores dos dados.",
            "recommended": True
        }
    }

    # Create styled radio buttons
    selected_viz = None
    for viz_type, config in viz_options.items():
        recommended_badge = " ⭐ **Recomendado**" if config["recommended"] else ""

        if st.radio(
            label="",
            options=[viz_type],
            key=f"viz_{viz_type}",
            format_func=lambda x: f"{viz_options[x]['icon']} {x}{' ⭐' if viz_options[x]['recommended'] else ''}"
        ):
            selected_viz = viz_type
            st.info(f"ℹ️ {config['description']}{recommended_badge}")

    # Default selection if none made
    if not selected_viz:
        selected_viz = "Círculos Proporcionais"

    # Data variable selection
    st.markdown("#### 📊 Variável dos Dados:")

    data_columns = {
        'total_final_nm_ano': 'Potencial Total de Biogás',
        'total_agricola_nm_ano': 'Potencial Agrícola',
        'total_pecuaria_nm_ano': 'Potencial Pecuário',
        'biogas_bovinos_nm_ano': 'Biogás de Bovinos',
        'biogas_suino_nm_ano': 'Biogás de Suínos',
        'biogas_aves_nm_ano': 'Biogás de Aves',
        'biogas_cana_nm_ano': 'Biogás de Cana-de-açúcar',
        'biogas_soja_nm_ano': 'Biogás de Soja',
        'biogas_milho_nm_ano': 'Biogás de Milho'
    }

    display_col = st.selectbox(
        "Selecione a variável para visualizar:",
        options=list(data_columns.keys()),
        format_func=lambda x: data_columns[x],
        index=0
    )

    # Filters section
    st.markdown("#### 🔍 Filtros de Dados:")

    with st.expander("Configurar Filtros", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            min_potential = st.number_input(
                "Potencial Mínimo (m³/ano)",
                min_value=0,
                max_value=int(df[display_col].max()),
                value=0,
                step=1000
            )

        with col2:
            max_potential = st.number_input(
                "Potencial Máximo (m³/ano)",
                min_value=min_potential,
                max_value=int(df[display_col].max()),
                value=int(df[display_col].max()),
                step=1000
            )

        # Region filter
        if 'region' in df.columns:
            regions = ['Todos'] + sorted(df['region'].unique().tolist())
            selected_region = st.selectbox(
                "Região Administrativa:",
                options=regions,
                index=0
            )
        else:
            selected_region = 'Todos'

    # Apply filters
    filtered_df = df.copy()
    if min_potential > 0:
        filtered_df = filtered_df[filtered_df[display_col] >= min_potential]
    if max_potential < df[display_col].max():
        filtered_df = filtered_df[filtered_df[display_col] <= max_potential]
    if selected_region != 'Todos':
        filtered_df = filtered_df[filtered_df['region'] == selected_region]

    # Layer configuration
    st.markdown("#### 🗃️ Camadas do Mapa:")

    with st.expander("Configurar Camadas Visíveis", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            show_plantas = st.checkbox("🏭 Plantas de Biogás", value=True)
            show_gasodutos = st.checkbox("⛽ Gasodutos", value=False)

        with col2:
            show_rodovias = st.checkbox("🛣️ Rodovias", value=False)
            show_rios = st.checkbox("🌊 Rios Principais", value=False)

        with col3:
            show_regioes = st.checkbox("📍 Regiões Admin", value=False)
            show_border = st.checkbox("🗺️ Limite do Estado", value=True)

    layers_config = {
        'plantas': show_plantas,
        'gasodutos_dist': show_gasodutos,
        'gasodutos_transp': show_gasodutos,
        'rodovias': show_rodovias,
        'rios': show_rios,
        'regioes_admin': show_regioes,
        'sp_border': show_border
    }

    # Generate map button
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🗺️ Gerar Mapa com Estilo Selecionado", type="primary", use_container_width=True):
            with st.spinner(f"Gerando mapa {selected_viz.lower()}..."):
                try:
                    # Create the map with selected visualization style
                    map_obj = create_visualization_map(
                        filtered_df,
                        display_col,
                        selected_viz,
                        layers_config
                    )

                    if map_obj:
                        # Display the map
                        st.markdown("### 🗺️ Mapa Gerado")

                        # Map stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Municípios Exibidos", len(filtered_df))
                        with col2:
                            st.metric("Estilo de Visualização", selected_viz)
                        with col3:
                            total_potential = filtered_df[display_col].sum()
                            st.metric("Potencial Total", f"{total_potential:,.0f} m³/ano")

                        # Display map
                        from streamlit_folium import st_folium
                        map_data = st_folium(
                            map_obj,
                            width=1200,
                            height=600,
                            returned_objects=["last_clicked", "all_drawings"]
                        )

                        # Show clicked municipality info if available
                        if map_data["last_clicked"]:
                            show_clicked_municipality_info(map_data["last_clicked"], filtered_df, display_col)

                except Exception as e:
                    logger.error(f"Error creating visualization map: {e}")
                    st.error(f"❌ Erro ao gerar o mapa: {str(e)}")

    # Add helpful tips
    st.markdown("---")
    with st.expander("💡 Dicas de Uso", expanded=False):
        st.markdown("""
        **🔵 Círculos Proporcionais**: Melhor para comparar valores entre municípios. Círculos maiores = maior potencial.

        **🔥 Mapa de Calor**: Ideal para identificar regiões de alta concentração de potencial.

        **🌐 Agrupamentos**: Útil quando há muitos pontos próximos, melhora a performance do mapa.

        **🎨 Mapa Coroplético**: Excelente para visualizar distribuição espacial por área municipal.

        **⚡ Dica de Performance**: Para melhor performance, use filtros para reduzir a quantidade de dados exibidos.
        """)

def create_visualization_map(df: pd.DataFrame, display_col: str, viz_type: str, layers_config: Dict[str, bool]) -> Optional[folium.Map]:
    """
    Create a map with the specified visualization style

    Args:
        df: Municipality data
        display_col: Column to visualize
        viz_type: Type of visualization
        layers_config: Which layers to show

    Returns:
        folium.Map or None
    """
    try:
        # Use the integrated map creation function
        return create_integrated_map(
            df=df,
            display_col=display_col,
            layers_config=layers_config,
            viz_type=viz_type
        )
    except Exception as e:
        logger.error(f"Error creating visualization map: {e}")
        return None

def show_clicked_municipality_info(clicked_data: Dict[str, Any], df: pd.DataFrame, display_col: str):
    """Show information about clicked municipality"""
    try:
        if not clicked_data or 'lat' not in clicked_data:
            return

        lat, lon = clicked_data['lat'], clicked_data['lng']

        # Find closest municipality (simplified approach)
        # In a real implementation, you'd want to do proper point-in-polygon checking
        closest_idx = ((df['latitude'] - lat)**2 + (df['longitude'] - lon)**2).idxmin()
        municipality = df.loc[closest_idx]

        st.markdown("### 📍 Informações do Município Selecionado")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Município", municipality['name'])
            st.metric("População (2022)", f"{municipality.get('populacao_2022', 0):,.0f}")

        with col2:
            value = municipality[display_col]
            st.metric("Valor Selecionado", f"{value:,.0f} m³/ano")

        with col3:
            if 'region' in municipality:
                st.metric("Região", municipality['region'])

    except Exception as e:
        logger.error(f"Error showing municipality info: {e}")
        st.warning("Informações do município não disponíveis")

# Helper function for backward compatibility
def get_viz_style_selection():
    """Get visualization style selection - utility function"""
    return st.session_state.get('selected_viz_style', 'Círculos Proporcionais')