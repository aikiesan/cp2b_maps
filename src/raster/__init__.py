"""
Módulo de carregamento de rasters para CP2B Maps
"""

from .raster_loader import RasterLoader, get_raster_loader, create_mapbiomas_legend

__all__ = ['RasterLoader', 'get_raster_loader', 'create_mapbiomas_legend']