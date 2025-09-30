"""
Bagacinho RAG - Retrieval Augmented Generation
Conecta o Bagacinho ao banco SQLite do CP2B Maps para respostas contextuais dinâmicas
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class BagacinhoRAG:
    """Sistema RAG para o Bagacinho acessar dados reais do CP2B de forma inteligente"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa conexão com banco de dados SQLite

        Args:
            db_path: Caminho para o arquivo cp2b_maps.db
        """
        if db_path is None:
            # Usar caminho padrão
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "cp2b_maps.db"

        self.db_path = db_path

        if not self.db_path.exists():
            logger.error(f"Banco de dados não encontrado: {self.db_path}")
            raise FileNotFoundError(f"Banco de dados não encontrado: {self.db_path}")

        logger.info(f"BagacinhoRAG inicializado com: {self.db_path}")

    def _get_connection(self):
        """Cria conexão com o banco de dados"""
        return sqlite3.connect(str(self.db_path))

    def buscar_municipio(self, nome: str) -> Optional[Dict]:
        """
        Busca dados completos de um município específico

        Args:
            nome: Nome do município (parcial ou completo)

        Returns:
            Dicionário com dados do município ou None se não encontrado
        """
        try:
            with self._get_connection() as conn:
                query = """
                SELECT
                    nome_municipio,
                    codigo_municipio,
                    cd_mun,
                    area_km2,
                    populacao_2022,
                    total_final_m_ano,
                    total_agricola_m_ano,
                    total_pecuaria_m_ano,
                    total_urbano_m_ano,
                    biogas_cana_m_ano,
                    biogas_soja_m_ano,
                    biogas_milho_m_ano,
                    biogas_citros_m_ano,
                    biogas_cafe_m_ano,
                    biogas_bovinos_m_ano,
                    biogas_suino_m_ano,
                    biogas_aves_m_ano,
                    biogas_piscicultura_m_ano,
                    rsu_potencial_m_ano,
                    rpo_potencial_m_ano,
                    categoria_potencial,
                    densidade_demografica
                FROM municipalities
                WHERE LOWER(nome_municipio) LIKE LOWER(?)
                LIMIT 1
                """

                cursor = conn.cursor()
                cursor.execute(query, (f"%{nome}%",))
                row = cursor.fetchone()

                if row:
                    return {
                        'nome_municipio': row[0],
                        'codigo_municipio': row[1],
                        'cd_mun': row[2],
                        'area_km2': row[3],
                        'populacao_2022': row[4],
                        'total_final_m_ano': row[5],
                        'total_agricola_m_ano': row[6],
                        'total_pecuaria_m_ano': row[7],
                        'total_urbano_m_ano': row[8],
                        'biogas_cana_m_ano': row[9],
                        'biogas_soja_m_ano': row[10],
                        'biogas_milho_m_ano': row[11],
                        'biogas_citros_m_ano': row[12],
                        'biogas_cafe_m_ano': row[13],
                        'biogas_bovinos_m_ano': row[14],
                        'biogas_suino_m_ano': row[15],
                        'biogas_aves_m_ano': row[16],
                        'biogas_piscicultura_m_ano': row[17],
                        'rsu_potencial_m_ano': row[18],
                        'rpo_potencial_m_ano': row[19],
                        'categoria_potencial': row[20],
                        'densidade_demografica': row[21]
                    }
        except Exception as e:
            logger.error(f"Erro ao buscar município '{nome}': {e}")

        return None

    def buscar_top_municipios(self, limite: int = 10, fonte: Optional[str] = None) -> pd.DataFrame:
        """
        Busca top N municípios por potencial total ou por fonte específica

        Args:
            limite: Número de municípios a retornar (default: 10)
            fonte: Fonte específica ("cana", "soja", "bovinos", "suinos", "aves", etc.)

        Returns:
            DataFrame com ranking de municípios
        """
        try:
            # Mapear nome de fonte para coluna do banco
            fonte_coluna_map = {
                "cana": "biogas_cana_m_ano",
                "soja": "biogas_soja_m_ano",
                "milho": "biogas_milho_m_ano",
                "citros": "biogas_citros_m_ano",
                "laranja": "biogas_citros_m_ano",
                "cafe": "biogas_cafe_m_ano",
                "bovinos": "biogas_bovinos_m_ano",
                "gado": "biogas_bovinos_m_ano",
                "suinos": "biogas_suino_m_ano",
                "porco": "biogas_suino_m_ano",
                "aves": "biogas_aves_m_ano",
                "frango": "biogas_aves_m_ano",
                "piscicultura": "biogas_piscicultura_m_ano",
                "agricola": "total_agricola_m_ano",
                "pecuaria": "total_pecuaria_m_ano",
                "urbano": "total_urbano_m_ano"
            }

            if fonte and fonte.lower() in fonte_coluna_map:
                coluna_ordem = fonte_coluna_map[fonte.lower()]
            else:
                coluna_ordem = "total_final_m_ano"

            with self._get_connection() as conn:
                query = f"""
                SELECT
                    nome_municipio,
                    total_final_m_ano,
                    {coluna_ordem} as potencial_fonte,
                    populacao_2022,
                    categoria_potencial
                FROM municipalities
                WHERE {coluna_ordem} IS NOT NULL
                ORDER BY {coluna_ordem} DESC
                LIMIT ?
                """

                return pd.read_sql_query(query, conn, params=(limite,))

        except Exception as e:
            logger.error(f"Erro ao buscar top municípios: {e}")
            return pd.DataFrame()

    def estatisticas_estado(self) -> Dict:
        """
        Retorna estatísticas gerais do Estado de São Paulo

        Returns:
            Dicionário com estatísticas agregadas
        """
        try:
            with self._get_connection() as conn:
                query = """
                SELECT
                    COUNT(*) as total_municipios,
                    SUM(total_final_m_ano) as potencial_total_sp,
                    AVG(total_final_m_ano) as media_municipal,
                    MAX(total_final_m_ano) as maior_potencial,
                    SUM(total_agricola_m_ano) as total_agricola,
                    SUM(total_pecuaria_m_ano) as total_pecuaria,
                    SUM(total_urbano_m_ano) as total_urbano,
                    SUM(biogas_cana_m_ano) as total_cana,
                    SUM(biogas_soja_m_ano) as total_soja,
                    SUM(biogas_bovinos_m_ano) as total_bovinos,
                    SUM(biogas_suino_m_ano) as total_suinos,
                    SUM(biogas_aves_m_ano) as total_aves,
                    SUM(populacao_2022) as populacao_total
                FROM municipalities
                """

                cursor = conn.cursor()
                cursor.execute(query)
                row = cursor.fetchone()

                if row:
                    return {
                        'total_municipios': int(row[0]),
                        'potencial_total_sp': float(row[1] or 0),
                        'media_municipal': float(row[2] or 0),
                        'maior_potencial': float(row[3] or 0),
                        'total_agricola': float(row[4] or 0),
                        'total_pecuaria': float(row[5] or 0),
                        'total_urbano': float(row[6] or 0),
                        'total_cana': float(row[7] or 0),
                        'total_soja': float(row[8] or 0),
                        'total_bovinos': float(row[9] or 0),
                        'total_suinos': float(row[10] or 0),
                        'total_aves': float(row[11] or 0),
                        'populacao_total': int(row[12] or 0)
                    }
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas do estado: {e}")

        return {}

    def comparar_municipios(self, nomes: List[str]) -> pd.DataFrame:
        """
        Compara múltiplos municípios lado a lado

        Args:
            nomes: Lista de nomes de municípios

        Returns:
            DataFrame com comparação
        """
        try:
            with self._get_connection() as conn:
                placeholders = ','.join(['?' for _ in nomes])
                query = f"""
                SELECT
                    nome_municipio,
                    total_final_m_ano,
                    total_agricola_m_ano,
                    total_pecuaria_m_ano,
                    populacao_2022,
                    biogas_cana_m_ano,
                    biogas_bovinos_m_ano
                FROM municipalities
                WHERE nome_municipio IN ({placeholders})
                """

                return pd.read_sql_query(query, conn, params=nomes)

        except Exception as e:
            logger.error(f"Erro ao comparar municípios: {e}")
            return pd.DataFrame()

    def construir_contexto(self, pergunta: str) -> str:
        """
        Analisa a pergunta e constrói contexto RAG com dados relevantes

        Este é o coração do sistema RAG - detecta intenção da pergunta
        e busca apenas os dados necessários do banco.

        Args:
            pergunta: Pergunta do usuário

        Returns:
            Contexto formatado em markdown com dados relevantes
        """
        contexto = "**DADOS REAIS DO BANCO CP2B:**\n\n"
        pergunta_lower = pergunta.lower()

        # Lista de municípios comuns para detecção
        municipios_conhecidos = [
            "barretos", "campinas", "ribeirão preto", "ribeirao preto",
            "são paulo", "sao paulo", "santos", "piracicaba",
            "araraquara", "franca", "presidente prudente",
            "são josé do rio preto", "sao jose do rio preto",
            "sorocaba", "guarulhos", "osasco", "são bernardo",
            "santo andré", "mauá", "diadema", "jundiaí"
        ]

        # ========== DETECÇÃO 1: MUNICÍPIO ESPECÍFICO ==========
        municipio_encontrado = None
        for mun in municipios_conhecidos:
            if mun in pergunta_lower:
                municipio_encontrado = mun
                break

        if municipio_encontrado:
            dados = self.buscar_municipio(municipio_encontrado)
            if dados:
                contexto += f"""### Municipio: {dados['nome_municipio']}

