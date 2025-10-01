"""
UI Components Module for CP2B Maps
Handles all user interface components and layout functions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from .data_loader import get_residue_label, format_number
from .reference_system import render_reference_button, get_substrate_reference_map

def render_header():
    """Render application header with WCAG Level A compliance"""
    st.markdown("""
    <header role="banner" style='background: linear-gradient(135deg, #2E8B57 0%, #228B22 50%, #32CD32 100%);
                color: white; padding: 1.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 0 0 15px 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h1 style='margin: 0; font-size: 2.2rem; font-weight: 700;'>🗺️ Análise de Potencial de Biogás</h1>
        <p style='margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>
            645 municípios de São Paulo
        </p>
    </header>
    """, unsafe_allow_html=True)

def render_navigation():
    """Render main navigation"""
    return st.sidebar.radio(
        "🧭 Navegação",
        ["🗺️ Mapa Principal", "🔍 Explorador", "📊 Análise", "ℹ️ Sobre"],
        key="main_navigation"
    )

def render_sidebar_filters():
    """Render sidebar filters for the main page"""
    st.sidebar.markdown("### 🎛️ Controles do Mapa")

    # Visualization type
    viz_type = st.sidebar.radio(
        "📊 Tipo de Visualização",
        ["Mapa de Preenchimento (Coroplético)", "Círculos Proporcionais", "Tamanho Fixo"],
        index=0,  # Default to choropleth map
        help="Como os municípios são representados no mapa"
    )

    # Data column selection with references
    data_options = {
        "total_final_nm_ano": "🏭 Potencial Total",
        "total_agricola_nm_ano": "🌾 Potencial Agrícola",
        "total_pecuaria_nm_ano": "🐄 Potencial Pecuário",
        "biogas_cana_nm_ano": "🌾 Biogás de Cana",
        "biogas_soja_nm_ano": "🌱 Biogás de Soja",
        "biogas_bovinos_nm_ano": "🐄 Biogás de Bovinos",
        "biogas_suino_nm_ano": "🐷 Biogás de Suínos"
    }

    display_col = st.sidebar.selectbox(
        "📈 Dados para Visualizar",
        options=list(data_options.keys()),
        format_func=lambda x: data_options[x],
        key="display_column"
    )

    # Add reference button for selected data type
    substrate_refs = get_substrate_reference_map()
    if display_col in substrate_refs:
        ref_col1, ref_col2 = st.sidebar.columns([3, 1])
        with ref_col1:
            st.sidebar.caption("Fonte científica:")
        with ref_col2:
            render_reference_button(substrate_refs[display_col], compact=True)

    return viz_type, display_col

def render_layer_controls():
    """Render layer control checkboxes"""
    st.sidebar.markdown("### 🗺️ Camadas do Mapa")
    
    layers = {}
    # Enable biogas municipalities by default - this is what users want to see first
    layers['show_municipios_biogas'] = st.sidebar.checkbox("📊 Potencial de Biogás", value=True, key="municipios_biogas_layer")
    
    # Other layers start disabled for cleaner initial view
    layers['show_mapbiomas'] = st.sidebar.checkbox("🌍 MapBiomas - Uso do Solo", key="mapbiomas_layer")
    layers['show_plantas_biogas'] = st.sidebar.checkbox("🏭 Plantas de Biogás", key="plantas_layer")
    layers['show_gasodutos_dist'] = st.sidebar.checkbox("⛽ Gasodutos - Distribuição", key="gasodutos_dist_layer")
    layers['show_gasodutos_transp'] = st.sidebar.checkbox("🚛 Gasodutos - Transporte", key="gasodutos_transp_layer")
    layers['show_rodovias'] = st.sidebar.checkbox("🛣️ Rodovias", key="rodovias_layer")
    layers['show_rios'] = st.sidebar.checkbox("🌊 Rios", key="rios_layer")
    # Remove urban areas layer (Step 2 of the plan)
    # layers['show_areas_urbanas'] = st.sidebar.checkbox("🏘️ Áreas Urbanas", key="areas_layer")
    layers['show_regioes_admin'] = st.sidebar.checkbox("🏛️ Regiões Administrativas", key="regioes_layer")
    
    return layers

def render_export_controls(map_object):
    """Render map export controls"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 Exportar Mapa")
    
    if st.sidebar.button("📥 Baixar Mapa HTML", help="Baixa o mapa atual como arquivo HTML"):
        if map_object:
            from .map_renderer import export_map_as_html
            
            try:
                map_html = export_map_as_html(map_object)
                if map_html:
                    st.sidebar.download_button(
                        label="💾 Salvar Arquivo",
                        data=map_html,
                        file_name=f"cp2b_map_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html",
                        mime="text/html"
                    )
                    st.sidebar.success("✅ Mapa pronto para download!")
                else:
                    st.sidebar.error("❌ Erro ao gerar arquivo de exportação")
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")

