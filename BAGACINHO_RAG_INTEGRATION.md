# Integracao RAG ao Bagacinho - Documentacao Completa

**Data:** 30 de Setembro, 2025
**Status:** IMPLEMENTADO E TESTADO
**Versao:** 1.0

---

## Resumo Executivo

O sistema RAG (Retrieval Augmented Generation) foi integrado com sucesso ao assistente Bagacinho do CP2B Maps. O sistema permite que o Bagacinho acesse dados reais do banco SQLite de forma dinamica e inteligente, gerando contexto relevante baseado na intencao da pergunta do usuario.

### Diferenciais:

- **Economia de Tokens:** ~70% menos tokens usados por consulta
- **Respostas Precisas:** Apenas dados relevantes sao injetados no prompt
- **Deteccao Inteligente:** NLP simples detecta intencao (municipio, ranking, estado, comparacao)
- **Fallback Gracioso:** Se RAG falhar, usa contexto estatico
- **Cache Otimizado:** Streamlit cache para queries repetidas

---

## Arquivos Criados/Modificados

### 1. Novos Arquivos:

- **src/streamlit/modules/bagacinho_rag.py** (465 linhas)
  - Classe `BagacinhoRAG` com sistema de busca inteligente
  - 8 metodos principais de consulta ao banco
  - Sistema de deteccao de intencao por NLP

- **test_rag_integration.py** (146 linhas)
  - Suite de testes completa para o RAG
  - 8 testes cobrindo todas as funcionalidades

### 2. Arquivos Modificados:

- **src/streamlit/modules/chatbot_assistant.py**
  - Adicionado import do `BagacinhoRAG`
  - Nova funcao `get_rag_instance()`
  - Modificada funcao `query_ollama()` com parametro `use_rag=True`
  - Integracao RAG automatica para todas as perguntas

---

## Arquitetura do Sistema RAG

### Fluxo de Execucao:

```
Usuario faz pergunta
    |
    v
query_ollama() recebe pergunta
    |
    v
get_rag_instance() inicializa RAG (cached)
    |
    v
rag.construir_contexto(pergunta)
    |
    +--> Detecta intencao da pergunta
    |    - Municipio especifico?
    |    - Ranking/Top N?
    |    - Comparacao?
    |    - Estado/Geral?
    |
    +--> Busca dados relevantes no SQLite
    |    - buscar_municipio()
    |    - buscar_top_municipios()
    |    - comparar_municipios()
    |    - estatisticas_estado()
    |
    v
Contexto formatado em markdown
    |
    v
Injetado no system prompt do Ollama
    |
    v
Bagacinho responde com dados reais!
```

---

## Metodos da Classe BagacinhoRAG

### 1. `buscar_municipio(nome: str) -> Dict`
Busca dados completos de um municipio especifico.

**Retorna:**
- Dados demograficos (populacao, area, densidade)
- Potencial total de biogas
- Breakdown por categoria (agricola, pecuaria, urbano)
- Breakdown por fonte (cana, soja, bovinos, etc.)

**Exemplo:**
```python
dados = rag.buscar_municipio("Barretos")
# Retorna: {'nome_municipio': 'Barretos', 'total_final_m_ano': 650448740, ...}
```

### 2. `buscar_top_municipios(limite: int, fonte: str) -> DataFrame`
Retorna ranking de municipios por potencial.

**Parametros:**
- `limite`: Numero de municipios (default: 10, max: 20)
- `fonte`: Opcional - "cana", "bovinos", "suinos", "aves", "agricola", "pecuaria"

**Exemplo:**
```python
top_cana = rag.buscar_top_municipios(limite=5, fonte="cana")
# Retorna DataFrame com top 5 municipios produtores de cana
```

### 3. `estatisticas_estado() -> Dict`
Estatisticas agregadas do Estado de Sao Paulo.

**Retorna:**
- Total de municipios (645)
- Populacao total
- Potencial total SP
- Medias
- Distribuicao por fonte e categoria

### 4. `comparar_municipios(nomes: List[str]) -> DataFrame`
Compara multiplos municipios lado a lado.

**Exemplo:**
```python
comp = rag.comparar_municipios(["Barretos", "Campinas", "Ribeirao Preto"])
```

### 5. `construir_contexto(pergunta: str) -> str` ⭐核心
**Metodo principal do RAG** - Analisa a pergunta e constroi contexto inteligente.

**Detecta 4 tipos de intencao:**

#### Tipo 1: Municipio Especifico
**Gatilhos:** Detecta nome de municipio na pergunta
**Acao:** Busca dados completos do municipio
**Contexto:** ~800 caracteres com todos os dados do municipio

**Exemplo:**
- Pergunta: "Qual o potencial de Barretos?"
- Contexto: Dados completos de Barretos

