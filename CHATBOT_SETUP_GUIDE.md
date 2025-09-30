# 🤖 Guia de Configuração do Assistente IA CP2B

## 📋 Visão Geral

O CP2B Maps agora inclui um assistente de IA alimentado por **Llama 3.1** via **Ollama**, que pode responder perguntas sobre o potencial de biogás em São Paulo, explicar a metodologia, e fornecer insights sobre os dados.

### Características do Assistente:

✅ **Sempre visível** na barra lateral do Mapa Principal  
✅ **Interface completa** disponível em aba dedicada "🤖 Assistente IA"  
✅ **Contexto automático** do banco de dados CP2B  
✅ **Conversação contínua** com histórico de mensagens  
✅ **Execução local** - seus dados não saem do seu computador  

---

## 🚀 Instalação e Configuração

### Passo 1: Instalar Dependências Python

```bash
pip install -r requirements.txt
```

Isso instalará o pacote `ollama` Python necessário para comunicação com o Ollama.

### Passo 2: Instalar Ollama

#### Windows:
1. Baixe o instalador do Ollama: https://ollama.ai/download
2. Execute o instalador `OllamaSetup.exe`
3. Siga as instruções de instalação

#### macOS:
```bash
# Via Homebrew
brew install ollama

# Ou baixe o instalador em:
# https://ollama.ai/download
```

#### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Passo 3: Baixar o Modelo Llama 3.1

Após instalar o Ollama, baixe o modelo Llama 3.1:

```bash
ollama pull llama3.1
```

**Nota:** O download é de aproximadamente 4-5 GB. Certifique-se de ter espaço em disco e uma boa conexão de internet.

#### Modelos Alternativos (Opcional)

Se você preferir um modelo menor ou quiser experimentar outros:

```bash
# Modelo menor e mais rápido (2GB)
ollama pull llama3.1:8b

# Modelo maior e mais preciso (40GB)
ollama pull llama3.1:70b

# Outros modelos disponíveis
ollama pull mistral
ollama pull phi3
```

### Passo 4: Verificar Instalação

Verifique se o Ollama está rodando:

```bash
ollama list
```

Você deve ver algo como:
```
NAME                ID              SIZE      MODIFIED
llama3.1:latest     abc123def456    4.7 GB    2 hours ago
```

---

## 🎮 Usando o Assistente

### Opção 1: Sidebar (Acesso Rápido)

1. Abra o CP2B Maps (`streamlit run src/streamlit/app.py`)
2. Vá para a aba **"🏠 Mapa Principal"**
3. Na barra lateral, role até o final
4. Você verá o **🤖 Assistente CP2B** sempre visível
5. Digite sua pergunta e clique em **📤 Enviar**

### Opção 2: Interface Completa

1. Abra o CP2B Maps
2. Clique na aba **"🤖 Assistente IA"**
3. Você terá acesso à interface completa do chatbot
4. Faça suas perguntas com mais espaço para visualizar o histórico

---

## 💡 Exemplos de Perguntas

### Sobre Municípios Específicos:
- "Qual o potencial de biogás do município de Campinas?"
- "Quais são os 10 municípios com maior potencial total?"
- "Compare o potencial de Ribeirão Preto e São José do Rio Preto"

### Sobre Substratos:
- "Qual substrato contribui mais para o potencial total de São Paulo?"
- "Quanto biogás pode ser produzido a partir de cana-de-açúcar no estado?"
- "Quais são os principais municípios produtores de biogás pecuário?"

### Sobre Metodologia:
- "Como é calculado o potencial de biogás?"
- "Quais fatores de conversão são utilizados?"
- "Qual a diferença entre potencial agrícola e pecuário?"

### Estatísticas Gerais:
- "Qual o potencial total de biogás do estado de São Paulo?"
- "Quantos municípios têm potencial de biogás acima de 1 milhão de m³/ano?"
- "Qual a média de potencial por município?"

---

## ⚙️ Configurações Avançadas

### Alterar o Modelo

Na interface do assistente, você pode selecionar diferentes modelos do dropdown "Modelo" se tiver baixado múltiplos modelos.

### Configurar Host do Ollama

Se você está rodando o Ollama em um servidor remoto ou porta diferente, você pode modificar no código:

```python
# Em src/streamlit/modules/chatbot_assistant.py
# Linha ~170 e outras funções

def check_ollama_connection(host: str = "http://localhost:11434"):
    # Altere para seu host customizado
    # Exemplo: "http://192.168.1.100:11434"
```

### Limpar Histórico de Conversa

Clique no botão **🗑️** para limpar o histórico e começar uma nova conversa.

---

## 🔧 Solução de Problemas

### ❌ "Ollama library not available"

**Problema:** A biblioteca Python do Ollama não está instalada.

**Solução:**
```bash
pip install ollama
```

### ❌ "Não foi possível conectar ao Ollama"

**Problema:** O serviço Ollama não está rodando.

**Solução:**

**Windows/macOS:** Abra o aplicativo Ollama (deve iniciar automaticamente após instalação)

**Linux:** Inicie o serviço:
```bash
ollama serve
```

**Docker:** Se estiver usando Docker Desktop:
```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.1
```

### ❌ "Ollama conectado mas nenhum modelo encontrado"

**Problema:** Nenhum modelo foi baixado.

**Solução:**
```bash
ollama pull llama3.1
```