def show_municipality_details_compact(df, municipality_id, selected_residues):
    """Show compact municipality details in sidebar"""
    if municipality_id is None:
        return
        
    try:
        mun_data = df[df['cd_mun'].astype(str) == str(municipality_id)].iloc[0]
        municipio_nome = mun_data.get('nome_municipio', 'Município Desconhecido')
        
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### 📍 {municipio_nome}")
        
        # Key metrics
        total_potential = mun_data.get('total_final_nm_ano', 0)
        population = mun_data.get('populacao_2022', 0)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            ref_col1, ref_col2 = st.columns([3, 1])
            with ref_col1:
                st.metric("🏭 Potencial Total", f"{total_potential:,.0f}")
            with ref_col2:
                render_reference_button("biogas_calculation", compact=True)
        with col2:
            st.metric("👥 População", f"{population:,.0f}")

        # Agricultural breakdown with references
        if st.sidebar.expander("🌾 Detalhes Agrícolas"):
            agri_cols = ['biogas_cana_nm_ano', 'biogas_soja_nm_ano', 'biogas_milho_nm_ano']
            substrate_refs = get_substrate_reference_map()
            for col in agri_cols:
                if col in mun_data and mun_data[col] > 0:
                    label = get_residue_label(col)
                    detail_col1, detail_col2 = st.sidebar.columns([4, 1])
                    with detail_col1:
                        st.sidebar.write(f"• {label}: {mun_data[col]:,.0f} m³/ano")
                    with detail_col2:
                        if col in substrate_refs:
                            render_reference_button(substrate_refs[col], compact=True)

        # Livestock breakdown with references
        if st.sidebar.expander("🐄 Detalhes Pecuários"):
            livestock_cols = ['biogas_bovinos_nm_ano', 'biogas_suino_nm_ano', 'biogas_aves_nm_ano']
            substrate_refs = get_substrate_reference_map()
            for col in livestock_cols:
                if col in mun_data and mun_data[col] > 0:
                    label = get_residue_label(col)
                    detail_col1, detail_col2 = st.sidebar.columns([4, 1])
                    with detail_col1:
                        st.sidebar.write(f"• {label}: {mun_data[col]:,.0f} m³/ano")
                    with detail_col2:
                        if col in substrate_refs:
                            render_reference_button(substrate_refs[col], compact=True)
                    
    except Exception as e:
        st.sidebar.error(f"❌ Erro ao carregar detalhes: {e}")

def render_municipality_comparison(df, selected_municipalities):
    """Render comparison table for selected municipalities"""
    if not selected_municipalities:
        return
        
    st.markdown("### 📊 Comparação de Municípios Selecionados")
    
    try:
        selected_df = df[df['cd_mun'].isin(selected_municipalities)]
        
        if selected_df.empty:
            st.warning("Nenhum município encontrado para comparação.")
            return
            
        # Create comparison table
        comparison_cols = [
            'nome_municipio', 'populacao_2022', 'total_final_nm_ano',
            'total_agricola_nm_ano', 'total_pecuaria_nm_ano'
        ]
        
        display_df = selected_df[comparison_cols].copy()
        display_df.columns = [
            'Município', 'População', 'Potencial Total (m³/ano)',
            'Potencial Agrícola (m³/ano)', 'Potencial Pecuário (m³/ano)'
        ]
        
        # Format numbers for display
        for col in display_df.columns[1:]:  # Skip municipality name
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Clear selection button
        if st.button("🗑️ Limpar Seleção"):
            st.session_state.selected_municipalities = []
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Erro na comparação: {e}")

