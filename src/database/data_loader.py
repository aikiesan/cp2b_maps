"""Data loader for CP2B Maps - Clean and Simple"""
import sqlite3
import pandas as pd
import logging
from pathlib import Path
from .migrations import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Column mapping for data cleaning
COLUMN_MAPPING = {
    'codigo_municipio': 'cd_mun',
    'codigo_ibge': 'cd_mun',
    'cd_municipio': 'cd_mun',
    'CD_MUN': 'cd_mun',
    'nome': 'nome_municipio',
    'municipio': 'nome_municipio',
    'NM_MUN': 'nome_municipio',
    'latitude': 'lat',
    'longitude': 'lon',
    'area': 'area_km2',
    'AREA_KM2': 'area_km2',
    'populacao': 'populacao_2022',
    'pop_2022': 'populacao_2022',
    # Biogas columns
    'TOTAL FINAL (Nm³/ano)': 'total_final_nm_ano',
    'Total Agrícola (Nm³/ano)': 'total_agricola_nm_ano',
    'Total Pecuária (Nm³/ano)': 'total_pecuaria_nm_ano',
    'Biogás Cana (Nm³/ano)': 'biogas_cana_nm_ano',
    'Biogás Soja (Nm³/ano)': 'biogas_soja_nm_ano',
    'Biogás Milho (Nm³/ano)': 'biogas_milho_nm_ano',
    'Biogás Café (Nm³/ano)': 'biogas_cafe_nm_ano',
    'Biogás Citros (Nm³/ano)': 'biogas_citros_nm_ano',
    'Biogás Bovino (Nm³/ano)': 'biogas_bovinos_nm_ano',
    'Biogás Suínos (Nm³/ano)': 'biogas_suino_nm_ano',
    'Biogás Aves (Nm³/ano)': 'biogas_aves_nm_ano',
    'Biogás Piscicultura (Nm³/ano)': 'biogas_piscicultura_nm_ano'
}

