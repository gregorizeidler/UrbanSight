import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
# import openai
from agents.osm_data_collector import PropertyData, POI
from agents.neighborhood_analyst import NeighborhoodMetrics
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PropertyInsight:
    """Complete property analysis insight"""
    executive_summary: str
    neighborhood_description: str
    strengths: List[str]
    concerns: List[str]
    recommendations: List[str]
    ideal_resident_profile: str
    market_positioning: str
    investment_potential: str


class InsightGenerator:
    """Agent specialized in generating human-readable insights using LLM"""

    def __init__(self):
        self.config = Config()
        # openai.api_key = self.config.OPENAI_API_KEY
        # self.client = openai.OpenAI()

    def _format_pois_for_llm(self, pois: List[POI], limit: int = 20) -> str:
        """Format POIs data for LLM consumption"""
        # Group by category and get closest ones
        pois_by_category = {}
        for poi in pois:
            if poi.category not in pois_by_category:
                pois_by_category[poi.category] = []
            pois_by_category[poi.category].append(poi)

        # Sort by distance and take closest ones
        formatted_pois = []
        for category, category_pois in pois_by_category.items():
            closest_pois = sorted(category_pois, key=lambda p: p.distance)[:5]
            formatted_pois.extend([
                f"- {poi.name} ({poi.subcategory}) - {poi.distance:.0f}m"
                for poi in closest_pois
            ])

        return "\n".join(formatted_pois[:limit])

    def _create_analysis_prompt(
        self, property_data: PropertyData, metrics: NeighborhoodMetrics,
        pois: List[POI]
    ) -> str:
        """Create comprehensive prompt for LLM analysis"""

        pois_text = self._format_pois_for_llm(pois)

        prompt = f"""
Você é um especialista em análise imobiliária e PropTech. Analise os dados abaixo e gere insights profundos sobre esta propriedade:

DADOS DA PROPRIEDADE:
- Endereço: {property_data.address}
- Cidade: {property_data.city}, {property_data.state}
- Coordenadas: {property_data.lat:.6f}, {property_data.lon:.6f}

MÉTRICAS DE ANÁLISE:
- Walk Score: {metrics.walk_score.overall_score:.1f}/100 (Nota: {metrics.walk_score.grade})
- Score de Acessibilidade: {metrics.accessibility_score:.1f}/100
- Score de Conveniência: {metrics.convenience_score:.1f}/100
- Score de Segurança: {metrics.safety_score:.1f}/100
- Score de Qualidade de Vida: {metrics.quality_of_life_score:.1f}/100
- Score Total: {metrics.total_score:.1f}/100

PONTOS DE INTERESSE PRÓXIMOS:
{pois_text}

CONTAGEM POR CATEGORIA:
{json.dumps(metrics.category_counts, indent=2)}

DENSIDADE DE POIs (por km²):
{json.dumps({k: f"{v:.1f}" for k, v in metrics.poi_density.items()}, indent=2)}

INSTRUÇÕES:
1. Crie uma análise completa e profissional
2. Use linguagem acessível mas técnica
3. Seja específico sobre distâncias e quantidades
4. Identifique o público-alvo ideal
5. Sugira estratégias de marketing
6. Avalie potencial de investimento
7. Mantenha tom profissional mas humano

Formate sua resposta como JSON com as seguintes chaves:
- executive_summary: Resumo executivo (2-3 parágrafos)
- neighborhood_description: Descrição detalhada da vizinhança
- strengths: Lista de pontos fortes
- concerns: Lista de pontos de atenção
- recommendations: Lista de recomendações
- ideal_resident_profile: Perfil do morador ideal
- market_positioning: Posicionamento no mercado
- investment_potential: Análise do potencial de investimento
"""
        return prompt

    async def generate_insights(
        self, property_data: PropertyData, metrics: NeighborhoodMetrics,
        pois: List[POI]
    ) -> PropertyInsight:
        """Generate comprehensive property insights using LLM"""

        logger.info(f"Generating insights for {property_data.address}")

        try:
            # prompt = self._create_analysis_prompt(property_data, metrics, pois)

            # response = self.client.chat.completions.create(
            #     model="gpt-4-turbo-preview",
            #     messages=[
            #         {
            #             "role": "system",
            #             "content": "Você é um especialista em análise imobiliária e PropTech. Sempre responda em português brasileiro com análises profundas e insights valiosos."
            #         },
            #         {
            #             "role": "user",
            #             "content": prompt
            #         }
            #     ],
            #     temperature=0.7,
            #     max_tokens=2000
            # )

            # # Parse JSON response
            # content = response.choices[0].message.content

            # # Clean up the response to extract JSON
            # if "```json" in content:
            #     content = content.split("```json")[1].split("```")[0]
            # elif "```" in content:
            #     content = content.split("```")[1].split("```")[0]

            # try:
            #     insights_data = json.loads(content)
            # except json.JSONDecodeError:
            #     # Fallback: create structured response manually
            insights_data = self._create_fallback_insights(property_data, metrics, pois)

            return PropertyInsight(**insights_data)

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            fallback_data = self._create_fallback_insights(property_data, metrics, pois)
            return PropertyInsight(**fallback_data)

    def _create_fallback_insights(
        self, property_data: PropertyData, metrics: NeighborhoodMetrics,
        pois: List[POI]
    ) -> Dict:
        """Create fallback insights if LLM fails"""

        # Basic analysis based on metrics
        grade_description = {
            "A+": "excepcional",
            "A": "excelente",
            "B": "boa",
            "C": "regular",
            "D": "limitada",
            "F": "deficiente"
        }

        walkability = grade_description.get(metrics.walk_score.grade, "regular")

        return {
            "executive_summary": f"Propriedade localizada em {property_data.city} com caminhabilidade {walkability} (Walk Score: {metrics.walk_score.overall_score:.1f}). A localização oferece acesso a {len(pois)} pontos de interesse em um raio de 1km, com score total de {metrics.total_score:.1f}/100.",

            "neighborhood_description": f"A vizinhança apresenta uma densidade variada de serviços e comodidades. Com {metrics.category_counts.get('food', 0)} estabelecimentos alimentícios, {metrics.category_counts.get('shopping', 0)} opções de compras e {metrics.category_counts.get('transport', 0)} pontos de transporte público, a área oferece uma infraestrutura {walkability} para as necessidades diárias.",

            "strengths": [
                f"Walk Score de {metrics.walk_score.overall_score:.1f} pontos",
                f"Score de acessibilidade: {metrics.accessibility_score:.1f}/100",
                f"Score de conveniência: {metrics.convenience_score:.1f}/100"
            ],

            "concerns": [
                "Análise detalhada requer avaliação manual",
                "Dados podem variar conforme atualizações do OpenStreetMap"
            ],

            "recommendations": [
                "Validar informações com visita local",
                "Considerar tendências de desenvolvimento da região",
                "Avaliar potencial de valorização futura"
            ],

            "ideal_resident_profile": f"Adequado para pessoas que valorizam {'conveniência urbana' if metrics.total_score > 70 else 'tranquilidade residencial'}",

            "market_positioning": f"Posicionamento {'premium' if metrics.total_score > 80 else 'intermediário' if metrics.total_score > 60 else 'econômico'} no mercado local",

            "investment_potential": f"Potencial de investimento {'alto' if metrics.total_score > 75 else 'médio' if metrics.total_score > 50 else 'conservador'} baseado nas métricas de localização"
        }

    def create_marketing_copy(self, property_data: PropertyData, insights: PropertyInsight) -> str:
        """Generate marketing copy for the property"""

        try:
            # prompt = f"""
