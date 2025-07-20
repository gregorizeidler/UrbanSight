"""
Investment Analysis Agent
Agente especializado em análise de investimento imobiliário com IA
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import json
from agents.utils import get_poi_category

logger = logging.getLogger(__name__)

@dataclass
class InvestmentMetrics:
    roi_potential: float  # 0-100
    appreciation_forecast: float  # % anual esperado
    rental_yield_estimate: float  # % anual
    liquidity_score: float  # 0-100
    risk_score: float  # 0-100
    market_timing_score: float  # 0-100
    overall_investment_score: float  # 0-100

@dataclass
class MarketComparison:
    similar_properties_avg_price: float
    price_per_sqm_comparison: str  # "acima/abaixo/igual"
    neighborhood_growth_trend: str
    market_saturation_level: str
    competitive_advantage: List[str]

@dataclass
class InvestmentRecommendations:
    buy_hold_sell: str  # "BUY", "HOLD", "SELL"
    optimal_timeline: str
    financing_suggestions: List[str]
    improvement_opportunities: List[str]
    exit_strategy: str

@dataclass
class InvestmentAnalysisResult:
    metrics: InvestmentMetrics
    market_comparison: MarketComparison
    recommendations: InvestmentRecommendations
    ai_insights: str
    risk_factors: List[str]
    success: bool
    error_message: Optional[str] = None

class InvestmentAnalyzer:
    """Agente especializado em análise de investimento imobiliário"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def analyze_investment_potential(self, 
                                         address: str,
                                         property_data: Any,
                                         pois: List[Dict],
                                         metrics: Any) -> InvestmentAnalysisResult:
        """Analisa o potencial de investimento de uma propriedade"""
        
        try:
            logger.info(f"Analisando potencial de investimento para {address}")
            
            # Calcular métricas básicas
            investment_metrics = self._calculate_investment_metrics(pois, metrics)
            
            # Análise de mercado
            market_comparison = self._analyze_market_comparison(pois, metrics)
            
            # Gerar recomendações
            recommendations = self._generate_investment_recommendations(investment_metrics, market_comparison)
            
            # Gerar insights com IA (se disponível)
            ai_insights = await self._generate_ai_investment_insights(
                address, investment_metrics, market_comparison, recommendations
            )
            
            # Identificar fatores de risco
            risk_factors = self._identify_risk_factors(pois, metrics)
            
            return InvestmentAnalysisResult(
                metrics=investment_metrics,
                market_comparison=market_comparison,
                recommendations=recommendations,
                ai_insights=ai_insights,
                risk_factors=risk_factors,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro na análise de investimento: {str(e)}")
            return InvestmentAnalysisResult(
                metrics=None,
                market_comparison=None,
                recommendations=None,
                ai_insights="",
                risk_factors=[],
                success=False,
                error_message=str(e)
            )
    
    def _calculate_investment_metrics(self, pois: List[Dict], metrics: Any) -> InvestmentMetrics:
        """Calcula métricas de investimento baseadas nos dados"""
        
        # ROI Potential baseado na infraestrutura
        infrastructure_score = getattr(metrics, 'total_score', 70)
        transport_access = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        roi_potential = min(100, infrastructure_score + (transport_access * 2))
        
        # Forecast de valorização baseado na diversidade urbana
        if hasattr(metrics, 'walk_score') and metrics.walk_score:
            urban_diversity = getattr(metrics.walk_score, 'overall_score', 50)
        else:
            urban_diversity = 50
        appreciation_forecast = (urban_diversity / 100) * 8 + 2  # 2-10% anual
        
        # Rental yield baseado na conveniência
        convenience = getattr(metrics, 'convenience_score', 60)
        rental_yield = (convenience / 100) * 6 + 2  # 2-8% anual
        
        # Liquidez baseada na acessibilidade
        accessibility = getattr(metrics, 'accessibility_score', 60)
        liquidity_score = accessibility
        
        # Risco baseado na segurança e estabilidade
        safety = getattr(metrics, 'safety_score', 70)
        risk_score = 100 - safety
        
        # Market timing (sempre moderado sem dados históricos)
        market_timing_score = 65
        
        # Score geral
        overall_score = (roi_potential + liquidity_score + (100 - risk_score)) / 3
        
        return InvestmentMetrics(
            roi_potential=roi_potential,
            appreciation_forecast=appreciation_forecast,
            rental_yield_estimate=rental_yield,
            liquidity_score=liquidity_score,
            risk_score=risk_score,
            market_timing_score=market_timing_score,
            overall_investment_score=overall_score
        )
    
    def _analyze_market_comparison(self, pois: List[Dict], metrics: Any) -> MarketComparison:
        """Analisa comparação com o mercado"""
        
        # Simular análise de mercado baseada nos POIs
        commercial_density = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services']])
        
        if commercial_density > 20:
            market_saturation = "Alto"
            growth_trend = "Estável"
        elif commercial_density > 10:
            market_saturation = "Médio"
            growth_trend = "Crescimento"
        else:
            market_saturation = "Baixo"
            growth_trend = "Emergente"
        
        # Vantagens competitivas baseadas nos POIs
        competitive_advantages = []
        if len([poi for poi in pois if get_poi_category(poi) == 'transport']) > 5:
            competitive_advantages.append("Excelente conectividade de transporte")
        if len([poi for poi in pois if get_poi_category(poi) == 'education']) > 3:
            competitive_advantages.append("Proximidade a instituições educacionais")
        if len([poi for poi in pois if get_poi_category(poi) == 'healthcare']) > 2:
            competitive_advantages.append("Acesso facilitado à saúde")
        if len([poi for poi in pois if get_poi_category(poi) == 'leisure']) > 5:
            competitive_advantages.append("Rica oferta de lazer e entretenimento")
        
        return MarketComparison(
            similar_properties_avg_price=0,  # Seria necessário API de preços
            price_per_sqm_comparison="Dados não disponíveis",
            neighborhood_growth_trend=growth_trend,
            market_saturation_level=market_saturation,
            competitive_advantage=competitive_advantages
        )
    
    def _generate_investment_recommendations(self, 
                                           metrics: InvestmentMetrics, 
                                           market: MarketComparison) -> InvestmentRecommendations:
        """Gera recomendações de investimento"""
        
        # Lógica de recomendação
        if metrics.overall_investment_score >= 80:
            recommendation = "BUY"
            timeline = "Curto prazo (0-6 meses)"
        elif metrics.overall_investment_score >= 60:
            recommendation = "HOLD"
            timeline = "Médio prazo (6-18 meses)"
        else:
            recommendation = "AVALIAR"
            timeline = "Longo prazo (18+ meses)"
        
        # Sugestões de financiamento
        financing_suggestions = [
            "Considere financiamento com entrada de 20%",
            "Avalie programas habitacionais disponíveis",
            "Compare taxas de juros de diferentes bancos"
        ]
        
        if metrics.rental_yield_estimate > 6:
            financing_suggestions.append("Alta rentabilidade permite financiamento mais agressivo")
        
        # Oportunidades de melhoria
        improvements = [
            "Melhorias na propriedade podem aumentar ROI",
            "Considere sustentabilidade para maior valorização"
        ]
        
        # Estratégia de saída
        if metrics.liquidity_score > 70:
            exit_strategy = "Mercado com boa liquidez permite venda facilitada"
        else:
            exit_strategy = "Foque em valorização de longo prazo"
        
        return InvestmentRecommendations(
            buy_hold_sell=recommendation,
            optimal_timeline=timeline,
            financing_suggestions=financing_suggestions,
            improvement_opportunities=improvements,
            exit_strategy=exit_strategy
        )
    
    async def _generate_ai_investment_insights(self, 
                                             address: str,
                                             metrics: InvestmentMetrics,
                                             market: MarketComparison,
                                             recommendations: InvestmentRecommendations) -> str:
        """Gera insights de investimento usando IA"""
        
        if not self.openai_client:
            return "Insights de IA indisponíveis. Configure a API key do OpenAI."
        
        try:
            prompt = f"""
            Você é um especialista em investimento imobiliário. Analise os dados abaixo e forneça insights profundos:

            PROPRIEDADE: {address}
            
            MÉTRICAS DE INVESTIMENTO:
            - Potencial ROI: {metrics.roi_potential:.1f}/100
            - Valorização esperada: {metrics.appreciation_forecast:.1f}% ao ano
            - Rental Yield: {metrics.rental_yield_estimate:.1f}% ao ano
            - Score de Liquidez: {metrics.liquidity_score:.1f}/100
            - Score de Risco: {metrics.risk_score:.1f}/100
            - Score Geral: {metrics.overall_investment_score:.1f}/100
            
            ANÁLISE DE MERCADO:
            - Tendência do bairro: {market.neighborhood_growth_trend}
            - Saturação do mercado: {market.market_saturation_level}
            - Vantagens competitivas: {', '.join(market.competitive_advantage)}
            
            RECOMENDAÇÃO: {recommendations.buy_hold_sell}
            
            Forneça uma análise detalhada cobrindo:
            1. Avaliação geral do investimento
            2. Pontos fortes e fracos da oportunidade
            3. Riscos específicos a considerar
            4. Estratégias para maximizar retorno
            5. Comparação com outras oportunidades de investimento
            
            Seja específico, prático e baseado em dados. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um consultor especialista em investimentos imobiliários com 20 anos de experiência."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando insights de IA: {str(e)}")
            return f"Erro ao gerar insights de IA: {str(e)}"
    
    def _identify_risk_factors(self, pois: List[Dict], metrics: Any) -> List[str]:
        """Identifica fatores de risco do investimento"""
        
        risk_factors = []
        
        # Análise de transporte
        transport_pois = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        if transport_pois < 3:
            risk_factors.append("Baixa conectividade de transporte público")
        
        # Análise de comércio
        shopping_pois = len([poi for poi in pois if get_poi_category(poi) == 'shopping'])
        if shopping_pois < 5:
            risk_factors.append("Limitada oferta comercial na região")
        
        # Análise de serviços essenciais
        healthcare_pois = len([poi for poi in pois if get_poi_category(poi) == 'healthcare'])
        if healthcare_pois < 2:
            risk_factors.append("Acesso limitado a serviços de saúde")
        
        # Análise de diversidade
        categories = set(get_poi_category(poi) for poi in pois)
        if len(categories) < 5:
            risk_factors.append("Baixa diversidade urbana")
        
        # Score geral baixo
        total_score = getattr(metrics, 'total_score', 70)
        if total_score < 60:
            risk_factors.append("Score geral de qualidade urbana abaixo da média")
        
        if not risk_factors:
            risk_factors.append("Nenhum fator de risco significativo identificado")
        
        return risk_factors 