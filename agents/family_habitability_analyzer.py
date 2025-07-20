"""
Family Habitability Analyzer
Análise de habitabilidade específica para diferentes tipos de família
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import json
from agents.utils import get_poi_category, get_poi_name, get_poi_subcategory

logger = logging.getLogger(__name__)

@dataclass
class ChildrenMetrics:
    schools_nearby: int
    schools_quality_score: float  # 0-100
    playgrounds_count: int
    pediatric_services: int
    child_safety_score: float  # 0-100
    educational_opportunities: List[str]

@dataclass
class ElderlyMetrics:
    healthcare_accessibility: float  # 0-100
    pharmacy_proximity: float  # 0-100
    senior_services: int
    accessibility_infrastructure: float  # 0-100
    public_transport_elderly_friendly: float  # 0-100

@dataclass
class PetFriendlyMetrics:
    veterinary_services: int
    pet_parks_count: int
    pet_stores_nearby: int
    pet_friendly_establishments: int
    pet_walking_areas_score: float  # 0-100

@dataclass
class FamilyTypeAnalysis:
    family_type: str
    suitability_score: float  # 0-100
    key_advantages: List[str]
    potential_concerns: List[str]
    recommendations: List[str]

@dataclass
class FamilyHabitabilityResult:
    children_metrics: ChildrenMetrics
    elderly_metrics: ElderlyMetrics
    pet_friendly_metrics: PetFriendlyMetrics
    family_analyses: List[FamilyTypeAnalysis]
    overall_family_score: float
    ai_family_insights: str
    success: bool
    error_message: Optional[str] = None

class FamilyHabitabilityAnalyzer:
    """Analisador especializado em habitabilidade familiar"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def analyze_family_habitability(self, 
                                        address: str,
                                        property_data: Any,
                                        pois: List[Dict],
                                        metrics: Any) -> FamilyHabitabilityResult:
        """Analisa habitabilidade para diferentes tipos de família"""
        
        try:
            logger.info(f"Analisando habitabilidade familiar para {address}")
            
            # Métricas para crianças
            children_metrics = self._analyze_children_suitability(pois, metrics)
            
            # Métricas para idosos
            elderly_metrics = self._analyze_elderly_suitability(pois, metrics)
            
            # Métricas pet-friendly
            pet_metrics = self._analyze_pet_friendliness(pois, metrics)
            
            # Análises por tipo de família
            family_analyses = self._analyze_family_types(children_metrics, elderly_metrics, pet_metrics, pois, metrics)
            
            # Score geral familiar
            overall_score = self._calculate_overall_family_score(children_metrics, elderly_metrics, pet_metrics)
            
            # Insights de IA
            ai_insights = await self._generate_family_ai_insights(
                address, children_metrics, elderly_metrics, pet_metrics, family_analyses
            )
            
            return FamilyHabitabilityResult(
                children_metrics=children_metrics,
                elderly_metrics=elderly_metrics,
                pet_friendly_metrics=pet_metrics,
                family_analyses=family_analyses,
                overall_family_score=overall_score,
                ai_family_insights=ai_insights,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro na análise de habitabilidade familiar: {str(e)}")
            return FamilyHabitabilityResult(
                children_metrics=None,
                elderly_metrics=None,
                pet_friendly_metrics=None,
                family_analyses=[],
                overall_family_score=0,
                ai_family_insights="",
                success=False,
                error_message=str(e)
            )
    
    def _analyze_children_suitability(self, pois: List[Dict], metrics: Any) -> ChildrenMetrics:
        """Analisa adequação para famílias com crianças"""
        
        # Contar escolas próximas
        education_pois = [poi for poi in pois if get_poi_category(poi) == 'education']
        schools_nearby = len(education_pois)
        
        # Score de qualidade das escolas (baseado na quantidade e diversidade)
        education_types = set(get_poi_subcategory(poi) or 'school' for poi in education_pois)
        quality_score = min(100, (len(education_types) * 20) + (schools_nearby * 5))
        
        # Contar parques e playgrounds
        leisure_pois = [poi for poi in pois if get_poi_category(poi) == 'leisure']
        playgrounds = len([poi for poi in leisure_pois if 'park' in get_poi_name(poi).lower() or 'playground' in get_poi_name(poi).lower()])
        
        # Serviços pediátricos
        healthcare_pois = [poi for poi in pois if get_poi_category(poi) == 'healthcare']
        pediatric_services = len([poi for poi in healthcare_pois if 'pediatr' in get_poi_name(poi).lower() or 'infantil' in get_poi_name(poi).lower()])
        
        # Score de segurança para crianças
        safety_score = getattr(metrics, 'safety_score', 70)
        child_safety = min(100, safety_score + (10 if playgrounds > 2 else 0))
        
        # Oportunidades educacionais
        educational_opportunities = []
        if schools_nearby >= 3:
            educational_opportunities.append("Múltiplas opções de escolas na região")
        if any('university' in get_poi_subcategory(poi) for poi in education_pois):
            educational_opportunities.append("Proximidade a universidades")
        if len([poi for poi in pois if 'biblioteca' in get_poi_name(poi).lower()]) > 0:
            educational_opportunities.append("Bibliotecas disponíveis")
        if len([poi for poi in leisure_pois if 'esporte' in get_poi_name(poi).lower()]) > 1:
            educational_opportunities.append("Atividades esportivas para crianças")
        
        return ChildrenMetrics(
            schools_nearby=schools_nearby,
            schools_quality_score=quality_score,
            playgrounds_count=playgrounds,
            pediatric_services=pediatric_services,
            child_safety_score=child_safety,
            educational_opportunities=educational_opportunities
        )
    
    def _analyze_elderly_suitability(self, pois: List[Dict], metrics: Any) -> ElderlyMetrics:
        """Analisa adequação para idosos"""
        
        # Acessibilidade a cuidados de saúde
        healthcare_pois = [poi for poi in pois if get_poi_category(poi) == 'healthcare']
        healthcare_access = min(100, len(healthcare_pois) * 15)
        
        # Proximidade a farmácias
        pharmacies = len([poi for poi in pois if 'farmácia' in get_poi_name(poi).lower() or 'pharmacy' in get_poi_name(poi).lower()])
        pharmacy_score = min(100, pharmacies * 25)
        
        # Serviços para idosos
        senior_services = len([poi for poi in pois if 'idoso' in get_poi_name(poi).lower() or 'terceira idade' in get_poi_name(poi).lower()])
        
        # Infraestrutura de acessibilidade
        accessibility_score = getattr(metrics, 'accessibility_score', 70)
        
        # Transporte público amigável para idosos
        transport_pois = [poi for poi in pois if get_poi_category(poi) == 'transport']
        elderly_transport = min(100, len(transport_pois) * 12 + (accessibility_score * 0.3))
        
        return ElderlyMetrics(
            healthcare_accessibility=healthcare_access,
            pharmacy_proximity=pharmacy_score,
            senior_services=senior_services,
            accessibility_infrastructure=accessibility_score,
            public_transport_elderly_friendly=elderly_transport
        )
    
    def _analyze_pet_friendliness(self, pois: List[Dict], metrics: Any) -> PetFriendlyMetrics:
        """Analisa adequação para pets"""
        
        # Serviços veterinários
        vet_services = len([poi for poi in pois if 'veterinári' in get_poi_name(poi).lower() or 'pet' in get_poi_name(poi).lower()])
        
        # Parques para pets
        leisure_pois = [poi for poi in pois if get_poi_category(poi) == 'leisure']
        pet_parks = len([poi for poi in leisure_pois if 'park' in get_poi_name(poi).lower()])
        
        # Pet shops
        pet_stores = len([poi for poi in pois if 'pet' in get_poi_name(poi).lower() and 'shop' in get_poi_name(poi).lower()])
        
        # Estabelecimentos pet-friendly
        pet_friendly = len([poi for poi in pois if 'pet' in get_poi_name(poi).lower() or 'animal' in get_poi_name(poi).lower()])
        
        # Áreas para passear com pets
        if hasattr(metrics, 'walk_score') and metrics.walk_score:
            walk_score = getattr(metrics.walk_score, 'overall_score', 70)
        else:
            walk_score = 70
        walking_areas_score = min(100, walk_score + (pet_parks * 10))
        
        return PetFriendlyMetrics(
            veterinary_services=vet_services,
            pet_parks_count=pet_parks,
            pet_stores_nearby=pet_stores,
            pet_friendly_establishments=pet_friendly,
            pet_walking_areas_score=walking_areas_score
        )
    
    def _analyze_family_types(self, 
                            children: ChildrenMetrics,
                            elderly: ElderlyMetrics,
                            pets: PetFriendlyMetrics,
                            pois: List[Dict],
                            metrics: Any) -> List[FamilyTypeAnalysis]:
        """Analisa adequação para diferentes tipos de família"""
        
        analyses = []
        
        # Família com crianças pequenas
        child_score = (children.schools_quality_score + children.child_safety_score + (children.playgrounds_count * 15)) / 3
        child_score = min(100, child_score)
        
        child_advantages = []
        child_concerns = []
        child_recommendations = []
        
        if children.schools_nearby >= 3:
            child_advantages.append("Excelente oferta educacional")
        if children.playgrounds_count >= 2:
            child_advantages.append("Áreas de lazer adequadas para crianças")
        if children.child_safety_score >= 80:
            child_advantages.append("Ambiente seguro para crianças")
        
        if children.schools_nearby < 2:
            child_concerns.append("Limitada oferta de escolas próximas")
        if children.playgrounds_count == 0:
            child_concerns.append("Falta de áreas de lazer infantil")
        if children.pediatric_services == 0:
            child_concerns.append("Ausência de serviços pediátricos próximos")
        
        child_recommendations.append("Verificar qualidade específica das escolas")
        if children.playgrounds_count < 2:
            child_recommendations.append("Considerar proximidade a parques maiores")
        
        analyses.append(FamilyTypeAnalysis(
            family_type="Família com Crianças",
            suitability_score=child_score,
            key_advantages=child_advantages,
            potential_concerns=child_concerns,
            recommendations=child_recommendations
        ))
        
        # Família com idosos
        elderly_score = (elderly.healthcare_accessibility + elderly.accessibility_infrastructure + elderly.public_transport_elderly_friendly) / 3
        
        elderly_advantages = []
        elderly_concerns = []
        elderly_recommendations = []
        
        if elderly.healthcare_accessibility >= 80:
            elderly_advantages.append("Excelente acesso a cuidados de saúde")
        if elderly.pharmacy_proximity >= 75:
            elderly_advantages.append("Farmácias próximas")
        if elderly.accessibility_infrastructure >= 70:
            elderly_advantages.append("Boa infraestrutura de acessibilidade")
        
        if elderly.healthcare_accessibility < 60:
            elderly_concerns.append("Acesso limitado a cuidados de saúde")
        if elderly.senior_services == 0:
            elderly_concerns.append("Falta de serviços especializados para idosos")
        
        elderly_recommendations.append("Verificar proximidade a hospitais especializados")
        elderly_recommendations.append("Avaliar qualidade do transporte público")
        
        analyses.append(FamilyTypeAnalysis(
            family_type="Família com Idosos",
            suitability_score=elderly_score,
            key_advantages=elderly_advantages,
            potential_concerns=elderly_concerns,
            recommendations=elderly_recommendations
        ))
        
        # Família com pets
        pet_score = (pets.pet_walking_areas_score + (pets.veterinary_services * 20) + (pets.pet_parks_count * 15)) / 3
        pet_score = min(100, pet_score)
        
        pet_advantages = []
        pet_concerns = []
        pet_recommendations = []
        
        if pets.veterinary_services >= 2:
            pet_advantages.append("Bons serviços veterinários")
        if pets.pet_parks_count >= 3:
            pet_advantages.append("Múltiplas áreas para exercitar pets")
        if pets.pet_walking_areas_score >= 80:
            pet_advantages.append("Excelentes áreas para caminhadas")
        
        if pets.veterinary_services == 0:
            pet_concerns.append("Ausência de veterinários próximos")
        if pets.pet_parks_count < 2:
            pet_concerns.append("Limitadas áreas de exercício para pets")
        
        pet_recommendations.append("Verificar políticas de pets em condomínios")
        if pets.veterinary_services < 2:
            pet_recommendations.append("Localizar clínicas veterinárias de emergência")
        
        analyses.append(FamilyTypeAnalysis(
            family_type="Família com Pets",
            suitability_score=pet_score,
            key_advantages=pet_advantages,
            potential_concerns=pet_concerns,
            recommendations=pet_recommendations
        ))
        
        # Jovem casal
        young_couple_score = (getattr(metrics, 'convenience_score', 70) + getattr(metrics, 'accessibility_score', 70)) / 2
        social_pois = len([poi for poi in pois if get_poi_category(poi) in ['food', 'leisure']])
        young_couple_score = min(100, young_couple_score + (social_pois * 2))
        
        young_advantages = ["Proximidade a opções de entretenimento", "Boa conectividade urbana"]
        young_concerns = []
        young_recommendations = ["Considerar crescimento futuro da família", "Avaliar potencial de investimento"]
        
        analyses.append(FamilyTypeAnalysis(
            family_type="Jovem Casal",
            suitability_score=young_couple_score,
            key_advantages=young_advantages,
            potential_concerns=young_concerns,
            recommendations=young_recommendations
        ))
        
        return analyses
    
    def _calculate_overall_family_score(self, 
                                      children: ChildrenMetrics,
                                      elderly: ElderlyMetrics,
                                      pets: PetFriendlyMetrics) -> float:
        """Calcula score geral de habitabilidade familiar"""
        
        # Média ponderada considerando diferentes aspectos familiares
        child_component = (children.schools_quality_score + children.child_safety_score) / 2
        elderly_component = (elderly.healthcare_accessibility + elderly.accessibility_infrastructure) / 2
        pet_component = (pets.pet_walking_areas_score + (pets.veterinary_services * 20)) / 2
        
        # Score geral
        overall = (child_component * 0.4 + elderly_component * 0.3 + pet_component * 0.3)
        return min(100, overall)
    
    async def _generate_family_ai_insights(self, 
                                         address: str,
                                         children: ChildrenMetrics,
                                         elderly: ElderlyMetrics,
                                         pets: PetFriendlyMetrics,
                                         analyses: List[FamilyTypeAnalysis]) -> str:
        """Gera insights familiares usando IA"""
        
        if not self.openai_client:
            return "Insights familiares de IA indisponíveis. Configure a API key do OpenAI."
        
        try:
            analyses_text = "\n".join([
                f"- {a.family_type}: {a.suitability_score:.1f}/100"
                for a in analyses
            ])
            
            prompt = f"""
            Você é um especialista em habitabilidade familiar e planejamento urbano. Analise os dados para famílias:

            LOCALIZAÇÃO: {address}
            
            MÉTRICAS PARA CRIANÇAS:
            - Escolas próximas: {children.schools_nearby}
            - Qualidade educacional: {children.schools_quality_score:.1f}/100
            - Playgrounds: {children.playgrounds_count}
            - Segurança infantil: {children.child_safety_score:.1f}/100
            
            MÉTRICAS PARA IDOSOS:
            - Acesso à saúde: {elderly.healthcare_accessibility:.1f}/100
            - Proximidade farmácias: {elderly.pharmacy_proximity:.1f}/100
            - Acessibilidade: {elderly.accessibility_infrastructure:.1f}/100
            
            MÉTRICAS PET-FRIENDLY:
            - Serviços veterinários: {pets.veterinary_services}
            - Parques para pets: {pets.pet_parks_count}
            - Áreas para caminhada: {pets.pet_walking_areas_score:.1f}/100
            
            ANÁLISES POR TIPO:
            {analyses_text}
            
            Forneça uma análise detalhada incluindo:
            1. Adequação geral da região para vida familiar
            2. Pontos fortes únicos para diferentes tipos de família
            3. Desafios específicos que famílias podem enfrentar
            4. Recomendações para maximizar a qualidade de vida familiar
            5. Comparação com outras áreas familiares ideais
            
            Seja específico sobre as necessidades de cada tipo de família. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um consultor especialista em habitabilidade familiar e qualidade de vida urbana."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando insights familiares de IA: {str(e)}")
            return f"Erro ao gerar insights familiares de IA: {str(e)}" 