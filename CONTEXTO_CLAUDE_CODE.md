# 📋 CONTEXTO CLAUDE CODE - CP2B MAPS

> **Use este resumo para iniciar novos chats do Claude Code com contexto adequado**

## 🎯 SOBRE O PROJETO

**CP2B Maps** é uma aplicação Streamlit avançada para análise e visualização de **potencial de biogás** no estado de São Paulo. Combina dados de resíduos agropecuários com visualizações interativas e análises geoespaciais.

**Repositório:** https://github.com/aikiesan/cp2b_maps
**Tecnologia:** Streamlit + Folium + GeoPandas + Plotly

## 🗂️ ESTRUTURA DO PROJETO

```
CP2B_Maps/
├── src/streamlit/app.py          # ⭐ App principal - 3000+ linhas
├── src/raster/                   # Sistema MapBiomas completo
│   ├── __init__.py
│   └── raster_loader.py         # Processamento de GeoTIFF
├── rasters/                     # GeoTIFF otimizado (12.87 MB)
│   └── MapBiomas_SP_2024_APENAS_AGROPECUARIA_COG_90m_SELECIONADAS.tif
├── shapefile/                   # Camadas geográficas
│   ├── Limite_SP.shp           # Contorno do estado
│   ├── ETEs_2019_SP.shp        # Estações de tratamento
│   └── [outros shapefiles...]
├── data/                       # Base de dados
│   └── base_dados_municipios_biogas_2024.xlsx
├── requirements.txt            # Dependências com fallbacks
└── [arquivos de teste...]
```

## 🚀 FUNCIONALIDADES IMPLEMENTADAS

### 📊 Sistema Principal
- **Mapa interativo** com 4 tipos de visualização (círculos, heatmap, clusters, coroplético)
- **Dados de 645 municípios** de SP com potencial de biogás
- **12 tipos de resíduos** agropecuários analisados
- **Análise de proximidade** com raios de captação personalizáveis
- **Comparação de municípios** com métricas detalhadas

### 🌾 Sistema MapBiomas (DESTAQUE)
- **Integração completa** com dados de uso do solo
- **Controles granulares** para seleção de culturas individuais
- **GeoTIFF otimizado** processado no Google Earth Engine
- **Legendas dinâmicas** que mostram apenas culturas ativas
- **10 classes de culturas** organizadas por categoria

### 🎛️ Interface Avançada (RECÉM-IMPLEMENTADA)
- **Sidebar hierárquica** com `st.expander` organizando controles
- **Banner de filtros ativos** mostrando configurações aplicadas
- **Feedback interativo** com `st.toast` para todas as ações
- **Design profissional** tipo "painel de controle"

## 🔧 ASPECTOS TÉCNICOS IMPORTANTES

### 📦 Dependências e Fallbacks
```python
# Principais dependências
streamlit>=1.31.0
folium>=0.15.0
geopandas>=0.14.0
plotly>=5.17.0

# Opcionais com fallbacks graceful
rasterio>=1.3.0    # Para sistema MapBiomas
matplotlib>=3.7.0  # Para processamento de cores
```

### 🛡️ Sistema de Fallbacks
- **HAS_RASTER_SYSTEM**: Flag que detecta se dependências geoespaciais estão disponíveis
- **Degradação elegante**: App funciona sem MapBiomas quando dependências ausentes
- **Conversão manual**: hex→RGB sem matplotlib quando necessário

### ⚡ Performance e Otimizações
- **Cache LRU** para carregamento de dados
- **GeoTIFF otimizado** de 100MB → 12.87MB
- **Renderização seletiva** apenas de culturas ativas
- **Lazy loading** de shapefiles conforme necessário

## 📈 DADOS E MÉTRICAS

### 🗄️ Base de Dados Principal
- **645 municípios** do estado de São Paulo
- **12 tipos de resíduos**: suínos, bovinos, aves, cana, soja, etc.
- **Métricas calculadas**: potencial total, per capita, por área, densidade populacional
- **Classificações**: Linear, Quantiles, Jenks, Desvio Padrão