**Informações Gerais:**
- **Código IBGE:** {dados['cd_mun']}
- **População (2022):** {int(dados['populacao_2022']):,} habitantes
- **Área:** {dados['area_km2']:.2f} km²
- **Densidade Demográfica:** {dados['densidade_demografica']:.2f} hab/km²
- **Categoria:** {dados['categoria_potencial']}

**Potencial de Biogas:**
- **TOTAL:** {dados['total_final_m_ano']:,.0f} Nm3/ano

**Breakdown por Categoria:**
- Agricola: {dados['total_agricola_m_ano']:,.0f} Nm3/ano ({dados['total_agricola_m_ano']/dados['total_final_m_ano']*100:.1f}%)
- Pecuaria: {dados['total_pecuaria_m_ano']:,.0f} Nm3/ano ({dados['total_pecuaria_m_ano']/dados['total_final_m_ano']*100:.1f}%)
- Urbano: {dados['total_urbano_m_ano']:,.0f} Nm3/ano ({dados['total_urbano_m_ano']/dados['total_final_m_ano']*100:.1f}%)

**Breakdown por Fonte (Detalhado):**
- Cana-de-acucar: {dados['biogas_cana_m_ano']:,.0f} Nm3/ano
- Soja: {dados['biogas_soja_m_ano']:,.0f} Nm3/ano
- Milho: {dados['biogas_milho_m_ano']:,.0f} Nm3/ano
- Citros (Laranja): {dados['biogas_citros_m_ano']:,.0f} Nm3/ano
- Cafe: {dados['biogas_cafe_m_ano']:,.0f} Nm3/ano
- Bovinos: {dados['biogas_bovinos_m_ano']:,.0f} Nm3/ano
- Suinos: {dados['biogas_suino_m_ano']:,.0f} Nm3/ano
- Aves: {dados['biogas_aves_m_ano']:,.0f} Nm3/ano
- Piscicultura: {dados['biogas_piscicultura_m_ano']:,.0f} Nm3/ano
- RSU (Residuos Urbanos): {dados['rsu_potencial_m_ano']:,.0f} Nm3/ano
- RPO (Poda): {dados['rpo_potencial_m_ano']:,.0f} Nm3/ano