#### Tipo 2: Ranking/Top N
**Gatilhos:** "top", "maiores", "ranking", "melhores", "principais"
**Acao:** Busca top N municipios (detecta numero e fonte)
**Contexto:** ~500 caracteres com lista de municipios

**Exemplo:**
- Pergunta: "Top 5 municipios com maior potencial de cana"
- Contexto: Lista dos 5 maiores produtores de cana

#### Tipo 3: Comparacao
**Gatilhos:** "comparar", "compare", "diferenca", "vs", "versus"
**Acao:** Extrai nomes de municipios e compara
**Contexto:** Tabela comparativa

**Exemplo:**
- Pergunta: "Compare Barretos vs Campinas"
- Contexto: Dados lado a lado dos dois municipios

#### Tipo 4: Estado/Geral
**Gatilhos:** "estado", "sao paulo", "sp", "total", "estadual", "geral"
**Acao:** Busca estatisticas agregadas
**Contexto:** ~700 caracteres com panorama completo

**Exemplo:**
- Pergunta: "Qual o potencial total de Sao Paulo?"
- Contexto: Todas as estatisticas do estado

#### Fallback:
Se nenhum padrao for detectado, retorna contexto generico com overview do sistema.

---

## Resultados dos Testes

### Teste 1: Municipio Especifico (Barretos)
✅ **PASSOU**
- Encontrado: Barretos
- Potencial Total: 650,448,740 Nm3/ano
- Populacao: 122,485
- Cana-de-acucar: 622,049,794 Nm3/ano

### Teste 2: Top 5 Municipios (Total)
✅ **PASSOU**
1. Barretos: 650,448,740 Nm3/ano
2. Morro Agudo: 644,444,719 Nm3/ano
3. Guaira: 565,704,176 Nm3/ano
4. Jaboticabal: 494,873,109 Nm3/ano
5. Rancharia: 482,880,024 Nm3/ano

### Teste 3: Top 5 Municipios (Cana)
✅ **PASSOU**
1. Morro Agudo: 627,732,000 Nm3/ano
2. Barretos: 622,049,794 Nm3/ano
3. Guaira: 507,365,000 Nm3/ano
4. Jaboticabal: 486,873,000 Nm3/ano
5. Novo Horizonte: 439,450,000 Nm3/ano

### Teste 4: Estatisticas do Estado
✅ **PASSOU**
- Total de Municipios: 645
- Populacao Total: 44,411,238
- Potencial Total SP: 48,844,701,321 Nm3/ano
- Media Municipal: 75,728,219 Nm3/ano
- Contribuicao Cana: 84.5%
- Contribuicao Bovinos: 3.0%

### Teste 5-7: Construcao de Contexto RAG
✅ **PASSOU**
- Contexto para municipio: 805 caracteres
- Contexto para ranking: 535 caracteres
- Contexto para estado: 709 caracteres

### Teste 8: Comparacao de Municipios
✅ **PASSOU**
- Barretos: 650,448,740 Nm3/ano (98.3% agricola)
- Campinas: 60,234,304 Nm3/ano (23.3% agricola)

---

## Vantagens do RAG vs Contexto Estatico

### Antes (Contexto Estatico):
```
System Prompt = Instrucoes + TODO o banco de dados (estatisticas gerais)
                |
                +-> ~2000 caracteres
                +-> Mesmos dados para qualquer pergunta
                +-> Desperdicio de tokens
                +-> Informacao generica
```

### Depois (RAG Dinamico):
```
System Prompt = Instrucoes + APENAS dados relevantes da pergunta
                |
                +-> 500-800 caracteres (economia de 60-75%)
                +-> Dados especificos por pergunta
                +-> Uso otimizado de tokens
                +-> Informacao precisa
```

### Exemplo Pratico:

**Pergunta:** "Qual o potencial de Barretos?"

**Antes (Estatico):**
- Contexto: Estatisticas de todos os 645 municipios
- Tamanho: ~2000 chars
- Bagacinho precisa "achar" Barretos na lista mental

**Depois (RAG):**
- Contexto: Apenas dados de Barretos
- Tamanho: ~800 chars
- Bagacinho recebe exatamente o que precisa

**Resultado:** Resposta mais rapida, precisa e economica!

---

## Como Usar

### No Streamlit (Automatico):

O RAG esta **automaticamente ativado** para todas as perguntas. Nao precisa fazer nada!

```python
# Isso ja acontece automaticamente no chatbot_assistant.py
answer, success = query_ollama(
    question="Qual o potencial de Barretos?",
    model="bagacinho",
    use_rag=True  # <- RAG ativado por padrao
)
```

### Programaticamente:

```python
from src.streamlit.modules.bagacinho_rag import BagacinhoRAG

# Inicializar
rag = BagacinhoRAG()

# Exemplo 1: Buscar municipio
dados = rag.buscar_municipio("Campinas")
print(dados['total_final_m_ano'])

# Exemplo 2: Top 10
top_df = rag.buscar_top_municipios(limite=10)
print(top_df)

# Exemplo 3: Construir contexto inteligente
contexto = rag.construir_contexto("Quais os top 5 municipios?")
print(contexto)
```

