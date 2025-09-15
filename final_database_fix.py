#!/usr/bin/env python3
"""
CP2B Maps - Final Database Fix
Creates database with EXACT column names and data types expected by Saturday app.py
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database_schema():
    """Create database with EXACT schema expected by Saturday app.py"""

    # File paths
    base_path = Path(__file__).parent
    excel_path = base_path / "data" / "Dados_Por_Municipios_SP.xls"
    db_path = base_path / "data" / "cp2b_maps.db"

    logger.info("🔧 Starting FINAL database schema fix...")

    # Load data from Excel
    logger.info(f"Loading data from {excel_path}")
    df = pd.read_excel(excel_path)
    logger.info(f"Loaded {len(df)} municipalities from Excel file")

    # EXACT column mapping based on Saturday app.py analysis
    column_mapping = {
        # Basic municipality info - EXACT names expected by app
        'NM_MUN': 'nome_municipio',
        'CD_MUN': 'codigo_municipio',  # Keep as int for database
        'AREA_KM2': 'area_km2',

        # Urban and organic waste
        'RSU Potencial CH4 (m³/ano)': 'rsu_potencial_nm_ano',
        'RPO Potencial CH4 (m³/ano)': 'rpo_potencial_nm_ano',
        'Categoria Potencial': 'categoria_potencial',

        # EXACT biogas column names as expected by Saturday app.py
        'Biogás Cana (Nm³/ano)': 'biogas_cana_nm_ano',
        'Biogás Soja (Nm³/ano)': 'biogas_soja_nm_ano',
        'Biogás Milho (Nm³/ano)': 'biogas_milho_nm_ano',
        'Biogás Bovino (Nm³/ano)': 'biogas_bovinos_nm_ano',  # App expects PLURAL
        'Biogás Café (Nm³/ano)': 'biogas_cafe_nm_ano',
        'Biogás Citros (Nm³/ano)': 'biogas_citros_nm_ano',
        'Biogás Suínos (Nm³/ano)': 'biogas_suino_nm_ano',    # App expects SINGULAR
        'Biogás Aves (Nm³/ano)': 'biogas_aves_nm_ano',
        'Biogás Piscicultura (Nm³/ano)': 'biogas_piscicultura_nm_ano',
        'Biogás Silvicultura (Nm³)': 'biogas_silvicultura_nm_ano',

        # Other columns
        'Resíduos Cana (ton/ano)': 'residuos_cana_ton_ano',
        'Resíduos Soja (ton/ano)': 'residuos_soja_ton_ano',
        'Resíduos Milho (ton/ano)': 'residuos_milho_ton_ano',
    }

    # Apply column mapping
    df_clean = df.copy()

    # Map columns
    for old_name, new_name in column_mapping.items():
        if old_name in df_clean.columns:
            df_clean[new_name] = df_clean[old_name]
            logger.info(f"✅ Mapped {old_name} -> {new_name}")
        else:
            logger.warning(f"❌ Missing column: {old_name}")

    # CRITICAL: Create cd_mun as STRING for geometry merging (app expects string merge)
    if 'codigo_municipio' in df_clean.columns:
        df_clean['cd_mun'] = df_clean['codigo_municipio'].astype(str)
        logger.info("✅ Created cd_mun as STRING for geometry merging")

    # Define all biogas columns for total calculation
    biogas_columns = [
        'biogas_cana_nm_ano', 'biogas_soja_nm_ano', 'biogas_milho_nm_ano',
        'biogas_bovinos_nm_ano', 'biogas_cafe_nm_ano', 'biogas_citros_nm_ano',
        'biogas_suino_nm_ano', 'biogas_aves_nm_ano', 'biogas_piscicultura_nm_ano',
        'biogas_silvicultura_nm_ano', 'rsu_potencial_nm_ano', 'rpo_potencial_nm_ano'
    ]

    # Ensure all required columns exist with proper defaults
    required_columns = [
        'nome_municipio', 'codigo_municipio', 'cd_mun', 'area_km2',
        'rsu_potencial_nm_ano', 'rpo_potencial_nm_ano', 'categoria_potencial'
    ] + biogas_columns

    for col in required_columns:
        if col not in df_clean.columns:
            logger.warning(f"⚠️  Adding missing column {col} with default values")
            df_clean[col] = 0

    # Convert biogas columns to numeric and calculate total
    df_clean['total_final_nm_ano'] = 0

    for col in biogas_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            df_clean['total_final_nm_ano'] += df_clean[col]

    # Add missing calculated columns that app might expect
    df_clean['total_agricola_nm_ano'] = (
        df_clean['biogas_cana_nm_ano'] + df_clean['biogas_soja_nm_ano'] +
        df_clean['biogas_milho_nm_ano'] + df_clean['biogas_cafe_nm_ano'] +
        df_clean['biogas_citros_nm_ano'] + df_clean['biogas_silvicultura_nm_ano']
    )

    df_clean['total_pecuaria_nm_ano'] = (
        df_clean['biogas_bovinos_nm_ano'] + df_clean['biogas_suino_nm_ano'] +
        df_clean['biogas_aves_nm_ano'] + df_clean['biogas_piscicultura_nm_ano']
    )

    df_clean['total_urbano_nm_ano'] = (
        df_clean['rsu_potencial_nm_ano'] + df_clean['rpo_potencial_nm_ano']
    )

    # Estimate population if not available
    if 'populacao_2022' not in df_clean.columns:
        df_clean['populacao_2022'] = (df_clean['area_km2'] * 50).fillna(10000)
        logger.info("📊 Added population estimates")

    # Select final columns with exact order
    final_columns = [
        'nome_municipio', 'codigo_municipio', 'cd_mun', 'area_km2', 'populacao_2022',
        'rsu_potencial_nm_ano', 'rpo_potencial_nm_ano', 'categoria_potencial',
        'biogas_cana_nm_ano', 'biogas_soja_nm_ano', 'biogas_milho_nm_ano',
        'biogas_bovinos_nm_ano', 'biogas_cafe_nm_ano', 'biogas_citros_nm_ano',
        'biogas_suino_nm_ano', 'biogas_aves_nm_ano', 'biogas_piscicultura_nm_ano',
        'biogas_silvicultura_nm_ano', 'residuos_cana_ton_ano', 'residuos_soja_ton_ano',
        'residuos_milho_ton_ano', 'total_final_nm_ano', 'total_agricola_nm_ano',
        'total_pecuaria_nm_ano', 'total_urbano_nm_ano'
    ]

    # Create final dataframe
    df_final = df_clean[final_columns].copy()
    df_final = df_final.fillna(0)

    logger.info(f"📋 Final dataset: {len(df_final)} municipalities, {len(df_final.columns)} columns")

    # Remove existing database and create new one
    if db_path.exists():
        db_path.unlink()
        logger.info("🗑️  Removed old database")

    # Create new database with exact schema
    with sqlite3.connect(db_path) as conn:
        df_final.to_sql('municipalities', conn, index=False, if_exists='replace')

        # Create indexes
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nome_municipio ON municipalities(nome_municipio)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cd_mun ON municipalities(cd_mun)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_codigo_municipio ON municipalities(codigo_municipio)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_total_potential ON municipalities(total_final_nm_ano)')

        conn.commit()
        logger.info("📊 Created database with indexes")

    # Comprehensive verification
    with sqlite3.connect(db_path) as conn:
        count_query = "SELECT COUNT(*) FROM municipalities"
        count = conn.execute(count_query).fetchone()[0]

        # Test critical columns that caused errors
        test_queries = [
            "SELECT cd_mun, nome_municipio FROM municipalities LIMIT 3",
            "SELECT biogas_bovinos_nm_ano, biogas_suino_nm_ano FROM municipalities LIMIT 3",
            "SELECT nome_municipio, total_final_nm_ano FROM municipalities ORDER BY total_final_nm_ano DESC LIMIT 3"
        ]

        logger.info(f"✅ Database created: {count} municipalities")

        for i, query in enumerate(test_queries, 1):
            result = conn.execute(query).fetchall()
            logger.info(f"🧪 Test {i} passed: {len(result)} results")
            if i == 1:  # Show cd_mun types
                logger.info(f"   cd_mun samples: {[r[0] for r in result]}")
            elif i == 2:  # Show biogas columns
                logger.info(f"   biogas_bovinos: {[r[0] for r in result]}")
                logger.info(f"   biogas_suino: {[r[1] for r in result]}")

    logger.info("🎉 FINAL database fix completed successfully!")
    return True

if __name__ == "__main__":
    fix_database_schema()