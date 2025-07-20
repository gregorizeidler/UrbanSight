"""
Interactive Simulator
Simulador Interativo para cenários de desenvolvimento e decisões
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SimulationParameter:
    name: str
    description: str
    min_value: float
    max_value: float
    current_value: float
    step: float
    unit: str

@dataclass
class ScenarioResult:
    scenario_name: str
    parameters: Dict[str, float]
    projected_scores: Dict[str, float]
    roi_projection: float
    timeline_months: int
    confidence_level: float
    key_insights: List[str]

@dataclass
class SimulationSession:
    session_id: str
    base_analysis: Any
    current_parameters: Dict[str, float]
    scenario_history: List[ScenarioResult]
    created_at: datetime
    
class InteractiveSimulator:
    """Simulador interativo para análise de cenários urbanos"""
    
    def __init__(self):
        self.active_sessions = {}
        
    def create_simulation_session(self, 
                                session_id: str,
                                base_analysis: Any) -> SimulationSession:
        """Cria nova sessão de simulação"""
        
        # Parâmetros base extraídos da análise
        base_params = self._extract_base_parameters(base_analysis)
        
        session = SimulationSession(
            session_id=session_id,
            base_analysis=base_analysis,
            current_parameters=base_params,
            scenario_history=[],
            created_at=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        return session
    
    def get_simulation_parameters(self, session_id: str) -> List[SimulationParameter]:
        """Retorna parâmetros disponíveis para simulação"""
        
        if session_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[session_id]
        
        parameters = [
            SimulationParameter(
                name="transport_investment",
                description="Investimento em Transporte Público",
                min_value=0,
                max_value=100,
                current_value=session.current_parameters.get("transport_score", 50),
                step=5,
                unit="milhões R$"
            ),
            SimulationParameter(
                name="security_investment",
                description="Investimento em Segurança",
                min_value=0,
                max_value=100,
                current_value=session.current_parameters.get("safety_score", 50),
                step=5,
                unit="milhões R$"
            ),
            SimulationParameter(
                name="commercial_development",
                description="Desenvolvimento Comercial",
                min_value=0,
                max_value=100,
                current_value=session.current_parameters.get("convenience_score", 50),
                step=10,
                unit="novos estabelecimentos"
            ),
            SimulationParameter(
                name="green_areas",
                description="Áreas Verdes e Lazer",
                min_value=0,
                max_value=100,
                current_value=session.current_parameters.get("leisure_score", 50),
                step=5,
                unit="m² por habitante"
            ),
            SimulationParameter(
                name="educational_infrastructure",
                description="Infraestrutura Educacional",
                min_value=0,
                max_value=100,
                current_value=session.current_parameters.get("education_score", 50),
                step=10,
                unit="novas instituições"
            ),
            SimulationParameter(
                name="market_demand",
                description="Demanda do Mercado",
                min_value=50,
                max_value=150,
                current_value=100,
                step=5,
                unit="% da demanda atual"
            ),
            SimulationParameter(
                name="economic_growth",
                description="Crescimento Econômico Regional",
                min_value=-5,
                max_value=15,
                current_value=3,
                step=0.5,
                unit="% ao ano"
            )
        ]
        
        return parameters
    
    def run_scenario_simulation(self, 
                              session_id: str,
                              scenario_name: str,
                              parameter_changes: Dict[str, float],
                              timeline_months: int = 36) -> ScenarioResult:
        """Executa simulação de cenário"""
        
        if session_id not in self.active_sessions:
            raise ValueError("Sessão de simulação não encontrada")
        
        session = self.active_sessions[session_id]
        
        # Aplicar mudanças nos parâmetros
        new_parameters = session.current_parameters.copy()
        new_parameters.update(parameter_changes)
        
        # Calcular projeções
        projected_scores = self._calculate_projected_scores(
            new_parameters, timeline_months, session.base_analysis
        )
        
        # Calcular ROI projetado
        roi_projection = self._calculate_roi_projection(
            new_parameters, projected_scores, timeline_months
        )
        
        # Calcular nível de confiança
        confidence_level = self._calculate_confidence_level(
            parameter_changes, timeline_months
        )
        
        # Gerar insights chave
        key_insights = self._generate_scenario_insights(
            scenario_name, parameter_changes, projected_scores, roi_projection
        )
        
        # Criar resultado
        result = ScenarioResult(
            scenario_name=scenario_name,
            parameters=new_parameters,
            projected_scores=projected_scores,
            roi_projection=roi_projection,
            timeline_months=timeline_months,
            confidence_level=confidence_level,
            key_insights=key_insights
        )
        
        # Adicionar ao histórico
        session.scenario_history.append(result)
        
        return result
    
    def compare_scenarios(self, 
                         session_id: str,
                         scenario_names: List[str]) -> Dict[str, Any]:
        """Compara múltiplos cenários"""
        
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        
        # Filtrar cenários pelo nome
        scenarios = [
            s for s in session.scenario_history 
            if s.scenario_name in scenario_names
        ]
        
        if not scenarios:
            return {}
        
        comparison = {
            'scenarios': scenarios,
            'best_roi': max(scenarios, key=lambda s: s.roi_projection),
            'highest_confidence': max(scenarios, key=lambda s: s.confidence_level),
            'summary_comparison': self._generate_comparison_summary(scenarios)
        }
        
        return comparison
    
    def get_optimization_suggestions(self, session_id: str) -> List[Dict[str, Any]]:
        """Gera sugestões de otimização baseadas no histórico"""
        
        if session_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[session_id]
        base_scores = self._extract_base_scores(session.base_analysis)
        
        suggestions = []
        
        # Sugestão 1: Melhorar score mais baixo
        lowest_score_key = min(base_scores.keys(), key=lambda k: base_scores[k])
        suggestions.append({
            'type': 'improve_weakest',
            'title': f'Melhorar {lowest_score_key.replace("_", " ").title()}',
            'description': f'Score atual: {base_scores[lowest_score_key]:.1f}. Investimento focado pode gerar maior impacto.',
            'suggested_investment': self._suggest_investment_for_metric(lowest_score_key),
            'expected_improvement': 15
        })
        
        # Sugestão 2: Aproveitar pontos fortes
        highest_score_key = max(base_scores.keys(), key=lambda k: base_scores[k])
        suggestions.append({
            'type': 'leverage_strength',
            'title': f'Potencializar {highest_score_key.replace("_", " ").title()}',
            'description': f'Score atual: {base_scores[highest_score_key]:.1f}. Expandir pontos fortes para criar diferencial.',
            'suggested_investment': self._suggest_investment_for_metric(highest_score_key),
            'expected_improvement': 10
        })
        
        # Sugestão 3: Investimento balanceado
        suggestions.append({
            'type': 'balanced_growth',
            'title': 'Crescimento Equilibrado',
            'description': 'Investimento distribuído em múltiplas áreas para desenvolvimento harmonioso.',
            'suggested_investment': 'Distribuir investimentos entre transporte, segurança e áreas verdes',
            'expected_improvement': 12
        })
        
        return suggestions
    
    def _extract_base_parameters(self, base_analysis: Any) -> Dict[str, float]:
        """Extrai parâmetros base da análise"""
        
        params = {}
        
        if hasattr(base_analysis, 'metrics') and base_analysis.metrics:
            metrics = base_analysis.metrics
            params['accessibility_score'] = getattr(metrics, 'accessibility_score', 50)
            params['safety_score'] = getattr(metrics, 'safety_score', 50)
            params['convenience_score'] = getattr(metrics, 'convenience_score', 50)
            params['leisure_score'] = getattr(metrics, 'leisure_score', 50)
        
        # Parâmetros adicionais
        params['transport_score'] = params.get('accessibility_score', 50)
        params['education_score'] = 70  # Valor padrão
        
        return params
    
    def _extract_base_scores(self, base_analysis: Any) -> Dict[str, float]:
        """Extrai scores base da análise"""
        
        scores = {}
        
        if hasattr(base_analysis, 'metrics') and base_analysis.metrics:
            metrics = base_analysis.metrics
            scores['accessibility'] = getattr(metrics, 'accessibility_score', 50)
            scores['safety'] = getattr(metrics, 'safety_score', 50)
            scores['convenience'] = getattr(metrics, 'convenience_score', 50)
            scores['leisure'] = getattr(metrics, 'leisure_score', 50)
        
        return scores
    
    def _calculate_projected_scores(self, 
                                  parameters: Dict[str, float],
                                  timeline_months: int,
                                  base_analysis: Any) -> Dict[str, float]:
        """Calcula scores projetados baseados nos parâmetros"""
        
        # Fator de tempo (impacto diminui com timeline muito longo)
        time_factor = max(0.5, 1 - (timeline_months - 12) / 60)
        
        # Calcular novos scores
        projected = {}
        
        # Transport/Accessibility
        transport_boost = (parameters.get('transport_investment', 50) - 50) * 0.3 * time_factor
        projected['accessibility'] = min(100, parameters.get('accessibility_score', 50) + transport_boost)
        
        # Safety
        safety_boost = (parameters.get('security_investment', 50) - 50) * 0.4 * time_factor
        projected['safety'] = min(100, parameters.get('safety_score', 50) + safety_boost)
        
        # Convenience
        commercial_boost = (parameters.get('commercial_development', 50) - 50) * 0.35 * time_factor
        projected['convenience'] = min(100, parameters.get('convenience_score', 50) + commercial_boost)
        
        # Leisure
        green_boost = (parameters.get('green_areas', 50) - 50) * 0.4 * time_factor
        projected['leisure'] = min(100, parameters.get('leisure_score', 50) + green_boost)
        
        # Score total
        projected['total'] = np.mean(list(projected.values()))
        
        return projected
    
    def _calculate_roi_projection(self, 
                                parameters: Dict[str, float],
                                projected_scores: Dict[str, float],
                                timeline_months: int) -> float:
        """Calcula projeção de ROI"""
        
        # Score improvement factor
        base_total = np.mean([
            parameters.get('accessibility_score', 50),
            parameters.get('safety_score', 50),
            parameters.get('convenience_score', 50),
            parameters.get('leisure_score', 50)
        ])
        
        improvement = projected_scores['total'] - base_total
        
        # Market factors
        market_demand = parameters.get('market_demand', 100) / 100
        economic_growth = parameters.get('economic_growth', 3) / 100
        
        # ROI calculation (simplified model)
        base_roi = improvement * 0.8  # Each score point = 0.8% ROI
        market_adjustment = base_roi * market_demand
        economic_adjustment = market_adjustment * (1 + economic_growth * timeline_months / 12)
        
        # Time value adjustment
        annual_roi = economic_adjustment / (timeline_months / 12)
        
        return max(0, min(50, annual_roi))  # Cap between 0-50%
    
    def _calculate_confidence_level(self, 
                                  parameter_changes: Dict[str, float],
                                  timeline_months: int) -> float:
        """Calcula nível de confiança da projeção"""
        
        base_confidence = 80
        
        # Reduzir confiança para mudanças muito grandes
        change_magnitude = sum(abs(v) for v in parameter_changes.values())
        if change_magnitude > 200:
            base_confidence -= 20
        elif change_magnitude > 100:
            base_confidence -= 10
        
        # Reduzir confiança para timeline muito longo
        if timeline_months > 48:
            base_confidence -= 15
        elif timeline_months > 24:
            base_confidence -= 8
        
        return max(30, base_confidence)
    
    def _generate_scenario_insights(self, 
                                  scenario_name: str,
                                  changes: Dict[str, float],
                                  projected_scores: Dict[str, float],
                                  roi: float) -> List[str]:
        """Gera insights chave do cenário"""
        
        insights = []
        
        # Insight sobre ROI
        if roi > 15:
            insights.append(f"ROI projetado de {roi:.1f}% indica excelente potencial de retorno")
        elif roi > 8:
            insights.append(f"ROI moderado de {roi:.1f}% sugere retorno estável")
        else:
            insights.append(f"ROI de {roi:.1f}% indica necessidade de revisão da estratégia")
        
        # Insights sobre mudanças específicas
        for param, value in changes.items():
            if value > 20:
                insights.append(f"Investimento alto em {param.replace('_', ' ')} pode gerar impacto significativo")
        
        # Insight sobre score total
        total_score = projected_scores.get('total', 0)
        if total_score > 85:
            insights.append("Região alcançaria padrão de excelência urbana")
        elif total_score > 70:
            insights.append("Desenvolvimento resultaria em região de alta qualidade")
        
        return insights
    
    def _generate_comparison_summary(self, scenarios: List[ScenarioResult]) -> Dict[str, Any]:
        """Gera resumo comparativo de cenários"""
        
        if not scenarios:
            return {}
        
        roi_values = [s.roi_projection for s in scenarios]
        confidence_values = [s.confidence_level for s in scenarios]
        
        return {
            'best_scenario': max(scenarios, key=lambda s: s.roi_projection).scenario_name,
            'roi_range': f"{min(roi_values):.1f}% - {max(roi_values):.1f}%",
            'avg_confidence': np.mean(confidence_values),
            'recommendation': self._generate_recommendation(scenarios)
        }
    
    def _generate_recommendation(self, scenarios: List[ScenarioResult]) -> str:
        """Gera recomendação baseada na comparação"""
        
        best_roi = max(scenarios, key=lambda s: s.roi_projection)
        best_confidence = max(scenarios, key=lambda s: s.confidence_level)
        
        if best_roi.scenario_name == best_confidence.scenario_name:
            return f"Recomendamos o cenário '{best_roi.scenario_name}' por combinar melhor ROI e maior confiança"
        else:
            return f"Considere balancear entre '{best_roi.scenario_name}' (melhor ROI) e '{best_confidence.scenario_name}' (maior confiança)"
    
    def _suggest_investment_for_metric(self, metric: str) -> str:
        """Sugere tipo de investimento para melhorar métrica específica"""
        
        suggestions = {
            'accessibility': 'Melhorar transporte público e ciclofaixas',
            'safety': 'Instalar iluminação e câmeras de segurança',
            'convenience': 'Atrair novos comércios e serviços',
            'leisure': 'Criar parques e espaços de lazer'
        }
        
        return suggestions.get(metric, 'Investimento em infraestrutura geral') 