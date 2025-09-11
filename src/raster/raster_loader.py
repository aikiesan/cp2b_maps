"""
Sistema de Carregamento de Rasters Otimizado para CP2B Maps
Carrega e processa rasters do MapBiomas de forma eficiente com cache
"""

import streamlit as st
import rasterio
import numpy as np
import os
from pathlib import Path
import logging
from functools import lru_cache
import pickle
from typing import Optional, Tuple, Dict, Any, List
import folium
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import ColorInterp
import base64
from io import BytesIO

# Matplotlib é opcional - fallback se não estiver disponível
try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None
    mcolors = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paleta de cores do MapBiomas para classes de agropecuária
MAPBIOMAS_COLORS = {
    # Pastagem
    15: '#FFD966',  # Amarelo claro
    # Silvicultura
    9: '#6D4C41',   # Marrom
    # Lavouras Temporárias
    39: '#E1BEE7', # Soja - Roxo claro
    20: '#C5E1A5', # Cana - Verde claro
    40: '#FFCDD2', # Arroz - Rosa claro
    62: '#F8BBD9', # Algodão - Rosa
    41: '#DCEDC8', # Outras Temporárias - Verde muito claro
    # Lavouras Perenes
    46: '#8D6E63', # Café - Marrom claro
    47: '#FFA726', # Citrus - Laranja
    35: '#66BB6A', # Dendê - Verde
    48: '#A1887F'  # Outras Perenes - Marrom acinzentado
}

