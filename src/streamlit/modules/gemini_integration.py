"""
CP2B Maps - Google Gemini API Integration
Uses Bagacinho training data as few-shot examples for context
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing google-generativeai
try:
    import google.generativeai as genai
    HAS_GEMINI = True
    logger.info("Google Gemini library loaded successfully")
except ImportError:
    HAS_GEMINI = False
    logger.warning("Google Gemini library not available. Install with: pip install google-generativeai")


class GeminiAssistant:
    """Google Gemini integration for CP2B chatbot"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini assistant

        Args:
            api_key: Google API key. If None, will try to read from GEMINI_API_KEY env variable
        """
        if not HAS_GEMINI:
            raise ImportError("google-generativeai not installed")

        # Get API key
        # Try Streamlit secrets first, then environment variable
        try:
            import streamlit as st
            if "GEMINI_API_KEY" in st.secrets:
                self.api_key = api_key or st.secrets["GEMINI_API_KEY"]
            else:
                self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        except (KeyError, FileNotFoundError, AttributeError) as e:
            logger.warning(f"Streamlit secrets access failed: {e}")
            self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key not provided. Either pass it to __init__ or set GEMINI_API_KEY environment variable"
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Use Gemini Flash (free tier, very capable)
        self.model = genai.GenerativeModel('gemini-flash-latest')

        # Load Bagacinho training examples
        self.training_examples = self._load_training_data()

        logger.info(f"GeminiAssistant initialized with {len(self.training_examples)} training examples")

    def _load_training_data(self) -> List[Dict]:
        """
        Load Bagacinho training data from JSONL file

        Returns:
            List of training examples
        """
        # Use relative path from this file's location (works on both Windows and Linux)
        training_file = Path(__file__).parent / "data" / "cp2b_biogas_dataset.jsonl"

        if not training_file.exists():
            logger.warning(f"Training data not found at {training_file}")
            return []

        examples = []
        try:
            with open(training_file, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    if 'conversations' in data:
                        examples.append(data['conversations'])

            logger.info(f"Loaded {len(examples)} training examples")
            return examples

        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return []

    def _build_system_prompt(self, db_context: str) -> str:
        """
        Build comprehensive system prompt with training examples

        Args:
            db_context: Current database statistics and information

        Returns:
            System prompt string
        """
        prompt_parts = []

        # Base system identity
        prompt_parts.append("""Você é o Bagacinho 🍊, assistente especializado em análise de potencial de biogás do CP2B Maps (UNICAMP).

SUAS ESPECIALIDADES:
- 📊 Análise de dados MapBIOMAS Coleção 9
- 🗺️ Metodologias MCDA (Multi-Criteria Decision Analysis) para localização de plantas
- ⚡ Cálculos de potencial energético de biogás
- 🏙️ Análise geoespacial dos 645 municípios de São Paulo
- 🌾 Conhecimento em substratos: cana-de-açúcar, soja, milho, resíduos pecuários, RSU

PERSONALIDADE:
- Técnico mas acessível
- Entusiasta de energia renovável
- Prestativo e didático
- Usa emojis ocasionalmente para tornar respostas amigáveis

IMPORTANTE:
- Sempre responda em português brasileiro
- Cite números exatos quando disponíveis no contexto
- Se não souber algo, seja honesto
- Use formatação clara para grandes números (ex: "1,2 milhão de m³/ano")
""")

        # Add training examples as few-shot learning
        if self.training_examples:
            prompt_parts.append("\n## EXEMPLOS DE CONHECIMENTO ESPECIALIZADO:\n")
            prompt_parts.append("Aqui estão exemplos do tipo de conhecimento técnico que você possui:\n")

            for i, example in enumerate(self.training_examples[:3], 1):  # Use first 3 examples
                for conv in example:
                    if conv['from'] == 'human':
                        prompt_parts.append(f"\n**Exemplo {i} - Pergunta:**")
                        prompt_parts.append(conv['value'])
                    elif conv['from'] == 'gpt':
                        prompt_parts.append(f"\n**Exemplo {i} - Resposta:**")
                        prompt_parts.append(conv['value'])

        # Add current database context
        prompt_parts.append("\n\n## CONTEXTO ATUALIZADO DO BANCO DE DADOS CP2B:\n")
        prompt_parts.append(db_context)

        prompt_parts.append("""

## INSTRUÇÕES DE RESPOSTA:
1. Use PRIORITARIAMENTE os dados reais do contexto acima
2. Cite números exatos quando disponíveis
3. Para perguntas técnicas, use seu conhecimento especializado (exemplos acima)
4. Se os dados não tiverem a informação exata, use conhecimento geral mas deixe claro
5. Seja técnico mas acessível - explique termos complexos quando necessário
6. Use formatação markdown para melhor legibilidade (listas, negrito, etc)

