"""
Commercial Viability Analyzer
Análise de viabilidade comercial para empreendedores
"""

import logging
from agents.utils import get_poi_category, get_poi_name
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI

logger = logging.getLogger(__name__)

@dataclass
class BusinessOpportunity:
    business_type: str
    viability_score: float  # 0-100
    competition_level: str  # "Baixa", "Média", "Alta"
    market_potential: float  # 0-100
    startup_difficulty: str  # "Fácil", "Médio", "Difícil"

@dataclass
class CommercialViabilityResult:
    foot_traffic_score: float
    commercial_density: float
    target_demographics_score: float
    competition_analysis: Dict[str, int]
    business_opportunities: List[BusinessOpportunity]
    overall_commercial_score: float
    ai_business_insights: str
    success: bool
    error_message: Optional[str] = None

class CommercialViabilityAnalyzer:
    """Analisador de viabilidade comercial"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def analyze_commercial_viability(self, 
                                         address: str,
                                         property_data: Any,
                                         pois: List[Dict],
                                         metrics: Any) -> CommercialViabilityResult:
        """Analisa viabilidade comercial"""
        
        try:
            logger.info(f"Analisando viabilidade comercial para {address}")
            
            # Análise de fluxo de pessoas
            foot_traffic = self._calculate_foot_traffic_score(pois, metrics)
            
            # Densidade comercial
            commercial_density = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services', 'food']]) / len(pois) * 100
            
            # Demografia alvo
            demographics_score = self._analyze_target_demographics(pois, metrics)
            
            # Análise de competição
            competition = self._analyze_competition(pois)
            
            # Oportunidades de negócio
            opportunities = self._identify_business_opportunities(pois, metrics, competition)
            
            # Score geral
            overall_score = (foot_traffic + demographics_score + (100 - commercial_density/2)) / 3
            
            # Insights de IA
            ai_insights = await self._generate_business_ai_insights(
                address, foot_traffic, demographics_score, opportunities
            )
            
            return CommercialViabilityResult(
                foot_traffic_score=foot_traffic,
                commercial_density=commercial_density,
                target_demographics_score=demographics_score,
                competition_analysis=competition,
                business_opportunities=opportunities,
                overall_commercial_score=overall_score,
                ai_business_insights=ai_insights,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro na análise comercial: {str(e)}")
            return CommercialViabilityResult(
                foot_traffic_score=0,
                commercial_density=0,
                target_demographics_score=0,
                competition_analysis={},
                business_opportunities=[],
                overall_commercial_score=0,
                ai_business_insights="",
                success=False,
                error_message=str(e)
            )
    
    def _calculate_foot_traffic_score(self, pois: List[Dict], metrics: Any) -> float:
        """Calcula score de fluxo de pessoas"""
        transport_pois = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        commercial_pois = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services']])
        
        traffic_score = min(100, (transport_pois * 15) + (commercial_pois * 5))
        return traffic_score
    
    def _analyze_target_demographics(self, pois: List[Dict], metrics: Any) -> float:
        """Analisa demografia alvo"""
        education_pois = len([poi for poi in pois if get_poi_category(poi) == 'education'])
        office_pois = len([poi for poi in pois if 'office' in get_poi_name(poi).lower()])
        
        demographics_score = min(100, (education_pois * 10) + (office_pois * 8) + 40)
        return demographics_score
    
    def _analyze_competition(self, pois: List[Dict]) -> Dict[str, int]:
        """Analisa competição por categoria"""
        competition = {
            'food': len([poi for poi in pois if get_poi_category(poi) == 'food']),
            'services': len([poi for poi in pois if get_poi_category(poi) == 'services']),
            'shopping': len([poi for poi in pois if get_poi_category(poi) == 'shopping']),
            'leisure': len([poi for poi in pois if get_poi_category(poi) == 'leisure'])
        }
        return competition
    
    def _identify_business_opportunities(self, pois: List[Dict], metrics: Any, competition: Dict[str, int]) -> List[BusinessOpportunity]:
        """Identifica oportunidades de negócio"""
        opportunities = []
        
        # Cafeteria/Padaria
        if competition['food'] < 5:
            opportunities.append(BusinessOpportunity(
                business_type="Cafeteria/Padaria",
                viability_score=85,
                competition_level="Baixa",
                market_potential=90,
                startup_difficulty="Médio"
            ))
        
        # Coworking
        education_pois = len([poi for poi in pois if get_poi_category(poi) == 'education'])
        if education_pois > 2 and competition['services'] < 10:
            opportunities.append(BusinessOpportunity(
                business_type="Coworking",
                viability_score=75,
                competition_level="Média",
                market_potential=80,
                startup_difficulty="Médio"
            ))
        
        # Fitness/Academia
        if competition['leisure'] < 3:
            opportunities.append(BusinessOpportunity(
                business_type="Academia/Fitness",
                viability_score=70,
                competition_level="Baixa",
                market_potential=85,
                startup_difficulty="Difícil"
            ))
        
        return opportunities
    
    async def _generate_business_ai_insights(self, address: str, foot_traffic: float, demographics: float, opportunities: List[BusinessOpportunity]) -> str:
        """Gera insights de negócio com IA"""
        
        if not self.openai_client:
            return "Insights de negócio indisponíveis. Configure a API key do OpenAI."
        
        try:
            opportunities_text = "\n".join([f"- {o.business_type}: {o.viability_score}/100" for o in opportunities])
            
            prompt = f"""
            Analise a viabilidade comercial para empreendedores em {address}:
            
            - Fluxo de pessoas: {foot_traffic:.1f}/100
            - Demografia alvo: {demographics:.1f}/100
            
            OPORTUNIDADES:
            {opportunities_text}
            
            Forneça insights sobre:
            1. Melhores tipos de negócio para a região
            2. Estratégias de marketing local
            3. Horários de funcionamento ideais
            4. Investimento inicial recomendado
            
            Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um consultor de negócios especializado em análise de viabilidade comercial."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Erro ao gerar insights: {str(e)}" 