class RasterLoader:
    """Classe para carregar e gerenciar rasters do MapBiomas"""
    
    def __init__(self, raster_dir: str = "rasters"):
        self.raster_dir = Path(raster_dir)
        self.raster_dir.mkdir(exist_ok=True)
        
    def get_raster_path(self, filename: str) -> Path:
        """Retorna o caminho completo para um arquivo raster"""
        return self.raster_dir / filename
    
    def load_raster(self, raster_path: str, max_size: int = 2048) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]:
        """
        Carrega um raster GeoTIFF com cache e redimensionamento automático
        
        Args:
            raster_path: Caminho para o arquivo raster
            max_size: Tamanho máximo para redimensionamento (para performance)
            
        Returns:
            Tuple com (dados_raster, metadados)
        """
        try:
            if not os.path.exists(raster_path):
                logger.warning(f"Arquivo raster não encontrado: {raster_path}")
                return None, None
                
            with rasterio.open(raster_path) as src:
                # Lê os metadados
                profile = src.profile.copy()
                
                # Calcula fator de redimensionamento se necessário
                height, width = src.height, src.width
                scale_factor = 1.0
                
                if max(height, width) > max_size:
                    scale_factor = max_size / max(height, width)
                    new_height = int(height * scale_factor)
                    new_width = int(width * scale_factor)
                    
                    # Lê dados redimensionados
                    data = src.read(
                        out_shape=(src.count, new_height, new_width),
                        resampling=Resampling.nearest
                    )[0]  # Primeira banda
                    
                    logger.info(f"Raster redimensionado de {width}x{height} para {new_width}x{new_height}")
                else:
                    # Lê dados na resolução original
                    data = src.read(1)
                
                # Prepara metadados
                metadata = {
                    'width': data.shape[1] if len(data.shape) > 1 else data.shape[0],
                    'height': data.shape[0] if len(data.shape) > 1 else 1,
                    'crs': str(profile.get('crs', 'EPSG:4326')),
                    'transform': profile.get('transform'),
                    'bounds': src.bounds,
                    'dtype': str(data.dtype),
                    'scale_factor': scale_factor,
                    'original_size': (width, height),
                    'nodata': profile.get('nodata')
                }
                
                logger.info(f"Raster carregado com sucesso: {raster_path}")
                return data, metadata
                
        except Exception as e:
            logger.error(f"Erro ao carregar raster {raster_path}: {e}")
            return None, None
    
    def raster_to_folium_overlay(self, data: np.ndarray, metadata: Dict[str, Any], opacity: float = 0.7, selected_classes: List[int] = None) -> Optional[folium.raster_layers.ImageOverlay]:
        """
        Converte dados raster em uma sobreposição para Folium
        
        Args:
            data: Array numpy com os dados do raster
            metadata: Metadados do raster
            opacity: Transparência da camada (0-1)
            
        Returns:
            folium.raster_layers.ImageOverlay ou None
        """
        try:
            # Remove valores nulos/nodata
            if metadata.get('nodata') is not None:
                data_masked = np.where(data == metadata['nodata'], np.nan, data)
            else:
                data_masked = data.copy()
            
            # Filtra por classes selecionadas, se especificado
            if selected_classes is not None:
                # Cria máscara apenas para as classes selecionadas
                mask = np.zeros_like(data_masked, dtype=bool)
                for class_id in selected_classes:
                    mask |= (data_masked == class_id)
                # Define como NaN as áreas não selecionadas
                data_masked = np.where(mask, data_masked, np.nan)
            
            # Cria mapa de cores baseado nas classes do MapBiomas
            unique_values = np.unique(data_masked[~np.isnan(data_masked)])
            
            # Cria imagem colorida
            colored_image = self._create_colored_image(data_masked, unique_values)
            
            # Converte para formato que o Folium pode usar
            img_base64 = self._array_to_base64(colored_image)
            
            # Define bounds geográficos
            bounds = metadata['bounds']
            folium_bounds = [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
            
            # Cria sobreposição do Folium
            overlay = folium.raster_layers.ImageOverlay(
                image=img_base64,
                bounds=folium_bounds,
                opacity=opacity,
                interactive=True,
                cross_origin=False,
                zindex=1
            )
            
            return overlay
            
        except Exception as e:
            logger.error(f"Erro ao criar sobreposição Folium: {e}")
            return None
    
    def _create_colored_image(self, data: np.ndarray, unique_values: np.ndarray) -> np.ndarray:
        """Cria imagem colorida baseada nas classes do MapBiomas"""
        # Cria imagem RGB
        height, width = data.shape
        colored_image = np.zeros((height, width, 4), dtype=np.uint8)  # RGBA
        
        for value in unique_values:
            if np.isnan(value):
                continue
                
            mask = data == int(value)
            color = MAPBIOMAS_COLORS.get(int(value), '#CCCCCC')  # Cinza para classes desconhecidas
            
            # Converte cor hex para RGB
            if HAS_MATPLOTLIB:
                rgb = mcolors.hex2color(color)
                rgb_255 = [int(c * 255) for c in rgb]
            else:
                # Fallback: conversão manual hex para RGB
                hex_color = color.lstrip('#')
                rgb_255 = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            
            colored_image[mask] = [rgb_255[0], rgb_255[1], rgb_255[2], 200]  # 200 = ~78% opacidade
        
        return colored_image
    
    def _array_to_base64(self, array: np.ndarray) -> str:
        """Converte array numpy para string base64 para usar no Folium"""
        from PIL import Image
        
        # Converte para imagem PIL
        img = Image.fromarray(array, mode='RGBA')
        
        # Salva em buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Converte para base64
        img_str = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def get_raster_info(self, raster_path: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações básicas sobre um arquivo raster sem carregá-lo completamente
        
        Args:
            raster_path: Caminho para o arquivo raster
            
        Returns:
            Dicionário com informações do raster ou None
        """
        try:
            if not os.path.exists(raster_path):
                return None
                
            with rasterio.open(raster_path) as src:
                return {
                    'filename': os.path.basename(raster_path),
                    'width': src.width,
                    'height': src.height,
                    'count': src.count,
                    'dtype': str(src.dtypes[0]),
                    'crs': str(src.crs),
                    'bounds': src.bounds,
                    'transform': src.transform,
                    'size_mb': round(os.path.getsize(raster_path) / (1024*1024), 2)
                }
        except Exception as e:
            logger.error(f"Erro ao obter informações do raster: {e}")
            return None
    
    def list_available_rasters(self) -> list:
        """Lista todos os arquivos raster disponíveis no diretório"""
        raster_extensions = ['.tif', '.tiff', '.geotiff']
        rasters = []
        
        for ext in raster_extensions:
            rasters.extend(self.raster_dir.glob(f"*{ext}"))
            rasters.extend(self.raster_dir.glob(f"*{ext.upper()}"))
        
        return [str(r) for r in rasters]


# Função de conveniência para uso direto no Streamlit
def get_raster_loader():
    """Retorna uma instância cached do RasterLoader"""
    return RasterLoader()


def create_mapbiomas_legend(selected_classes: List[int] = None) -> str:
    """Cria HTML da legenda para as classes do MapBiomas"""
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 50px; right: 50px; width: 200px; height: auto; 
        background-color: white; border:2px solid grey; z-index:9999; 
        font-size:12px; padding: 10px;
        border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
    ">
    <h4 style="margin-top:0; text-align: center;">MapBiomas - Agropecuária</h4>
    """
    
    class_names = {
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
    
    # Filtra classes se especificado
    if selected_classes is not None:
        filtered_classes = {code: name for code, name in class_names.items() if code in selected_classes}
    else:
        filtered_classes = class_names
    
    for code, name in filtered_classes.items():
        color = MAPBIOMAS_COLORS.get(code, '#CCCCCC')
        legend_html += f"""
        <div style="margin: 3px 0;">
            <span style="
                display: inline-block; 
                width: 20px; height: 15px; 
                background-color: {color}; 
                margin-right: 8px;
                border: 1px solid #333;
                vertical-align: middle;
            "></span>
            <span style="font-size: 10px;">{name}</span>
        </div>
        """
    
    legend_html += "</div>"
    return legend_html