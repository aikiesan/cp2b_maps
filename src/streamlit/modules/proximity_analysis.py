"""
Proximity Analysis Module for CP2B Maps
Handles proximity analysis and raster analysis functionality
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import raster analysis if available
try:
    from ..raster.raster_loader import analyze_raster_in_radius
    HAS_RASTER_SYSTEM = True
except ImportError:
    analyze_raster_in_radius = None
    HAS_RASTER_SYSTEM = False

def force_raster_reanalysis():
    """Force re-analysis by clearing cached results"""
    memory_keys_to_clear = [
        'raster_analysis_results',
        'vector_analysis_results',
        'proximity_analysis_cache'
    ]
    
    for key in memory_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            
    logger.info("Raster analysis cache cleared - will trigger fresh analysis")

def find_raster_files():
    """Find available raster files for analysis"""
    project_root = Path(__file__).parent.parent.parent.parent
    raster_dir = project_root / "rasters"
    
    if not raster_dir.exists():
        logger.warning(f"Raster directory does not exist: {raster_dir}")
        return []
    
    # Look for common raster file extensions
    extensions = ['.tif', '.tiff', '.geotiff']
    raster_files = []
    
    for ext in extensions:
        raster_files.extend(raster_dir.glob(f"*{ext}"))
        raster_files.extend(raster_dir.glob(f"*{ext.upper()}"))
    
    return [str(f) for f in raster_files]

def validate_coordinates(lat, lon, radius_km):
    """Validate proximity analysis coordinates"""
    if not (-90 <= lat <= 90):
        return False, f"Invalid latitude: {lat}"
    if not (-180 <= lon <= 180):
        return False, f"Invalid longitude: {lon}"
    if not (0 < radius_km <= 200):
        return False, f"Invalid radius: {radius_km}"
    return True, "Valid coordinates"

def perform_raster_analysis(center_lat, center_lon, radius_km):
    """Perform raster analysis with proper error handling and debugging"""
    
    # Validation
    is_valid, msg = validate_coordinates(center_lat, center_lon, radius_km)
    if not is_valid:
        st.error(f"❌ Coordinate validation failed: {msg}")
        return None
    
    # Check system availability
    if not HAS_RASTER_SYSTEM or analyze_raster_in_radius is None:
        st.error("🔧 Sistema de análise de raster não está disponível. Verifique a instalação das dependências.")
        return {}
    
    # Find raster files
    raster_files = find_raster_files()
    if not raster_files:
        project_root = Path(__file__).parent.parent.parent.parent
        raster_dir = project_root / "rasters"
        st.error(f"📂 Nenhum arquivo raster (.tif) encontrado na pasta '{raster_dir}'.")
        st.info("💡 Baixe o arquivo raster do MapBiomas e coloque na pasta 'rasters/'")
        return {}
    
    # Show analysis details
    st.info(f"🎯 **Coordenadas:** {center_lat:.4f}, {center_lon:.4f}")
    st.info(f"📏 **Raio:** {radius_km} km")
    st.info(f"🗺️ **Arquivo:** {Path(raster_files[0]).name}")
    
    # Perform analysis
    try:
        raster_path = str(raster_files[0])
        
        # ENHANCED: Complete MapBiomas class mapping (not just agriculture)
        class_map = {
            # === AGRICULTURAL CLASSES (Priority) ===
            15: '🌾 Pastagem',
            20: '🌾 Cana-de-açúcar',  
            39: '🌱 Soja',
            40: '🌾 Arroz',
            41: '🌾 Outras Culturas Temporárias',
            46: '☕ Café',
            47: '🍊 Citrus', 
            62: '🌾 Algodão',
            35: '🌴 Dendê',
            48: '🌾 Outras Culturas Perenes',
            9: '🌲 Silvicultura',
            
            # === OTHER LAND USE CLASSES ===
            3: '🌳 Formação Florestal',
            4: '🌿 Formação Savânica',
            5: '🌾 Mangue',
            11: '🌾 Campo Alagado',
            12: '🌿 Formação Campestre',
            13: '🌿 Outras Formações',
            23: '🏖️ Praia e Duna',
            24: '🏘️ Área Urbanizada',
            25: '🌿 Outras Áreas não Vegetadas',
            26: '💧 Corpo d\'Água',
            27: '❄️ Não Observado',
            29: '🏞️ Afloramento Rochoso',
            30: '⛏️ Mineração',
            32: '💧 Apicum',
            33: '💧 Rio, Lago e Oceano'
        }
        
        logger.info(f"Starting raster analysis: center=({center_lat}, {center_lon}), radius={radius_km}km")
        
        results = analyze_raster_in_radius(
            raster_path=raster_path,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            class_map=class_map
        )
        
        if results:
            logger.info(f"Analysis successful: found {len(results)} land use types")
            st.success(f"✅ Análise concluída: {len(results)} tipos de uso do solo encontrados")
        else:
            logger.warning("Analysis returned empty results")
            st.warning("⚠️ Nenhum uso relevante do solo encontrado na área selecionada")
        
        return results
        
    except Exception as e:
        logger.error(f"Raster analysis failed: {e}")
        st.error(f"❌ Erro na análise raster: {e}")
        
        # Show detailed error in expander for debugging
        with st.expander("🔍 Detalhes do erro (para desenvolvedores)"):
            import traceback
            st.code(traceback.format_exc())
        
        return None

def render_proximity_controls():
    """Render proximity analysis controls in sidebar"""
    with st.sidebar.expander("🎯 Análise de Proximidade", expanded=False):
        # Initialize session state
        if 'catchment_center' not in st.session_state:
            st.session_state.catchment_center = None
        if 'catchment_radius' not in st.session_state:
            st.session_state.catchment_radius = 50
        
        enable_proximity = st.checkbox("Ativar Análise de Raio de Captação", 
                                     help="Clique no mapa para definir centro de análise")
        
        if enable_proximity:
            # Radius selection
            catchment_radius = st.radio(
                "Selecione o Raio de Captação:",
                options=[10, 30, 50],
                format_func=lambda x: f"{x} km",
                index=2,  # Default to 50km
                help="Raio da área a ser analisada"
            )
            
            # Update radius if changed
            if st.session_state.catchment_radius != catchment_radius:
                st.session_state.catchment_radius = catchment_radius
                # Force re-analysis with new radius
                force_raster_reanalysis()
            
            # Current center status
            if st.session_state.get('catchment_center'):
                center_lat, center_lon = st.session_state.catchment_center
                st.success(f"Centro definido em: {center_lat:.4f}, {center_lon:.4f}")
                
                if st.button("🗑️ Limpar Centro", key="clear_center_proximity"):
                    st.session_state.catchment_center = None
                    force_raster_reanalysis()
                    st.toast("Centro de captação removido.", icon="🗑️")
                    st.rerun()
            else:
                st.info("👆 Clique em uma área vazia do mapa para definir o centro")
        else:
            # Clear proximity data when disabled
            if st.session_state.get('catchment_center'):
                st.session_state.catchment_center = None
                force_raster_reanalysis()
        
        return enable_proximity

def handle_map_click(map_data, enable_proximity):
    """Handle map click events for proximity analysis with improved detection"""
    if not enable_proximity or not map_data:
        return False
    
    # Try different ways to detect map clicks
    clicked = False
    new_center = None
    
    try:
        # Method 1: Check for direct coordinate click
        if map_data.get('last_clicked') and 'lat' in map_data['last_clicked'] and 'lng' in map_data['last_clicked']:
            lat = map_data['last_clicked']['lat']
            lng = map_data['last_clicked']['lng']
            new_center = [float(lat), float(lng)]
            clicked = True
            logger.info(f"Map click detected via last_clicked: {new_center}")
            
        # Method 2: Check for popup clicks (fallback)
        elif map_data.get('last_object_clicked_popup'):
            popup_content = map_data['last_object_clicked_popup']
            if isinstance(popup_content, dict):
                if 'lat' in popup_content and 'lng' in popup_content:
                    new_center = [float(popup_content['lat']), float(popup_content['lng'])]
                    clicked = True
                    logger.info(f"Map click detected via popup: {new_center}")
        
        # Method 3: Check for feature clicks and extract coordinates
        elif map_data.get('last_object_clicked'):
            obj = map_data['last_object_clicked']
            if obj and 'lat' in str(obj) and 'lng' in str(obj):
                # Try to extract coordinates from the object
                try:
                    import re
                    coord_match = re.search(r'lat[\'\":\s]*([+-]?\d*\.?\d+).*lng[\'\":\s]*([+-]?\d*\.?\d+)', str(obj))
                    if coord_match:
                        lat, lng = float(coord_match.group(1)), float(coord_match.group(2))
                        new_center = [lat, lng]
                        clicked = True
                        logger.info(f"Map click detected via object parsing: {new_center}")
                except:
                    pass
        
        if clicked and new_center:
            current_center = st.session_state.get('catchment_center')
            
            # Check if this is a new location (avoid unnecessary re-analysis)
            is_new_location = (
                current_center is None or
                abs(new_center[0] - current_center[0]) > 0.0001 or
                abs(new_center[1] - current_center[1]) > 0.0001
            )
            
            if is_new_location:
                logger.info(f"New proximity center selected: {new_center}")
                
                # Clear old results and set new center
                force_raster_reanalysis()
                st.session_state.catchment_center = new_center
                
                st.toast(f"🎯 Centro definido: {new_center[0]:.4f}, {new_center[1]:.4f}", icon="🎯")
                return True  # Indicate that we should rerun
        
        return False
        
    except Exception as e:
        logger.error(f"Error handling map click: {e}")
        st.error(f"❌ Erro ao processar clique no mapa: {e}")
        return False

def render_proximity_results():
    """Render enhanced proximity analysis results with complete land-use profile"""
    if not st.session_state.get('catchment_center'):
        return
    
    center_lat, center_lon = st.session_state.catchment_center
    radius_km = st.session_state.catchment_radius
    
    st.markdown("---")
    st.markdown("### 🎯 Análise de Proximidade")
    
    # Perform raster analysis if needed
    if st.session_state.get('raster_analysis_results') is None:
        with st.spinner("🔍 Analisando uso do solo na área selecionada..."):
            results = perform_raster_analysis(center_lat, center_lon, radius_km)
            st.session_state.raster_analysis_results = results or {}
    
    # Display results
    results = st.session_state.get('raster_analysis_results', {})
    
    if results:
        st.markdown(f"#### 📍 Análise de Uso do Solo - Raio de {radius_km} km")
        st.caption(f"**Centro:** {center_lat:.4f}, {center_lon:.4f}")
        
        # Convert to DataFrame and separate agricultural from other uses
        results_df = pd.DataFrame([
            {'Tipo de Uso': uso, 'Área (hectares)': area}
            for uso, area in results.items()
        ]).sort_values('Área (hectares)', ascending=False)
        
        # Separate agricultural and other land uses
        agricultural_keywords = ['🌾', '🌱', '☕', '🍊', '🌴', '🌲']
        agri_df = results_df[results_df['Tipo de Uso'].str.contains('|'.join(agricultural_keywords), na=False)]
        other_df = results_df[~results_df['Tipo de Uso'].str.contains('|'.join(agricultural_keywords), na=False)]
        
        # Display agricultural results prominently
        if not agri_df.empty:
            st.success(f"✅ **Culturas de Interesse Encontradas: {len(agri_df)} tipos**")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(agri_df, use_container_width=True, hide_index=True)
            with col2:
                total_agri = agri_df['Área (hectares)'].sum()
                st.metric("🌾 Área Agrícola Total", f"{total_agri:,.0f} ha")
                
                # Show top agricultural use
                if len(agri_df) > 0:
                    top_use = agri_df.iloc[0]
                    st.metric("🥇 Uso Predominante", 
                            top_use['Tipo de Uso'].replace('🌾 ', '').replace('🌱 ', ''),
                            f"{top_use['Área (hectares)']:,.0f} ha")
        else:
            st.warning("⚠️ **Nenhuma Cultura Agrícola Encontrada**")
            st.info("💡 **Dica:** Tente clicar em regiões como Ribeirão Preto (cana), Sertãozinho (cana), ou Presidente Prudente (pastagem)")
        
        # Display other land uses
        if not other_df.empty:
            with st.expander(f"ℹ️ **Outros Usos do Solo na Área** ({len(other_df)} tipos)", expanded=len(agri_df) == 0):
                st.dataframe(other_df, use_container_width=True, hide_index=True)
        
        # Create comprehensive pie chart
        if len(results_df) > 1:
            try:
                import plotly.express as px
                
                # Color agricultural areas differently
                colors = []
                for uso in results_df['Tipo de Uso']:
                    if any(keyword in uso for keyword in agricultural_keywords):
                        colors.append('#2E8B57')  # Green for agriculture
                    else:
                        colors.append('#87CEEB')  # Light blue for other
                
                fig = px.pie(
                    results_df, 
                    values='Área (hectares)', 
                    names='Tipo de Uso',
                    title=f'Distribuição Completa de Uso do Solo (Raio: {radius_km}km)',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(height=400, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass  # Plotly not available
                
        # Summary statistics
        total_area = results_df['Área (hectares)'].sum()
        agri_area = agri_df['Área (hectares)'].sum() if not agri_df.empty else 0
        agri_percentage = (agri_area / total_area * 100) if total_area > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏞️ Área Total", f"{total_area:,.0f} ha")
        with col2:
            st.metric("🌾 Área Agrícola", f"{agri_area:,.0f} ha")
        with col3:
            st.metric("📊 % Agrícola", f"{agri_percentage:.1f}%")
            
    else:
        st.info("🔍 **Clique em uma área no mapa para iniciar a análise**")
        
        # Provide helpful suggestions
        with st.expander("💡 **Sugestões de Áreas para Testar**", expanded=True):
            st.markdown("""
            **🌾 Regiões Canavieiras:**
            - Ribeirão Preto, Sertãozinho, Jaboticabal
            
            **🐄 Regiões de Pastagem:**
            - Presidente Prudente, Araçatuba, Bauru
            
            **🌱 Regiões de Soja:**
            - Oeste do estado, região de Presidente Prudente
            
            **☕ Regiões Cafeeiras:**
            - Sul de Minas (fronteira), Franca, Mococa
            """)
            
        st.markdown("---")
        st.caption("💡 **Dica:** O sistema analisa o uso real do solo usando dados do MapBiomas. Se você clicar em áreas urbanas ou florestais, isso será mostrado nos resultados!")

def get_catchment_info():
    """Get catchment information for map rendering"""
    if not st.session_state.get('catchment_center'):
        return None
    
    return {
        "center": st.session_state.catchment_center,
        "radius": st.session_state.catchment_radius
    }