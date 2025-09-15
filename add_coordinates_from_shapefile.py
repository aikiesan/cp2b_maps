#!/usr/bin/env python3
"""
Adicionar coordenadas lat/lon calculadas dos centroides do shapefile
"""

import sqlite3
import pandas as pd
import geopandas as gpd
from pathlib import Path

def add_coordinates_from_shapefile():
    """Calcula centroides do shapefile e adiciona coordenadas ao banco"""

    base_path = Path(__file__).parent
    shp_path = base_path / "shapefile" / "SP_Municipios_2024.shp"
    db_path = base_path / "data" / "cp2b_maps.db"

    print("Carregando shapefile de municipios SP 2024...")
    gdf = gpd.read_file(shp_path)
    print(f"Carregados {len(gdf)} municipios do shapefile")

    # Converter para WGS84 (lat/lon) se necessário
    if gdf.crs != 'EPSG:4326':
        print(f"Convertendo de {gdf.crs} para EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')

    # Calcular centroides
    print("Calculando centroides...")
    centroids = gdf.geometry.centroid

    # Extrair coordenadas
    gdf['lon'] = centroids.x
    gdf['lat'] = centroids.y

    # Preparar dados para merge
    coords_df = gdf[['CD_MUN', 'NM_MUN', 'lat', 'lon']].copy()
    coords_df['CD_MUN'] = coords_df['CD_MUN'].astype(str)  # Converter para string

    print(f"Centroides calculados para {len(coords_df)} municipios")
    print(f"Range de coordenadas:")
    print(f"  - Latitude: {coords_df['lat'].min():.3f} a {coords_df['lat'].max():.3f}")
    print(f"  - Longitude: {coords_df['lon'].min():.3f} a {coords_df['lon'].max():.3f}")

    # Conectar ao banco e adicionar coordenadas
    with sqlite3.connect(db_path) as conn:
        # Adicionar colunas lat/lon se não existirem
        try:
            conn.execute('ALTER TABLE municipalities ADD COLUMN lat REAL')
            print("Coluna lat adicionada")
        except sqlite3.OperationalError:
            print("Coluna lat ja existe")

        try:
            conn.execute('ALTER TABLE municipalities ADD COLUMN lon REAL')
            print("Coluna lon adicionada")
        except sqlite3.OperationalError:
            print("Coluna lon ja existe")

        # Carregar dados atuais do banco
        df_db = pd.read_sql_query('SELECT * FROM municipalities', conn)
        print(f"Carregados {len(df_db)} municipios do banco")

        # Fazer merge usando cd_mun (string) com CD_MUN (string)
        print("Fazendo merge com coordenadas...")
        df_merged = df_db.merge(
            coords_df[['CD_MUN', 'lat', 'lon']],
            left_on='cd_mun',
            right_on='CD_MUN',
            how='left',
            suffixes=('', '_new')
        )

        # Atualizar coordenadas (usar as novas se disponíveis)
        df_merged['lat'] = df_merged['lat_new'].fillna(df_merged.get('lat', 0))
        df_merged['lon'] = df_merged['lon_new'].fillna(df_merged.get('lon', 0))

        # Remover colunas temporárias
        df_merged = df_merged.drop(columns=['lat_new', 'lon_new', 'CD_MUN'], errors='ignore')

        # Verificar resultados
        coords_added = df_merged['lat'].notna().sum()
        coords_nonzero = (df_merged['lat'] != 0).sum()
        print(f"Coordenadas válidas para {coords_nonzero} municipios")

        if coords_nonzero > 600:  # Esperamos pelo menos 600 municípios com coordenadas
            # Substituir tabela com dados atualizados
            print("Atualizando banco de dados...")
            df_merged.to_sql('municipalities', conn, index=False, if_exists='replace')

            # Recriar indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_nome_municipio ON municipalities(nome_municipio)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cd_mun ON municipalities(cd_mun)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_total_potential ON municipalities(total_final_nm_ano)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_lat_lon ON municipalities(lat, lon)')

            conn.commit()
            print("Banco de dados atualizado com coordenadas!")

            # Verificação final
            test_query = '''
            SELECT nome_municipio, lat, lon, total_final_nm_ano, cd_mun
            FROM municipalities
            WHERE lat != 0 AND lon != 0
            ORDER BY total_final_nm_ano DESC
            LIMIT 5
            '''
            test_result = pd.read_sql_query(test_query, conn)
            print("\\nVerificacao - Top 5 municipios com coordenadas:")
            for _, row in test_result.iterrows():
                print(f"  - {row['nome_municipio']} (ID: {row['cd_mun']}): ({row['lat']:.3f}, {row['lon']:.3f}) - {row['total_final_nm_ano']:,.0f} Nm³/ano")

            # Teste de análise de proximidade simulada
            print("\\nTeste de analise de proximidade (São Paulo, 50km):")
            proximity_test = '''
            SELECT nome_municipio, lat, lon, total_final_nm_ano,
                   SQRT(POW(lat - (-23.5505), 2) + POW(lon - (-46.6333), 2)) * 111 as distancia_km
            FROM municipalities
            WHERE lat != 0 AND lon != 0
            HAVING distancia_km <= 50
            ORDER BY total_final_nm_ano DESC
            LIMIT 5
            '''
            proximity_result = pd.read_sql_query(proximity_test, conn)
            print(f"Municipios encontrados num raio de 50km de SP: {len(proximity_result)}")
            for _, row in proximity_result.iterrows():
                print(f"  - {row['nome_municipio']}: {row['distancia_km']:.1f}km - {row['total_final_nm_ano']:,.0f} Nm³/ano")

            return True
        else:
            print(f"Erro: Apenas {coords_nonzero} municipios com coordenadas validas")
            return False

if __name__ == "__main__":
    add_coordinates_from_shapefile()