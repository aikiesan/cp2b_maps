"""
CP2B Maps - AI Chatbot Assistant
Integrates Ollama-powered LLM to answer questions about biogas data
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# Try importing ollama - graceful fallback if not available
try:
    import ollama
    HAS_OLLAMA = True
    logger.info("Ollama library loaded successfully")
except ImportError:
    HAS_OLLAMA = False
    logger.warning("Ollama library not available. Install with: pip install ollama")

# Import HTML escape for safe rendering
import html

# Import RAG module
from .bagacinho_rag import BagacinhoRAG


# ============================================================================
# DATABASE CONTEXT PREPARATION
# ============================================================================

def get_database_path():
    """Get the database path"""
    return Path(__file__).parent.parent.parent.parent / "data" / "cp2b_maps.db"


def get_rag_instance() -> Optional[BagacinhoRAG]:
    """
    Get or create BagacinhoRAG instance with caching

    Returns:
        BagacinhoRAG instance or None if initialization fails
    """
    if 'bagacinho_rag' not in st.session_state:
        try:
            db_path = get_database_path()
            st.session_state.bagacinho_rag = BagacinhoRAG(db_path=db_path)
            logger.info("BagacinhoRAG initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BagacinhoRAG: {e}")
            st.session_state.bagacinho_rag = None

    return st.session_state.bagacinho_rag


def prepare_database_context() -> str:
    """
    Prepare comprehensive context about the CP2B biogas database
    to provide to the LLM for better question answering.
    """
    context_parts = []
    
    # 1. System Overview
    context_parts.append("""
# CP2B Maps - Sistema de Análise de Potencial de Biogás

## Visão Geral
O CP2B Maps é uma plataforma WebGIS desenvolvida pelo Centro Paulista de Estudos em Biogás e Bioprodutos (UNICAMP).
O sistema analisa o potencial de produção de biogás a partir de resíduos orgânicos em 645 municípios do estado de São Paulo.

## Fontes de Resíduos
O sistema calcula o potencial de biogás de três categorias principais:

### 1. Resíduos Agrícolas
- **Cana-de-açúcar**: Bagaço e vinhaça da produção de etanol e açúcar
- **Soja**: Resíduos de colheita e processamento
- **Milho**: Restos de colheita e sabugo
- **Café**: Casca e polpa do beneficiamento
- **Citros**: Bagaço de laranja e cascas da indústria de suco

### 2. Resíduos Pecuários
- **Bovinos**: Esterco de gado de corte e leite
- **Suínos**: Dejetos de criações confinadas
- **Aves**: Cama de frango de corte e poedeiras
- **Piscicultura**: Resíduos de aquicultura

### 3. Resíduos Urbanos
- **RSU**: Resíduos Sólidos Urbanos orgânicos
- **RPO**: Resíduos de Poda e capina