def find_data_file():
    """Find available data files"""
    project_root = Path(__file__).parent.parent.parent
    possible_paths = [
        # Check project data directory first
        project_root / "data" / "Dados_Por_Municipios_SP.xls",
        project_root / "Banco_De_Dados_Residuos_Biogas_Municipios_SP.xlsx",
        project_root / "data" / "municipal_data.csv",
        project_root / "data" / "municipal_data.xlsx",
        # Check common data directories
        Path.home() / "Documents" / "CP2B" / "Dados_Por_Municipios_SP.xls",
        Path.home() / "Downloads" / "Dados_Por_Municipios_SP.xls",
        # Current directory fallback
        Path.cwd() / "Dados_Por_Municipios_SP.xls"
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found data file: {path}")
            return path
    
    logger.warning("No data file found")
    return None

def clean_data(df):
    """Clean and standardize municipal data"""
    logger.info("🔄 Cleaning data...")
    
    # Rename columns
    df = df.rename(columns=COLUMN_MAPPING)
    
    # Ensure required columns exist
    required_columns = ['cd_mun', 'nome_municipio']
    for col in required_columns:
        if col not in df.columns:
            logger.warning(f"Required column '{col}' not found")
            if col == 'cd_mun':
                df['cd_mun'] = range(1, len(df) + 1)
            elif col == 'nome_municipio':
                df['nome_municipio'] = f"Município {range(1, len(df) + 1)}"
    
    # Clean numeric columns
    numeric_columns = [
        'lat', 'lon', 'area_km2', 'populacao_2022',
        'total_final_nm_ano', 'total_agricola_nm_ano', 'total_pecuaria_nm_ano',
        'biogas_cana_nm_ano', 'biogas_soja_nm_ano', 'biogas_milho_nm_ano',
        'biogas_cafe_nm_ano', 'biogas_citros_nm_ano', 'biogas_bovinos_nm_ano',
        'biogas_suino_nm_ano', 'biogas_aves_nm_ano', 'biogas_piscicultura_nm_ano',
        'rsu_potencial_nm_habitante_ano', 'rpo_potencial_nm_habitante_ano'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Ensure cd_mun is string
    if 'cd_mun' in df.columns:
        df['cd_mun'] = df['cd_mun'].astype(str)
    
    # Remove duplicates
    if 'cd_mun' in df.columns:
        df = df.drop_duplicates(subset=['cd_mun'])
    
    logger.info(f"✅ Data cleaned. Shape: {df.shape}")
    return df

def create_sample_data():
    """Create realistic sample data for testing"""
    logger.info("🔄 Creating sample data...")
    
    sample_data = [
        {
            'cd_mun': '3550308', 'nome_municipio': 'São Paulo',
            'lat': -23.5505, 'lon': -46.6333, 'area_km2': 1521.1, 'populacao_2022': 11451245,
            'total_final_nm_ano': 45000000, 'total_agricola_nm_ano': 5000000, 'total_pecuaria_nm_ano': 15000000,
            'biogas_cana_nm_ano': 2000000, 'biogas_soja_nm_ano': 1500000, 'biogas_bovinos_nm_ano': 8000000,
            'biogas_suino_nm_ano': 4000000, 'biogas_aves_nm_ano': 3000000,
            'rsu_potencial_nm_habitante_ano': 15000000, 'rpo_potencial_nm_habitante_ano': 10000000
        },
        {
            'cd_mun': '3509502', 'nome_municipio': 'Campinas',
            'lat': -22.9099, 'lon': -47.0626, 'area_km2': 794.4, 'populacao_2022': 1213792,
            'total_final_nm_ano': 18000000, 'total_agricola_nm_ano': 8000000, 'total_pecuaria_nm_ano': 6000000,
            'biogas_cana_nm_ano': 4000000, 'biogas_soja_nm_ano': 2000000, 'biogas_bovinos_nm_ano': 3000000,
            'biogas_suino_nm_ano': 2000000, 'biogas_aves_nm_ano': 1000000,
            'rsu_potencial_nm_habitante_ano': 2500000, 'rpo_potencial_nm_habitante_ano': 1500000
        },
        {
            'cd_mun': '3552205', 'nome_municipio': 'Sorocaba',
            'lat': -23.5018, 'lon': -47.4583, 'area_km2': 450.4, 'populacao_2022': 687357,
            'total_final_nm_ano': 12000000, 'total_agricola_nm_ano': 5000000, 'total_pecuaria_nm_ano': 4000000,
            'biogas_cana_nm_ano': 2500000, 'biogas_soja_nm_ano': 1500000, 'biogas_bovinos_nm_ano': 2000000,
            'biogas_suino_nm_ano': 1500000, 'biogas_aves_nm_ano': 500000,
            'rsu_potencial_nm_habitante_ano': 2000000, 'rpo_potencial_nm_habitante_ano': 1000000
        },
        {
            'cd_mun': '3516200', 'nome_municipio': 'Guarulhos',
            'lat': -23.4538, 'lon': -46.5333, 'area_km2': 318.7, 'populacao_2022': 1291784,
            'total_final_nm_ano': 15000000, 'total_agricola_nm_ano': 3000000, 'total_pecuaria_nm_ano': 7000000,
            'biogas_cana_nm_ano': 1500000, 'biogas_soja_nm_ano': 800000, 'biogas_bovinos_nm_ano': 4000000,
            'biogas_suino_nm_ano': 2000000, 'biogas_aves_nm_ano': 1000000,
            'rsu_potencial_nm_habitante_ano': 3000000, 'rpo_potencial_nm_habitante_ano': 2000000
        },
        {
            'cd_mun': '3548708', 'nome_municipio': 'Santo André',
            'lat': -23.6629, 'lon': -46.5383, 'area_km2': 175.8, 'populacao_2022': 748919,
            'total_final_nm_ano': 8000000, 'total_agricola_nm_ano': 1000000, 'total_pecuaria_nm_ano': 3000000,
            'biogas_cana_nm_ano': 500000, 'biogas_soja_nm_ano': 300000, 'biogas_bovinos_nm_ano': 1500000,
            'biogas_suino_nm_ano': 1000000, 'biogas_aves_nm_ano': 500000,
            'rsu_potencial_nm_habitante_ano': 2500000, 'rpo_potencial_nm_habitante_ano': 1500000
        },
        {
            'cd_mun': '3518800', 'nome_municipio': 'Hortolândia',
            'lat': -22.8582, 'lon': -47.2200, 'area_km2': 62.4, 'populacao_2022': 234259,
            'total_final_nm_ano': 5500000, 'total_agricola_nm_ano': 2000000, 'total_pecuaria_nm_ano': 2500000,
            'biogas_cana_nm_ano': 1200000, 'biogas_soja_nm_ano': 500000, 'biogas_bovinos_nm_ano': 1500000,
            'biogas_suino_nm_ano': 700000, 'biogas_aves_nm_ano': 300000,
            'rsu_potencial_nm_habitante_ano': 800000, 'rpo_potencial_nm_habitante_ano': 200000
        },
        {
            'cd_mun': '3547809', 'nome_municipio': 'Santos',
            'lat': -23.9618, 'lon': -46.3322, 'area_km2': 280.7, 'populacao_2022': 433656,
            'total_final_nm_ano': 3200000, 'total_agricola_nm_ano': 200000, 'total_pecuaria_nm_ano': 800000,
            'biogas_cana_nm_ano': 100000, 'biogas_soja_nm_ano': 50000, 'biogas_bovinos_nm_ano': 400000,
            'biogas_suino_nm_ano': 250000, 'biogas_aves_nm_ano': 150000,
            'rsu_potencial_nm_habitante_ano': 1500000, 'rpo_potencial_nm_habitante_ano': 700000
        }
    ]
    
    return pd.DataFrame(sample_data)

def load_data_to_database(df):
    """Load data into SQLite database"""
    if df is None or df.empty:
        logger.error("❌ Cannot load empty dataframe to database")
        return False

    try:
        db_path = get_database_path()

        if not db_path or not Path(db_path).exists():
            logger.error("❌ Database file not found or invalid path")
            return False

        with sqlite3.connect(db_path, timeout=30) as conn:
            # Get the actual database columns
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(municipalities)")
            db_info = cursor.fetchall()

            if not db_info:
                logger.error("❌ Table 'municipalities' not found in database")
                return False

            db_columns = [row[1] for row in db_info]
            logger.info(f"Database columns: {db_columns}")

            # Filter dataframe to only include columns that exist in the database
            available_columns = [col for col in df.columns if col in db_columns]
            if not available_columns:
                logger.error("❌ No matching columns found between data and database schema")
                return False

            df_filtered = df[available_columns].copy()
            logger.info(f"Filtered columns: {available_columns}")

            # Validate required columns
            required_cols = ['cd_mun', 'nome_municipio']
            missing_required = [col for col in required_cols if col not in available_columns]
            if missing_required:
                logger.warning(f"⚠️ Missing required columns: {missing_required}")

            # Clear existing data and insert new data
            try:
                cursor.execute("DELETE FROM municipalities")

                # Insert new data (to_sql handles its own transactions)
                df_filtered.to_sql('municipalities', conn, if_exists='append', index=False)

                # Verify insertion
                count = cursor.execute("SELECT COUNT(*) FROM municipalities").fetchone()[0]
                if count == 0:
                    raise ValueError("No data was inserted into the database")

                logger.info(f"✅ Successfully loaded {count} municipalities into database")
                return True

            except Exception as e:
                # Clear any partial data on error
                try:
                    cursor.execute("DELETE FROM municipalities")
                except:
                    pass  # If this fails, we'll catch it in the outer exception handler
                raise e

    except sqlite3.OperationalError as e:
        logger.error(f"❌ Database operation error: {e}")
        return False
    except sqlite3.DatabaseError as e:
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error loading data to database: {e}")
        return False

def load_municipal_data():
    """Main function to load municipal data"""
    logger.info("📊 Loading municipal data...")
    
    # Try to find real data file
    data_file = find_data_file()
    
    if data_file:
        try:
            logger.info(f"📄 Loading from file: {data_file}")

            # Load based on file type with better error handling
            if data_file.suffix.lower() in ['.xls', '.xlsx']:
                try:
                    df = pd.read_excel(data_file, engine='openpyxl')
                except Exception as e:
                    logger.warning(f"Failed with openpyxl engine: {e}. Trying xlrd...")
                    df = pd.read_excel(data_file, engine='xlrd')
            elif data_file.suffix.lower() == '.csv':
                # Try different encodings for CSV files
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                df = None
                for encoding in encodings:
                    try:
                        df = pd.read_csv(data_file, encoding=encoding)
                        logger.info(f"Successfully loaded CSV with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue

                if df is None:
                    raise ValueError(f"Could not decode CSV file with any of these encodings: {encodings}")
            else:
                raise ValueError(f"Unsupported file type: {data_file.suffix}")

            if df.empty:
                raise ValueError("Loaded file contains no data")

            logger.info(f"📊 Loaded {len(df)} records from file")

            # Clean data
            df = clean_data(df)

            if df.empty:
                raise ValueError("No data remaining after cleaning")

        except FileNotFoundError:
            logger.error(f"❌ File not found: {data_file}")
            df = create_sample_data()
        except pd.errors.EmptyDataError:
            logger.error(f"❌ File is empty: {data_file}")
            df = create_sample_data()
        except PermissionError:
            logger.error(f"❌ Permission denied accessing file: {data_file}")
            df = create_sample_data()
        except Exception as e:
            logger.warning(f"⚠️ Error loading file data: {e}. Using sample data instead.")
            df = create_sample_data()
    else:
        logger.info("📊 No data file found. Creating sample data.")
        df = create_sample_data()
    
    # Load to database
    success = load_data_to_database(df)
    
    if success:
        logger.info(f"✅ Data loading complete! {len(df)} municipalities loaded.")
    else:
        logger.error("❌ Failed to load data to database")
    
    return success

def main():
    """Main function"""
    logger.info("🔄 Starting data loading process...")
    try:
        success = load_municipal_data()
        if success:
            logger.info("✅ Data loading completed successfully!")
        else:
            logger.error("❌ Data loading failed!")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()