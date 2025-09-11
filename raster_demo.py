"""
Demonstração do Sistema de Carregamento de Rasters MapBiomas
Execute este arquivo para testar o sistema antes de integrar no app principal
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from raster import get_raster_loader, create_mapbiomas_legend
    import folium
    from streamlit_folium import st_folium
except ImportError as e:
    st.error(f"Erro ao importar módulos necessários: {e}")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="CP2B - Demo Raster MapBiomas",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Demonstração - Integração Raster MapBiomas")
st.markdown("---")

# --- VERIFICAÇÕES INICIAIS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 Status do Sistema")
    
    # Verifica se a pasta rasters existe
    raster_dir = Path("rasters")
    if raster_dir.exists():
        st.success("✅ Pasta 'rasters/' encontrada")
    else:
        st.warning("⚠️ Pasta 'rasters/' não existe")
        if st.button("Criar pasta rasters"):
            raster_dir.mkdir(exist_ok=True)
            st.success("Pasta criada!")
            st.rerun()

with col2:
    st.subheader("📁 Arquivos Disponíveis")
    
    # Lista arquivos na pasta rasters
    if raster_dir.exists():
        raster_files = list(raster_dir.glob("*.tif")) + list(raster_dir.glob("*.tiff"))
        if raster_files:
            for file in raster_files:
                st.info(f"📄 {file.name} ({file.stat().st_size // (1024*1024)} MB)")
        else:
            st.warning("Nenhum arquivo .tif encontrado")
    else:
        st.error("Pasta rasters não existe")

# --- INSTRUÇÕES PARA O USUÁRIO ---
st.markdown("---")
st.subheader("📋 Instruções para Integração")

if not raster_dir.exists() or not list(raster_dir.glob("*.tif*")):
    st.warning("**Passos necessários:**")
    st.markdown("""
    1. **Execute seu script no Google Earth Engine** (o código que você já tem)
    2. **Baixe o arquivo GeoTIFF** gerado (algo como `MapBiomas_SP_2024_APENAS_AGROPECUARIA_COG_90m.tif`)
    3. **Coloque o arquivo na pasta `rasters/`** do seu projeto
    4. **Recarregue esta página** para testar a integração
    """)
else:
    st.success("✅ **Sistema pronto para uso!**")

# --- DEMONSTRAÇÃO COM ARQUIVO DISPONÍVEL ---
if raster_dir.exists():
    raster_loader = get_raster_loader()
    available_rasters = raster_loader.list_available_rasters()
    
    if available_rasters:
        st.markdown("---")
        st.subheader("🗺️ Visualização do Raster")
        
        # Seletor de arquivo
        selected_raster = st.selectbox(
            "Selecione o arquivo raster:",
            available_rasters,
            format_func=lambda x: os.path.basename(x)
        )
        
        if st.button("🚀 Carregar e Visualizar"):
            with st.spinner("Carregando raster..."):
                # Carrega informações do raster
                info = raster_loader.get_raster_info(selected_raster)
                
                if info:
                    # Mostra informações
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"""
                        **Informações do Arquivo:**
                        - **Nome:** {info['filename']}
                        - **Dimensões:** {info['width']} x {info['height']} pixels
                        - **Tamanho:** {info['size_mb']} MB
                        - **Sistema de Coordenadas:** {info['crs']}
                        """)
                    
                    # Carrega dados completos
                    data, metadata = raster_loader.load_raster(selected_raster)
                    
                    if data is not None and metadata is not None:
                        with col2:
                            st.success("✅ Raster carregado com sucesso!")
                            st.info(f"""
                            **Dados Processados:**
                            - **Classes únicas:** {len(set(data.flatten()))} 
                            - **Resolução processada:** {metadata['width']} x {metadata['height']}
                            - **Fator de escala:** {metadata['scale_factor']:.2f}
                            """)
                        
                        # Cria mapa com o raster
                        st.subheader("🗺️ Visualização no Mapa")
                        
                        # Cria mapa centrado em SP
                        m = folium.Map(
                            location=[-22.5, -48.5], 
                            zoom_start=7,
                            tiles="OpenStreetMap"
                        )
                        
                        # Adiciona raster ao mapa
                        overlay = raster_loader.raster_to_folium_overlay(data, metadata, opacity=0.7)
                        
                        if overlay is not None:
                            # Cria FeatureGroup
                            raster_group = folium.FeatureGroup(name="MapBiomas - Agropecuária", show=True)
                            overlay.add_to(raster_group)
                            raster_group.add_to(m)
                            
                            # Adiciona controle de camadas
                            folium.LayerControl().add_to(m)
                            
                            # Adiciona legenda
                            legend_html = create_mapbiomas_legend()
                            m.get_root().html.add_child(folium.Element(legend_html))
                            
                            # Mostra mapa
                            st_folium(m, width=None, height=600, use_container_width=True)
                            
                            st.success("🎉 **Integração funcionando perfeitamente!**")
                            st.info("Agora você pode habilitar a camada MapBiomas no app principal.")
                        else:
                            st.error("❌ Erro ao processar raster para visualização")
                    else:
                        st.error("❌ Erro ao carregar dados do raster")
                else:
                    st.error("❌ Erro ao obter informações do raster")

# --- INSTRUÇÕES TÉCNICAS ---
st.markdown("---")
st.subheader("🔧 Detalhes Técnicos")

with st.expander("Ver código de integração no app principal"):
    st.code("""
# No seu app.py, a integração já está pronta:

if show_mapbiomas_layer:
    try:
        raster_loader = get_raster_loader()
        available_rasters = raster_loader.list_available_rasters()
        mapbiomas_rasters = [r for r in available_rasters if 'mapbiomas' in r.lower() or 'agropecuaria' in r.lower()]
        
        if mapbiomas_rasters:
            raster_path = mapbiomas_rasters[0]
            data, metadata = raster_loader.load_raster(raster_path)
            
            if data is not None and metadata is not None:
                overlay = raster_loader.raster_to_folium_overlay(data, metadata, opacity=0.7)
                
                if overlay is not None:
                    mapbiomas_group = folium.FeatureGroup(name="MapBiomas - Agropecuária SP", show=True)
                    overlay.add_to(mapbiomas_group)
                    mapbiomas_group.add_to(m)
                    
                    legend_html = create_mapbiomas_legend()
                    m.get_root().html.add_child(folium.Element(legend_html))
    except Exception as e:
        st.warning(f"Erro ao carregar camada MapBiomas: {str(e)}")
""", language="python")

st.markdown("---")
st.markdown("**🚀 Sistema desenvolvido para CP2B Maps - Integração MapBiomas otimizada via Google Earth Engine**")