### 🌾 Dados MapBiomas (2024)
- **10 classes de culturas** agropecuárias
- **Pastagem**: Amarelo claro (#FFD966)
- **Temporárias**: Soja, Cana, Arroz, Algodão, Outras
- **Perenes**: Café, Citrus, Dendê, Outras  
- **Silvicultura**: Marrom escuro (#6D4C41)

## 🎨 UI/UX - MELHORIAS RECENTES

### 📁 Organização Hierárquica
```
🎛️ PAINEL DE CONTROLE
├── 🗺️ Camadas Visíveis (expandido por padrão)
│   ├── Dados Principais, Infraestrutura
│   ├── Referência (Rodovias, Áreas Urbanas)
│   └── Imagem de Satélite (MapBiomas aninhado)
├── 📊 Filtros de Dados (recolhido)
├── 🎨 Estilos de Visualização (recolhido) 
└── 🎯 Análises Avançadas (recolhido)
```

### 🔔 Sistema de Feedback
- **st.toast** implementado em todas ações importantes
- **Banner de filtros ativos** no topo da página
- **Mensagens contextuais** para estados da aplicação

## 🧪 TESTES E VALIDAÇÃO

### ✅ Suítes de Teste Disponíveis
- `test_mapbiomas_culturas.py` - Validação do sistema MapBiomas
- `test_ui_improvements.py` - Testes das melhorias de interface
- `test_fix_imports.py` - Validação de fallbacks de dependências

### 🔍 Comandos Úteis
```bash
# Executar aplicação
streamlit run src/streamlit/app.py

# Testes de funcionalidade
python test_mapbiomas_culturas.py
python test_fix_imports.py

# Verificar dependências
python -c "import streamlit; print(streamlit.__version__)"
```

## 🚨 PROBLEMAS CONHECIDOS E SOLUÇÕES

### 1. ModuleNotFoundError (RESOLVIDO)
- **Problema**: `matplotlib` não disponível no Streamlit Cloud
- **Solução**: Fallbacks implementados + `requirements.txt` atualizado

### 2. Performance em GeoTIFF grandes (RESOLVIDO)
- **Problema**: Arquivos de 100MB+ causavam lentidão
- **Solução**: Processamento no Google Earth Engine → 12.87MB

### 3. Sidebar lotada (RESOLVIDO)
- **Problema**: 20+ controles visíveis simultaneamente
- **Solução**: Organização hierárquica com `st.expander`

## 💡 PRÓXIMOS DESENVOLVIMENTOS SUGERIDOS

### 🎯 Funcionalidades
1. **Análise temporal** - Múltiplos anos de dados MapBiomas
2. **Exportação avançada** - Relatórios PDF personalizados
3. **API REST** - Endpoints para integração externa
4. **Cache distribuído** - Redis para múltiplos usuários

### 🔧 Melhorias Técnicas
1. **Testes automatizados** - CI/CD com GitHub Actions
2. **Documentação API** - Swagger/OpenAPI
3. **Containerização** - Docker para deployment
4. **Monitoramento** - Logs e métricas de uso

## 📞 CONTEXTO PARA CLAUDE CODE

### ⚡ Para Iniciar Rapidamente
```
Contexto: Trabalho com CP2B Maps, aplicação Streamlit de análise de biogás 
em SP. App principal: src/streamlit/app.py (3000+ linhas). Sistema MapBiomas 
integrado com controles granulares. Interface recém-reorganizada com 
st.expander hierárquico. Dependências com fallbacks graceful.

Repo: https://github.com/aikiesan/cp2b_maps
Foco atual: [descrever sua necessidade específica]
```

### 🎯 Comandos Frequentes
- Leia `CONTEXTO_CLAUDE_CODE.md` para contexto completo
- App principal está em `src/streamlit/app.py`
- Sistema raster em `src/raster/raster_loader.py`
- Dados em `data/base_dados_municipios_biogas_2024.xlsx`

## 📊 MÉTRICAS DE SUCESSO

- ✅ **3000+ linhas** de código organizadas e funcionais
- ✅ **Sistema MapBiomas** 100% operacional com 10 culturas
- ✅ **Interface profissional** com feedback interativo
- ✅ **Fallbacks robustos** para ambientes sem dependências geoespaciais
- ✅ **Performance otimizada** com GeoTIFF de 12.87MB
- ✅ **Testes validados** para funcionalidades principais

---

**📝 Última atualização:** Dezembro 2024  
**🔄 Status:** Produção - Totalmente funcional  
**🚀 Deploy:** Pronto para Streamlit Cloud