## Unidades
- Potencial de biogás: Nm³/ano (Normal metros cúbicos por ano)
- População: Habitantes (Censo 2022)
- Área: km²
""")
    
    # 2. Get database statistics
    try:
        db_path = get_database_path()
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Get basic statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_municipios,
                        SUM(total_final_m_ano) as potencial_total,
                        SUM(total_agricola_m_ano) as potencial_agricola,
                        SUM(total_pecuaria_m_ano) as potencial_pecuaria,
                        AVG(total_final_m_ano) as media_municipal,
                        MAX(total_final_m_ano) as maior_potencial,
                        SUM(populacao_2022) as populacao_total
                    FROM municipalities
                """)
                
                stats = cursor.fetchone()
                if stats:
                    context_parts.append(f"""
## Estatísticas do Banco de Dados

### Dados Gerais
- **Total de Municípios**: {stats[0]:,}
- **População Total**: {stats[6]:,} habitantes
- **Potencial Total de Biogás**: {stats[1]:,.0f} Nm³/ano
- **Potencial Agrícola**: {stats[2]:,.0f} Nm³/ano ({stats[2]/stats[1]*100:.1f}%)
- **Potencial Pecuário**: {stats[3]:,.0f} Nm³/ano ({stats[3]/stats[1]*100:.1f}%)
- **Média por Município**: {stats[4]:,.0f} Nm³/ano
- **Maior Potencial Municipal**: {stats[5]:,.0f} Nm³/ano
""")
                
                # Get top municipalities
                cursor.execute("""
                    SELECT nome_municipio, total_final_m_ano, populacao_2022
                    FROM municipalities 
                    ORDER BY total_final_m_ano DESC 
                    LIMIT 10
                """)
                
                top_cities = cursor.fetchall()
                if top_cities:
                    context_parts.append("\n### Top 10 Municípios por Potencial de Biogás\n")
                    for i, (nome, potencial, pop) in enumerate(top_cities, 1):
                        context_parts.append(
                            f"{i}. **{nome}**: {potencial:,.0f} Nm³/ano (Pop: {pop:,})\n"
                        )
                
                # Get substrate-specific statistics
                cursor.execute("""
                    SELECT 
                        SUM(biogas_cana_m_ano) as cana,
                        SUM(biogas_soja_m_ano) as soja,
                        SUM(biogas_bovinos_m_ano) as bovinos,
                        SUM(biogas_suino_m_ano) as suinos,
                        SUM(biogas_aves_m_ano) as aves
                    FROM municipalities
                """)
                
                substrates = cursor.fetchone()
                if substrates:
                    total = sum(s for s in substrates if s)
                    context_parts.append(f"""
### Contribuição por Substrato (Estado de São Paulo)
- **Cana-de-açúcar**: {substrates[0]:,.0f} Nm³/ano ({substrates[0]/total*100:.1f}%)
- **Soja**: {substrates[1]:,.0f} Nm³/ano ({substrates[1]/total*100:.1f}%)
- **Bovinos**: {substrates[2]:,.0f} Nm³/ano ({substrates[2]/total*100:.1f}%)
- **Suínos**: {substrates[3]:,.0f} Nm³/ano ({substrates[3]/total*100:.1f}%)
- **Aves**: {substrates[4]:,.0f} Nm³/ano ({substrates[4]/total*100:.1f}%)
""")
                
    except Exception as e:
        logger.error(f"Erro ao preparar contexto do banco: {e}")
        context_parts.append("\n⚠️ Erro ao acessar estatísticas do banco de dados.\n")
    
    # 3. Technical Information
    context_parts.append("""
## Informações Técnicas

### Fatores de Conversão
O sistema utiliza fatores de conversão validados pela literatura científica para calcular
o potencial de biogás a partir das quantidades de resíduos produzidos.

### Metodologia
A metodologia segue padrões internacionais de cálculo de potencial de biogás, considerando:
- Produção anual de resíduos por fonte
- Fatores de conversão (m³ CH₄/ton de resíduo)
- Potencial de metano como proxy para biogás (60-70% CH₄)

### Referências Científicas
O projeto é financiado pela FAPESP (processo 2024/01112-1) e utiliza dados de:
- IBGE (população, agricultura, pecuária)
- CETESB (resíduos urbanos)
- MapBiomas (uso do solo)
- Literatura científica peer-reviewed

## Como Usar Este Assistente
Você pode me perguntar sobre:
- Potencial de biogás de municípios específicos
- Comparação entre diferentes substatos ou regiões
- Explicações sobre a metodologia
- Estatísticas gerais do estado de São Paulo
- Informações sobre fontes de resíduos específicas

Exemplos de perguntas:
- "Qual o potencial de biogás do município de Campinas?"
- "Qual substrato contribui mais para o potencial total?"
- "Como é calculado o potencial de biogás da cana-de-açúcar?"
- "Quais são os 5 municípios com maior potencial pecuário?"
""")
    
    return "\n".join(context_parts)


# ============================================================================
# OLLAMA INTEGRATION
# ============================================================================

