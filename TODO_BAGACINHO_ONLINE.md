# TODO: Bagacinho Online - Decisao e Implementacao

**Data:** 30 de Setembro, 2025
**Status:** PENDENTE - Resolver amanha
**Prioridade:** ALTA

---

## Situacao Atual

### ✅ O que esta funcionando:

1. **Sistema RAG completo** (local)
   - Busca inteligente no banco SQLite
   - Deteccao de intencao por NLP
   - 8/8 testes passaram
   - Documentacao completa

2. **Interface do Bagacinho** (online e local)
   - Sidebar integrada
   - Pagina dedicada
   - Design completo

3. **Integracao com Ollama** (apenas local)
   - Docker Desktop com llama3.1
   - Respostas contextualizadas com RAG
   - Conversacao funcional

### ❌ O que NAO funciona online:

1. **Ollama no Streamlit Cloud**
   - Streamlit Cloud nao permite Docker/servidores externos
   - `localhost:11434` nao e acessivel da nuvem
   - Bagacinho mostra "Ollama nao disponivel"

---

## Problema a Resolver

O Bagacinho funciona **perfeitamente local**, mas **nao responde perguntas online** no Streamlit Cloud porque:

1. Ollama roda em `localhost:11434` (Docker Desktop local)
2. Streamlit Cloud nao acessa localhost do usuario
3. Precisa de backend externo OU API cloud

---

## Opcoes para Implementacao (Decidir Amanha)

### **Opcao 1: OpenAI API** ⭐ RECOMENDADA

**Vantagens:**
- ✅ Implementacao rapida (1-2 horas)
- ✅ Funciona imediatamente no Streamlit Cloud
- ✅ Sem necessidade de servidor proprio
- ✅ Respostas melhores (GPT-4 > llama3.1)
- ✅ Escalavel automaticamente
- ✅ Manutencao zero

**Desvantagens:**
- 💰 Custo por uso (~$0.03/1000 tokens)
- 💰 Estimativa: $5-20/mes para uso moderado

**Implementacao:**
```python
# Arquivo: src/streamlit/modules/openai_backend.py
import openai

def query_openai(question: str, context: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Voce e o Bagacinho...\n{context}"},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content
```

