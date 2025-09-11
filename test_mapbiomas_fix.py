#!/usr/bin/env python3
"""
TESTE MANUAL - Verificação da Correção MapBiomas
================================================

Este script testa a funcionalidade MapBiomas de forma independente
para confirmar que a correção do return prematuro funcionou.
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_mapbiomas_integration():
    """Teste para verificar se a integração MapBiomas está funcionando"""
    
    print("[TESTE] MANUAL - Verificacao MapBiomas")
    print("=" * 50)
    
    try:
        # 1. Importar módulos necessários
        print("1. Importando módulos...")
        from raster import RasterLoader, create_mapbiomas_legend
        print("[OK] Imports OK")
        
        # 2. Verificar diretório rasters
        print("\n2. Verificando diretorio rasters...")
        raster_dir = Path(__file__).parent / "rasters"
        print(f"   Diretorio: {raster_dir}")
        print(f"   Existe? {raster_dir.exists()}")
        
        if not raster_dir.exists():
            print("[ERRO] Diretorio rasters nao encontrado!")
            return False
            
        # 3. Testar RasterLoader
        print("\n3. Testando RasterLoader...")
        loader = RasterLoader(str(raster_dir))
        print("[OK] RasterLoader criado")
        
        # 4. Listar rasters disponíveis
        print("\n4. Listando rasters disponíveis...")
        available_rasters = loader.list_available_rasters()
        print(f"   Total encontrados: {len(available_rasters)}")
        
        for i, raster in enumerate(available_rasters, 1):
            print(f"   {i}. {raster}")
            
        # 5. Verificar rasters MapBiomas
        print("\n5. Verificando rasters MapBiomas...")
        mapbiomas_rasters = [r for r in available_rasters if 'mapbiomas' in r.lower() or 'agropecuaria' in r.lower()]
        print(f"   MapBiomas encontrados: {len(mapbiomas_rasters)}")
        
        if mapbiomas_rasters:
            print("[OK] Rasters MapBiomas disponiveis:")
            for raster in mapbiomas_rasters:
                print(f"      - {raster}")
                
            # 6. Teste de carregamento
            print("\n6. Testando carregamento do primeiro raster...")
            test_raster = mapbiomas_rasters[0]
            data, metadata = loader.load_raster(test_raster)
            
            if data is not None and metadata is not None:
                print("[OK] Raster carregado com sucesso!")
                print(f"   Shape dos dados: {data.shape}")
                print(f"   Metadados: {metadata}")
                
                # 7. Teste de criação de overlay
                print("\n7. Testando criacao de overlay...")
                overlay = loader.raster_to_folium_overlay(data, metadata, opacity=0.7)
                
                if overlay is not None:
                    print("[OK] Overlay criado com sucesso!")
                else:
                    print("[ERRO] Falha ao criar overlay")
                    return False
            else:
                print("[ERRO] Falha ao carregar raster")
                return False
        else:
            print("[AVISO] Nenhum raster MapBiomas encontrado")
            return False
            
        # 8. Teste de criação de legenda
        print("\n8. Testando criacao de legenda...")
        legend = create_mapbiomas_legend()
        print(f"[OK] Legenda criada: {len(legend)} caracteres")
        
        print("\n" + "=" * 50)
        print("[SUCESSO] TODOS OS TESTES PASSARAM!")
        print("[OK] A integracao MapBiomas esta FUNCIONANDO CORRETAMENTE")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] ERRO DURANTE O TESTE: {e}")
        import traceback
        print("Traceback completo:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_mapbiomas_integration()
    sys.exit(0 if success else 1)