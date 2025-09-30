# 🍊 Guia de Uso do Bagacinho

## O que é o Bagacinho?

O **Bagacinho** é um modelo LLM (Large Language Model) especializado e treinado especificamente para responder perguntas sobre o sistema CP2B Maps, análise de potencial de biogás, e dados geoespaciais do estado de São Paulo.

Diferente de modelos genéricos como Llama 3.1, o Bagacinho foi **fine-tuned** com conhecimento específico sobre:

- 📊 **Dados MapBIOMAS Coleção 9**
- 🗺️ **Metodologias MCDA** (Multi-Criteria Decision Analysis)
- ⚡ **Cálculos Energéticos de Biogás**
- 🏙️ **Análise dos 645 Municípios de São Paulo**
- 🌾 **Resíduos Agrícolas e Pecuários**
- ♻️ **Conversões e Fatores Técnicos**

---

## 🎯 Duas Maneiras de Usar o Bagacinho

### Opção 1: App Standalone (Teste Rápido)

Para testar o Bagacinho rapidamente em uma interface dedicada:

```bash
# Certifique-se que o Ollama está rodando e o modelo bagacinho está carregado
streamlit run test_bagacinho.py
```

**Vantagens:**
- ✅ Interface simples e focada
- ✅ Configurações visíveis (temperature, max tokens)
- ✅ Ideal para testes e validação do modelo
- ✅ Exemplos de perguntas incluídos

### Opção 2: Integrado ao CP2B Maps (Produção)

O Bagacinho está totalmente integrado ao app principal:

```bash
streamlit run src/streamlit/app.py
```

**Onde encontrar:**
1. **Sidebar** (Acesso Rápido): Vá para "🏠 Mapa Principal" → Role até o final da sidebar
2. **Aba Dedicada**: Clique na aba "🤖 Assistente IA" no topo

**Vantagens:**
- ✅ Acesso aos dados em tempo real do banco de dados
- ✅ Contexto automático com estatísticas atualizadas
- ✅ Histórico de conversa persistente
- ✅ Seletor de modelo (escolha entre bagacinho e outros modelos)

---

## ⚙️ Verificar se o Bagacinho está Disponível

Execute o script de verificação:

```bash
python check_ollama_models.py
```

Este script lista todos os modelos disponíveis no Ollama. Procure por `bagacinho` na lista.

Se o modelo **não aparecer**, você precisa criar/treinar o modelo primeiro.

---

## 🎓 Como o Bagacinho Foi Treinado?

O Bagacinho foi criado usando **fine-tuning** do modelo base Llama 3.1 com dados específicos do CP2B Maps.

### Passos do Treinamento:

1. **Preparação de Dados:**
   - Documentação técnica do CP2B Maps
   - Papers científicos sobre biogás
   - Dados reais do banco de dados
   - Metodologias MCDA aplicadas
   - Dados MapBIOMAS

2. **Fine-tuning:**
   ```bash
   # Exemplo de comando (varia conforme ferramenta usada)
   ollama create bagacinho -f Modelfile
   ```

3. **Validação:**
   - Testes com perguntas técnicas
   - Verificação de precisão nas respostas
   - Ajuste de hiperparâmetros

---

## 🔄 Seleção de Modelo no App

Quando você abre o CP2B Maps, o sistema automaticamente:

1. **Detecta modelos disponíveis** no Ollama
2. **Prioriza o Bagacinho** se disponível
3. **Permite alternar** entre modelos via dropdown

### Como Trocar de Modelo:

**Na Sidebar:**
- Procure o dropdown "🤖 Modelo"
- Selecione "bagacinho" (se disponível)
- Indicador mostrará: "🍊 Usando modelo **Bagacinho** treinado!"

**Na Aba Completa:**
- Topo da página tem "🤖 Modelo LLM"
- Selecione "bagacinho"
- Um ícone 🍊 aparecerá indicando "Modelo treinado"

---

## 💡 Diferenças Entre Bagacinho e Llama 3.1

| Característica | Bagacinho (Fine-tuned) | Llama 3.1 (Base) |
|----------------|------------------------|------------------|
| **Conhecimento CP2B** | ⭐⭐⭐⭐⭐ Especializado | ⭐⭐ Genérico |
| **Precisão Técnica** | ⭐⭐⭐⭐⭐ Alta | ⭐⭐⭐ Média |
| **Dados MapBIOMAS** | ⭐⭐⭐⭐⭐ Familiarizado | ⭐⭐ Desconhecido |
| **Terminologia** | ⭐⭐⭐⭐⭐ Específica | ⭐⭐⭐ Geral |
| **Velocidade** | ⭐⭐⭐⭐ Similar | ⭐⭐⭐⭐ Similar |
| **Tamanho** | ⭐⭐⭐⭐ ~5GB | ⭐⭐⭐⭐ ~5GB |

### Quando Usar Cada Um:

**Use o Bagacinho quando:**
- Perguntas técnicas sobre biogás
- Análise de municípios específicos
- Explicações metodológicas
- Cálculos e conversões energéticas
- Dados MapBIOMAS e MCDA

**Use o Llama 3.1 quando:**
- Bagacinho não estiver disponível
- Perguntas mais genéricas
- Testes de comparação
- Backup/fallback

---

## 📝 Exemplos de Perguntas para o Bagacinho

### Nível Básico:
```
- O que é biogás?
- Quais são as principais fontes de resíduos?
- Qual o potencial total de São Paulo?
```