"""
                return contexto

        # ========== DETECÇÃO 2: TOP / RANKING ==========
        if any(word in pergunta_lower for word in ["top", "maiores", "ranking", "melhores", "principais"]):

            # Detectar fonte específica
            fonte = None
            if "cana" in pergunta_lower or "açúcar" in pergunta_lower:
                fonte = "cana"
            elif "laranja" in pergunta_lower or "citros" in pergunta_lower or "citrus" in pergunta_lower:
                fonte = "citros"
            elif "bovino" in pergunta_lower or "gado" in pergunta_lower or "boi" in pergunta_lower:
                fonte = "bovinos"
            elif "suíno" in pergunta_lower or "porco" in pergunta_lower:
                fonte = "suinos"
            elif "ave" in pergunta_lower or "frango" in pergunta_lower or "galinha" in pergunta_lower:
                fonte = "aves"
            elif "soja" in pergunta_lower:
                fonte = "soja"
            elif "milho" in pergunta_lower:
                fonte = "milho"
            elif "agrícola" in pergunta_lower or "agricola" in pergunta_lower:
                fonte = "agricola"
            elif "pecuár" in pergunta_lower or "pecuar" in pergunta_lower:
                fonte = "pecuaria"
            elif "urbano" in pergunta_lower:
                fonte = "urbano"

            # Detectar número (top 5, top 10, etc)
            limite = 10  # default
            import re
            numeros = re.findall(r'\b(\d+)\b', pergunta_lower)
            if numeros:
                limite = min(int(numeros[0]), 20)  # Max 20

            top_df = self.buscar_top_municipios(limite, fonte)

            if not top_df.empty:
                if fonte:
                    contexto += f"### Top {limite} Municipios - Fonte: {fonte.title()}\n\n"
                else:
                    contexto += f"### Top {limite} Municipios - Potencial Total\n\n"

                for idx, row in top_df.iterrows():
                    contexto += f"{idx+1}. **{row['nome_municipio']}**: {row['total_final_m_ano']:,.0f} Nm3/ano"
                    if fonte:
                        contexto += f" (Fonte especifica: {row['potencial_fonte']:,.0f} Nm3/ano)"
                    contexto += f" - Pop: {int(row['populacao_2022']):,}\n"

                contexto += "\n"
                return contexto

        # ========== DETECÇÃO 3: COMPARAÇÃO ==========
        if any(word in pergunta_lower for word in ["comparar", "compare", "diferença", "vs", "versus"]):
            # Tentar extrair múltiplos municípios
            municipios_para_comparar = []
            for mun in municipios_conhecidos:
                if mun in pergunta_lower:
                    municipios_para_comparar.append(mun.title())

            if len(municipios_para_comparar) >= 2:
                comp_df = self.comparar_municipios(municipios_para_comparar)
                if not comp_df.empty:
                    contexto += "### Comparacao entre Municipios\n\n"
                    for _, row in comp_df.iterrows():
                        contexto += f"""**{row['nome_municipio']}:**
