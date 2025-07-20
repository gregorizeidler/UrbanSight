"""
Urban Trends Analysis Agent
Agente especializado em análise de tendências urbanas
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import json
from agents.utils import get_poi_category, get_poi_name

logger = logging.getLogger(__name__)

@dataclass
class DevelopmentPattern:
    pattern_type: str  # "Gentrification", "Urban Decay", "Stable", "Emerging"
    confidence_level: float  # 0-100
    key_indicators: List[str]
    timeline_estimate: str

@dataclass
class GrowthIndicators:
    commercial_growth_rate: float  # Score baseado na densidade comercial
    infrastructure_development: float  # Score baseado na infraestrutura
    residential_appeal: float  # Score baseado na habitabilidade
    innovation_index: float  # Score baseado em tecnologia/modernidade
    overall_growth_score: float

@dataclass
class FuturePredictions:
    five_year_outlook: str
    ten_year_projection: str
    emerging_opportunities: List[str]
    potential_challenges: List[str]
    investment_windows: List[str]

@dataclass
class UrbanTrendsResult:
    development_pattern: DevelopmentPattern
    growth_indicators: GrowthIndicators
    future_predictions: FuturePredictions
    ai_analysis: str
    trend_summary: str
    success: bool
    error_message: Optional[str] = None

class UrbanTrendsAnalyzer:
    """Agente especializado em análise de tendências urbanas"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def analyze_urban_trends(self, 
                                 address: str,
                                 property_data: Any,
                                 pois: List[Dict],
                                 metrics: Any) -> UrbanTrendsResult:
        """Analisa tendências urbanas de uma região"""
        
        try:
            logger.info(f"Analisando tendências urbanas para {address}")
            
            # Detectar padrões de desenvolvimento
            development_pattern = self._detect_development_pattern(pois, metrics)
            
            # Calcular indicadores de crescimento
            growth_indicators = self._calculate_growth_indicators(pois, metrics)
            
            # Gerar previsões futuras
            future_predictions = self._generate_future_predictions(development_pattern, growth_indicators)
            
            # Gerar análise com IA
            ai_analysis = await self._generate_ai_trends_analysis(
                address, development_pattern, growth_indicators, future_predictions
            )
            
            # Criar resumo das tendências
            trend_summary = self._create_trend_summary(development_pattern, growth_indicators)
            
            return UrbanTrendsResult(
                development_pattern=development_pattern,
                growth_indicators=growth_indicators,
                future_predictions=future_predictions,
                ai_analysis=ai_analysis,
                trend_summary=trend_summary,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro na análise de tendências urbanas: {str(e)}")
            return UrbanTrendsResult(
                development_pattern=None,
                growth_indicators=None,
                future_predictions=None,
                ai_analysis="",
                trend_summary="",
                success=False,
                error_message=str(e)
            )
    
    def _detect_development_pattern(self, pois: List[Dict], metrics: Any) -> DevelopmentPattern:
        """Detecta padrões de desenvolvimento urbano"""
        
        # Análise da diversidade de serviços
        categories = set(get_poi_category(poi) for poi in pois)
        diversity_score = len(categories) * 10  # 0-80 aproximadamente
        
        # Análise da densidade comercial
        commercial_pois = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services', 'food']])
        commercial_density = min(100, commercial_pois * 3)
        
        # Análise da infraestrutura
        transport_pois = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        infrastructure_score = min(100, transport_pois * 10)
        
        # Análise de qualidade de vida
        quality_score = getattr(metrics, 'total_score', 60)
        
        # Determinar padrão baseado nos scores
        combined_score = (diversity_score + commercial_density + infrastructure_score + quality_score) / 4
        
        if combined_score >= 80:
            pattern_type = "Gentrification"
            confidence = 85
            indicators = [
                "Alta diversidade de serviços",
                "Densidade comercial elevada",
                "Excelente infraestrutura",
                "Alta qualidade de vida"
            ]
            timeline = "Processo acelerado (2-5 anos)"
        elif combined_score >= 65:
            pattern_type = "Emerging"
            confidence = 75
            indicators = [
                "Crescimento da diversidade urbana",
                "Desenvolvimento comercial moderado",
                "Melhorias na infraestrutura"
            ]
            timeline = "Desenvolvimento gradual (5-10 anos)"
        elif combined_score >= 45:
            pattern_type = "Stable"
            confidence = 70
            indicators = [
                "Padrão de desenvolvimento estável",
                "Serviços básicos estabelecidos",
                "Infraestrutura consolidada"
            ]
            timeline = "Crescimento lento (10+ anos)"
        else:
            pattern_type = "Underdeveloped"
            confidence = 65
            indicators = [
                "Baixa diversidade urbana",
                "Infraestrutura limitada",
                "Potencial de desenvolvimento futuro"
            ]
            timeline = "Desenvolvimento necessário (10+ anos)"
        
        return DevelopmentPattern(
            pattern_type=pattern_type,
            confidence_level=confidence,
            key_indicators=indicators,
            timeline_estimate=timeline
        )
    
    def _calculate_growth_indicators(self, pois: List[Dict], metrics: Any) -> GrowthIndicators:
        """Calcula indicadores de crescimento"""
        
        # Taxa de crescimento comercial (baseada na densidade atual)
        commercial_pois = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services', 'food']])
        commercial_growth = min(100, commercial_pois * 2.5)
        
        # Desenvolvimento de infraestrutura
        transport_pois = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        infrastructure_dev = min(100, transport_pois * 8)
        
        # Apelo residencial
        residential_factors = [
            len([poi for poi in pois if get_poi_category(poi) == 'education']) * 5,
            len([poi for poi in pois if get_poi_category(poi) == 'healthcare']) * 7,
            len([poi for poi in pois if get_poi_category(poi) == 'leisure']) * 3
        ]
        residential_appeal = min(100, sum(residential_factors))
        
        # Índice de inovação (baseado em serviços modernos)
        modern_services = len([poi for poi in pois if get_poi_category(poi) in ['services'] 
                              and any(term in get_poi_name(poi).lower() 
                                    for term in ['coworking', 'tech', 'digital', 'wifi', 'startup'])])
        innovation_index = min(100, modern_services * 15 + 30)  # Base de 30
        
        # Score geral
        overall_score = (commercial_growth + infrastructure_dev + residential_appeal + innovation_index) / 4
        
        return GrowthIndicators(
            commercial_growth_rate=commercial_growth,
            infrastructure_development=infrastructure_dev,
            residential_appeal=residential_appeal,
            innovation_index=innovation_index,
            overall_growth_score=overall_score
        )
    
    def _generate_future_predictions(self, 
                                   pattern: DevelopmentPattern, 
                                   growth: GrowthIndicators) -> FuturePredictions:
        """Gera previsões para o futuro da região"""
        
        # Projeção de 5 anos
        if growth.overall_growth_score >= 80:
            five_year = "Crescimento acelerado com consolidação urbana"
        elif growth.overall_growth_score >= 60:
            five_year = "Desenvolvimento moderado com melhorias graduais"
        else:
            five_year = "Crescimento lento com potencial de desenvolvimento"
        
        # Projeção de 10 anos
        if pattern.pattern_type == "Gentrification":
            ten_year = "Região completamente transformada em hub urbano premium"
        elif pattern.pattern_type == "Emerging":
            ten_year = "Consolidação como bairro desenvolvido e atrativo"
        elif pattern.pattern_type == "Stable":
            ten_year = "Manutenção da estabilidade com melhorias pontuais"
        else:
            ten_year = "Potencial para transformação significativa com investimentos"
        
        # Oportunidades emergentes
        opportunities = []
        if growth.commercial_growth_rate > 70:
            opportunities.append("Expansão do setor de serviços e comércio")
        if growth.infrastructure_development > 60:
            opportunities.append("Melhorias na conectividade e transporte")
        if growth.innovation_index > 50:
            opportunities.append("Desenvolvimento de hub tecnológico")
        if growth.residential_appeal > 70:
            opportunities.append("Crescimento do mercado residencial")
        
        if not opportunities:
            opportunities.append("Oportunidades de desenvolvimento inicial")
        
        # Desafios potenciais
        challenges = []
        if growth.infrastructure_development < 50:
            challenges.append("Necessidade de investimentos em infraestrutura")
        if growth.commercial_growth_rate < 40:
            challenges.append("Limitada atividade econômica local")
        if pattern.pattern_type == "Gentrification":
            challenges.append("Risco de deslocamento de população local")
        
        if not challenges:
            challenges.append("Manutenção do crescimento sustentável")
        
        # Janelas de investimento
        investment_windows = []
        if pattern.pattern_type == "Emerging":
            investment_windows.append("Janela de oportunidade nos próximos 2-3 anos")
        if growth.overall_growth_score > 65:
            investment_windows.append("Momento favorável para investimentos comerciais")
        if growth.residential_appeal > 60:
            investment_windows.append("Oportunidade em desenvolvimento residencial")
        
        if not investment_windows:
            investment_windows.append("Aguardar sinais de desenvolvimento")
        
        return FuturePredictions(
            five_year_outlook=five_year,
            ten_year_projection=ten_year,
            emerging_opportunities=opportunities,
            potential_challenges=challenges,
            investment_windows=investment_windows
        )
    
    async def _generate_ai_trends_analysis(self, 
                                         address: str,
                                         pattern: DevelopmentPattern,
                                         growth: GrowthIndicators,
                                         predictions: FuturePredictions) -> str:
        """Gera análise de tendências usando IA"""
        
        if not self.openai_client:
            return "Análise de IA indisponível. Configure a API key do OpenAI."
        
        try:
            prompt = f"""
            Você é um especialista em planejamento urbano e desenvolvimento imobiliário. Analise as tendências urbanas:

            LOCALIZAÇÃO: {address}
            
            PADRÃO DE DESENVOLVIMENTO:
            - Tipo: {pattern.pattern_type}
            - Confiança: {pattern.confidence_level:.1f}%
            - Indicadores: {', '.join(pattern.key_indicators)}
            - Timeline: {pattern.timeline_estimate}
            
            INDICADORES DE CRESCIMENTO:
            - Crescimento Comercial: {growth.commercial_growth_rate:.1f}/100
            - Desenvolvimento Infraestrutura: {growth.infrastructure_development:.1f}/100
            - Apelo Residencial: {growth.residential_appeal:.1f}/100
            - Índice Inovação: {growth.innovation_index:.1f}/100
            - Score Geral: {growth.overall_growth_score:.1f}/100
            
            PREVISÕES:
            - 5 anos: {predictions.five_year_outlook}
            - 10 anos: {predictions.ten_year_projection}
            - Oportunidades: {', '.join(predictions.emerging_opportunities)}
            - Desafios: {', '.join(predictions.potential_challenges)}
            
            Forneça uma análise detalhada sobre:
            1. Avaliação do estágio de desenvolvimento atual
            2. Tendências de transformação urbana
            3. Fatores que podem acelerar ou retardar o desenvolvimento
            4. Comparação com outras regiões similares
            5. Recomendações estratégicas para diferentes tipos de investidor
            
            Seja específico e baseado em conhecimento de urbanismo. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um urbanista e consultor imobiliário com expertise em desenvolvimento urbano."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando análise de IA: {str(e)}")
            return f"Erro ao gerar análise de IA: {str(e)}"
    
    def _create_trend_summary(self, pattern: DevelopmentPattern, growth: GrowthIndicators) -> str:
        """Cria resumo das tendências"""
        
        if growth.overall_growth_score >= 80:
            momentum = "Alto"
        elif growth.overall_growth_score >= 60:
            momentum = "Moderado"
        else:
            momentum = "Baixo"
        
        summary = f"""
        RESUMO DE TENDÊNCIAS URBANAS:
        
        🏗️ Padrão de Desenvolvimento: {pattern.pattern_type}
        📈 Momentum de Crescimento: {momentum}
        ⏱️ Timeline de Transformação: {pattern.timeline_estimate}
        🎯 Confiança da Análise: {pattern.confidence_level:.0f}%
        
        A região apresenta características de {pattern.pattern_type.lower()} com 
        potencial de crescimento {momentum.lower()}. Os principais indicadores 
        sugerem um desenvolvimento {pattern.timeline_estimate.lower()}.
        """
        
        return summary.strip() 