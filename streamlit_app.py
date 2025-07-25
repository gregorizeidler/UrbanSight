import streamlit as st
import asyncio
import plotly.express as px
from streamlit_folium import folium_static
import folium
import pandas as pd
from datetime import datetime
import time

# Import our agents
from agents.orchestrator import PropertyAnalysisOrchestrator

# Configure Streamlit page
st.set_page_config(
    page_title="UrbanSight - Inteligência Imobiliária Profissional",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

# Initialize orchestrator


@st.cache_resource
def get_orchestrator():
    return PropertyAnalysisOrchestrator()


orchestrator = get_orchestrator()

# Helper functions


def get_score_grade(score):
    """Convert numeric score to letter grade"""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def create_folium_map(result):
    """Create enhanced Folium map"""
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=15,
        tiles='CartoDB positron'
    )

    # Property marker
    popup_text = f"<b>{result.property_data.address}</b><br>Score: {result.metrics.total_score:.1f}/100"
    folium.Marker(
        location=[result.property_data.lat, result.property_data.lon],
        popup=popup_text,
        tooltip="📍 Property Location",
        icon=folium.Icon(color='red', icon='home', prefix='fa')
    ).add_to(m)

    # Category colors
    category_colors = {
        'education': 'blue',
        'healthcare': 'green',
        'shopping': 'orange',
        'transport': 'purple',
        'leisure': 'darkgreen',
        'services': 'gray',
        'food': 'darkred',
        'other': 'lightgray'
    }

    # POI markers
    for poi_dict in result.pois:
        color = category_colors.get(poi_dict['category'], 'lightgray')
        poi_popup = f"<b>{poi_dict['name']}</b><br>{poi_dict['category'].title()}<br>{poi_dict['distance']:.0f}m"
        folium.Marker(
            location=[poi_dict['lat'], poi_dict['lon']],
            popup=poi_popup,
            tooltip=f"{poi_dict['name']} ({poi_dict['distance']:.0f}m)",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)

    # Analysis radius
    folium.Circle(
        location=[result.property_data.lat, result.property_data.lon],
        radius=1000,
        popup="Analysis Radius (1km)",
        color='#2563eb',
        fill=True,
        fillOpacity=0.1,
        weight=2,
        opacity=0.8
    ).add_to(m)

    return m