- Total: {row['total_final_m_ano']:,.0f} Nm3/ano
- Agricola: {row['total_agricola_m_ano']:,.0f} Nm3/ano
- Pecuaria: {row['total_pecuaria_m_ano']:,.0f} Nm3/ano
- Populacao: {int(row['populacao_2022']):,}
- Principal fonte: Cana ({row['biogas_cana_m_ano']:,.0f}) | Bovinos ({row['biogas_bovinos_m_ano']:,.0f})

"""
                    return contexto

        # ========== DETECÇÃO 4: ESTADO / GERAL ==========
        if any(word in pergunta_lower for word in ["estado", "são paulo", "sao paulo", "total", "sp", "estadual", "geral"]):
            stats = self.estatisticas_estado()

            if stats:
                contexto += f"""### Estado de Sao Paulo - Panorama Completo

**Dados Gerais:**
- **Total de Municipios:** {stats['total_municipios']}
- **Populacao Total:** {stats['populacao_total']:,} habitantes
- **Potencial Total SP:** {stats['potencial_total_sp']:,.0f} Nm3/ano
- **Media Municipal:** {stats['media_municipal']:,.0f} Nm3/ano
- **Maior Potencial Municipal:** {stats['maior_potencial']:,.0f} Nm3/ano

**Distribuicao por Categoria:**
- Agricola: {stats['total_agricola']:,.0f} Nm3/ano ({stats['total_agricola']/stats['potencial_total_sp']*100:.1f}%)
- Pecuaria: {stats['total_pecuaria']:,.0f} Nm3/ano ({stats['total_pecuaria']/stats['potencial_total_sp']*100:.1f}%)
- Urbano: {stats['total_urbano']:,.0f} Nm3/ano ({stats['total_urbano']/stats['potencial_total_sp']*100:.1f}%)

**Distribuicao por Fonte Principal:**
- Cana-de-acucar: {stats['total_cana']:,.0f} Nm3/ano ({stats['total_cana']/stats['potencial_total_sp']*100:.1f}%)
- Soja: {stats['total_soja']:,.0f} Nm3/ano ({stats['total_soja']/stats['potencial_total_sp']*100:.1f}%)
- Bovinos: {stats['total_bovinos']:,.0f} Nm3/ano ({stats['total_bovinos']/stats['potencial_total_sp']*100:.1f}%)
- Suinos: {stats['total_suinos']:,.0f} Nm3/ano ({stats['total_suinos']/stats['potencial_total_sp']*100:.1f}%)
- Aves: {stats['total_aves']:,.0f} Nm3/ano ({stats['total_aves']/stats['potencial_total_sp']*100:.1f}%)

"""
                return contexto

        # ========== FALLBACK: CONTEXTO GENERICO ==========
        # Se nao detectou padrao especifico, retorna overview simples
        stats = self.estatisticas_estado()
        if stats:
            contexto += f"""### Contexto Geral do Sistema

O CP2B Maps analisa o potencial de biogas de **{stats['total_municipios']} municipios** em Sao Paulo.

**Potencial Total do Estado:** {stats['potencial_total_sp']:,.0f} Nm3/ano

**Principais fontes:**
- Cana-de-acucar ({stats['total_cana']/stats['potencial_total_sp']*100:.1f}%)
- Pecuaria bovina ({stats['total_bovinos']/stats['potencial_total_sp']*100:.1f}%)
- Outras fontes agricolas e urbanas

"""

        return contexto

    @st.cache_data(ttl=3600)
    def buscar_municipio_cached(_self, nome: str):
        """Versão com cache para Streamlit (evita buscas repetidas)"""
        return _self.buscar_municipio(nome)

    @st.cache_data(ttl=3600)
    def estatisticas_estado_cached(_self):
        """Versão com cache para Streamlit"""
        return _self.estatisticas_estado()
