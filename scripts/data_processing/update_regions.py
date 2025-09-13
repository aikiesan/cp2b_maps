#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar o banco de dados com informações de região baseadas na lista do IBGE 2017
"""

import sqlite3
import pandas as pd

# Mapeamento de municípios para regiões baseado na lista IBGE 2017
REGION_MAPPING = {
    # Região Intermediária de São Paulo (3501)
    'Arujá': ('São Paulo', 'São Paulo'),
    'Barueri': ('São Paulo', 'São Paulo'),
    'Biritiba Mirim': ('São Paulo', 'São Paulo'),
    'Caieiras': ('São Paulo', 'São Paulo'),
    'Cajamar': ('São Paulo', 'São Paulo'),
    'Carapicuíba': ('São Paulo', 'São Paulo'),
    'Cotia': ('São Paulo', 'São Paulo'),
    'Diadema': ('São Paulo', 'São Paulo'),
    'Embu das Artes': ('São Paulo', 'São Paulo'),
    'Embu-Guaçu': ('São Paulo', 'São Paulo'),
    'Ferraz de Vasconcelos': ('São Paulo', 'São Paulo'),
    'Francisco Morato': ('São Paulo', 'São Paulo'),
    'Franco da Rocha': ('São Paulo', 'São Paulo'),
    'Guararema': ('São Paulo', 'São Paulo'),
    'Guarulhos': ('São Paulo', 'São Paulo'),
    'Itapecerica da Serra': ('São Paulo', 'São Paulo'),
    'Itapevi': ('São Paulo', 'São Paulo'),
    'Itaquaquecetuba': ('São Paulo', 'São Paulo'),
    'Jandira': ('São Paulo', 'São Paulo'),
    'Juquitiba': ('São Paulo', 'São Paulo'),
    'Mairiporã': ('São Paulo', 'São Paulo'),
    'Mauá': ('São Paulo', 'São Paulo'),
    'Mogi das Cruzes': ('São Paulo', 'São Paulo'),
    'Osasco': ('São Paulo', 'São Paulo'),
    'Pirapora do Bom Jesus': ('São Paulo', 'São Paulo'),
    'Poá': ('São Paulo', 'São Paulo'),
    'Ribeirão Pires': ('São Paulo', 'São Paulo'),
    'Rio Grande da Serra': ('São Paulo', 'São Paulo'),
    'Salesópolis': ('São Paulo', 'São Paulo'),
    'Santa Isabel': ('São Paulo', 'São Paulo'),
    'Santana de Parnaíba': ('São Paulo', 'São Paulo'),
    'Santo André': ('São Paulo', 'São Paulo'),
    'São Bernardo do Campo': ('São Paulo', 'São Paulo'),
    'São Caetano do Sul': ('São Paulo', 'São Paulo'),
    'São Lourenço da Serra': ('São Paulo', 'São Paulo'),
    'São Paulo': ('São Paulo', 'São Paulo'),
    'Suzano': ('São Paulo', 'São Paulo'),
    'Taboão da Serra': ('São Paulo', 'São Paulo'),
    'Vargem Grande Paulista': ('São Paulo', 'São Paulo'),
    
    # Santos
    'Bertioga': ('São Paulo', 'Santos'),
    'Cubatão': ('São Paulo', 'Santos'),
    'Guarujá': ('São Paulo', 'Santos'),
    'Itanhaém': ('São Paulo', 'Santos'),
    'Itariri': ('São Paulo', 'Santos'),
    'Mongaguá': ('São Paulo', 'Santos'),
    'Pedro de Toledo': ('São Paulo', 'Santos'),
    'Peruíbe': ('São Paulo', 'Santos'),
    'Praia Grande': ('São Paulo', 'Santos'),
    'Santos': ('São Paulo', 'Santos'),
    'São Vicente': ('São Paulo', 'Santos'),
    
    # Região Intermediária de Sorocaba (3502)
    'Alumínio': ('Sorocaba', 'Sorocaba'),
    'Araçariguama': ('Sorocaba', 'Sorocaba'),
    'Araçoiaba da Serra': ('Sorocaba', 'Sorocaba'),
    'Boituva': ('Sorocaba', 'Sorocaba'),
    'Capela do Alto': ('Sorocaba', 'Sorocaba'),
    'Cerquilho': ('Sorocaba', 'Sorocaba'),
    'Ibiúna': ('Sorocaba', 'Sorocaba'),
    'Iperó': ('Sorocaba', 'Sorocaba'),
    'Itu': ('Sorocaba', 'Sorocaba'),
    'Jumirim': ('Sorocaba', 'Sorocaba'),
    'Mairinque': ('Sorocaba', 'Sorocaba'),
    'Piedade': ('Sorocaba', 'Sorocaba'),
    'Pilar do Sul': ('Sorocaba', 'Sorocaba'),
    'Porto Feliz': ('Sorocaba', 'Sorocaba'),
    'Salto': ('Sorocaba', 'Sorocaba'),
    'Salto de Pirapora': ('Sorocaba', 'Sorocaba'),
    'São Roque': ('Sorocaba', 'Sorocaba'),
    'Sarapuí': ('Sorocaba', 'Sorocaba'),
    'Sorocaba': ('Sorocaba', 'Sorocaba'),
    'Tapiraí': ('Sorocaba', 'Sorocaba'),
    'Tietê': ('Sorocaba', 'Sorocaba'),
    'Votorantim': ('Sorocaba', 'Sorocaba'),
    
    # Itapeva
    'Apiaí': ('Sorocaba', 'Itapeva'),
    'Barão de Antonina': ('Sorocaba', 'Itapeva'),
    'Barra do Chapéu': ('Sorocaba', 'Itapeva'),
    'Bom Sucesso de Itararé': ('Sorocaba', 'Itapeva'),
    'Buri': ('Sorocaba', 'Itapeva'),
    'Capão Bonito': ('Sorocaba', 'Itapeva'),
    'Guapiara': ('Sorocaba', 'Itapeva'),
    'Itaberá': ('Sorocaba', 'Itapeva'),
    'Itaoca': ('Sorocaba', 'Itapeva'),
    'Itapeva': ('Sorocaba', 'Itapeva'),
    'Itapirapuã Paulista': ('Sorocaba', 'Itapeva'),
    'Itaporanga': ('Sorocaba', 'Itapeva'),
    'Itararé': ('Sorocaba', 'Itapeva'),
    'Nova Campina': ('Sorocaba', 'Itapeva'),
    'Ribeira': ('Sorocaba', 'Itapeva'),
    'Ribeirão Branco': ('Sorocaba', 'Itapeva'),
    'Ribeirão Grande': ('Sorocaba', 'Itapeva'),
    'Riversul': ('Sorocaba', 'Itapeva'),
    'Taquarivaí': ('Sorocaba', 'Itapeva'),
    
    # Jaú (onde fica Itapuí!)
    'Bariri': ('Bauru', 'Jaú'),
    'Barra Bonita': ('Bauru', 'Jaú'),
    'Bocaina': ('Bauru', 'Jaú'),
    'Boraceia': ('Bauru', 'Jaú'),
    'Brotas': ('Bauru', 'Jaú'),
    'Dois Córregos': ('Bauru', 'Jaú'),
    'Igaraçu do Tietê': ('Bauru', 'Jaú'),
    'Itaju': ('Bauru', 'Jaú'),
    'Itapuí': ('Bauru', 'Jaú'),  # ITAPUÍ FICA AQUI!
    'Jaú': ('Bauru', 'Jaú'),
    'Mineiros do Tietê': ('Bauru', 'Jaú'),
    'Torrinha': ('Bauru', 'Jaú'),
    
    # Adicionar mais regiões conforme necessário...
}

def update_database_with_regions():
    """Atualiza o banco de dados com informações de região"""
    print("Atualizando banco de dados com informações de região...")
    
    conn = sqlite3.connect('data/cp2b_maps.db')
    cursor = conn.cursor()
    
    # Adicionar colunas de região se não existirem
    try:
        cursor.execute('ALTER TABLE municipalities ADD COLUMN regiao_intermediaria TEXT')
        print("Coluna regiao_intermediaria adicionada")
    except:
        print("Coluna regiao_intermediaria já existe")
    
    try:
        cursor.execute('ALTER TABLE municipalities ADD COLUMN regiao_imediata TEXT')
        print("Coluna regiao_imediata adicionada")
    except:
        print("Coluna regiao_imediata já existe")
    
    # Atualizar dados de região
    updates = 0
    for municipio, (reg_inter, reg_imed) in REGION_MAPPING.items():
        cursor.execute("""
            UPDATE municipalities 
            SET regiao_intermediaria = ?, regiao_imediata = ?
            WHERE nome_municipio LIKE ?
        """, (reg_inter, reg_imed, f'%{municipio}%'))
        
        if cursor.rowcount > 0:
            updates += cursor.rowcount
            print(f"Atualizado {municipio}: {reg_inter} -> {reg_imed}")
    
    conn.commit()
    
    # Verificar resultados para Itapuí
    cursor.execute("""
        SELECT nome_municipio, regiao_intermediaria, regiao_imediata
        FROM municipalities 
        WHERE nome_municipio LIKE '%Itapu%'
    """)
    
    results = cursor.fetchall()
    print(f"\nResultados para municípios Itapu:")
    for nome, reg_inter, reg_imed in results:
        print(f"  {nome}: {reg_inter} -> {reg_imed}")
    
    # Estatísticas gerais
    cursor.execute("SELECT COUNT(*) FROM municipalities WHERE regiao_intermediaria IS NOT NULL")
    total_com_regiao = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM municipalities")
    total_municipios = cursor.fetchone()[0]
    
    print(f"\nTotal de municípios: {total_municipios}")
    print(f"Municípios com região: {total_com_regiao}")
    print(f"Atualizações realizadas: {updates}")
    
    conn.close()
    return updates

if __name__ == "__main__":
    update_database_with_regions()