def render_search_interface(df):
    """Render municipality search interface"""
    st.sidebar.markdown("### 🔍 Buscar Município")
    
    search_term = st.sidebar.text_input(
        "Digite o nome do município:",
        placeholder="Ex: São Paulo, Campinas...",
        key="municipality_search"
    )
    
    if search_term and len(search_term) >= 2:
        # Filter municipalities matching search
        matches = df[df['nome_municipio'].str.contains(search_term, case=False, na=False)]
        
        if not matches.empty:
            selected_mun = st.sidebar.selectbox(
                "Selecione:",
                options=matches['cd_mun'].tolist(),
                format_func=lambda x: matches[matches['cd_mun'] == x]['nome_municipio'].iloc[0],
                key="search_selected_municipality"
            )
            
            if st.sidebar.button("📍 Ir para Município"):
                st.session_state.clicked_municipality = selected_mun
                st.rerun()
        else:
            st.sidebar.warning("Nenhum município encontrado.")
    
    return search_term

def render_quick_stats(df, display_col):
    """Render quick statistics panel with references"""
    try:
        col1, col2, col3, col4 = st.columns(4)

        total_municipalities = len(df)
        total_potential = df[display_col].sum()
        avg_potential = df[display_col].mean()
        max_potential = df[display_col].max()

        with col1:
            st.metric("🏘️ Municípios", f"{total_municipalities:,}")

        with col2:
            stat_col1, stat_col2 = st.columns([4, 1])
            with stat_col1:
                st.metric("🏭 Potencial Total", f"{total_potential:,.0f}")
            with stat_col2:
                substrate_refs = get_substrate_reference_map()
                if display_col in substrate_refs:
                    render_reference_button(substrate_refs[display_col], compact=True)
                else:
                    render_reference_button("biogas_calculation", compact=True)

        with col3:
            st.metric("📊 Potencial Médio", f"{avg_potential:,.0f}")

        with col4:
            st.metric("🎯 Potencial Máximo", f"{max_potential:,.0f}")

        # Add methodology reference
        st.caption("💡 Dados baseados em pesquisas científicas - clique em 📚 para ver as fontes")

    except Exception as e:
        st.error(f"❌ Erro ao calcular estatísticas: {e}")

def render_academic_footer():
    """Render academic references footer"""
    st.markdown("---")

    with st.expander("📚 Referências Científicas", expanded=False):
        st.markdown("""
        ### 📖 Base Científica do CP2B Maps

        Este sistema utiliza dados e metodologias baseadas em **pesquisas acadêmicas revisadas por pares**.
        Cada valor, fator de conversão e estimativa apresentada possui respaldo científico.

        **Como usar as referências:**
        - Clique nos ícones 📚 ao lado dos dados para ver a fonte específica
        - Cada referência inclui link direto para o artigo científico
        - Citações formatadas em padrão ABNT disponíveis

        **Principais categorias de referências:**
        - 🌾 **Substratos Agrícolas**: Pesquisas sobre potencial de biogás de resíduos de culturas
        - 🐄 **Resíduos Pecuários**: Estudos sobre dejetos animais e produção de metano
        - 🔬 **Metodologias**: Métodos de cálculo e avaliação de potencial energético
        - 📊 **Fontes de Dados**: IBGE, MapBIOMAS, EPE e outras instituições oficiais
        - ⚗️ **Co-digestão**: Pesquisas sobre misturas ótimas de substratos

        ### 🎯 Qualidade dos Dados
        - **645 municípios** com estimativas baseadas em dados reais
        - **Fatores conservadores** aplicados para estimativas seguras
        - **Metodologia validada** por literatura científica internacional
        """)

        # Quick access to main methodology references
        col1, col2, col3 = st.columns(3)
        with col1:
            render_reference_button("biogas_calculation", compact=False, label="📊 Metodologia de Cálculo")
        with col2:
            render_reference_button("cn_ratio_importance", compact=False, label="⚗️ Relação C/N")
        with col3:
            render_reference_button("mapbiomas", compact=False, label="🗺️ Dados Geoespaciais")