def check_ollama_connection(host: str = "http://localhost:11434") -> Tuple[bool, str]:
    """
    Check if Ollama is running and accessible.
    
    Returns:
        Tuple of (is_connected, message)
    """
    if not HAS_OLLAMA:
        return False, "Biblioteca Ollama não instalada. Execute: pip install ollama"
    
    try:
        # Try to list available models
        client = ollama.Client(host=host)
        models_response = client.list()
        
        # Handle different response formats
        if isinstance(models_response, dict):
            models_list = models_response.get('models', [])
        else:
            # If it's an object with a models attribute
            models_list = getattr(models_response, 'models', [])
        
        if models_list and len(models_list) > 0:
            # Try different ways to get model names
            model_names = []
            for m in models_list:
                if isinstance(m, dict):
                    model_names.append(m.get('name', m.get('model', 'unknown')))
                else:
                    model_names.append(getattr(m, 'name', getattr(m, 'model', 'unknown')))
            
            return True, f"✅ Conectado! Modelos disponíveis: {', '.join(model_names)}"
        else:
            return False, "⚠️ Ollama conectado mas nenhum modelo encontrado. Execute: ollama pull llama3.1"
            
    except Exception as e:
        return False, f"❌ Não foi possível conectar ao Ollama: {str(e)}\n\nVerifique se o Ollama está rodando em {host}"


def get_available_models(host: str = "http://localhost:11434") -> List[str]:
    """Get list of available Ollama models"""
    if not HAS_OLLAMA:
        return []
    
    try:
        client = ollama.Client(host=host)
        models_response = client.list()
        
        # Handle different response formats
        if isinstance(models_response, dict):
            models_list = models_response.get('models', [])
        else:
            models_list = getattr(models_response, 'models', [])
        
        # Extract model names
        model_names = []
        for m in models_list:
            if isinstance(m, dict):
                model_names.append(m.get('name', m.get('model', 'unknown')))
            else:
                model_names.append(getattr(m, 'name', getattr(m, 'model', 'unknown')))
        
        return model_names
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return []


def query_ollama(
    question: str,
    model: str = "llama3.1",
    context: str = "",
    conversation_history: Optional[List[Dict]] = None,
    host: str = "http://localhost:11434",
    use_rag: bool = True
) -> Tuple[str, bool]:
    """
    Query Ollama with a question and context.

    Args:
        question: User's question
        model: Ollama model to use (supports "bagacinho", "llama3.1", etc.)
        context: Database context to provide (used as fallback if RAG fails)
        conversation_history: Previous messages for context
        host: Ollama host URL
        use_rag: Whether to use RAG for dynamic context retrieval (default: True)

    Returns:
        Tuple of (answer, success)
    """
    if not HAS_OLLAMA:
        return "Erro: Biblioteca Ollama não instalada.", False

    try:
        client = ollama.Client(host=host)

        # ========== RAG INTEGRATION ==========
        # Try to get dynamic context from RAG
        rag_context = None
        if use_rag:
            try:
                rag = get_rag_instance()
                if rag:
                    rag_context = rag.construir_contexto(question)
                    logger.info(f"RAG context generated for question: {question[:50]}...")
            except Exception as e:
                logger.warning(f"RAG failed, using static context: {e}")

        # Use RAG context if available, otherwise fallback to static context
        final_context = rag_context if rag_context else context

        # Build message history
        messages = []

        # Customized system prompt based on model
        if model.lower() == "bagacinho":
            # Special prompt for the fine-tuned Bagacinho model
            system_prompt = f"""Você é o Bagacinho 🍊, modelo especializado em análise de potencial de biogás do CP2B Maps (UNICAMP).

Você foi treinado especificamente com conhecimento sobre:
- 📊 Dados MapBIOMAS Coleção 9
- 🗺️ Metodologias MCDA (Multi-Criteria Decision Analysis)
- ⚡ Cálculos energéticos de biogás
- 🏙️ Análise dos 645 municípios de São Paulo

CONTEXTO ATUALIZADO DO BANCO DE DADOS:
{final_context}

IMPORTANTE:
- Use PRIORITARIAMENTE os dados reais fornecidos acima
- Cite números exatos quando disponíveis
- Se os dados acima não tiverem a informação, use seu conhecimento geral mas deixe claro
- Seja técnico mas acessível

Use seu conhecimento especializado combinado com os dados acima para responder de forma precisa e técnica, mas acessível."""
        else:
            # Default prompt for general models
            system_prompt = f"""Você é o Bagacinho, um assistente especializado e amigável do sistema CP2B Maps,
uma plataforma de análise de potencial de biogás desenvolvida pela UNICAMP.

Sua função é ajudar os usuários a entender os dados do sistema, responder perguntas
sobre potencial de biogás em municípios de São Paulo, e explicar a metodologia de forma clara e acessível.

PERSONALIDADE:
- Você é prestativo, entusiasmado e didático
- Use emojis ocasionalmente para tornar as respostas mais amigáveis 🍊
- Mantenha um tom profissional mas descontraído

IMPORTANTE:
- Responda sempre em português brasileiro
- Seja preciso e cite números quando relevante
- Se não souber algo, seja honesto e sugira como o usuário pode encontrar a informação
- Use os dados do contexto fornecido abaixo
- Quando falar sobre grandes números, use formatação clara (ex: "1,2 milhão de m³/ano")

CONTEXTO DO BANCO DE DADOS CP2B:
{final_context}

Responda de forma clara, útil e profissional, mas com um toque amigável."""

        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current question
        messages.append({
            "role": "user",
            "content": question
        })
        
        # Query Ollama
        response = client.chat(
            model=model,
            messages=messages,
            stream=False
        )
        
        answer = response['message']['content']
        return answer, True
        
    except Exception as e:
        error_msg = f"Erro ao consultar Ollama: {str(e)}"
        logger.error(error_msg)
        return error_msg, False


