"""Database migrations for CP2B Maps - Clean and Simple"""
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_path():
    """Get the path to the database file"""
    return Path(__file__).parent.parent.parent / "data" / "cp2b_maps.db"

def create_database():
    """Create the SQLite database and tables with error handling"""
    try:
        db_path = get_database_path()
        
        # Ensure data directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory: {db_path.parent}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Create municipalities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS municipalities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cd_mun TEXT UNIQUE NOT NULL,
                    nome_municipio TEXT NOT NULL,
                    lat REAL DEFAULT 0,
                    lon REAL DEFAULT 0,
                    area_km2 REAL DEFAULT 0,
                    populacao_2022 INTEGER DEFAULT 0,
                    
                    -- Biogas potential columns (Nm³/ano)
                    total_final_nm_ano REAL DEFAULT 0,
                    total_agricola_nm_ano REAL DEFAULT 0,
                    total_pecuaria_nm_ano REAL DEFAULT 0,
                    
                    -- Agricultural sources
                    biogas_cana_nm_ano REAL DEFAULT 0,
                    biogas_soja_nm_ano REAL DEFAULT 0,
                    biogas_milho_nm_ano REAL DEFAULT 0,
                    biogas_cafe_nm_ano REAL DEFAULT 0,
                    biogas_citros_nm_ano REAL DEFAULT 0,
                    
                    -- Livestock sources  
                    biogas_bovinos_nm_ano REAL DEFAULT 0,
                    biogas_suino_nm_ano REAL DEFAULT 0,
                    biogas_aves_nm_ano REAL DEFAULT 0,
                    biogas_piscicultura_nm_ano REAL DEFAULT 0,
                    
                    -- Urban waste sources
                    rsu_potencial_nm_habitante_ano REAL DEFAULT 0,
                    rpo_potencial_nm_habitante_ano REAL DEFAULT 0,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_cd_mun ON municipalities(cd_mun)',
                'CREATE INDEX IF NOT EXISTS idx_nome ON municipalities(nome_municipio)',
                'CREATE INDEX IF NOT EXISTS idx_total ON municipalities(total_final_nm_ano DESC)'
            ]
            
            for index in indexes:
                cursor.execute(index)
            
            conn.commit()
            logger.info(f"✅ Database created successfully at: {db_path}")
            return db_path
            
    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        raise

def main():
    """Run database migrations"""
    logger.info("🔄 Starting database setup...")
    try:
        create_database()
        logger.info("✅ Database setup completed successfully!")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        raise

if __name__ == "__main__":
    main()