### 🐌 Respostas Lentas

**Possíveis Causas:**
1. **Hardware:** Llama 3.1 requer recursos significativos
2. **Modelo muito grande:** Experimente um modelo menor (llama3.1:8b)
3. **Primeira execução:** O modelo precisa ser carregado na memória

**Soluções:**
- Use um modelo menor: `ollama pull llama3.1:8b`
- Certifique-se de ter RAM suficiente (mínimo 8GB recomendado)
- Feche outros aplicativos pesados

---

## 📊 Requisitos do Sistema

### Mínimos:
- **CPU:** Intel i5 ou AMD Ryzen 5 (4 cores)
- **RAM:** 8 GB
- **Disco:** 10 GB livres
- **Modelo recomendado:** llama3.1:8b

### Recomendados:
- **CPU:** Intel i7 ou AMD Ryzen 7 (8+ cores)
- **RAM:** 16 GB ou mais
- **Disco:** 20 GB livres (para múltiplos modelos)
- **GPU:** Opcional, mas acelera significativamente (NVIDIA com CUDA)
- **Modelo recomendado:** llama3.1:latest

---

## 🎓 Como Funciona

### Arquitetura

1. **Contexto do Banco de Dados:** Quando o assistente inicia, ele prepara um contexto rico com:
   - Estatísticas gerais do estado de São Paulo
   - Top 10 municípios por potencial
   - Contribuição de cada substrato
   - Explicação da metodologia

2. **Comunicação Local:** Suas perguntas são enviadas ao Ollama rodando localmente, junto com o contexto do banco de dados.

3. **Modelo LLM:** O Llama 3.1 processa sua pergunta usando o contexto e gera uma resposta fundamentada nos dados reais.

4. **Histórico de Conversa:** O sistema mantém o histórico para permitir perguntas de acompanhamento.

### Privacidade e Segurança

✅ **100% Local** - Nenhum dado sai do seu computador  
✅ **Sem API Keys** - Não requer chaves de API externas  
✅ **Open Source** - Llama 3.1 é um modelo open source  
✅ **Sem custos** - Completamente gratuito após a instalação  

---

## 🔬 Treinar com Dados Específicos do CP2B

Se você quiser treinar ou fine-tune o modelo com dados específicos do CP2B:

### Opção 1: Modelfile Customizado (Recomendado)

Crie um arquivo chamado `Modelfile` com instruções específicas:

```modelfile
FROM llama3.1

# Temperatura (0-1): controla aleatoriedade
PARAMETER temperature 0.7

# System prompt customizado
SYSTEM """
Você é um especialista em biogás e energia renovável do CP2B/UNICAMP.
Você tem conhecimento profundo sobre:
- Produção de biogás a partir de resíduos agrícolas e pecuários
- Metodologias de cálculo de potencial energético
- Geografia e agricultura do estado de São Paulo
- Fatores de conversão validados pela literatura científica

Sempre forneça respostas precisas, baseadas em dados, e cite números quando relevante.
"""
```

Crie o modelo customizado:
```bash
ollama create cp2b-assistant -f Modelfile
```

Use o modelo customizado no código (modifique `chatbot_assistant.py`):
```python
selected_model = "cp2b-assistant"
```

### Opção 2: Fine-tuning Completo (Avançado)

Para um fine-tuning completo com seus dados:

1. Prepare um dataset de perguntas e respostas sobre biogás
2. Use ferramentas como `llama-factory` ou `unsloth`
3. Fine-tune o modelo base
4. Importe para o Ollama

**Nota:** Isso requer conhecimento avançado de ML e recursos computacionais significativos (GPU recomendada).

---

## 📝 Customização do Assistente

### Modificar o Prompt do Sistema

Edite o arquivo `src/streamlit/modules/chatbot_assistant.py`, função `query_ollama()`:

```python
system_prompt = f"""Você é um assistente especializado no sistema CP2B Maps...
[Modifique esta seção conforme necessário]
"""
```

### Adicionar Mais Contexto

Na função `prepare_database_context()`, você pode adicionar mais informações:

```python
def prepare_database_context() -> str:
    # Adicione queries SQL personalizadas
    cursor.execute("""
        SELECT sua_query_customizada FROM municipalities
    """)
    # Formate e adicione ao contexto
```

### Ajustar Interface

Modifique as funções `render_chatbot_sidebar()` e `render_chatbot_fullpage()` para alterar:
- Cores e estilo
- Tamanho das áreas de texto
- Número de mensagens exibidas
- Layout dos botões

---

## 🆘 Suporte

### Recursos Úteis:
- **Ollama Documentation:** https://ollama.ai/docs
- **Llama 3.1 Info:** https://ai.meta.com/llama/
- **CP2B Maps Issues:** [Abra uma issue no GitHub do projeto]

### Logs e Debug:

Para ver logs detalhados do assistente:

```python
# Em src/streamlit/modules/chatbot_assistant.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Execute o Streamlit com logs:
```bash
streamlit run src/streamlit/app.py --logger.level=debug
```

---

## 🎉 Parabéns!

Você agora tem um assistente de IA completamente funcional integrado ao CP2B Maps! 

Experimente fazer diferentes tipos de perguntas e veja como o assistente pode ajudar seus usuários a entender melhor os dados de potencial de biogás.

**Desenvolvido com ❤️ pelo CP2B - UNICAMP**