### Nível Intermediário:
```
- Qual o potencial de biogás de Campinas?
- Compare o potencial agrícola e pecuário do estado
- Quais os 10 municípios com maior potencial?
```

### Nível Avançado:
```
- Explique a metodologia MCDA aplicada no CP2B Maps
- Como são calculados os fatores de conversão para cana-de-açúcar?
- Qual a relação entre área de uso do solo e potencial energético?
- Dimensione um biodigestor para 5000 bovinos em Ribeirão Preto
```

### Análise Regional:
```
- Qual a melhor região para instalação de plantas de biogás?
- Análise comparativa da bacia do Rio Tietê vs Paranapanema
- Potencial agregado da região metropolitana de São Paulo
```

---

## 🔧 Troubleshooting

### ❌ "Modelo bagacinho não encontrado"

**Problema:** O modelo não foi criado ou não está disponível no Ollama.

**Solução:**
1. Verifique modelos disponíveis: `ollama list`
2. Se não estiver lá, você precisa criar o modelo
3. Veja a documentação de fine-tuning do Ollama

### ❌ "Resposta muito genérica"

**Problema:** Pode estar usando o modelo base em vez do Bagacinho.

**Solução:**
1. Verifique o dropdown de modelo
2. Confirme que "bagacinho" está selecionado
3. Veja o indicador "🍊 Usando modelo Bagacinho treinado!"

### ❌ "Respostas lentas"

**Problema:** Modelo pode estar sendo carregado pela primeira vez.

**Solução:**
1. Primeira consulta pode demorar (carregamento do modelo)
2. Consultas subsequentes serão mais rápidas
3. Considere usar `num_predict` menor (max tokens)

### ❌ "Erro de timeout"

**Problema:** Timeout ao consultar o modelo.

**Solução:**
1. Aumente o timeout no código (padrão: 120s)
2. Reduza `max_tokens` nas configurações
3. Verifique recursos do sistema (RAM/CPU)

---

## 🚀 Boas Práticas

### Para Melhores Respostas:

1. **Seja específico:**
   ❌ "Fale sobre biogás"
   ✅ "Qual o potencial de biogás de cana-de-açúcar em Ribeirão Preto?"

2. **Use contexto:**
   ❌ "Qual o potencial?"
   ✅ "Qual o potencial total de biogás do município de Campinas considerando todos os substratos?"

3. **Perguntas de acompanhamento:**
   ```
   Pergunta 1: "Quais os 5 municípios com maior potencial?"
   Pergunta 2: "Desses 5, qual tem maior contribuição de resíduos pecuários?"
   ```

4. **Solicite comparações:**
   ```
   "Compare o potencial de Ribeirão Preto e Barretos"
   "Qual região tem maior densidade de potencial por km²?"
   ```

---

## 📊 Configurações Avançadas

### Temperature (0.0 - 1.0):

- **0.0 - 0.3:** Respostas determinísticas, precisas, repetíveis
- **0.4 - 0.7:** Equilíbrio entre precisão e criatividade (recomendado)
- **0.8 - 1.0:** Mais criativo, variado, menos determinístico

**Recomendação para Bagacinho:** `0.7 - 0.8`

### Max Tokens (256 - 2048):

- **256:** Respostas curtas e diretas
- **512 - 1024:** Respostas médias, detalhadas (recomendado)
- **1024 - 2048:** Respostas longas, muito detalhadas

**Recomendação para Bagacinho:** `1024`

---

## 🎓 Retreinamento e Atualização

Se você precisar retreinar ou atualizar o Bagacinho com novos dados:

1. **Prepare novos dados** (documentos, Q&A, etc.)
2. **Crie um novo Modelfile** com instruções atualizadas
3. **Recrie o modelo:**
   ```bash
   ollama create bagacinho -f Modelfile.new
   ```
4. **Teste o novo modelo** usando o `test_bagacinho.py`
5. **Se satisfeito**, use no app principal

---

## 📈 Monitoramento de Performance

### Métricas a Observar:

- **Tempo de resposta:** Primeira consulta vs subsequentes
- **Qualidade das respostas:** Precisão técnica
- **Uso de memória:** RAM consumida durante inferência
- **Contexto:** Manutenção do histórico de conversa

### Logs:

```python
# Habilitar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🎯 Roadmap Futuro

Possíveis melhorias para o Bagacinho:

- [ ] RAG (Retrieval-Augmented Generation) com papers científicos
- [ ] Integração com gráficos inline
- [ ] Sugestões contextuais de perguntas
- [ ] Export de conversas como PDF
- [ ] Fine-tuning incremental com feedback de usuários
- [ ] Suporte a múltiplos idiomas

---

## 🆘 Suporte

**Problemas com o Bagacinho?**

1. Verifique logs do Ollama: `docker logs <ollama-container>`
2. Teste com modelo base: `llama3.1`
3. Verifique recursos do sistema: RAM, CPU
4. Consulte `CHATBOT_SETUP_GUIDE.md` para configuração base

---

## ✨ Conclusão

O **Bagacinho** representa um assistente especializado que combina:
- ✅ Conhecimento técnico específico
- ✅ Dados em tempo real
- ✅ Interface amigável
- ✅ Execução 100% local

Aproveite este assistente para explorar os dados do CP2B Maps de forma interativa e obter insights valiosos sobre o potencial de biogás em São Paulo!

---

**Desenvolvido com 🍊 pelo CP2B - Centro Paulista de Estudos em Biogás e Bioprodutos (UNICAMP)**

*Última atualização: Setembro 2025*