# Crie um texto de marketing atrativo para esta propriedade:

# ENDEREÇO: {property_data.address}
# CIDADE: {property_data.city}, {property_data.state}

# INSIGHTS DA PROPRIEDADE:
# {insights.executive_summary}

# PONTOS FORTES:
# {chr(10).join(f'• {strength}' for strength in insights.strengths)}

# PERFIL IDEAL:
# {insights.ideal_resident_profile}

# INSTRUÇÕES:
# 1. Crie um texto de marketing de 2-3 parágrafos
# 2. Use linguagem persuasiva mas honesta
# 3. Destaque os principais benefícios da localização
# 4. Inclua call-to-action sutil
# 5. Mantenha tom profissional e atrativo

# Foque na experiência de vida que a localização proporciona.
# """

            # response = self.client.chat.completions.create(
            #     model="gpt-4-turbo-preview",
            #     messages=[
            #         {
            #             "role": "system",
            #             "content": "Você é um especialista em marketing imobiliário. Crie textos persuasivos e atrativos."
            #         },
            #         {
            #             "role": "user",
            #             "content": prompt
            #         }
            #     ],
            #     temperature=0.8,
            #     max_tokens=500
            # )

            # return response.choices[0].message.content
            return f"Excelente oportunidade em {property_data.city}! {insights.executive_summary}"

        except Exception as e:
            logger.error(f"Error generating marketing copy: {str(e)}")
            return f"Excelente oportunidade em {property_data.city}! {insights.executive_summary}" 