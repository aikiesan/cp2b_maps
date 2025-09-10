def create_centroid_map_optimized(df, display_col, filters=None, get_legend_only=False, search_term="", viz_type="Círculos Proporcionais", show_mapbiomas_layer=False, show_rios=False, show_rodovias=False, show_plantas_biogas=False, show_gasodutos_dist=False, show_gasodutos_transp=False, show_areas_urbanas=False, show_regioes_admin=False):
    """VERSÃO ULTRA-OTIMIZADA - Cria mapa folium de forma muito mais rápida"""
    
    try:
        # 1. SETUP BÁSICO DO MAPA - MINIMAL
        m = folium.Map(
            location=[-22.5, -48.5], 
            zoom_start=7,
            tiles='CartoDB positron',
            prefer_canvas=True  # Melhora performance de renderização
        )
        
        # Remover todos os debug prints/writes para melhor performance
        
        # 2. ADICIONAR BORDAS DO ESTADO DE SÃO PAULO (SEMPRE ATIVO)
        try:
            from pathlib import Path
            import geopandas as gpd
            sp_border_path = Path(__file__).parent.parent / "shapefile" / "Limite_SP.shp"
            if sp_border_path.exists():
                sp_border = gpd.read_file(sp_border_path)
                if sp_border.crs != 'EPSG:4326':
                    sp_border = sp_border.to_crs('EPSG:4326')
                
                folium.GeoJson(
                    sp_border,
                    style_function=lambda x: {
                        'fillColor': 'rgba(46, 139, 87, 0.1)',
                        'color': '#2E8B57',
                        'weight': 2,
                        'opacity': 0.8,
                        'fillOpacity': 0.1,
                        'dashArray': '5, 5'
                    },
                    tooltip='Estado de São Paulo',
                    interactive=False
                ).add_to(m)
        except Exception as e:
            pass  # Falha silenciosa para não quebrar o mapa
        
        if df.empty:
            return m, ""
        
        # 3. PRÉ-CARREGAR TODAS AS CAMADAS DE UMA VEZ (CACHE)
        with st.spinner("⚡ Carregando dados das camadas..."):
            layer_data = prepare_layer_data()
        
        # 3. ADICIONAR CAMADAS SELECIONADAS - OTIMIZADO
        layers_added = []
        
        if show_plantas_biogas and layer_data['plantas'] is not None:
            add_plantas_layer_fast(m, layer_data['plantas'])
            layers_added.append("Plantas de Biogás")
        
        if show_gasodutos_dist and layer_data['gasodutos_dist'] is not None:
            add_lines_layer_fast(m, layer_data['gasodutos_dist'], "Gasodutos Distribuição", "#0066CC")
            layers_added.append("Gasodutos Distribuição")
            
        if show_gasodutos_transp and layer_data['gasodutos_transp'] is not None:
            add_lines_layer_fast(m, layer_data['gasodutos_transp'], "Gasodutos Transporte", "#CC0000", weight=4)
            layers_added.append("Gasodutos Transporte")
        
        if show_rodovias and layer_data['rodovias'] is not None:
            add_lines_layer_fast(m, layer_data['rodovias'], "Rodovias Estaduais", "#FF4500", weight=2)
            layers_added.append("Rodovias")
            
        if show_rios and layer_data['rios'] is not None:
            add_lines_layer_fast(m, layer_data['rios'], "Rios Principais", "#1E90FF", weight=2)
            layers_added.append("Rios")
        
        if show_areas_urbanas and layer_data['areas_urbanas'] is not None:
            # Usar amostragem para áreas urbanas se houver muitos polígonos
            areas_sample = layer_data['areas_urbanas']
            if len(areas_sample) > 5000:  # Limitar para performance
                areas_sample = areas_sample.sample(n=5000)
            add_polygons_layer_fast(m, areas_sample, "Áreas Urbanas", "#DEB887", fill_opacity=0.3)
            layers_added.append("Áreas Urbanas")
        
        if show_regioes_admin and layer_data['regioes_admin'] is not None:
            add_regioes_layer_fast(m, layer_data['regioes_admin'])
            layers_added.append("Regiões Administrativas")
        
        # 4. CARREGAR DADOS DOS MUNICÍPIOS - SIMPLIFICADO
        if not df.empty:
            try:
                centroid_path = Path(__file__).parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
                if centroid_path.exists():
                    centroids_df = pd.read_parquet(centroid_path)
                    if 'geometry' in centroids_df.columns:
                        centroids_gdf = gpd.GeoDataFrame(centroids_df)
                        df_merged = centroids_gdf.merge(df, on='cd_mun', how='inner')
                        
                        if not df_merged.empty and display_col in df_merged.columns:
                            # Adicionar círculos dos municípios de forma otimizada
                            add_municipality_circles_fast(m, df_merged, display_col, viz_type)
            except Exception as e:
                # Falha silenciosa para não quebrar o mapa
                pass
        
        # 5. ADICIONAR APENAS CONTROLES ESSENCIAIS
        if layers_added:
            folium.LayerControl(collapsed=False).add_to(m)
        
        # 6. RETORNAR SEM LEGENDA COMPLEXA (PARA VELOCIDADE)
        legend_simple = f"Camadas ativas: {', '.join(layers_added)}" if layers_added else ""
        
        return m, legend_simple
        
    except Exception as e:
        st.error(f"❌ Erro ao criar mapa: {e}")
        # Retornar mapa básico em caso de erro
        basic_map = folium.Map(location=[-22.5, -48.5], zoom_start=7)
        return basic_map, ""

def add_municipality_circles_fast(m, df_merged, display_col, viz_type):
    """Adiciona círculos dos municípios de forma ultra-otimizada"""
    if df_merged.empty or display_col not in df_merged.columns:
        return
    
    # Usar apenas uma amostra se houver muitos municípios para melhor performance
    if len(df_merged) > 500:
        df_sample = df_merged.nlargest(500, display_col)  # Top 500 maiores valores
    else:
        df_sample = df_merged
    
    # Normalizar valores para tamanho dos círculos
    values = df_sample[display_col].fillna(0)
    if values.max() > 0:
        sizes = ((values / values.max()) * 15 + 3).astype(int)  # Tamanhos de 3 a 18
    else:
        sizes = pd.Series([5] * len(df_sample))
    
    # Adicionar círculos de forma batch
    for idx, row in df_sample.iterrows():
        try:
            if hasattr(row, 'geometry') and row.geometry:
                lat, lon = row.geometry.y, row.geometry.x
                size = sizes.loc[idx]
                value = values.loc[idx]
                
                # Popup mínimo para performance
                popup = f"<b>{row.get('nome_municipio', 'N/A')}</b><br>{value:,.0f} Nm³/ano"
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=size,
                    popup=popup,
                    tooltip=row.get('nome_municipio', 'N/A'),
                    color='#2E8B57',
                    fillColor='#90EE90',
                    fillOpacity=0.7,
                    weight=1
                ).add_to(m)
        except:
            continue  # Pular erros silenciosamente