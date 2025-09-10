# test_wms.py
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("Teste Mínimo de Camada WMS")

# A mesma configuração que estamos tentando usar
RASTER_LAYERS = {
    "Cobertura do Solo (MapBiomas)": {
        "url": "https://brasil.mapbiomas.org/geoserver/wms",
        "layer": "mapbiomas:mapbiomas_brazil_collection_80_integration_v1", 
        "attr": "MapBiomas Project - Collection 8.0"
    }
}

m = folium.Map(location=[-22.5, -48.5], zoom_start=7)

try:
    layer_info = RASTER_LAYERS["Cobertura do Solo (MapBiomas)"]
    folium.WmsTileLayer(
        url=layer_info["url"],
        layers=layer_info["layer"],
        name="MapBiomas - Uso do Solo",
        attr=layer_info["attr"],
        transparent=True,
        overlay=True,
        control=True, # Ativa o controle de camadas do Folium
        fmt="image/png",
        version="1.3.0"
    ).add_to(m)
    st.success("Camada WMS adicionada ao objeto do mapa com sucesso!")
except Exception as e:
    st.error(f"Falha ao criar o objeto da camada WMS: {e}")

st_folium(m, width=None, height=600, use_container_width=True)