Agora responda às perguntas do usuário com precisão, conhecimento técnico e entusiasmo! 🍊
""")

        return "\n".join(prompt_parts)

    def query(
        self,
        question: str,
        db_context: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, bool]:
        """
        Query Gemini with a question

        Args:
            question: User's question
            db_context: Database context string
            conversation_history: Previous messages [{"role": "user"/"assistant", "content": "..."}]

        Returns:
            Tuple of (answer, success)
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(db_context)

            # Build conversation
            messages = []

            # Add system context as first message
            messages.append({
                "role": "user",
                "parts": [system_prompt]
            })
            messages.append({
                "role": "model",
                "parts": ["Entendido! Sou o Bagacinho 🍊, especialista em análise de potencial de biogás do CP2B Maps. Estou pronto para responder suas perguntas com base nos dados atualizados e meu conhecimento técnico em MapBIOMAS, MCDA e cálculos energéticos. Como posso ajudar?"]
            })

            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    messages.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })

            # Add current question
            messages.append({
                "role": "user",
                "parts": [question]
            })

            # Create chat session
            chat = self.model.start_chat(history=messages[:-1])

            # Send message and get response
            response = chat.send_message(question)

            return response.text, True

        except Exception as e:
            error_msg = f"Erro ao consultar Gemini: {str(e)}"
            logger.error(error_msg)
            return error_msg, False

    @staticmethod
    def check_availability() -> Tuple[bool, str]:
        """
        Check if Gemini is available and configured

        Returns:
            Tuple of (is_available, message)
        """
        try:
            logger.info("Checking Gemini availability...")

            if not HAS_GEMINI:
                logger.warning("google-generativeai library not installed")
                return False, "❌ Biblioteca google-generativeai não instalada. Execute: pip install google-generativeai"

            # Try Streamlit secrets first, then environment variable
            api_key = None
            key_source = None

            try:
                import streamlit as st
                logger.info("Checking Streamlit secrets for GEMINI_API_KEY...")

                if "GEMINI_API_KEY" in st.secrets:
                    api_key = st.secrets["GEMINI_API_KEY"]
                    key_source = "Streamlit Secrets"
                    logger.info("✓ API key found in Streamlit secrets")
                else:
                    logger.info("GEMINI_API_KEY not found in Streamlit secrets, checking environment...")
                    api_key = os.getenv("GEMINI_API_KEY")
                    key_source = "Environment Variable" if api_key else None

            except Exception as e:
                logger.warning(f"Failed to access Streamlit secrets: {type(e).__name__}: {e}")
                logger.info("Falling back to environment variable...")
                api_key = os.getenv("GEMINI_API_KEY")
                key_source = "Environment Variable" if api_key else None

            if not api_key:
                logger.error("No API key found in secrets or environment")
                return False, """❌ Chave API do Gemini não configurada.

**Como configurar:**
1. Obtenha sua chave gratuita em: https://makersuite.google.com/app/apikey
2. Configure a variável de ambiente GEMINI_API_KEY
3. Ou adicione no Streamlit Secrets (.streamlit/secrets.toml):
   ```
   GEMINI_API_KEY = "sua-chave-aqui"
   ```
"""

            logger.info(f"✓ API key found via {key_source}")
            logger.info(f"API key length: {len(api_key)} characters")
            logger.info(f"API key starts with: {api_key[:10]}...")

            # Try to actually initialize Gemini to verify it works
            try:
                logger.info("Testing Gemini API initialization...")
                genai.configure(api_key=api_key)
                logger.info("✓ Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {type(e).__name__}: {e}")
                return False, f"❌ Erro ao configurar Gemini API: {str(e)}"

            return True, f"✅ Gemini configurado! Usando modelo gratuito Gemini Flash (fonte: {key_source})"

        except Exception as e:
            logger.error(f"Unexpected error in check_availability: {type(e).__name__}: {e}", exc_info=True)
            return False, f"❌ Erro inesperado ao verificar Gemini: {str(e)}"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def query_gemini(
    question: str,
    db_context: str,
    conversation_history: Optional[List[Dict]] = None,
    api_key: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Convenience function to query Gemini

    Args:
        question: User's question
        db_context: Database context
        conversation_history: Previous messages
        api_key: Optional API key (otherwise uses GEMINI_API_KEY env var)

    Returns:
        Tuple of (answer, success)
    """
    try:
        assistant = GeminiAssistant(api_key=api_key)
        return assistant.query(question, db_context, conversation_history)
    except Exception as e:
        return f"Erro ao inicializar Gemini: {str(e)}", False


def check_gemini_connection() -> Tuple[bool, str]:
    """
    Check if Gemini is available

    Returns:
        Tuple of (is_connected, message)
    """
    return GeminiAssistant.check_availability()