# ============================================================================
# STREAMLIT CHAT INTERFACE
# ============================================================================

def render_chatbot_sidebar():
    """
    Render chatbox interface in sidebar with message bubbles.
    """
    st.markdown("---")
    st.markdown("""
    <div style='background: linear-gradient(135deg, #FF8C00 0%, #FF6347 100%); 
                color: white; padding: 0.6rem; border-radius: 8px; text-align: center;
                margin-bottom: 0.8rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <h4 style='margin: 0; font-size: 0.95rem;'>🍊 Bagacinho</h4>
        <p style='margin: 0.2rem 0 0 0; font-size: 0.7rem; opacity: 0.95;'>
            Seu assistente de biogás CP2B
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check connection
    is_connected, status_msg = check_ollama_connection()
    
    if not is_connected:
        st.error(status_msg)
        st.info("""
        **Para usar o assistente:**
        1. Certifique-se que o Docker Ollama está rodando
        2. Recarregue a página
        """)
        return
    
    # Model selection
    available_models = get_available_models()
    
    # Prioritize bagacinho if available
    default_model = "bagacinho" if "bagacinho" in available_models else (available_models[0] if available_models else "llama3.1")
    
    if 'selected_model_sidebar' not in st.session_state:
        st.session_state.selected_model_sidebar = default_model
    
    selected_model = st.selectbox(
        "🤖 Modelo",
        options=available_models if available_models else ["llama3.1"],
        index=available_models.index(st.session_state.selected_model_sidebar) if st.session_state.selected_model_sidebar in available_models else 0,
        key="model_selector_sidebar",
        help="Escolha o modelo LLM (recomendado: bagacinho se disponível)"
    )
    
    st.session_state.selected_model_sidebar = selected_model
    
    # Show model indicator
    if selected_model == "bagacinho":
        st.success("🍊 Usando modelo **Bagacinho** treinado!")
    else:
        st.info(f"🤖 Usando modelo: {selected_model}")
    
    # Initialize chat history with greeting message
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        # Add initial greeting from Bagacinho
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "Olá! Vamos falar sobre a Cana?"
        })
    
    if 'db_context' not in st.session_state:
        with st.spinner("Preparando contexto..."):
            st.session_state.db_context = prepare_database_context()
    
    # Chat messages container with scroll and auto-grow
    st.markdown("""
    <style>
    /* Hide form buttons completely */
    div[data-testid="stForm"] button[kind="formSubmit"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Chat messages with container that grows
    chat_container = st.container()
    with chat_container:
        # Display chat history with bubbles
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                # User message bubble (right-aligned, green)
                # Escape HTML to prevent rendering issues
                safe_content = html.escape(msg['content']).replace('\n', '<br>')
                st.markdown(f"""
                <div style='margin-bottom: 0.8rem; display: flex; justify-content: flex-end;'>
                    <div style='background: #DCF8C6; color: #000; padding: 0.6rem 0.8rem; 
                                border-radius: 12px 12px 0 12px; max-width: 85%; 
                                box-shadow: 0 1px 2px rgba(0,0,0,0.1); font-size: 0.85rem;
                                word-wrap: break-word;'>
                        {safe_content}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Bagacinho message bubble (left-aligned, white)
                # Escape HTML to prevent rendering issues
                safe_content = html.escape(msg['content']).replace('\n', '<br>')
                st.markdown(f"""
                <div style='margin-bottom: 0.8rem; display: flex; justify-content: flex-start;'>
                    <div style='background: #FFFFFF; color: #000; padding: 0.6rem 0.8rem; 
                                border-radius: 12px 12px 12px 0; max-width: 85%; 
                                box-shadow: 0 1px 2px rgba(0,0,0,0.1); font-size: 0.85rem;
                                border: 1px solid #E5E5EA; word-wrap: break-word;'>
                        <strong style='color: #FF8C00;'>🍊</strong> {safe_content}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Input area - simple text_input that sends with Enter
    with st.form(key="chat_form_sidebar", clear_on_submit=True):
        user_input = st.text_input(
            "Mensagem",
            key="chat_input_sidebar",
            placeholder="Digite sua pergunta e pressione Enter...",
            label_visibility="collapsed"
        )
        # Hidden submit button (form needs it but we hide it with CSS)
        submitted = st.form_submit_button("send", use_container_width=True)
    
    # Handle submission
    if submitted and user_input.strip():
        with st.spinner("🍊 Bagacinho está pensando..."):
            answer, success = query_ollama(
                question=user_input,
                model=st.session_state.selected_model_sidebar,
                context=st.session_state.db_context,
                conversation_history=st.session_state.chat_history
            )
            
            if success:
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer
                })
                st.rerun()


def render_chatbot_fullpage():
    """
    Render full-page chatbot interface with beautiful bubble design.
    """
    st.markdown("""
    <div style='background: linear-gradient(135deg, #FF8C00 0%, #FF6347 100%); 
                color: white; padding: 2rem; border-radius: 15px; text-align: center;
                margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.15);'>
        <h1 style='margin: 0; font-size: 2.5rem;'>🍊 Bagacinho</h1>
        <p style='margin: 0.8rem 0 0 0; font-size: 1.2rem; opacity: 0.95;'>
            Especialista em Biogás do CP2B Maps
        </p>
        <p style='margin: 0.4rem 0 0 0; font-size: 0.9rem; opacity: 0.85;'>
            Análise geoespacial • MapBIOMAS • MCDA • 645 municípios de SP
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check connection
    is_connected, status_msg = check_ollama_connection()
    
    if not is_connected:
        st.error(status_msg)
        st.info("""
        **Para usar o assistente:**
        1. Certifique-se que o Docker Ollama está rodando
        2. Recarregue a página
        """)
        return
    
    # Model selection at top
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        st.success(f"✅ {status_msg}")
    
    with col2:
        available_models = get_available_models()
        
        # Prioritize bagacinho if available
        default_model = "bagacinho" if "bagacinho" in available_models else (available_models[0] if available_models else "llama3.1")
        
        if 'selected_model_fullpage' not in st.session_state:
            st.session_state.selected_model_fullpage = default_model
        
        selected_model = st.selectbox(
            "🤖 Modelo LLM",
            options=available_models if available_models else ["llama3.1"],
            index=available_models.index(st.session_state.selected_model_fullpage) if st.session_state.selected_model_fullpage in available_models else 0,
            key="model_selector_fullpage",
            help="Escolha o modelo (recomendado: bagacinho se disponível)"
        )
        
        st.session_state.selected_model_fullpage = selected_model
    
    with col3:
        if selected_model == "bagacinho":
            st.markdown("### 🍊")
            st.caption("Modelo treinado")
    
    st.divider()
    
    # Initialize session state with greeting
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "Olá! Vamos falar sobre a Cana? 🍊"
        })
    
    if 'db_context' not in st.session_state:
        with st.spinner("Preparando contexto..."):
            st.session_state.db_context = prepare_database_context()
    
    # Hide form buttons
    st.markdown("""
    <style>
    /* Hide form buttons */
    div[data-testid="stForm"] button[kind="formSubmit"] {
        display: none !important;
    }
    /* Make chat container scrollable */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Chat messages area with bubbles
    chat_container = st.container()
    
    with chat_container:
        # Display chat history with beautiful bubbles
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                # User message bubble (right-aligned, light green)
                # Escape HTML to prevent rendering issues
                safe_content = html.escape(msg['content']).replace('\n', '<br>')
                st.markdown(f"""
                <div style='margin: 1rem 0; display: flex; justify-content: flex-end;'>
                    <div style='background: #DCF8C6; color: #000; padding: 1rem 1.2rem; 
                                border-radius: 18px 18px 4px 18px; max-width: 70%; 
                                box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-size: 1rem;
                                word-wrap: break-word; line-height: 1.5;'>
                        {safe_content}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Bagacinho message bubble (left-aligned, white)
                # Escape HTML to prevent rendering issues
                safe_content = html.escape(msg['content']).replace('\n', '<br>')
                st.markdown(f"""
                <div style='margin: 1rem 0; display: flex; justify-content: flex-start;'>
                    <div style='background: #FFFFFF; color: #000; padding: 1rem 1.2rem; 
                                border-radius: 18px 18px 18px 4px; max-width: 70%; 
                                box-shadow: 0 2px 5px rgba(0,0,0,0.1); font-size: 1rem;
                                border: 1px solid #E5E5EA; word-wrap: break-word; line-height: 1.5;'>
                        <strong style='color: #FF8C00; font-size: 1.1rem;'>🍊 Bagacinho:</strong><br><br>
                        {safe_content}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Spacer before input
    st.markdown("<br>" * 2, unsafe_allow_html=True)
    
    # Input area at bottom - fixed position
    st.markdown("""
    <div style='background: #f8f9fa; padding: 1.5rem; border-radius: 12px; 
                border: 2px solid #e0e0e0; margin-top: 2rem;'>
    </div>
    """, unsafe_allow_html=True)
    
    # Input form
    with st.form(key="chat_form_fullpage", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_area(
                "Mensagem",
                key="chat_input_full",
                placeholder="Digite sua pergunta e pressione Ctrl+Enter para enviar...",
                height=100,
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style='text-align: center; padding: 1rem 0;'>
                <p style='font-size: 0.85rem; color: #666; margin: 0;'>
                    Pressione<br>
                    <strong style='color: #25D366;'>Ctrl + Enter</strong><br>
                    para enviar
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Hidden submit button
        submitted = st.form_submit_button("send")
    
    # Handle submission
    if submitted and user_input.strip():
        with st.spinner("🍊 Bagacinho está pensando..."):
            answer, success = query_ollama(
                question=user_input,
                model=st.session_state.selected_model_fullpage,
                context=st.session_state.db_context,
                conversation_history=st.session_state.chat_history
            )
            
            if success:
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer
                })
                st.rerun()
            else:
                st.error(f"Erro: {answer}")
