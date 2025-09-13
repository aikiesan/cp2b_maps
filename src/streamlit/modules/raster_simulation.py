"""
Raster analysis simulation module
"""
import random
import math
import pandas as pd


def simulate_raster_analysis(center_lat, center_lon, radius_km, df):
    """Simula análise de raster baseada em dados municipais e características regionais"""
    import random
    import math
    
    # Definir culturas típicas de São Paulo por região
    culturas_por_regiao = {
        "norte": ["Cana-de-açúcar", "Soja", "Milho", "Pastagem"],
        "centro": ["Cana-de-açúcar", "Citros", "Café", "Pastagem"], 
        "sul": ["Milho", "Soja", "Pastagem", "Silvicultura"],
        "leste": ["Pastagem", "Cana-de-açúcar", "Milho"],
        "oeste": ["Cana-de-açúcar", "Pastagem", "Soja", "Milho"]
    }
    
    # Determinar região baseada em coordenadas
    if center_lat > -21:
        regiao = "norte"
    elif center_lat < -23.5:
        regiao = "sul"
    elif center_lon > -47:
        regiao = "leste"
    elif center_lon < -49:
        regiao = "oeste"
    else:
        regiao = "centro"
    
    culturas_locais = culturas_por_regiao.get(regiao, culturas_por_regiao["centro"])
    
    # Simular dados baseados no raio
    area_total_km2 = math.pi * radius_km ** 2
    
    # Calcular densidades baseadas em municípios próximos
    municipios_proximos = []
    for _, municipio in df.iterrows():
        if 'lat' in municipio and 'lon' in municipio:
            dist = math.sqrt((center_lat - municipio['lat'])**2 + (center_lon - municipio['lon'])**2) * 111
            if dist <= radius_km:
                municipios_proximos.append(municipio)
    
    results = {}
    
    # Gerar dados simulados mais realistas
    for i, cultura in enumerate(culturas_locais[:4]):  # Top 4 culturas
        # Usar dados reais dos municípios se disponível
        potencial_base = 0
        if municipios_proximos:
            for mun in municipios_proximos:
                # Tentar encontrar dados de biogas relacionados
                for col in mun.index:
                    if cultura.lower().replace('-', '').replace(' ', '') in col.lower():
                        if pd.notna(mun[col]) and mun[col] > 0:
                            potencial_base += mun[col]
        
        # Se não há dados reais, simular baseado na área e tipo de cultura
        if potencial_base == 0:
            if cultura == "Pastagem":
                densidade_base = random.uniform(5, 25) * area_total_km2 * 0.3
            elif cultura == "Cana-de-açúcar":  
                densidade_base = random.uniform(15, 45) * area_total_km2 * 0.2
            elif cultura in ["Soja", "Milho"]:
                densidade_base = random.uniform(8, 30) * area_total_km2 * 0.15
            else:
                densidade_base = random.uniform(3, 15) * area_total_km2 * 0.1
        else:
            densidade_base = potencial_base * random.uniform(0.7, 1.3)
        
        # Calcular área e percentual
        area_cultura = area_total_km2 * random.uniform(0.1, 0.4) / (i + 1)  # Distribuição mais realista
        percentual = (area_cultura / area_total_km2) * 100
        
        results[cultura] = {
            "area_km2": round(area_cultura, 2),
            "percentual": round(percentual, 1),
            "potencial_biogas": round(densidade_base, 0),
            "densidade": round(densidade_base / area_cultura if area_cultura > 0 else 0, 1)
        }
    
    # Adicionar dados de contexto
    results["_metadata"] = {
        "regiao": regiao.title(),
        "total_area_km2": round(area_total_km2, 1),
        "municipios_encontrados": len(municipios_proximos),
        "metodo": "Análise Simplificada"
    }
    
    return results


def get_classification_label(percentile):
    """Get classification label based on percentile"""
    if percentile >= 90:
        return "🔥 Muito Alto"
    elif percentile >= 75:
        return "📈 Alto"
    elif percentile >= 50:
        return "➡️ Médio"
    elif percentile >= 25:
        return "📉 Baixo"
    else:
        return "❄️ Muito Baixo"


def find_neighboring_municipalities(df, target_mun, radius_km=50):
    """Find neighboring municipalities within radius"""
    target_lat = target_mun.get('lat', 0)
    target_lng = target_mun.get('lon', 0)
    
    if target_lat == 0 or target_lng == 0:
        return df.head(10).to_dict('records')  # Fallback
    
    # Calculate distances (simplified)
    distances = []
    for idx, row in df.iterrows():
        lat = row.get('lat', 0)
        lng = row.get('lon', 0)
        
        if lat != 0 and lng != 0:
            # Simplified distance calculation
            distance = ((target_lat - lat)**2 + (target_lng - lng)**2)**0.5 * 111  # Rough km conversion
            if distance <= radius_km:
                row_dict = row.to_dict()
                row_dict['distance'] = distance
                distances.append(row_dict)
    
    # Sort by distance
    distances.sort(key=lambda x: x['distance'])
    return distances