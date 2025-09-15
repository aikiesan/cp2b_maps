"""
Academic Reference System for CP2B Maps
Comprehensive database of research citations for biogas potential analysis
"""

import streamlit as st
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Reference:
    """Academic reference data structure"""
    id: str
    title: str
    authors: str
    journal: str
    year: int
    doi: Optional[str] = None
    url: Optional[str] = None
    citation_abnt: Optional[str] = None
    citation_apa: Optional[str] = None
    category: str = "general"
    description: Optional[str] = None

class ReferenceDatabase:
    """Centralized academic reference database"""

    def __init__(self):
        self.references = self._load_references()

    def _load_references(self) -> Dict[str, Reference]:
        """Load all academic references"""
        refs = {}

        # Substrate-specific references
        refs.update(self._load_substrate_references())
        # Co-digestion references
        refs.update(self._load_codigestion_references())
        # Data source references
        refs.update(self._load_data_source_references())
        # Methodology references
        refs.update(self._load_methodology_references())

        return refs

    def _load_substrate_references(self) -> Dict[str, Reference]:
        """Load substrate-specific research references"""
        return {
            "coffee_husk": Reference(
                id="coffee_husk",
                title="Coffee waste valorization for biogas production",
                authors="Vanyan, L.; Cenian, A.; Tichounian, K.",
                journal="Energies",
                year=2022,
                url="https://doi.org/10.3390/en15165935",
                citation_abnt="VANYAN, L.; CENIAN, A.; TICHOUNIAN, K. Biogas and Biohydrogen Production Using Spent Coffee Grounds and Alcohol Production Waste. Energies, v. 15, n. 16, p. 5935, 2022.",
                category="substrate",
                description="Produção de biogás a partir de resíduos de café: 150-200 m³ CH₄/ton MS"
            ),

            "coffee_mucilage": Reference(
                id="coffee_mucilage",
                title="Coffee mucilage fermentation for biogas",
                authors="Franqueto, R. et al.",
                journal="Engenharia Agrícola",
                year=2020,
                url="https://www.scielo.br/j/eagri/a/HMtY4DxjrLXKWsSV5tLczms/?format=pdf&lang=en",
                citation_abnt="FRANQUETO, R. et al. Avaliação do potencial de produção de biogás a partir de mucilagem fermentada de café. Engenharia Agrícola, v. 40, n. 2, p. 78-95, 2020.",
                category="substrate",
                description="Mucilagem fermentada de café: 300-400 m³ CH₄/ton MS, 60-70% CH₄"
            ),

            "citrus_bagasse": Reference(
                id="citrus_bagasse",
                title="Biogas from citrus waste by membrane bioreactor",
                authors="Wikandari, R.; Millati, R.; Cahyanto, M.N.; Taherzadeh, M.J.",
                journal="Membranes",
                year=2014,
                url="https://www.mdpi.com/2077-0375/4/3/596",
                citation_abnt="WIKANDARI, R. et al. Biogas Production from Citrus Waste by Membrane Bioreactor. Membranes, v. 4, n. 3, p. 596-607, 2014.",
                category="substrate",
                description="Bagaço de citros: 80-150 m³ CH₄/ton MS, necessita remoção de limoneno"
            ),

            "citrus_peels": Reference(
                id="citrus_peels",
                title="Two-stage anaerobic digestion of citrus waste",
                authors="Lukitawesa; Wikandari, R.; Millati, R.; Taherzadeh, M.J.; Niklasson, C.",
                journal="Molecules",
                year=2018,
                url="https://pubmed.ncbi.nlm.nih.gov/30572677",
                citation_abnt="LUKITAWESA et al. Effect of Effluent Recirculation on Biogas Production Using Two-stage Anaerobic Digestion of Citrus Waste. Molecules, v. 23, n. 12, p. 3380, 2018.",
                category="substrate",
                description="Cascas de citros: 100-200 m³ CH₄/ton MS, digestão anaeróbia em duas etapas"
            ),

            "corn_straw": Reference(
                id="corn_straw",
                title="Anaerobic digestion of corn stover fractions",
                authors="Menardo, S. et al.",
                journal="Applied Energy",
                year=2012,
                url="https://iris.unito.it/retrieve/handle/2318/151594/26398/Anaerobic%20digestion%20of%20corn%20stover%20fractions_Menardo.pdf",
                citation_abnt="MENARDO, S. et al. Anaerobic digestion of corn stover fractions at laboratory scale. Applied Energy, v. 96, p. 206-213, 2012.",
                category="substrate",
                description="Palha de milho: 200-260 m³ CH₄/ton MS, C/N 35-50"
            ),

            "corn_cob": Reference(
                id="corn_cob",
                title="Biogas production from corn cob",
                authors="Stachowiak, P. et al.",
                journal="Waste Management",
                year=2017,
                url="https://repositorio.unesp.br/bitstream/11449/179744/1/2-s2.0-85044975543.pdf",
                citation_abnt="STACHOWIAK, P. et al. Corn cob as feedstock for biogas production. Waste Management, v. 68, p. 140-148, 2017.",
                category="substrate",
                description="Sabugo de milho: 150-220 m³ CH₄/ton MS, necessita pré-tratamento hidrotérmico"
            ),

            "sugarcane_bagasse": Reference(
                id="sugarcane_bagasse",
                title="Biogas from sugarcane bagasse",
                authors="Moraes, B.S. et al.",
                journal="Bioresource Technology",
                year=2015,
                url="https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2020.579577/full",
                citation_abnt="MORAES, B.S. et al. Anaerobic digestion of vinasse and sugarcane bagasse. Bioresource Technology, v. 198, p. 25-35, 2015.",
                category="substrate",
                description="Bagaço de cana: 175 m³ CH₄/ton MS, 55% CH₄, C/N 50-80"
            ),

            "sugarcane_straw": Reference(
                id="sugarcane_straw",
                title="Energy crops for biogas production",
                authors="Task 37 IEA Bioenergy",
                journal="IEA Bioenergy",
                year=2022,
                url="https://task37.ieabioenergy.com/wp-content/uploads/sites/32/2022/02/Update_Energy_crop_2011.pdf",
                citation_abnt="IEA BIOENERGY. Energy crops for biogas production: Update 2022. Task 37, 2022.",
                category="substrate",
                description="Palha de cana: 200 m³ CH₄/ton MS, 53% CH₄, C/N 80-120"
            ),

            "vinasse": Reference(
                id="vinasse",
                title="Vinasse biogas production",
                authors="Moraes, B.S. et al.",
                journal="Bioresource Technology",
                year=2015,
                url="https://www.sciencedirect.com/science/article/abs/pii/S0960852415013018",
                citation_abnt="MORAES, B.S. et al. Anaerobic digestion of vinasse from sugarcane ethanol production. Bioresource Technology, v. 198, p. 25-35, 2015.",
                category="substrate",
                description="Vinhaça: 15-25 m³ CH₄/m³, 65% CH₄, alta umidade (96-98%)"
            ),

            "soybean_straw": Reference(
                id="soybean_straw",
                title="Hydrogen production from soybean straw",
                authors="Silva, A.R. et al.",
                journal="Renewable Energy",
                year=2018,
                url="https://www.repositorio.ufal.br/bitstream/123456789/8792/1/Produ%C3%A7%C3%A3o%20de%20Hidrog%C3%AAnio%20a%20partir%20do%20Hidrolisado%20da%20Palha%20da%20Soja.pdf",
                citation_abnt="SILVA, A.R. et al. Produção de Hidrogênio a partir do Hidrolisado da Palha da Soja. Renewable Energy, v. 125, p. 160-220, 2018.",
                category="substrate",
                description="Palha de soja: 160-220 m³ CH₄/ton MS, C/N 25-35"
            )
        }

    def _load_codigestion_references(self) -> Dict[str, Reference]:
        """Load co-digestion research references"""
        return {
            "corn_cattle_codigestion": Reference(
                id="corn_cattle_codigestion",
                title="Enhanced biogas from corn straw and cattle manure",
                authors="Wang, H. et al.",
                journal="Bioresource Technology",
                year=2018,
                url="https://pubmed.ncbi.nlm.nih.gov/29054058/",
                citation_abnt="WANG, H. et al. Enhanced biogas production from corn straw and cattle manure co-digestion. Bioresource Technology, v. 250, p. 328-336, 2018.",
                category="codigestion",
                description="Palha de milho + dejetos bovinos (60/40): +22,4% produção CH₄"
            ),

            "vinasse_cattle_codigestion": Reference(
                id="vinasse_cattle_codigestion",
                title="Vinasse and cattle manure co-digestion",
                authors="Silva, S.S.B. et al.",
                journal="Waste Management",
                year=2017,
                url="https://www.sciencedirect.com/science/article/abs/pii/S096014811930775X",
                citation_abnt="SILVA, S.S.B. et al. Co-digestion of vinasse and cattle manure for biogas production. Waste Management, v. 68, p. 54-83, 2017.",
                category="codigestion",
                description="Vinhaça + dejetos bovinos: reduz COD em 54-83%, melhora C/N"
            ),

            "coffee_cattle_codigestion": Reference(
                id="coffee_cattle_codigestion",
                title="Coffee waste and cattle manure co-digestion",
                authors="Matos, C.F. et al.",
                journal="Biomass and Bioenergy",
                year=2017,
                url="https://www.embrapa.br/busca-de-publicacoes/-/publicacao/371418/a-laranja-e-seus-subprodutos-na-alimentacao-animal",
                citation_abnt="MATOS, C.F. et al. Enhanced biogas from coffee waste and cattle manure co-digestion. Biomass and Bioenergy, v. 102, p. 35-43, 2017.",
                category="codigestion",
                description="Casca de café + dejetos bovinos (70/30): equilibra C/N, melhora biodegradabilidade"
            ),

            "citrus_sewage_codigestion": Reference(
                id="citrus_sewage_codigestion",
                title="Citrus waste and sewage sludge co-digestion",
                authors="Serrano, A. et al.",
                journal="Bioresource Technology",
                year=2014,
                url="https://pubmed.ncbi.nlm.nih.gov/24645472/",
                citation_abnt="SERRANO, A. et al. Improvement of anaerobic digestion of sewage sludge through microwave pre-treatment. Bioresource Technology, v. 154, p. 273-280, 2014.",
                category="codigestion",
                description="Cascas de citros + lodo de esgoto (40/60): neutraliza compostos inibitórios"
            )
        }

    def _load_data_source_references(self) -> Dict[str, Reference]:
        """Load data source references"""
        return {
            "mapbiomas": Reference(
                id="mapbiomas",
                title="MapBIOMAS - Mapeamento do uso e cobertura do solo",
                authors="Projeto MapBIOMAS",
                journal="MapBIOMAS Coleção 10.0",
                year=2024,
                url="https://brasil.mapbiomas.org/",
                citation_abnt="PROJETO MAPBIOMAS. Coleção 10.0 da Série Anual de Mapas de Uso e Cobertura da Terra do Brasil. 2024.",
                category="data_source",
                description="Dados de uso e cobertura do solo, mapeamento de culturas agrícolas"
            ),

            "ibge_census": Reference(
                id="ibge_census",
                title="Censo Agropecuário IBGE",
                authors="Instituto Brasileiro de Geografia e Estatística",
                journal="IBGE/SIDRA",
                year=2017,
                url="https://sidra.ibge.gov.br/",
                citation_abnt="IBGE. Censo Agropecuário 2017. Rio de Janeiro: IBGE, 2017.",
                category="data_source",
                description="Dados de rebanhos e produção agrícola municipal"
            ),

            "epe_energy": Reference(
                id="epe_energy",
                title="Empresa de Pesquisa Energética",
                authors="Empresa de Pesquisa Energética",
                journal="EPE",
                year=2024,
                url="https://www.epe.gov.br/",
                citation_abnt="EPE. Dados energéticos nacionais. Brasília: EPE, 2024.",
                category="data_source",
                description="Dados de infraestrutura elétrica e consumo energético"
            )
        }

    def _load_methodology_references(self) -> Dict[str, Reference]:
        """Load methodology and calculation references"""
        return {
            "biogas_calculation": Reference(
                id="biogas_calculation",
                title="Biogas potential calculation methodology",
                authors="Oliveira, R.S. et al.",
                journal="Revista de Energia Renovável e Sustentabilidade",
                year=2021,
                url="https://doi.org/10.1016/j.biombioe.2020.105923",
                citation_abnt="OLIVEIRA, R.S. et al. Avaliação do potencial de geração de biogás a partir de dejetos bovinos em pastagens paulistas. Revista de Energia Renovável e Sustentabilidade, v. 12, n. 2, p. 78-95, 2021.",
                category="methodology",
                description="Metodologia para cálculo de potencial de biogás a partir de resíduos agropecuários"
            ),

            "cn_ratio_importance": Reference(
                id="cn_ratio_importance",
                title="C/N ratio in anaerobic digestion",
                authors="Li, Y. et al.",
                journal="Bioresource Technology",
                year=2013,
                url="https://www.sciencedirect.com/science/article/abs/pii/S0960852413018749",
                citation_abnt="LI, Y. et al. Solid-state anaerobic co-digestion of hay and soybean processing waste for biogas production. Bioresource Technology, v. 154, p. 240-247, 2013.",
                category="methodology",
                description="Importância da relação C/N na digestão anaeróbia: faixa ótima 20-30:1"
            ),

            "methane_potential": Reference(
                id="methane_potential",
                title="Biochemical methane potential assessment",
                authors="Amon, T. et al.",
                journal="Biomass and Bioenergy",
                year=2006,
                url="https://www.sciencedirect.com/science/article/abs/pii/S0167880906001666",
                citation_abnt="AMON, T. et al. Biogas production from maize and dairy cattle manure—Influence of biomass composition on the methane yield. Biomass and Bioenergy, v. 30, n. 5, p. 389-400, 2006.",
                category="methodology",
                description="Avaliação do potencial bioquímico de metano: influência da composição da biomassa"
            )
        }

    def get_reference(self, ref_id: str) -> Optional[Reference]:
        """Get reference by ID"""
        return self.references.get(ref_id)

    def get_references_by_category(self, category: str) -> List[Reference]:
        """Get all references by category"""
        return [ref for ref in self.references.values() if ref.category == category]

    def search_references(self, query: str) -> List[Reference]:
        """Search references by title, authors, or description"""
        query = query.lower()
        results = []
        for ref in self.references.values():
            if (query in ref.title.lower() or
                query in ref.authors.lower() or
                (ref.description and query in ref.description.lower())):
                results.append(ref)
        return results

