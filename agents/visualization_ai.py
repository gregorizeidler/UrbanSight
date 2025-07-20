"""
Visualization AI Generator
IA Geradora de Visualizações dinâmicas e insights visuais
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from agents.utils import get_poi_category
from openai import OpenAI

logger = logging.getLogger(__name__)

@dataclass
class VisualizationInsight:
    chart_type: str
    title: str
    description: str
    chart_data: Dict[str, Any]
    plotly_figure: Optional[go.Figure] = None

@dataclass
class VisualizationAIResult:
    insights_charts: List[VisualizationInsight]
    comparison_charts: List[VisualizationInsight]
    predictive_charts: List[VisualizationInsight]
    interactive_dashboard: Optional[go.Figure]
    ai_visual_narrative: str
    success: bool
    error_message: Optional[str] = None

class VisualizationAI:
    """IA especializada em geração de visualizações inteligentes"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        
    async def generate_intelligent_visualizations(self, 
                                                analysis_result: Any,
                                                address: str) -> VisualizationAIResult:
        """Gera visualizações inteligentes baseadas na análise"""
        
        try:
            logger.info(f"Gerando visualizações inteligentes para {address}")
            
            # Extrair dados para visualização
            viz_data = self._extract_visualization_data(analysis_result)
            
            # Gerar insights visuais
            insights_charts = self._generate_insights_charts(viz_data, analysis_result)
            
            # Gerar comparações visuais
            comparison_charts = self._generate_comparison_charts(viz_data, analysis_result)
            
            # Gerar gráficos preditivos
            predictive_charts = self._generate_predictive_charts(viz_data, analysis_result)
            
            # Criar dashboard interativo
            dashboard = self._create_interactive_dashboard(viz_data, analysis_result)
            
            # Narrativa visual com IA
            visual_narrative = await self._generate_visual_narrative(
                address, insights_charts, comparison_charts, predictive_charts
            )
            
            return VisualizationAIResult(
                insights_charts=insights_charts,
                comparison_charts=comparison_charts,
                predictive_charts=predictive_charts,
                interactive_dashboard=dashboard,
                ai_visual_narrative=visual_narrative,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro gerando visualizações: {str(e)}")
            return VisualizationAIResult(
                insights_charts=[],
                comparison_charts=[],
                predictive_charts=[],
                interactive_dashboard=None,
                ai_visual_narrative="",
                success=False,
                error_message=str(e)
            )
    
    def _extract_visualization_data(self, analysis_result: Any) -> Dict[str, Any]:
        """Extrai dados relevantes para visualização"""
        
        data = {}
        
        # Métricas básicas
        if hasattr(analysis_result, 'metrics') and analysis_result.metrics:
            metrics = analysis_result.metrics
            data['basic_scores'] = {
                'Acessibilidade': getattr(metrics, 'accessibility_score', 0),
                'Conveniência': getattr(metrics, 'convenience_score', 0),
                'Lazer': getattr(metrics, 'leisure_score', 0),
                'Segurança': getattr(metrics, 'safety_score', 0),
                'Score Total': getattr(metrics, 'total_score', 0)
            }
        
        # POIs por categoria
        if hasattr(analysis_result, 'pois') and analysis_result.pois:
            poi_categories = {}
            for poi in analysis_result.pois:
                category = get_poi_category(poi)
                poi_categories[category] = poi_categories.get(category, 0) + 1
            data['poi_distribution'] = poi_categories
        
        # Dados de investimento
        if hasattr(analysis_result, 'investment_analysis') and analysis_result.investment_analysis:
            inv = analysis_result.investment_analysis
            data['investment_metrics'] = {
                'ROI Potencial': getattr(inv, 'roi_potential', 0),
                'Score Investimento': getattr(inv, 'investment_score', 0),
                'Risco': getattr(inv, 'risk_level', 50)
            }
        
        # Dados preditivos
        if hasattr(analysis_result, 'predictive_analysis') and analysis_result.predictive_analysis:
            pred = analysis_result.predictive_analysis
            if hasattr(pred, 'market_forecasting') and pred.market_forecasting:
                data['price_forecasting'] = {
                    '1 ano': getattr(pred.market_forecasting, 'price_growth_1yr', 0),
                    '3 anos': getattr(pred.market_forecasting, 'price_growth_3yr', 0),
                    '5 anos': getattr(pred.market_forecasting, 'price_growth_5yr', 0)
                }
        
        # Dados familiares
        if hasattr(analysis_result, 'family_habitability') and analysis_result.family_habitability:
            fam = analysis_result.family_habitability
            if hasattr(fam, 'family_analyses') and fam.family_analyses:
                data['family_scores'] = {
                    analysis.family_type: analysis.suitability_score 
                    for analysis in fam.family_analyses
                }
        
        return data
    
    def _generate_insights_charts(self, viz_data: Dict, analysis_result: Any) -> List[VisualizationInsight]:
        """Gera gráficos de insights principais"""
        
        charts = []
        
        # 1. Radar Chart - Scores Principais
        if 'basic_scores' in viz_data:
            scores = viz_data['basic_scores']
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=list(scores.values()),
                theta=list(scores.keys()),
                fill='toself',
                name='Scores da Região',
                line_color='rgb(0,100,200)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="Análise Multidimensional da Região"
            )
            
            charts.append(VisualizationInsight(
                chart_type="radar",
                title="Scores Principais da Região",
                description="Visualização radial dos principais indicadores de qualidade urbana",
                chart_data=scores,
                plotly_figure=fig
            ))
        
        # 2. Treemap - Distribuição de POIs
        if 'poi_distribution' in viz_data:
            poi_data = viz_data['poi_distribution']
            
            # Preparar dados para treemap
            categories = list(poi_data.keys())
            values = list(poi_data.values())
            
            fig = go.Figure(go.Treemap(
                labels=categories,
                values=values,
                parents=[""] * len(categories),
                textinfo="label+value+percent parent"
            ))
            
            fig.update_layout(
                title="Distribuição de Pontos de Interesse",
                font_size=12
            )
            
            charts.append(VisualizationInsight(
                chart_type="treemap",
                title="Distribuição de POIs",
                description="Mapa hierárquico mostrando a diversidade de estabelecimentos na região",
                chart_data=poi_data,
                plotly_figure=fig
            ))
        
        # 3. Gauge Chart - Score de Investimento
        if 'investment_metrics' in viz_data:
            inv_score = viz_data['investment_metrics'].get('Score Investimento', 0)
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = inv_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Score de Investimento"},
                delta = {'reference': 70},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90}}))
            
            charts.append(VisualizationInsight(
                chart_type="gauge",
                title="Potencial de Investimento",
                description="Medidor do potencial de retorno financeiro da região",
                chart_data=viz_data['investment_metrics'],
                plotly_figure=fig
            ))
        
        return charts
    
    def _generate_comparison_charts(self, viz_data: Dict, analysis_result: Any) -> List[VisualizationInsight]:
        """Gera gráficos de comparação"""
        
        charts = []
        
        # 1. Comparação Familiar
        if 'family_scores' in viz_data:
            family_data = viz_data['family_scores']
            
            fig = px.bar(
                x=list(family_data.keys()),
                y=list(family_data.values()),
                title="Adequação por Tipo de Família",
                labels={'x': 'Tipo de Família', 'y': 'Score de Adequação'},
                color=list(family_data.values()),
                color_continuous_scale='Viridis'
            )
            
            fig.update_layout(showlegend=False)
            
            charts.append(VisualizationInsight(
                chart_type="bar_comparison",
                title="Comparação Familiar",
                description="Comparação de adequação da região para diferentes perfis familiares",
                chart_data=family_data,
                plotly_figure=fig
            ))
        
        # 2. Benchmarking - Comparação com médias ideais
        if 'basic_scores' in viz_data:
            scores = viz_data['basic_scores']
            ideal_scores = {key: 85 for key in scores.keys()}  # Scores ideais
            
            categories = list(scores.keys())
            atual = list(scores.values())
            ideal = list(ideal_scores.values())
            
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Atual', x=categories, y=atual, marker_color='lightblue'))
            fig.add_trace(go.Bar(name='Ideal', x=categories, y=ideal, marker_color='darkblue', opacity=0.6))
            
            fig.update_layout(
                title="Comparação com Padrões Ideais",
                barmode='group',
                yaxis_title="Score"
            )
            
            charts.append(VisualizationInsight(
                chart_type="comparison_bar",
                title="Benchmarking de Qualidade",
                description="Comparação dos scores atuais com padrões ideais de qualidade urbana",
                chart_data={'atual': scores, 'ideal': ideal_scores},
                plotly_figure=fig
            ))
        
        return charts
    
    def _generate_predictive_charts(self, viz_data: Dict, analysis_result: Any) -> List[VisualizationInsight]:
        """Gera gráficos preditivos"""
        
        charts = []
        
        # 1. Projeção de Preços
        if 'price_forecasting' in viz_data:
            price_data = viz_data['price_forecasting']
            
            # Simular crescimento acumulado
            periods = list(price_data.keys())
            growth_rates = list(price_data.values())
            
            # Calcular valores acumulados
            base_value = 100
            cumulative_values = [base_value]
            for rate in growth_rates:
                cumulative_values.append(cumulative_values[-1] * (1 + rate/100))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=['Hoje'] + periods,
                y=cumulative_values,
                mode='lines+markers',
                line=dict(color='green', width=3),
                marker=dict(size=8),
                name='Projeção de Valor'
            ))
            
            fig.update_layout(
                title="Projeção de Valorização Imobiliária",
                xaxis_title="Período",
                yaxis_title="Valor Relativo (%)",
                showlegend=True
            )
            
            charts.append(VisualizationInsight(
                chart_type="line_prediction",
                title="Projeção de Valorização",
                description="Projeção do crescimento de valor imobiliário ao longo do tempo",
                chart_data=price_data,
                plotly_figure=fig
            ))
        
        # 2. Cenários de Desenvolvimento
        scenarios = ['Pessimista', 'Provável', 'Otimista']
        probabilities = [20, 60, 20]  # Probabilidades padrão
        
        fig = go.Figure(data=[
            go.Pie(labels=scenarios, values=probabilities, hole=.3)
        ])
        
        fig.update_layout(
            title="Cenários de Desenvolvimento Futuro",
            annotations=[dict(text='Probabilidades', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        charts.append(VisualizationInsight(
            chart_type="pie_scenarios",
            title="Cenários Futuros",
            description="Distribuição de probabilidades para diferentes cenários de desenvolvimento",
            chart_data={'scenarios': scenarios, 'probabilities': probabilities},
            plotly_figure=fig
        ))
        
        return charts
    
    def _create_interactive_dashboard(self, viz_data: Dict, analysis_result: Any) -> go.Figure:
        """Cria dashboard interativo consolidado"""
        
        # Criar subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Scores Principais', 'Distribuição POIs', 'Investimento', 'Família'),
            specs=[[{"type": "polar"}, {"type": "pie"}],
                   [{"type": "indicator"}, {"type": "bar"}]]
        )
        
        # 1. Radar chart
        if 'basic_scores' in viz_data:
            scores = viz_data['basic_scores']
            fig.add_trace(go.Scatterpolar(
                r=list(scores.values()),
                theta=list(scores.keys()),
                fill='toself',
                name='Scores'
            ), row=1, col=1)
        
        # 2. Pie chart POIs
        if 'poi_distribution' in viz_data:
            poi_data = viz_data['poi_distribution']
            fig.add_trace(go.Pie(
                labels=list(poi_data.keys()),
                values=list(poi_data.values()),
                name="POIs"
            ), row=1, col=2)
        
        # 3. Gauge investimento
        if 'investment_metrics' in viz_data:
            inv_score = viz_data['investment_metrics'].get('Score Investimento', 0)
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=inv_score,
                title={'text': "Investimento"},
                gauge={'axis': {'range': [0, 100]}}
            ), row=2, col=1)
        
        # 4. Bar chart família
        if 'family_scores' in viz_data:
            family_data = viz_data['family_scores']
            fig.add_trace(go.Bar(
                x=list(family_data.keys()),
                y=list(family_data.values()),
                name="Família"
            ), row=2, col=2)
        
        fig.update_layout(
            title_text="Dashboard Interativo - Análise Completa",
            showlegend=False,
            height=800
        )
        
        return fig
    
    async def _generate_visual_narrative(self, 
                                       address: str,
                                       insights: List[VisualizationInsight],
                                       comparisons: List[VisualizationInsight], 
                                       predictions: List[VisualizationInsight]) -> str:
        """Gera narrativa visual com IA"""
        
        if not self.openai_client:
            return "Narrativa visual de IA indisponível. Configure a API key do OpenAI."
        
        try:
            insights_summary = "\n".join([f"- {i.title}: {i.description}" for i in insights])
            comparisons_summary = "\n".join([f"- {c.title}: {c.description}" for c in comparisons])
            predictions_summary = "\n".join([f"- {p.title}: {p.description}" for p in predictions])
            
            prompt = f"""
            Você é um especialista em storytelling com dados e visualização. Crie uma narrativa visual cativante:

            LOCALIZAÇÃO: {address}
            
            VISUALIZAÇÕES DE INSIGHTS:
            {insights_summary}
            
            VISUALIZAÇÕES COMPARATIVAS:
            {comparisons_summary}
            
            VISUALIZAÇÕES PREDITIVAS:
            {predictions_summary}
            
            Crie uma narrativa que:
            1. Conta a "história" dos dados de forma envolvente
            2. Conecta as diferentes visualizações em uma narrativa coerente
            3. Destaca os insights mais importantes revelados pelos gráficos
            4. Explica o que cada visualização "diz" sobre a região
            5. Sugere como interpretar os padrões visuais identificados
            
            Use linguagem acessível e cativante. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um especialista em storytelling visual e análise de dados urbanos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Erro ao gerar narrativa visual: {str(e)}" 