"""
Predictive Analysis Agent
IA Preditiva para análise de desenvolvimento urbano futuro
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import json
from agents.utils import get_poi_category
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class InfrastructureProjection:
    project_type: str  # "transport", "commercial", "residential", "public"
    probability: float  # 0-100
    timeline: str
    impact_score: float  # 0-100
    confidence_level: float  # 0-100

@dataclass
class MarketForecasting:
    price_growth_1yr: float  # % esperado
    price_growth_3yr: float
    price_growth_5yr: float
    demand_forecast: str  # "Crescente", "Estável", "Decrescente"
    supply_constraints: List[str]
    market_saturation_risk: float  # 0-100

@dataclass
class DevelopmentScenarios:
    best_case: str
    most_likely: str
    worst_case: str
    scenario_probabilities: Dict[str, float]
    critical_factors: List[str]

@dataclass
class PredictiveAlerts:
    upcoming_opportunities: List[str]
    potential_risks: List[str]
    timing_recommendations: List[str]
    monitoring_indicators: List[str]

@dataclass
class PredictiveAnalysisResult:
    infrastructure_projections: List[InfrastructureProjection]
    market_forecasting: MarketForecasting
    development_scenarios: DevelopmentScenarios
    predictive_alerts: PredictiveAlerts
    ai_predictions: str
    confidence_rating: float
    success: bool
    error_message: Optional[str] = None

class PredictiveAnalyzer:
    """IA especializada em análises preditivas urbanas"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def analyze_future_development(self, 
                                       address: str,
                                       property_data: Any,
                                       pois: List[Dict],
                                       metrics: Any) -> PredictiveAnalysisResult:
        """Executa análise preditiva completa"""
        
        try:
            logger.info(f"Executando análise preditiva para {address}")
            
            # Projeções de infraestrutura
            infrastructure_projections = self._project_infrastructure_development(pois, metrics)
            
            # Previsão de mercado
            market_forecasting = self._forecast_market_trends(pois, metrics)
            
            # Cenários de desenvolvimento
            development_scenarios = self._generate_development_scenarios(infrastructure_projections, market_forecasting)
            
            # Alertas preditivos
            predictive_alerts = self._generate_predictive_alerts(infrastructure_projections, market_forecasting)
            
            # Análise de IA
            ai_predictions = await self._generate_ai_predictions(
                address, infrastructure_projections, market_forecasting, development_scenarios
            )
            
            # Rating de confiança geral
            confidence_rating = self._calculate_confidence_rating(infrastructure_projections, market_forecasting)
            
            return PredictiveAnalysisResult(
                infrastructure_projections=infrastructure_projections,
                market_forecasting=market_forecasting,
                development_scenarios=development_scenarios,
                predictive_alerts=predictive_alerts,
                ai_predictions=ai_predictions,
                confidence_rating=confidence_rating,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro na análise preditiva: {str(e)}")
            return PredictiveAnalysisResult(
                infrastructure_projections=[],
                market_forecasting=None,
                development_scenarios=None,
                predictive_alerts=None,
                ai_predictions="",
                confidence_rating=0,
                success=False,
                error_message=str(e)
            )
    
    def _project_infrastructure_development(self, pois: List[Dict], metrics: Any) -> List[InfrastructureProjection]:
        """Projeta desenvolvimentos futuros de infraestrutura"""
        
        projections = []
        
        # Análise de transporte
        transport_pois = len([poi for poi in pois if get_poi_category(poi) == 'transport'])
        if transport_pois < 5:
            projections.append(InfrastructureProjection(
                project_type="transport",
                probability=75,
                timeline="2-4 anos",
                impact_score=85,
                confidence_level=70
            ))
        
        # Análise comercial
        commercial_pois = len([poi for poi in pois if get_poi_category(poi) in ['shopping', 'services']])
        if commercial_pois > 15:
            projections.append(InfrastructureProjection(
                project_type="commercial",
                probability=65,
                timeline="1-3 anos",
                impact_score=70,
                confidence_level=75
            ))
        
        # Análise residencial
        total_score = getattr(metrics, 'total_score', 70)
        if total_score > 75:
            projections.append(InfrastructureProjection(
                project_type="residential",
                probability=80,
                timeline="1-2 anos",
                impact_score=75,
                confidence_level=80
            ))
        
        # Análise de serviços públicos
        education_pois = len([poi for poi in pois if get_poi_category(poi) == 'education'])
        healthcare_pois = len([poi for poi in pois if get_poi_category(poi) == 'healthcare'])
        
        if education_pois < 3 or healthcare_pois < 2:
            projections.append(InfrastructureProjection(
                project_type="public",
                probability=60,
                timeline="3-5 anos",
                impact_score=90,
                confidence_level=65
            ))
        
        return projections
    
    def _forecast_market_trends(self, pois: List[Dict], metrics: Any) -> MarketForecasting:
        """Prevê tendências de mercado imobiliário"""
        
        # Calcular crescimento baseado na infraestrutura atual
        total_score = getattr(metrics, 'total_score', 70)
        accessibility = getattr(metrics, 'accessibility_score', 70)
        convenience = getattr(metrics, 'convenience_score', 70)
        
        # Modelo simplificado de previsão
        base_growth = (total_score - 50) / 10  # -2% a +5% base
        
        price_growth_1yr = max(0, min(12, base_growth + 2))
        price_growth_3yr = max(0, min(35, base_growth * 3 + 5))
        price_growth_5yr = max(0, min(60, base_growth * 5 + 8))
        
        # Previsão de demanda
        if total_score >= 80:
            demand = "Crescente"
        elif total_score >= 60:
            demand = "Estável"
        else:
            demand = "Emergente"
        
        # Restrições de oferta
        supply_constraints = []
        if len(pois) > 200:
            supply_constraints.append("Alta densidade já estabelecida")
        if accessibility < 60:
            supply_constraints.append("Limitações de transporte")
        if convenience < 60:
            supply_constraints.append("Infraestrutura comercial insuficiente")
        
        if not supply_constraints:
            supply_constraints.append("Nenhuma restrição significativa identificada")
        
        # Risco de saturação
        poi_density = len(pois) / 3.14159  # Densidade por km²
        saturation_risk = min(100, (poi_density - 50) * 2) if poi_density > 50 else 20
        
        return MarketForecasting(
            price_growth_1yr=price_growth_1yr,
            price_growth_3yr=price_growth_3yr,
            price_growth_5yr=price_growth_5yr,
            demand_forecast=demand,
            supply_constraints=supply_constraints,
            market_saturation_risk=max(0, saturation_risk)
        )
    
    def _generate_development_scenarios(self, 
                                      projections: List[InfrastructureProjection],
                                      market: MarketForecasting) -> DevelopmentScenarios:
        """Gera cenários de desenvolvimento futuro"""
        
        # Cenário otimista
        best_case = f"""
        Crescimento acelerado com valorização de {market.price_growth_5yr * 1.2:.1f}% em 5 anos.
        Novos projetos de infraestrutura aumentam significativamente a atratividade.
        Demanda supera oferta, criando ambiente de valorização sustentada.
        """
        
        # Cenário mais provável
        most_likely = f"""
        Desenvolvimento moderado com valorização de {market.price_growth_5yr:.1f}% em 5 anos.
        Implementação gradual de melhorias conforme planejamento urbano.
        Equilíbrio entre oferta e demanda mantém crescimento estável.
        """
        
        # Cenário pessimista
        worst_case = f"""
        Crescimento lento com valorização de {market.price_growth_5yr * 0.6:.1f}% em 5 anos.
        Atrasos em projetos de infraestrutura limitam desenvolvimento.
        Excesso de oferta ou mudanças econômicas impactam demanda.
        """
        
        # Probabilidades dos cenários
        if market.demand_forecast == "Crescente":
            probabilities = {"best_case": 30, "most_likely": 55, "worst_case": 15}
        elif market.demand_forecast == "Estável":
            probabilities = {"best_case": 20, "most_likely": 60, "worst_case": 20}
        else:
            probabilities = {"best_case": 40, "most_likely": 45, "worst_case": 15}
        
        # Fatores críticos
        critical_factors = [
            "Implementação de projetos de transporte público",
            "Políticas municipais de zoneamento",
            "Crescimento econômico regional",
            "Tendências demográficas da população"
        ]
        
        return DevelopmentScenarios(
            best_case=best_case.strip(),
            most_likely=most_likely.strip(),
            worst_case=worst_case.strip(),
            scenario_probabilities=probabilities,
            critical_factors=critical_factors
        )
    
    def _generate_predictive_alerts(self, 
                                  projections: List[InfrastructureProjection],
                                  market: MarketForecasting) -> PredictiveAlerts:
        """Gera alertas e recomendações preditivas"""
        
        # Oportunidades emergentes
        opportunities = []
        for proj in projections:
            if proj.probability > 70 and proj.impact_score > 80:
                opportunities.append(f"Projeto de {proj.project_type} com alta probabilidade em {proj.timeline}")
        
        if market.price_growth_3yr > 20:
            opportunities.append("Janela de valorização acelerada nos próximos 3 anos")
        
        if not opportunities:
            opportunities.append("Monitorar desenvolvimentos futuros para identificar oportunidades")
        
        # Riscos potenciais
        risks = []
        if market.market_saturation_risk > 70:
            risks.append("Alto risco de saturação do mercado")
        
        for constraint in market.supply_constraints:
            if "Limitações" in constraint:
                risks.append(f"Risco: {constraint}")
        
        if market.price_growth_1yr < 3:
            risks.append("Crescimento de preços abaixo da média do mercado")
        
        if not risks:
            risks.append("Nenhum risco significativo identificado no horizonte de análise")
        
        # Recomendações de timing
        timing = []
        if market.demand_forecast == "Crescente":
            timing.append("Momento favorável para entrada no mercado")
        
        high_impact_projects = [p for p in projections if p.impact_score > 80]
        if high_impact_projects:
            timing.append("Antecipar projetos de alto impacto para maximizar ganhos")
        
        timing.append("Monitorar indicadores econômicos regionais")
        
        # Indicadores para monitoramento
        indicators = [
            "Número de alvarás de construção aprovados",
            "Investimentos públicos em transporte",
            "Crescimento populacional da região",
            "Índices de emprego local",
            "Preços médios de venda e aluguel"
        ]
        
        return PredictiveAlerts(
            upcoming_opportunities=opportunities,
            potential_risks=risks,
            timing_recommendations=timing,
            monitoring_indicators=indicators
        )
    
    async def _generate_ai_predictions(self, 
                                     address: str,
                                     projections: List[InfrastructureProjection],
                                     market: MarketForecasting,
                                     scenarios: DevelopmentScenarios) -> str:
        """Gera previsões usando IA"""
        
        if not self.openai_client:
            return "Previsões de IA indisponíveis. Configure a API key do OpenAI."
        
        try:
            projections_text = "\n".join([
                f"- {p.project_type}: {p.probability}% probabilidade em {p.timeline}"
                for p in projections
            ])
            
            prompt = f"""
            Você é um especialista em análise preditiva urbana e mercado imobiliário. Analise os dados e faça previsões:

            LOCALIZAÇÃO: {address}
            
            PROJEÇÕES DE INFRAESTRUTURA:
            {projections_text}
            
            PREVISÃO DE MERCADO:
            - Crescimento 1 ano: {market.price_growth_1yr:.1f}%
            - Crescimento 3 anos: {market.price_growth_3yr:.1f}%
            - Crescimento 5 anos: {market.price_growth_5yr:.1f}%
            - Demanda: {market.demand_forecast}
            - Risco saturação: {market.market_saturation_risk:.1f}%
            
            CENÁRIOS:
            - Melhor caso: {scenarios.best_case[:100]}...
            - Mais provável: {scenarios.most_likely[:100]}...
            - Pior caso: {scenarios.worst_case[:100]}...
            
            Forneça uma análise preditiva detalhada incluindo:
            1. Principais tendências que moldarão o futuro da região
            2. Catalysadores de crescimento mais prováveis
            3. Riscos e desafios no horizonte de 5-10 anos
            4. Recomendações estratégicas baseadas nas previsões
            5. Cronograma de marcos importantes a acompanhar
            
            Seja específico sobre timelines e probabilidades. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um analista sênior especializado em previsões de desenvolvimento urbano e mercado imobiliário."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando previsões de IA: {str(e)}")
            return f"Erro ao gerar previsões de IA: {str(e)}"
    
    def _calculate_confidence_rating(self, 
                                   projections: List[InfrastructureProjection],
                                   market: MarketForecasting) -> float:
        """Calcula rating de confiança das previsões"""
        
        if not projections:
            base_confidence = 60
        else:
            # Média das confianças dos projetos
            proj_confidence = sum(p.confidence_level for p in projections) / len(projections)
            base_confidence = proj_confidence
        
        # Ajustar baseado na volatilidade do mercado
        if market.market_saturation_risk > 80:
            base_confidence -= 15
        elif market.market_saturation_risk < 30:
            base_confidence += 10
        
        # Ajustar baseado na demanda
        if market.demand_forecast == "Crescente":
            base_confidence += 10
        elif market.demand_forecast == "Decrescente":
            base_confidence -= 10
        
        return max(30, min(95, base_confidence)) 