def main():
    # Main Application Header
    st.title("🏙️ UrbanSight")
    st.subheader("Plataforma Profissional de Inteligência Imobiliária")
    st.write("---")

    # Search Section
    st.header("🔍 Análise de Propriedades")

    # Address Input
    address = st.text_input(
        "Endereço da Propriedade",
        placeholder="Digite o endereço completo (ex: Avenida Paulista, 1000, Bela Vista, São Paulo, SP)",
        help="💡 Quanto mais específico o endereço, melhor será a análise"
    )

    # Analysis Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button(
            "🚀 Iniciar Análise",
            type="primary",
            use_container_width=True
        )

    # Analysis Execution
    if analyze_button and address:
        st.info("🤖 UrbanSight Processando - Analisando dados de localização...")

        try:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Step 1: Data Collection
            status_text.text("🗺️ Coletando dados do OpenStreetMap...")
            progress_bar.progress(25)
            time.sleep(0.5)

            # Run analysis
            result = asyncio.run(orchestrator.analyze_property(address))

            # Step 2: Processing
            status_text.text("🏘️ Analisando características da vizinhança...")
            progress_bar.progress(50)
            time.sleep(0.5)

            # Step 3: Metrics
            status_text.text("📊 Calculando métricas avançadas...")
            progress_bar.progress(75)
            time.sleep(0.5)

            # Step 4: AI Insights
            status_text.text("🧠 Gerando insights com IA...")
            progress_bar.progress(100)
            time.sleep(0.5)

            # Store result
            st.session_state.analysis_results[address] = result
            st.session_state.current_analysis = address

            # Clear progress
            progress_bar.empty()
            status_text.empty()

            if result.success:
                st.success("✅ Análise concluída com sucesso!")
                st.balloons()
            else:
                st.error(f"❌ Falha na análise: {result.error_message}")

        except Exception as e:
            st.error(f"❌ Erro inesperado: {str(e)}")

    elif analyze_button and not address:
        st.warning("⚠️ Por favor, digite um endereço válido")

    # Results Display
    if (st.session_state.current_analysis and
            st.session_state.current_analysis in st.session_state.analysis_results):

        result = st.session_state.analysis_results[st.session_state.current_analysis]

        if result.success:
            st.write("---")

            # Analysis Header
            st.header("📋 Relatório de Análise")
            st.subheader(f"📍 {result.property_data.address}")
            st.caption(
                f"Analisado em {datetime.now().strftime('%d de %B de %Y às %H:%M')}")

            # Key Metrics Row using native Streamlit columns
            st.subheader("🎯 Métricas Principais de Desempenho")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    "Pontuação Geral",
                    f"{result.metrics.total_score:.1f}",
                    help="Pontuação geral da propriedade"
                )

            with col2:
                st.metric(
                    "Walk Score",
                    f"{result.metrics.walk_score.overall_score:.1f}",
                    help="Classificação de caminhabilidade"
                )

            with col3:
                st.metric(
                    "Transporte",
                    f"{result.metrics.accessibility_score:.1f}",
                    help="Acesso ao transporte público"
                )

            with col4:
                st.metric(
                    "Conveniência",
                    f"{result.metrics.convenience_score:.1f}",
                    help="Serviços próximos"
                )

            with col5:
                st.metric(
                    "Estilo de Vida",
                    f"{result.metrics.quality_of_life_score:.1f}",
                    help="Pontuação de qualidade de vida"
                )

            # Tabbed Content
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Resumo Executivo",
                "🗺️ Mapa Interativo",
                "📊 Análise Detalhada",
                "🧠 Insights de IA",
                "🔍 Análise Avançada"
            ])

            with tab1:
                st.subheader("📄 Resumo Executivo")

                st.info(
                    f"**🎯 Avaliação Geral:** {result.insights.executive_summary}")

                col1, col2 = st.columns(2)

                with col1:
                    st.write("### ✅ Principais Pontos Fortes")
                    for i, strength in enumerate(result.insights.strengths[:3], 1):
                        st.success(f"**{i}.** {strength}")

                with col2:
                    st.write("### ⚠️ Áreas de Preocupação")
                    for i, concern in enumerate(result.insights.concerns[:3], 1):
                        st.warning(f"**{i}.** {concern}")

                st.info(
                    f"**👥 Perfil Ideal do Morador:** {result.insights.ideal_resident_profile}")

            with tab2:
                st.subheader("🗺️ Visão Geral da Localização")

                # Map Legend
                col1, col2 = st.columns([3, 1])

                with col2:
                    st.write("**🎯 Legenda do Mapa**")
                    st.write("🏠 **Vermelho:** Localização da Propriedade")
                    st.write("🔵 **Azul:** Educação")
                    st.write("🟢 **Verde:** Saúde")
                    st.write("🟠 **Laranja:** Compras")
                    st.write("🟣 **Roxo:** Transporte")

                with col1:
                    try:
                        m = create_folium_map(result)
                        folium_static(m, width=800, height=600)
                    except Exception as e:
                        st.error(f"Erro ao carregar mapa: {str(e)}")

                # POI Summary
                st.write("### 📍 Resumo de Pontos de Interesse")
                categories = result.metrics.category_counts

                poi_cols = st.columns(len(categories))
                for i, (category, count) in enumerate(categories.items()):
                    with poi_cols[i]:
                        category_translations = {
                            'education': 'Educação',
                            'healthcare': 'Saúde',
                            'shopping': 'Compras',
                            'transport': 'Transporte',
                            'leisure': 'Lazer',
                            'services': 'Serviços',
                            'food': 'Alimentação',
                            'other': 'Outros'
                        }
                        translated_category = category_translations.get(
                            category, category.title())
                        st.metric(translated_category, count, "próximos")

            with tab3:
                st.subheader("📊 Dashboard de Desempenho")

                # Score Breakdown Chart
                metrics_labels = ['Walk Score', 'Acessibilidade',
                                  'Conveniência', 'Segurança', 'Qualidade de Vida']
                scores_data = {
                    'Métrica': metrics_labels,
                    'Pontuação': [
                        result.metrics.walk_score.overall_score,
                        result.metrics.accessibility_score,
                        result.metrics.convenience_score,
                        result.metrics.safety_score,
                        result.metrics.quality_of_life_score
                    ]
                }

                fig = px.bar(
                    scores_data,
                    x='Métrica',
                    y='Pontuação',
                    title='🎯 Detalhamento das Pontuações',
                    color='Pontuação',
                    color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'],
                    text='Pontuação'
                )
                fig.update_traces(
                    texttemplate='%{text:.1f}', textposition='outside')
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

                # Closest POIs Table
                if result.metrics.closest_pois:
                    st.write("### 📍 Pontos de Interesse Mais Próximos")

                    closest_data = []
                    for category, poi in result.metrics.closest_pois.items():
                        category_translations = {
                            'education': 'Educação',
                            'healthcare': 'Saúde',
                            'shopping': 'Compras',
                            'transport': 'Transporte',
                            'leisure': 'Lazer',
                            'services': 'Serviços',
                            'food': 'Alimentação',
                            'other': 'Outros'
                        }
                        translated_category = category_translations.get(
                            category, category.title())
                        closest_data.append({
                            'Categoria': translated_category,
                            'Nome': poi.name,
                            'Distância (m)': f"{poi.distance:.0f}",
                            'Tipo': poi.subcategory.replace('_', ' ').title()
                        })

                    if closest_data:
                        df = pd.DataFrame(closest_data)
                        st.dataframe(df, use_container_width=True,
                                     hide_index=True)

            with tab4:
                st.subheader("🧠 Insights Gerados por IA")

                st.write("### 🏘️ Análise da Vizinhança")
                st.info(
                    f"**📍 Características Locais:** {result.insights.neighborhood_description}")

                st.write("### 💡 Recomendações Estratégicas")
                for i, rec in enumerate(result.insights.recommendations[:3], 1):
                    st.info(f"**💡 Recomendação {i}:** {rec}")

                col1, col2 = st.columns(2)

                with col1:
                    st.write("### 📈 Posição no Mercado")
                    st.info(
                        f"**💰 Análise de Mercado:** {result.insights.market_positioning}")

                with col2:
                    st.write("### 💎 Potencial de Investimento")
                    st.info(
                        f"**📊 Perspectiva de Investimento:** {result.insights.investment_potential}")

            with tab5:
                st.subheader("🔬 Análise Avançada")

                if result.advanced_metrics:
                    # Service Density Analysis
                    st.write("### 🏢 Densidade de Serviços")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        variety_score = result.advanced_metrics.service_density.service_variety_score
                        st.metric("Variedade de Serviços",
                                  f"{variety_score:.1f}/100")
                    with col2:
                        completeness_score = result.advanced_metrics.service_density.completeness_score
                        st.metric("Completude",
                                  f"{completeness_score:.1f}/100")
                    with col3:
                        total_services = result.advanced_metrics.service_density.total_services
                        st.metric("Total de Serviços", total_services)

                    st.write("### 📏 Densidade por Área")
                    density = result.advanced_metrics.service_density.total_services / 1.0
                    st.info(
                        f"**🎯 Densidade de Serviços:** {density:.1f} serviços por km² - Boa variedade de amenidades na área.")

                    # Urban Diversity
                    st.write("### 🏙️ Diversidade Urbana")
                    shannon = result.advanced_metrics.urban_diversity.shannon_diversity_index
                    st.metric("Índice de Diversidade Shannon",
                              f"{shannon:.2f}")
                    dominant = result.advanced_metrics.urban_diversity.dominant_category
                    st.info(
                        f"**🏆 Categoria Dominante:** Serviços de {dominant.title()} são mais prevalentes nesta área.")

                    # Activity Analysis with translated categories
                    if hasattr(result.advanced_metrics, 'activity_analysis') and result.advanced_metrics.activity_analysis:
                        st.write("### 🚶‍♂️ Análise de Atividades")
                        activity_labels = [
                            'Vida Cotidiana', 'Entretenimento', 'Família', 'Profissional']
                        activity_scores = [
                            result.advanced_metrics.activity_analysis.daily_life_support,
                            result.advanced_metrics.activity_analysis.entertainment_options,
                            result.advanced_metrics.activity_analysis.family_suitability,
                            result.advanced_metrics.activity_analysis.professional_services
                        ]

                        activity_data = {
                            'Categoria': activity_labels,
                            'Pontuação': activity_scores
                        }

                        fig = px.radar(
                            activity_data,
                            r='Pontuação',
                            theta='Categoria',
                            title='🎯 Adequação por Atividade',
                            range_r=[0, 100]
                        )
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)

                else:
                    st.warning(
                        "⚠️ Métricas avançadas não estão disponíveis para esta localização. Isso pode ser devido à cobertura limitada de dados na área.")

            # Footer
            st.divider()
            with st.expander("ℹ️ Sobre o UrbanSight", expanded=False):
                st.write("""
                **UrbanSight** é uma plataforma avançada de análise imobiliária que combina:
                - 🗺️ **OpenStreetMap** para dados geoespaciais abrangentes
                - 🤖 **Inteligência Artificial** para insights estratégicos
                - 📊 **Analytics Urbanos** para métricas de habitabilidade
                - 🎯 **Análise de Mercado** para inteligência imobiliária

                Desenvolvido para fornecer insights acionáveis para decisões imobiliárias informadas.
                """)


if __name__ == "__main__":
    main()