**Configuracao:**
1. Criar conta OpenAI (https://platform.openai.com)
2. Obter API key
3. Adicionar em `.streamlit/secrets.toml`:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. Modificar `chatbot_assistant.py` para detectar:
   - Se local: usa Ollama
   - Se cloud: usa OpenAI

**Tempo estimado:** 1-2 horas

---

### **Opcao 2: Servidor VPS com Ollama**

**Vantagens:**
- ✅ Controle total sobre modelo
- ✅ Privacidade dos dados
- ✅ Sem custo por token
- ✅ Pode usar modelo proprio (bagacinho fine-tuned)

**Desvantagens:**
- 💰 Custo fixo mensal ($20-50/mes)
- ⚙️ Manutencao de servidor
- ⏱️ Tempo de setup (4-6 horas)
- 🔧 Conhecimento de DevOps necessario

**Implementacao:**
1. Alugar VPS (DigitalOcean, AWS EC2, Linode)
2. Instalar Ubuntu + CUDA (se GPU)
3. Instalar Docker + Ollama
4. Configurar firewall (abrir porta 11434)
5. Obter IP fixo ou dominio
6. Modificar codigo:
   ```python
   OLLAMA_HOST = st.secrets.get("OLLAMA_URL", "http://seu-ip:11434")
   ```

**Tempo estimado:** 4-6 horas

---

### **Opcao 3: Anthropic Claude API**

**Vantagens:**
- ✅ Mesmo modelo usado no desenvolvimento (Claude)
- ✅ Respostas de alta qualidade
- ✅ Contexto grande (200K tokens)
- ✅ Funciona no Streamlit Cloud

**Desvantagens:**
- 💰 Custo por uso (~$0.015/1000 tokens)
- 💰 Mais barato que OpenAI

**Implementacao:**
```python
import anthropic

client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": f"{context}\n\n{question}"}]
)
```

**Tempo estimado:** 1-2 horas

---

### **Opcao 4: Deixar Apenas Local**

**Vantagens:**
- ✅ Sem custo adicional
- ✅ Sem trabalho adicional
- ✅ Ja funciona perfeitamente

**Desvantagens:**
- ❌ Usuarios online nao podem usar
- ❌ Apenas demonstracao visual online

**Acao:**
- Adicionar aviso no README
- Atualizar documentacao

---

## Recomendacao Tecnica

### Para MVP/Demonstracao Rapida:
**Opcao 1 (OpenAI)** ou **Opcao 3 (Claude)**
- Rapido de implementar
- Funciona imediatamente
- Custo baixo inicialmente

### Para Producao de Longo Prazo:
**Opcao 2 (VPS)** se:
- Tiver orcamento para servidor
- Quiser privacidade total
- Usar modelo proprio fine-tuned

**Opcao 1/3 (API)** se:
- Preferir pay-as-you-go
- Nao quiser gerenciar infraestrutura
- Qualidade > custo

---

## Checklist de Implementacao (Amanha)

### Pre-decisao:
- [ ] Definir orcamento mensal
- [ ] Definir prioridade: velocidade vs custo vs controle
- [ ] Escolher opcao (1, 2, 3 ou 4)

### Se escolher Opcao 1 (OpenAI):
- [ ] Criar conta OpenAI
- [ ] Obter API key
- [ ] Criar `src/streamlit/modules/openai_backend.py`
- [ ] Modificar `chatbot_assistant.py` com deteccao de ambiente
- [ ] Adicionar secrets no Streamlit Cloud
- [ ] Testar localmente
- [ ] Fazer deploy
- [ ] Testar online
- [ ] Atualizar documentacao

### Se escolher Opcao 2 (VPS):
- [ ] Escolher provedor (DigitalOcean recomendado)
- [ ] Criar droplet/instancia
- [ ] Instalar Ollama
- [ ] Configurar firewall
- [ ] Testar conexao externa
- [ ] Modificar codigo com URL do servidor
- [ ] Fazer deploy
- [ ] Testar online
- [ ] Configurar monitoramento

### Se escolher Opcao 3 (Claude):
- [ ] Criar conta Anthropic
- [ ] Obter API key
- [ ] Criar `src/streamlit/modules/claude_backend.py`
- [ ] Modificar `chatbot_assistant.py`
- [ ] Adicionar secrets
- [ ] Testar e fazer deploy

### Se escolher Opcao 4 (Local apenas):
- [ ] Atualizar README com instrucoes locais
- [ ] Adicionar badge "Local only"
- [ ] Documentar no Streamlit Cloud

---

## Estimativas de Custo

### Opcao 1 (OpenAI):
- Custo/1000 tokens: $0.03 (GPT-4) ou $0.002 (GPT-3.5)
- Estimativa de uso: 100 perguntas/dia
- Tokens/pergunta: ~1000 (contexto RAG + resposta)
- **Custo mensal: $5-20** (depende do modelo)

### Opcao 2 (VPS):
- DigitalOcean Droplet (4GB RAM): $24/mes
- AWS EC2 t3.medium: ~$30/mes
- Com GPU (para modelo grande): $50-100/mes
- **Custo mensal fixo: $24-100**

### Opcao 3 (Claude):
- Custo/1000 tokens: $0.015
- Mesma estimativa de uso
- **Custo mensal: $3-10** (mais barato que OpenAI)

### Opcao 4 (Local):
- **Custo: $0**

---

## Arquivos a Modificar (Dependendo da Escolha)

### Para APIs (Opcoes 1 ou 3):
```
src/streamlit/modules/
├── chatbot_assistant.py          ← Modificar (adicionar deteccao)
├── openai_backend.py             ← Criar (se OpenAI)
├── claude_backend.py             ← Criar (se Claude)
└── bagacinho_rag.py              ← Manter (RAG funciona igual)

.streamlit/
└── secrets.toml                   ← Adicionar API keys
```

### Para VPS (Opcao 2):
```
src/streamlit/modules/
└── chatbot_assistant.py          ← Modificar (mudar OLLAMA_HOST)

.streamlit/
└── secrets.toml                   ← Adicionar URL do servidor
```

---

## Proximos Passos (Cronograma)

**Amanha:**
1. ☕ Revisar este documento
2. 🤔 Decidir qual opcao implementar
3. 🛠️ Implementar solucao escolhida
4. ✅ Testar localmente
5. 🚀 Fazer deploy no Streamlit Cloud
6. 🎉 Bagacinho funcionando online!

---

## Notas Tecnicas

### Compatibilidade do RAG:
O sistema RAG **funciona com qualquer backend**:
- ✅ OpenAI
- ✅ Claude
- ✅ Ollama (local ou remoto)
- ✅ Qualquer LLM via API

O RAG apenas prepara o contexto. O backend escolhido recebe:
```
contexto_rag = rag.construir_contexto(pergunta)
resposta = backend.query(pergunta, contexto_rag)
```

### Migracao Facil:
O codigo foi desenhado para trocar de backend facilmente:
```python
if st.secrets.get("USE_OPENAI"):
    from openai_backend import query_openai as query_llm
elif st.secrets.get("USE_CLAUDE"):
    from claude_backend import query_claude as query_llm
else:
    from chatbot_assistant import query_ollama as query_llm
```

---

**Desenvolvido para CP2B Maps - UNICAMP**
**Decisao e implementacao: 01 de Outubro, 2025**