def render_value_with_reference(value: float, unit: str, ref_id: str, label: str = "") -> None:
    """
    Render a value with its scientific reference

    Args:
        value: Numerical value to display
        unit: Unit of measurement
        ref_id: Reference ID for the source
        label: Optional label for the value
    """
    col1, col2 = st.columns([4, 1])
    with col1:
        if label:
            st.metric(label, f"{value:,.0f} {unit}")
        else:
            st.write(f"**{value:,.0f} {unit}**")
    with col2:
        render_reference_button(ref_id, compact=True)

def render_substrate_info_panel():
    """Render substrate information panel with references"""
    with st.expander("🧪 Informações sobre Substratos", expanded=False):
        st.markdown("### 📋 Características dos Principais Substratos")

        tabs = st.tabs(["🌾 Agrícolas", "🐄 Pecuários", "⚗️ Co-digestão"])

        with tabs[0]:  # Agricultural substrates
            st.markdown("#### Resíduos Agrícolas")

            agri_data = [
                ("Cana-de-açúcar (bagaço)", "175 m³ CH₄/ton", "55% CH₄", "sugarcane_bagasse"),
                ("Cana-de-açúcar (palha)", "200 m³ CH₄/ton", "53% CH₄", "sugarcane_straw"),
                ("Café (casca)", "150-200 m³ CH₄/ton", "55-65% CH₄", "coffee_husk"),
                ("Citros (bagaço)", "80-150 m³ CH₄/ton", "45-65% CH₄", "citrus_bagasse"),
                ("Milho (palha)", "200-260 m³ CH₄/ton", "52-58% CH₄", "corn_straw"),
                ("Soja (palha)", "160-220 m³ CH₄/ton", "48-55% CH₄", "soybean_straw")
            ]

            for substrate, potential, methane, ref_id in agri_data:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{substrate}**")
                with col2:
                    st.write(potential)
                with col3:
                    st.write(methane)
                with col4:
                    render_reference_button(ref_id, compact=True)

        with tabs[1]:  # Livestock substrates
            st.markdown("#### Resíduos Pecuários")
            st.markdown("""
            - **Dejetos Bovinos**: 150-300 m³ CH₄/ton MS, 60-68% CH₄
            - **Dejetos Suínos**: 450-650 m³ CH₄/ton MS, 65-70% CH₄
            - **Cama de Frango**: 180-280 m³ CH₄/ton MS, 60-65% CH₄

            💡 *Resíduos pecuários geralmente têm maior potencial metanogênico devido ao menor teor de lignina.*
            """)

        with tabs[2]:  # Co-digestion
            st.markdown("#### Melhores Combinações")

            codig_data = [
                ("Palha milho + Dejetos bovinos", "60/40", "+22,4% CH₄", "corn_cattle_codigestion"),
                ("Vinhaça + Dejetos bovinos", "5-50% vinhaça", "Reduz COD 54-83%", "vinasse_cattle_codigestion"),
                ("Café + Dejetos bovinos", "70/30", "Equilibra C/N", "coffee_cattle_codigestion")
            ]

            for combination, ratio, benefit, ref_id in codig_data:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{combination}**")
                with col2:
                    st.write(ratio)
                with col3:
                    st.write(benefit)
                with col4:
                    render_reference_button(ref_id, compact=True)

def render_memory_info():
    """Render memory usage information"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > 100:  # Only show if significant memory usage
            st.sidebar.caption(f"💾 Memória: {memory_mb:.1f}MB")
    except:
        pass  # Silently ignore if psutil not available