### Testar:

```bash
# Rodar suite de testes
python test_rag_integration.py

# Resultado esperado:
# [OK] Todos os testes passaram
```

---

## Exemplos de Perguntas que o RAG Detecta

### Categoria 1: Municipio Especifico
- "Qual o potencial de Barretos?"
- "Me fale sobre Campinas"
- "Quais sao os dados de Ribeirao Preto?"
- "Barretos tem quanto de biogas?"

### Categoria 2: Rankings
- "Top 10 municipios por potencial"
- "Quais os maiores produtores de cana?"
- "Me mostre os 5 melhores municipios de biogas"
- "Ranking de municipios por potencial de bovinos"

### Categoria 3: Estado/Geral
- "Qual o potencial total de Sao Paulo?"
- "Quantos municipios tem no sistema?"
- "Qual a media de potencial no estado?"
- "Dados gerais do estado"

### Categoria 4: Comparacao
- "Compare Barretos e Campinas"
- "Qual a diferenca entre Ribeirao Preto vs Sao Jose do Rio Preto?"
- "Barretos ou Morro Agudo: qual tem mais potencial?"

---

## Performance e Otimizacoes

### Cache do Streamlit:
O RAG usa `@st.cache_data` para cachear queries repetidas:

```python
@st.cache_data(ttl=3600)  # Cache por 1 hora
def buscar_municipio_cached(_self, nome: str):
    return _self.buscar_municipio(nome)
```

### Indices do SQLite:
O banco tem indices otimizados para as queries mais comuns:
- Index em `nome_municipio`
- Index em `total_final_m_ano`
- Index em `cd_mun`

### Tamanho dos Contextos:
- Municipio especifico: ~800 chars
- Ranking: ~500 chars
- Estado: ~700 chars
- **Media de economia: 70% vs contexto estatico**

---

## Limitacoes Conhecidas

### 1. Deteccao de Municipios
Atualmente detecta 21 municipios comuns na lista hardcoded:
```python
municipios_conhecidos = [
    "barretos", "campinas", "ribeirao preto",
    "sao paulo", "santos", "piracicaba", ...
]
```

**Solucao futura:** Usar NER (Named Entity Recognition) ou fuzzy matching para detectar qualquer municipio.

### 2. Encoding Issues (Windows)
Os emojis foram removidos do contexto RAG para evitar `UnicodeEncodeError` no Windows CMD.

**Nota:** Emojis ainda funcionam normalmente no Streamlit (UTF-8).

### 3. Limites de Ranking
Top N limitado a maximo de 20 municipios para evitar contexto muito grande.

---

## Proximos Passos (Opcio
nais)

### Melhorias Sugeridas:

1. **NER para Municipios**
   - Usar spaCy ou fuzzy matching
   - Detectar qualquer um dos 645 municipios

2. **Queries mais Complexas**
   - "Municipios com mais de 100M Nm3/ano"
   - "Municipios da regiao de Campinas"
   - "Municipios onde cana > 80% do total"

3. **Cache Persistente**
   - Usar Redis ou SQLite para cache entre sessoes

4. **Embeddings para Similarity**
   - Usar sentence-transformers para matching semantico
   - "Municipios parecidos com Barretos"

5. **Integracao com Mapas**
   - Retornar coordenadas geograficas
   - Destacar municipios no mapa interativo

---

## Troubleshooting

### Problema: "RAG failed, using static context"
**Causa:** Banco de dados nao encontrado ou erro de conexao
**Solucao:** Verificar se `data/cp2b_maps.db` existe

### Problema: Contexto vazio ou generico
**Causa:** Deteccao de intencao nao funcionou
**Solucao:** Verificar se a pergunta contem gatilhos conhecidos

### Problema: Municipio nao encontrado
**Causa:** Nome do municipio nao esta na lista hardcoded
**Solucao:** Adicionar municipio em `municipios_conhecidos` ou usar busca fuzzy

### Problema: UnicodeEncodeError
**Causa:** Windows CMD nao suporta certos caracteres UTF-8
**Solucao:** Rodar `chcp 65001` antes do script ou usar PowerShell

---

## Conclusao

✅ **Sistema RAG totalmente funcional e testado**
✅ **8/8 testes passaram com sucesso**
✅ **Integracao automatica com o Bagacinho**
✅ **Economia de ~70% de tokens**
✅ **Respostas mais precisas e rapidas**
✅ **Fallback gracioso se RAG falhar**

O Bagacinho agora tem acesso inteligente aos dados reais do CP2B Maps, proporcionando respostas contextualizadas e precisas baseadas em dados do banco SQLite!

---

**Desenvolvido para CP2B Maps - UNICAMP**
**Data:** 30 de Setembro, 2025
