# 🍊 Bagacinho - Quick Start Guide

## 🚀 Como Começar em 3 Passos

### Passo 1: Verificar se o Bagacinho está disponível

```bash
python check_ollama_models.py
```

**Saída esperada:**
```
✅ ÓTIMO! Modelo 'bagacinho' encontrado!
   O assistente usará automaticamente o modelo treinado.
```

---

### Passo 2: Escolha como usar

#### Opção A: Teste Rápido (Interface Standalone)

```bash
streamlit run test_bagacinho.py
```

**Interface dedicada com:**
- 🎛️ Controles de configuração (temperature, max_tokens)
- 💬 Chat simples e direto
- 💡 Exemplos de perguntas
- 📊 Status da conexão

#### Opção B: App Principal (Produção)

```bash
streamlit run src/streamlit/app.py
```

**Duas formas de acessar:**

1. **Sidebar** (Acesso Rápido):
   - Vá para aba "🏠 Mapa Principal"
   - Role até o final da sidebar
   - Encontre "🍊 Bagacinho"
   - Selecione "bagacinho" no dropdown

2. **Aba Dedicada** (Interface Completa):
   - Clique na aba "🤖 Assistente IA"
   - Selecione "bagacinho" no dropdown
   - Interface completa com histórico

---

### Passo 3: Faça suas perguntas!

#### Perguntas Iniciais para Testar:

```
1. "Qual o potencial total de biogás do estado de São Paulo?"

2. "Quais são os 5 municípios com maior potencial?"

3. "Qual substrato contribui mais para o potencial total?"

4. "Como é calculado o potencial de biogás da cana-de-açúcar?"

5. "Compare o potencial de Campinas e Ribeirão Preto"
```

---

## 🔍 Verificações Rápidas

### ✅ Está usando o Bagacinho?

Procure por estes indicadores:

**Na Sidebar:**
```
🍊 Usando modelo Bagacinho treinado!
```

**Na Aba Completa:**
```
🍊
Modelo treinado
```

### ❌ Bagacinho não encontrado?

Se você vir:
```
⚠️ Modelo 'bagacinho' NÃO encontrado
```

**Causas possíveis:**
1. Modelo não foi criado ainda
2. Nome do modelo está diferente
3. Ollama não está acessível

**Soluções:**
```bash
# Liste modelos disponíveis
ollama list

# Se bagacinho não estiver lá, você precisa criar o modelo
# (consulte documentação de fine-tuning)
```

---

## 📊 Diferença: Bagacinho vs Llama 3.1

| Aspecto | Bagacinho 🍊 | Llama 3.1 |
|---------|-------------|-----------|
| **Conhecimento CP2B** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Precisão Técnica** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **MapBIOMAS** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **MCDA** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 🎯 Exemplos de Uso por Categoria

### 📍 Municipal
```
"Qual o potencial de biogás de Barretos?"
"Analise os municípios da região de Campinas"
```

### 🌾 Agrícola
```
"Potencial de cana-de-açúcar no estado"
"Quais culturas geram mais biogás?"
```

### 🐄 Pecuário
```
"Potencial de resíduos bovinos em SP"
"Dimensione um biodigestor para 2000 suínos"
```

### ⚡ Técnico
```
"Como converter Nm³ em kWh?"
"Fatores de conversão para vinhaça"
```

### 🗺️ Regional
```
"Melhor região para planta de biogás"
"Análise da bacia do Rio Tietê"
```

---

## ⚙️ Configurações Recomendadas

**Para Respostas Técnicas Precisas:**
- Temperature: `0.7`
- Max Tokens: `1024`

**Para Explicações Detalhadas:**
- Temperature: `0.8`
- Max Tokens: `1536`

**Para Respostas Rápidas:**
- Temperature: `0.6`
- Max Tokens: `512`

---

## 🔧 Solução Rápida de Problemas

### Problema: "Ollama não conecta"

```bash
# Windows/Mac: Abra o app Ollama Desktop
# Linux: 
ollama serve

# Docker:
docker ps | grep ollama
# Se não aparecer, inicie o container
```

### Problema: "Respostas muito lentas"

1. Primeira consulta é sempre mais lenta (carrega o modelo)
2. Reduza `max_tokens` para 512
3. Verifique RAM disponível (mínimo 8GB)

### Problema: "Respostas genéricas"

1. Verifique se está usando o modelo "bagacinho"
2. Confirme no dropdown de modelos
3. Veja o indicador 🍊

---

## 📚 Documentação Completa

- **Guia Detalhado:** `BAGACINHO_USAGE_GUIDE.md`
- **Status da Integração:** `BAGACINHO_INTEGRATION_STATUS.md`
- **Setup Geral:** `CHATBOT_SETUP_GUIDE.md`

---

## 🎓 Dicas de Boas Práticas

### ✅ Faça:
- Seja específico nas perguntas
- Use nomes completos de municípios
- Peça comparações e análises
- Faça perguntas de acompanhamento

### ❌ Evite:
- Perguntas muito vagas
- Múltiplas perguntas em uma
- Informações fora do contexto do CP2B

---

## 🚦 Status do Sistema

**Verde (✅):** Tudo funcionando
- Ollama conectado
- Modelo bagacinho disponível
- Respostas rápidas e precisas

**Amarelo (⚠️):** Funcional com limitações
- Usando modelo base (llama3.1)
- Respostas genéricas possíveis

**Vermelho (❌):** Requer atenção
- Ollama não conectado
- Nenhum modelo disponível

---

## 💡 Casos de Uso Reais

### 1. Análise de Viabilidade
```
"Qual o potencial de biogás da região de Ribeirão Preto 
considerando apenas resíduos de cana-de-açúcar?"
```

### 2. Dimensionamento
```
"Preciso dimensionar um biodigestor para uma fazenda em 
Barretos com 3000 bovinos. Qual o potencial diário?"
```

### 3. Comparação Regional
```
"Compare o potencial energético das regiões administrativas 
de Campinas, Sorocaba e São José do Rio Preto"
```

### 4. Metodologia
```
"Explique como o CP2B Maps calcula o potencial de biogás 
a partir de dados do MapBIOMAS"
```

### 5. Planejamento
```
"Quais os 10 municípios mais promissores para instalação 
de plantas de biogás considerando infraestrutura e potencial?"
```

---

## 🎉 Pronto para Usar!

Você está pronto para explorar o Bagacinho! Escolha uma das opções:

```bash
# Teste rápido
streamlit run test_bagacinho.py

# App completo
streamlit run src/streamlit/app.py
```

**Divirta-se explorando o potencial de biogás de São Paulo! 🍊**

---

**CP2B - Centro Paulista de Estudos em Biogás e Bioprodutos (UNICAMP)**  
*Setembro 2025*

