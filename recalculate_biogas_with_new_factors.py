#!/usr/bin/env python3
"""
Script to recalculate biogas potentials using literature-validated conversion factors.

This script:
1. Reads the new conversion factors from the conversion_factors table
2. Recalculates biogas potentials for all municipalities using updated factors
3. Updates the municipalities table with new values
4. Creates a backup of the original calculations for comparison
"""

import sqlite3
import pandas as pd
from datetime import datetime

def get_conversion_factors(db_path):
    """Get the new conversion factors from the database."""
    with sqlite3.connect(db_path) as conn:
        query = """
        SELECT category, subcategory, final_factor 
        FROM conversion_factors
        ORDER BY category, subcategory
        """
        df = pd.read_sql_query(query, conn)
    
    # Convert to dictionary for easy lookup
    factors = {}
    for _, row in df.iterrows():
        key = row['subcategory'].lower().replace('-', '_').replace('ã', 'a').replace('ú', 'u').replace('í', 'i')
        factors[key] = row['final_factor']
    
    return factors

def backup_current_calculations(db_path):
    """Create backup of current biogas calculations."""
    backup_table = f"municipalities_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    with sqlite3.connect(db_path) as conn:
        # Create backup table
        conn.execute(f"""
        CREATE TABLE {backup_table} AS 
        SELECT * FROM municipalities
        """)
        print(f"✅ Backup created: {backup_table}")
        return backup_table

