"""
Database Validation and Correction Script
Updates municipality data with 2022 Census information and removes region indicators
"""

import sqlite3
import pandas as pd
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_census_data(csv_path):
    """Load and parse the 2022 Census CSV data"""
    logger.info(f"Loading Census data from: {csv_path}")
    
    # Read CSV with proper handling of Brazilian number format
    df = pd.read_csv(csv_path)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Convert Brazilian number format (comma as decimal separator)
    df['Area_Da_Unidade_territorial_km²'] = (
        df['Area_Da_Unidade_territorial_km²']
        .astype(str)
        .str.replace(',', '.')
        .astype(float)
    )
    
    df['Densidade_Demografica_2022'] = (
        df['Densidade_Demografica_2022']
        .astype(str)
        .str.replace(',', '.')
        .astype(float)
    )
    
    # Rename columns to match database schema
    df = df.rename(columns={
        'CD_MUN': 'codigo_municipio',
        'NM_MUN': 'nome_municipio',
        'Populacao_Residente_2022': 'populacao_2022',
        'Area_Da_Unidade_territorial_km²': 'area_km2',
        'Densidade_Demografica_2022': 'densidade_demografica'
    })
    
    # Ensure codigo_municipio is string for matching
    df['codigo_municipio'] = df['codigo_municipio'].astype(str)
    
    logger.info(f"Loaded {len(df)} municipalities from Census data")
    return df

def update_database(db_path, census_df):
    """Update database with Census data"""
    logger.info(f"Updating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current municipality data
    current_data = pd.read_sql_query(
        "SELECT nome_municipio, codigo_municipio, cd_mun, populacao_2022, area_km2 FROM municipalities",
        conn
    )
    
    logger.info(f"Current database has {len(current_data)} municipalities")
    
    updates_made = 0
    mismatches = []
    
    for _, census_row in census_df.iterrows():
        codigo = str(census_row['codigo_municipio'])
        nome_censo = census_row['nome_municipio']
        pop_censo = census_row['populacao_2022']
        area_censo = census_row['area_km2']
        
        # Find matching municipality in database
        db_match = current_data[
            (current_data['codigo_municipio'].astype(str) == codigo) |
            (current_data['cd_mun'].astype(str) == codigo)
        ]
        
        if len(db_match) > 0:
            db_row = db_match.iloc[0]
            nome_db = db_row['nome_municipio']
            pop_db = db_row['populacao_2022']
            area_db = db_row['area_km2']
            
            # Check if update is needed
            pop_diff = abs(pop_censo - pop_db) if pd.notna(pop_db) else float('inf')
            area_diff = abs(area_censo - area_db) if pd.notna(area_db) else float('inf')
            
            if pop_diff > 1 or area_diff > 0.001:  # Allow small floating point differences
                # Update the record
                cursor.execute("""
                    UPDATE municipalities 
                    SET populacao_2022 = ?, area_km2 = ?, nome_municipio = ?
                    WHERE codigo_municipio = ? OR cd_mun = ?
                """, (pop_censo, area_censo, nome_censo, codigo, codigo))
                
                updates_made += 1
                mismatches.append({
                    'codigo': codigo,
                    'nome_censo': nome_censo,
                    'nome_db': nome_db,
                    'pop_censo': pop_censo,
                    'pop_db': pop_db,
                    'pop_diff': pop_diff,
                    'area_censo': area_censo,
                    'area_db': area_db,
                    'area_diff': area_diff
                })
                
                logger.info(f"Updated {nome_censo} (code: {codigo})")
                logger.info(f"  Population: {pop_db} -> {pop_censo}")
                logger.info(f"  Area: {area_db} -> {area_censo}")
        else:
            logger.warning(f"Municipality not found in database: {nome_censo} (code: {codigo})")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Database update complete. Made {updates_made} updates.")
    return mismatches

def generate_validation_report(mismatches, output_path="validation_report.txt"):
    """Generate a validation report of changes made"""
    logger.info(f"Generating validation report: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("DATABASE VALIDATION AND CORRECTION REPORT\n")
        f.write("="*50 + "\n\n")
        f.write(f"Total municipalities updated: {len(mismatches)}\n\n")
        
        if mismatches:
            f.write("DETAILED CHANGES:\n")
            f.write("-" * 30 + "\n")
            
            for mismatch in mismatches:
                f.write(f"\nMunicipality: {mismatch['nome_censo']} (Code: {mismatch['codigo']})\n")
                f.write(f"  Name Database: {mismatch['nome_db']}\n")
                f.write(f"  Population: {mismatch['pop_db']:,.0f} -> {mismatch['pop_censo']:,.0f} (diff: {mismatch['pop_diff']:,.0f})\n")
                f.write(f"  Area: {mismatch['area_db']:.3f} -> {mismatch['area_censo']:.3f} (diff: {mismatch['area_diff']:.3f})\n")
        else:
            f.write("No changes were needed - all data was already correct.\n")
    
    logger.info("Validation report generated successfully")

def main():
    """Main execution function"""
    # Paths
    csv_path = "Censo 2022 - Território - São Paulo.csv"
    db_path = "data/cp2b_maps.db"
    
    try:
        # Load Census data
        census_df = load_census_data(csv_path)
        
        # Update database
        mismatches = update_database(db_path, census_df)
        
        # Generate report
        generate_validation_report(mismatches)
        
        logger.info("Database validation and correction completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        raise

if __name__ == "__main__":
    main()