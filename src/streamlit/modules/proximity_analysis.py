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
        
        # MapBiomas class mapping for agriculture/livestock
        class_map = {
            15: 'Pastagem',
            9: 'Silvicultura',
            39: 'Soja',
            20: 'Cana-de-açúcar',
            40: 'Arroz',
            62: 'Algodão',
            41: 'Outras Temporárias',
            46: 'Café',
            47: 'Citrus',
            35: 'Dendê',
            48: 'Outras Perenes'
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
    """Handle map click events for proximity analysis"""
    if not enable_proximity or not map_data.get('last_object_clicked_popup'):
        return
    
    try:
        # Extract coordinates from click
        popup_content = map_data['last_object_clicked_popup']
        
        # Parse coordinates from various possible formats
        coords = None
        if 'lat' in popup_content and 'lng' in popup_content:
            coords = [popup_content['lat'], popup_content['lng']]
        elif 'coordinates' in popup_content:
            coords = popup_content['coordinates']
        
        if not coords or len(coords) != 2:
            logger.warning(f"Could not extract coordinates from map click: {popup_content}")
            return
        
        new_center = [float(coords[0]), float(coords[1])]
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
            
            st.toast(f"Centro definido: {new_center[0]:.4f}, {new_center[1]:.4f}", icon="🎯")
            st.rerun()
            
    except Exception as e:
        logger.error(f"Error handling map click: {e}")
        st.error(f"❌ Erro ao processar clique no mapa: {e}")

def render_proximity_results():
    """Render proximity analysis results"""
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
        st.markdown(f"#### 🌾 Uso do Solo no Raio de {radius_km} km")
        
        # Convert to DataFrame for better display
        results_df = pd.DataFrame([
            {'Tipo de Uso': uso, 'Área (hectares)': area}
            for uso, area in results.items()
        ]).sort_values('Área (hectares)', ascending=False)
        
        # Display table
        st.dataframe(results_df, use_container_width=True)
        
        # Create pie chart if possible
        if len(results_df) > 1:
            try:
                import plotly.express as px
                fig = px.pie(
                    results_df, 
                    values='Área (hectares)', 
                    names='Tipo de Uso',
                    title=f'Distribuição de Uso do Solo ({radius_km}km)'
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass  # Plotly not available
                
        # Summary statistics
        total_area = results_df['Área (hectares)'].sum()
        st.metric("🏞️ Área Total Analisada", f"{total_area:,.0f} hectares")
        
    else:
        st.info("🔍 Clique em uma área no mapa para iniciar a análise de proximidade")

def get_catchment_info():
    """Get catchment information for map rendering"""
    if not st.session_state.get('catchment_center'):
        return None
    
    return {
        "center": st.session_state.catchment_center,
        "radius": st.session_state.catchment_radius
    }