def recalculate_biogas_potentials(db_path, factors):
    """Recalculate biogas potentials using new factors."""
    
    with sqlite3.connect(db_path) as conn:
        # Get current data with residue data and existing biogas calculations
        query = """
        SELECT cd_mun, nome_municipio,
               -- Residue data for crops (tons/year)
               residuos_cana_ton_ano,
               residuos_soja_ton_ano, 
               residuos_milho_ton_ano,
               -- Current biogas values for comparison
               biogas_cana_m_ano as old_biogas_cana,
               biogas_soja_m_ano as old_biogas_soja,
               biogas_milho_m_ano as old_biogas_milho,
               biogas_cafe_m_ano as old_biogas_cafe,
               biogas_citros_m_ano as old_biogas_citros,
               biogas_bovinos_m_ano as old_biogas_bovinos,
               biogas_suino_m_ano as old_biogas_suino,
               biogas_aves_m_ano as old_biogas_aves,
               -- Current totals
               total_final_m_ano as old_total_final,
               total_agricola_m_ano as old_total_agricola,
               total_pecuaria_m_ano as old_total_pecuaria,
               total_urbano_m_ano as old_total_urbano
        FROM municipalities
        WHERE cd_mun IS NOT NULL
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Apply new conversion factors
        print("🔄 Recalculating biogas potentials with new factors...")
        
        # Calculate current implied factors for livestock by reverse engineering
        print("📊 Calculating implied livestock factors from current data...")
        
        # For livestock, we need to back-calculate the livestock numbers from existing biogas values
        # and current factors, then apply new factors
        
        # Current implied factors (from our analysis)
        current_factors = {
            'cana': 167,
            'soja': 174,
            'milho': 168,
            'bovinos': 135,  # from real data analysis
            'suinos': 461,   # from real data analysis  
            'aves': 1.2      # from real data analysis
        }
        
        # Crops: Use residue data with new factors
        df['new_biogas_cana'] = df['residuos_cana_ton_ano'].fillna(0) * factors.get('cana_de_acucar', 85)
        df['new_biogas_soja'] = df['residuos_soja_ton_ano'].fillna(0) * factors.get('soja', 200) 
        df['new_biogas_milho'] = df['residuos_milho_ton_ano'].fillna(0) * factors.get('milho', 210)
        
        # For crops without residue data, proportionally adjust current values
        df['new_biogas_cafe'] = df['old_biogas_cafe'].fillna(0) * (factors.get('cafe', 280) / current_factors.get('cafe', 310))
        df['new_biogas_citros'] = df['old_biogas_citros'].fillna(0) * (factors.get('citros', 19) / current_factors.get('citros', 21))
        
        # Livestock: Back-calculate numbers and apply new factors
        df['new_biogas_bovinos'] = df['old_biogas_bovinos'].fillna(0) * (factors.get('bovinos', 130) / current_factors['bovinos'])
        df['new_biogas_suino'] = df['old_biogas_suino'].fillna(0) * (factors.get('suinos', 380) / current_factors['suinos'])
        df['new_biogas_aves'] = df['old_biogas_aves'].fillna(0) * (factors.get('aves', 1.5) / current_factors['aves'])
        
        # Calculate new totals
        df['new_total_agricola'] = (df['new_biogas_cana'] + df['new_biogas_soja'] + 
                                  df['new_biogas_milho'] + df['new_biogas_cafe'] + 
                                  df['new_biogas_citros'])
        
        df['new_total_pecuaria'] = (df['new_biogas_bovinos'] + df['new_biogas_suino'] + 
                                  df['new_biogas_aves'])
        
        # Keep urban totals unchanged (RSU + RPO)
        # Get current urban values
        urban_query = "SELECT cd_mun, rsu_potencial_m_ano, rpo_potencial_m_ano FROM municipalities"
        urban_df = pd.read_sql_query(urban_query, conn)
        df = df.merge(urban_df, on='cd_mun', how='left')
        
        df['new_total_urbano'] = (df['rsu_potencial_m_ano'].fillna(0) + 
                                df['rpo_potencial_m_ano'].fillna(0))
        
        df['new_total_final'] = (df['new_total_agricola'] + df['new_total_pecuaria'] + 
                               df['new_total_urbano'])
        
        # Update the database
        print("💾 Updating database with new calculations...")
        
        for _, row in df.iterrows():
            update_query = """
            UPDATE municipalities 
            SET biogas_cana_m_ano = ?,
                biogas_soja_m_ano = ?,
                biogas_milho_m_ano = ?,
                biogas_cafe_m_ano = ?,
                biogas_citros_m_ano = ?,
                biogas_bovinos_m_ano = ?,
                biogas_suino_m_ano = ?,
                biogas_aves_m_ano = ?,
                total_agricola_m_ano = ?,
                total_pecuaria_m_ano = ?,
                total_urbano_m_ano = ?,
                total_final_m_ano = ?
            WHERE cd_mun = ?
            """
            
            conn.execute(update_query, (
                row['new_biogas_cana'],
                row['new_biogas_soja'], 
                row['new_biogas_milho'],
                row['new_biogas_cafe'],
                row['new_biogas_citros'],
                row['new_biogas_bovinos'],
                row['new_biogas_suino'],
                row['new_biogas_aves'],
                row['new_total_agricola'],
                row['new_total_pecuaria'],
                row['new_total_urbano'],
                row['new_total_final'],
                row['cd_mun']
            ))
        
        conn.commit()
        
        # Generate comparison report
        print("\n📊 COMPARISON REPORT - OLD vs NEW FACTORS")
        print("=" * 60)
        
        # Calculate state-wide totals
        old_totals = {
            'cana': df['old_biogas_cana'].sum(),
            'soja': df['old_biogas_soja'].sum(),
            'milho': df['old_biogas_milho'].sum(),
            'cafe': df['old_biogas_cafe'].sum(),
            'citros': df['old_biogas_citros'].sum(),
            'bovinos': df['old_biogas_bovinos'].sum(),
            'suino': df['old_biogas_suino'].sum(),
            'aves': df['old_biogas_aves'].sum()
        }
        
        new_totals = {
            'cana': df['new_biogas_cana'].sum(),
            'soja': df['new_biogas_soja'].sum(),
            'milho': df['new_biogas_milho'].sum(),
            'cafe': df['new_biogas_cafe'].sum(),
            'citros': df['new_biogas_citros'].sum(),
            'bovinos': df['new_biogas_bovinos'].sum(),
            'suino': df['new_biogas_suino'].sum(),
            'aves': df['new_biogas_aves'].sum()
        }
        
        for category in old_totals.keys():
            old_val = old_totals[category]
            new_val = new_totals[category] 
            change = ((new_val - old_val) / old_val * 100) if old_val > 0 else 0
            
            print(f"{category.title():12} | Old: {old_val:>12,.0f} | New: {new_val:>12,.0f} | Change: {change:>+6.1f}%")
        
        print("=" * 60)
        
        old_total_final = sum(old_totals.values())
        new_total_final = sum(new_totals.values())
        total_change = ((new_total_final - old_total_final) / old_total_final * 100) if old_total_final > 0 else 0
        
        print(f"{'TOTAL':12} | Old: {old_total_final:>12,.0f} | New: {new_total_final:>12,.0f} | Change: {total_change:>+6.1f}%")
        print(f"\n✅ Successfully updated {len(df)} municipalities with literature-validated factors!")
        
        return df

def main():
    """Main execution function."""
    db_path = "data/cp2b_maps.db"
    
    print("🔬 BIOGAS CONVERSION FACTORS UPDATE")
    print("Using Literature-Validated Factors (2024)")
    print("=" * 50)
    
    try:
        # Step 1: Get new conversion factors
        print("📖 Loading new conversion factors...")
        factors = get_conversion_factors(db_path)
        
        print("\n🎯 New Conversion Factors:")
        for key, value in factors.items():
            print(f"  {key.title():15}: {value:>8} m³/unit/year")
        
        # Step 2: Create backup
        print(f"\n💾 Creating backup...")
        backup_table = backup_current_calculations(db_path)
        
        # Step 3: Recalculate
        result_df = recalculate_biogas_potentials(db_path, factors)
        
        print(f"\n🎉 Update completed successfully!")
        print(f"   - Backup table: {backup_table}")
        print(f"   - Updated municipalities: {len(result_df)}")
        print(f"   - New factors source: Academic literature 2023-2024")
        
    except Exception as e:
        print(f"❌ Error during update: {e}")
        raise

if __name__ == "__main__":
    main()