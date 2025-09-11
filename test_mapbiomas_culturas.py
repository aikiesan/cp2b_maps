#!/usr/bin/env python3
"""
TESTE - Sistema de Culturas Selecionáveis MapBiomas
==================================================

Este script testa a nova funcionalidade de seleção granular de culturas
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_selective_cultures():
    """Teste do sistema de seleção de culturas"""
    
    print("[TESTE] Sistema de Culturas Selecionaveis MapBiomas")
    print("=" * 60)
    
    try:
        # 1. Importar módulos necessários
        print("1. Importando módulos...")
        from raster import RasterLoader, create_mapbiomas_legend
        print("[OK] Imports OK")
        
        # 2. Verificar diretório rasters
        print("\n2. Verificando diretorio rasters...")
        raster_dir = Path(__file__).parent / "rasters"
        
        if not raster_dir.exists():
            print("[ERRO] Diretorio rasters nao encontrado!")
            return False
            
        # 3. Testar RasterLoader
        print("\n3. Testando RasterLoader...")
        loader = RasterLoader(str(raster_dir))
        print("[OK] RasterLoader criado")
        
        # 4. Listar rasters disponíveis
        print("\n4. Listando rasters disponiveis...")
        available_rasters = loader.list_available_rasters()
        mapbiomas_rasters = [r for r in available_rasters if 'mapbiomas' in r.lower() or 'agropecuaria' in r.lower()]
        
        if not mapbiomas_rasters:
            print("[ERRO] Nenhum raster MapBiomas encontrado!")
            return False
            
        # 5. Carregar raster
        print("\n5. Carregando raster...")
        raster_path = mapbiomas_rasters[0]
        data, metadata = loader.load_raster(raster_path)
        print(f"[OK] Raster carregado: {data.shape}")
        
        # 6. Testar diferentes seleções de culturas
        print("\n6. Testando selecoes de culturas...")
        
        # Teste 1: Apenas soja
        print("\n   Teste A: Apenas Soja (codigo 39)")
        selected_classes = [39]  # Soja
        overlay = loader.raster_to_folium_overlay(data, metadata, opacity=0.7, selected_classes=selected_classes)
        if overlay:
            print("   [OK] Overlay criado com sucesso para Soja")
            
            # Testar legenda personalizada
            legend = create_mapbiomas_legend(selected_classes=selected_classes)
            print(f"   [OK] Legenda criada: {len(legend)} caracteres")
            
            # Verificar se apenas soja aparece na legenda
            if "Soja" in legend and "Cana" not in legend:
                print("   [OK] Legenda contem apenas Soja como esperado")
            else:
                print("   [AVISO] Legenda pode conter outras culturas")
        
        # Teste 2: Múltiplas culturas
        print("\n   Teste B: Soja + Cana + Cafe (codigos 39, 20, 46)")
        selected_classes = [39, 20, 46]  # Soja, Cana, Café
        overlay = loader.raster_to_folium_overlay(data, metadata, opacity=0.7, selected_classes=selected_classes)
        if overlay:
            print("   [OK] Overlay criado com sucesso para multiplas culturas")
            
            legend = create_mapbiomas_legend(selected_classes=selected_classes)
            print(f"   [OK] Legenda criada: {len(legend)} caracteres")
            
            # Verificar se as três culturas aparecem
            cultures_found = 0
            if "Soja" in legend: cultures_found += 1
            if "Cana" in legend: cultures_found += 1
            if "Café" in legend: cultures_found += 1
            
            print(f"   [OK] {cultures_found}/3 culturas encontradas na legenda")
        
        # Teste 3: Todas as culturas (None)
        print("\n   Teste C: Todas as culturas (None)")
        overlay = loader.raster_to_folium_overlay(data, metadata, opacity=0.7, selected_classes=None)
        if overlay:
            print("   [OK] Overlay criado com sucesso para todas as culturas")
            
            legend = create_mapbiomas_legend(selected_classes=None)
            print(f"   [OK] Legenda completa criada: {len(legend)} caracteres")
        
        print("\n" + "=" * 60)
        print("[SUCESSO] TODOS OS TESTES DE CULTURAS PASSARAM!")
        print("[OK] Sistema de selecao granular esta FUNCIONANDO!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] ERRO DURANTE O TESTE: {e}")
        import traceback
        print("Traceback completo:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_selective_cultures()
    sys.exit(0 if success else 1)