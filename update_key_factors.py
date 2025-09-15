#!/usr/bin/env python3
"""
Focused update script - Only updates the most important conversion factors.

Updates only factors with significant discrepancies from literature:
1. Suínos: 461 → 380 m³/cabeça/ano (-18%)
2. Aves: 1.2 → 1.5 m³/ave/ano (+25%) 
3. Soja: 174 → 200 m³/ton (+15%)
4. Milho: 168 → 210 m³/ton (+25%)

Other factors remain unchanged as they are already close to literature values.
"""

import sqlite3
import pandas as pd
from datetime import datetime

def update_key_conversion_factors(db_path):
    """Update only the most important conversion factors."""
    
    # Define the key factors to update
    factor_updates = {
        'suinos': {'old': 461, 'new': 380, 'change': -17.6},
        'aves': {'old': 1.2, 'new': 1.5, 'change': 25.0},
        'soja': {'old': 174, 'new': 200, 'change': 14.9},
        'milho': {'old': 168, 'new': 210, 'change': 25.0}
    }
    
    print("FOCUSED BIOGAS CONVERSION FACTORS UPDATE")
    print("Literature-Validated Key Factors Only")
    print("=" * 50)
    
    for factor, data in factor_updates.items():
        print(f"{factor.title():8}: {data['old']:>6} -> {data['new']:>6} ({data['change']:+5.1f}%)")
    
    print("=" * 50)
    
    with sqlite3.connect(db_path) as conn:
        # Create backup first
        backup_table = f"municipalities_backup_focused_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conn.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM municipalities")
        print(f"Backup created: {backup_table}")
        
        # Get current data
        query = """
        SELECT cd_mun, nome_municipio,
               residuos_soja_ton_ano,
               residuos_milho_ton_ano,
               biogas_soja_m_ano,
               biogas_milho_m_ano,
               biogas_suino_m_ano,
               biogas_aves_m_ano,
               total_final_m_ano,
               total_agricola_m_ano,
               total_pecuaria_m_ano
        FROM municipalities
        WHERE cd_mun IS NOT NULL
        """
        
        df = pd.read_sql_query(query, conn)
        
        print("Applying focused updates...")
        
        # Calculate new values
        df['new_biogas_soja'] = df['residuos_soja_ton_ano'].fillna(0) * factor_updates['soja']['new']
        df['new_biogas_milho'] = df['residuos_milho_ton_ano'].fillna(0) * factor_updates['milho']['new']
        
        # For livestock, adjust proportionally from current values
        df['new_biogas_suino'] = df['biogas_suino_m_ano'].fillna(0) * (factor_updates['suinos']['new'] / factor_updates['suinos']['old'])
        df['new_biogas_aves'] = df['biogas_aves_m_ano'].fillna(0) * (factor_updates['aves']['new'] / factor_updates['aves']['old'])
        
        # Calculate changes
        df['delta_soja'] = df['new_biogas_soja'] - df['biogas_soja_m_ano'].fillna(0)
        df['delta_milho'] = df['new_biogas_milho'] - df['biogas_milho_m_ano'].fillna(0)
        df['delta_suino'] = df['new_biogas_suino'] - df['biogas_suino_m_ano'].fillna(0)
        df['delta_aves'] = df['new_biogas_aves'] - df['biogas_aves_m_ano'].fillna(0)
        
        df['total_delta_agricola'] = df['delta_soja'] + df['delta_milho']
        df['total_delta_pecuaria'] = df['delta_suino'] + df['delta_aves']
        df['total_delta'] = df['total_delta_agricola'] + df['total_delta_pecuaria']
        
        # Update new totals
        df['new_total_agricola'] = df['total_agricola_m_ano'].fillna(0) + df['total_delta_agricola']
        df['new_total_pecuaria'] = df['total_pecuaria_m_ano'].fillna(0) + df['total_delta_pecuaria']
        df['new_total_final'] = df['total_final_m_ano'].fillna(0) + df['total_delta']
        
        # Update database
        print("Updating database...")
        
        for _, row in df.iterrows():
            update_query = """
            UPDATE municipalities 
            SET biogas_soja_m_ano = ?,
                biogas_milho_m_ano = ?,
                biogas_suino_m_ano = ?,
                biogas_aves_m_ano = ?,
                total_agricola_m_ano = ?,
                total_pecuaria_m_ano = ?,
                total_final_m_ano = ?
            WHERE cd_mun = ?
            """
            
            conn.execute(update_query, (
                row['new_biogas_soja'],
                row['new_biogas_milho'],
                row['new_biogas_suino'],
                row['new_biogas_aves'],
                row['new_total_agricola'],
                row['new_total_pecuaria'],
                row['new_total_final'],
                row['cd_mun']
            ))
        
        conn.commit()
        
        # Generate summary report
        print("\nUPDATE SUMMARY")
        print("=" * 40)
        
        total_changes = {
            'soja': df['delta_soja'].sum(),
            'milho': df['delta_milho'].sum(), 
            'suino': df['delta_suino'].sum(),
            'aves': df['delta_aves'].sum()
        }
        
        for category, change in total_changes.items():
            print(f"{category.title():8}: {change:>+15,.0f} m³/ano")
        
        total_state_change = sum(total_changes.values())
        current_state_total = df['total_final_m_ano'].sum()
        percentage_change = (total_state_change / current_state_total * 100) if current_state_total > 0 else 0
        
        print("-" * 40)
        print(f"{'TOTAL':8}: {total_state_change:>+15,.0f} m³/ano ({percentage_change:+.1f}%)")
        
        print(f"\nUpdated {len(df)} municipalities")
        print(f"State total potential change: {percentage_change:+.1f}%")
        
        return df

def main():
    """Main execution function."""
    db_path = "data/cp2b_maps.db"
    
    try:
        result_df = update_key_conversion_factors(db_path)
        print(f"\nFocused update completed successfully!")
        print(f"   - Only key factors updated (Suinos, Aves, Soja, Milho)")
        print(f"   - Literature-validated changes applied")
        print(f"   - Conservative approach maintained")
        
    except Exception as e:
        print(f"Error during update: {e}")
        raise

if __name__ == "__main__":
    main()