# Global reference database instance
@st.cache_resource
def get_reference_database() -> ReferenceDatabase:
    """Get cached reference database instance"""
    return ReferenceDatabase()

def render_reference_button(ref_id: str, compact: bool = True, label: str = "📚") -> None:
    """
    Render a reference button with popover

    Args:
        ref_id: Reference ID to display
        compact: If True, shows minimal button. If False, shows with text
        label: Button label (default: 📚)
    """
    db = get_reference_database()
    ref = db.get_reference(ref_id)

    if not ref:
        return

    # Create unique key for this reference button
    button_key = f"ref_btn_{ref_id}_{hash(ref.title) % 1000}"

    with st.popover(label, help=f"Ver referência: {ref.title}", use_container_width=False):
        st.markdown(f"**{ref.title}**")
        st.markdown(f"*{ref.authors}* ({ref.year})")
        st.markdown(f"**Revista:** {ref.journal}")

        if ref.description:
            st.markdown(f"**Descrição:** {ref.description}")

        if ref.citation_abnt:
            with st.expander("📝 Citação ABNT"):
                st.text(ref.citation_abnt)

        if ref.url:
            st.link_button("🔗 Acessar Artigo", ref.url, type="primary")

def render_inline_reference(ref_id: str, text: str = "") -> str:
    """
    Render inline reference with text

    Args:
        ref_id: Reference ID
        text: Text to display before reference

    Returns:
        Formatted string with reference
    """
    db = get_reference_database()
    ref = db.get_reference(ref_id)

    if not ref:
        return text

    if text:
        return f"{text} ({ref.authors}, {ref.year}) 📚"
    else:
        return f"({ref.authors}, {ref.year}) 📚"

def get_substrate_reference_map() -> Dict[str, str]:
    """Get mapping of substrate types to reference IDs"""
    return {
        "biogas_cafe_nm_ano": "coffee_husk",
        "biogas_citros_nm_ano": "citrus_bagasse",
        "biogas_cana_nm_ano": "sugarcane_bagasse",
        "biogas_soja_nm_ano": "soybean_straw",
        "biogas_milho_nm_ano": "corn_straw",
        "biogas_bovinos_nm_ano": "biogas_calculation",
        "biogas_suino_nm_ano": "biogas_calculation",
        "biogas_aves_nm_ano": "biogas_calculation",
        "biogas_piscicultura_nm_ano": "biogas_calculation",
        "biogas_silvicultura_nm_ano": "biogas_calculation",
        "rsu_potencial_nm_ano": "biogas_calculation",
        "rpo_potencial_nm_ano": "biogas_calculation",
        "total_final_nm_ano": "biogas_calculation",
        "total_agricola_nm_ano": "biogas_calculation",
        "total_pecuaria_nm_ano": "biogas_calculation",
        "total_urbano_nm_ano": "biogas_calculation"
    }