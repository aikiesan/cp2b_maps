#!/usr/bin/env python3
"""
Estimar potencial de biogás para municípios zerados
Baseia-se em dados reais de RSU per capita e área
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

def estimate_zero_municipalities():
    """Estima potencial de biogás para municípios com valores zerados"""

    base_path = Path(__file__).parent
    db_path = base_path / "data" / "cp2b_maps.db"

    print("Iniciando estimativas para municipios zerados...")

    with sqlite3.connect(db_path) as conn:
        # Carregar todos os dados
        df = pd.read_sql_query('SELECT * FROM municipalities', conn)
        print(f"Carregados {len(df)} municipios")

        # Identificar municípios zerados
        zeros = df[df['total_final_nm_ano'] == 0].copy()
        print(f"Municipios zerados: {len(zeros)}")

        if len(zeros) == 0:
            print("Nenhum municipio zerado encontrado!")
            return

        # Calcular estatísticas dos municípios com dados
        with_data = df[df['rsu_potencial_nm_ano'] > 0].copy()

        # RSU per capita médio e desvio padrão
        with_data['rsu_per_capita'] = with_data['rsu_potencial_nm_ano'] / with_data['populacao_2022']
        rsu_per_capita_mean = with_data['rsu_per_capita'].mean()
        rsu_per_capita_std = with_data['rsu_per_capita'].std()

        print(f"\\nEstatisticas RSU dos municipios com dados:")
        print(f"  RSU per capita medio: {rsu_per_capita_mean:.1f} Nm³/hab/ano")
        print(f"  RSU per capita desvio: {rsu_per_capita_std:.1f}")
        print(f"  RSU per capita minimo: {with_data['rsu_per_capita'].min():.1f}")
        print(f"  RSU per capita maximo: {with_data['rsu_per_capita'].max():.1f}")

        # RPO por área (para municípios que têm RPO)
        with_rpo = df[df['rpo_potencial_nm_ano'] > 0].copy()
        if len(with_rpo) > 0:
            with_rpo['rpo_per_km2'] = with_rpo['rpo_potencial_nm_ano'] / with_rpo['area_km2']
            rpo_per_km2_mean = with_rpo['rpo_per_km2'].mean()
            print(f"  RPO per km² medio: {rpo_per_km2_mean:.1f} Nm³/km²/ano")
        else:
            rpo_per_km2_mean = 0

        # Aplicar estimativas aos municípios zerados
        print(f"\\nAplicando estimativas a {len(zeros)} municipios:")

        for idx, row in zeros.iterrows():
            municipio = row['nome_municipio']
            pop = row['populacao_2022']
            area = row['area_km2']

            # Estimativa RSU baseada na população (usando média conservadora)
            # Usar 80% da média para ser conservador
            estimated_rsu = pop * rsu_per_capita_mean * 0.8

            # Estimativa RPO baseada na área (apenas se município tem área significativa)
            # RPO é mais raro, então usar estimativa muito conservadora
            estimated_rpo = 0
            if area > 100:  # Apenas para municípios maiores
                estimated_rpo = area * rpo_per_km2_mean * 0.1  # 10% da média

            # Estimar algum potencial agrícola baseado na área (muito conservador)
            estimated_agri = 0
            if area > 200:  # Apenas municípios grandes
                # Estimativa muito conservadora: 10 Nm³ por km² para agricultura
                estimated_agri = area * 10

            # Total estimado
            estimated_total = estimated_rsu + estimated_rpo + estimated_agri

            print(f"  {municipio}:")
            print(f"    Pop: {pop:,.0f} -> RSU estimado: {estimated_rsu:,.0f} Nm³/ano")
            if estimated_rpo > 0:
                print(f"    Area: {area:.1f}km² -> RPO estimado: {estimated_rpo:,.0f} Nm³/ano")
            if estimated_agri > 0:
                print(f"    Agricola estimado: {estimated_agri:,.0f} Nm³/ano")
            print(f"    TOTAL ESTIMADO: {estimated_total:,.0f} Nm³/ano")

            # Atualizar o DataFrame
            df.loc[df['nome_municipio'] == municipio, 'rsu_potencial_nm_ano'] = estimated_rsu
            if estimated_rpo > 0:
                df.loc[df['nome_municipio'] == municipio, 'rpo_potencial_nm_ano'] = estimated_rpo

            # Recalcular totais
            df.loc[df['nome_municipio'] == municipio, 'total_urbano_nm_ano'] = estimated_rsu + estimated_rpo
            df.loc[df['nome_municipio'] == municipio, 'total_final_nm_ano'] = estimated_total

        # Salvar no banco de dados
        print(f"\\nAtualizando banco de dados...")
        df.to_sql('municipalities', conn, index=False, if_exists='replace')

        # Recriar índices
        conn.execute('CREATE INDEX IF NOT EXISTS idx_nome_municipio ON municipalities(nome_municipio)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_cd_mun ON municipalities(cd_mun)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_total_potential ON municipalities(total_final_nm_ano)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_lat_lon ON municipalities(lat, lon)')

        conn.commit()
        print("Banco atualizado!")

        # Verificação final
        verification_query = '''
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN total_final_nm_ano = 0 THEN 1 END) as zeros,
            COUNT(CASE WHEN total_final_nm_ano > 0 THEN 1 END) as non_zeros,
            MIN(total_final_nm_ano) as min_total,
            AVG(total_final_nm_ano) as avg_total
        FROM municipalities
        '''

        verification = pd.read_sql_query(verification_query, conn)
        print(f"\\nVerificacao final:")
        print(f"  Total municipios: {verification.iloc[0]['total']}")
        print(f"  Com potencial zero: {verification.iloc[0]['zeros']}")
        print(f"  Com potencial > 0: {verification.iloc[0]['non_zeros']}")
        print(f"  Potencial minimo: {verification.iloc[0]['min_total']:,.0f} Nm³/ano")
        print(f"  Potencial medio: {verification.iloc[0]['avg_total']:,.0f} Nm³/ano")

        if verification.iloc[0]['zeros'] == 0:
            print("\\n✅ SUCESSO: Todos os municipios agora tem potencial > 0!")
        else:
            print(f"\\n⚠️  Ainda restam {verification.iloc[0]['zeros']} municipios zerados")

        # Mostrar alguns dos municípios que foram estimados
        print(f"\\nExemplos de municipios estimados:")
        updated_query = '''
        SELECT nome_municipio, populacao_2022, rsu_potencial_nm_ano, total_final_nm_ano
        FROM municipalities
        WHERE nome_municipio IN ('Santos', 'Cotia', 'Bertioga', 'São Bernardo do Campo')
        ORDER BY total_final_nm_ano DESC
        '''
        examples = pd.read_sql_query(updated_query, conn)
        for _, row in examples.iterrows():
            print(f"  - {row['nome_municipio']}: {row['total_final_nm_ano']:,.0f} Nm³/ano (RSU: {row['rsu_potencial_nm_ano']:,.0f})")

        return True

if __name__ == "__main__":
    estimate_zero_municipalities()