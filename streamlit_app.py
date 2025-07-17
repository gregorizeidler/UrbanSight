import streamlit as st
import asyncio
import plotly.graph_objects as go
import plotly.express as px
from streamlit_folium import folium_static
import folium
import pandas as pd
from datetime import datetime
import json
import time

# Import our agents
from agents.orchestrator import PropertyAnalysisOrchestrator
from config import Config

# Configure Streamlit page
st.set_page_config(
    page_title="UrbanSight - Inteligência Imobiliária",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
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

def get_score_color(score):
    if score >= 80:
        return "#2E8B57"  # SeaGreen
    elif score >= 60:
        return "#FFD700"  # Gold
    elif score >= 40:
        return "#FF8C00"  # DarkOrange
    else:
        return "#DC143C"  # Crimson

def create_folium_map(result):
    """Create Folium map for Streamlit"""
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=15,
        tiles='OpenStreetMap'
    )
    
    # Add property marker
    folium.Marker(
        location=[result.property_data.lat, result.property_data.lon],
        popup=f"<b>{result.property_data.address}</b><br>Score: {result.metrics.total_score:.1f}/100",
        tooltip="Propriedade Analisada",
        icon=folium.Icon(color='red', icon='home')
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
    
    # Add POI markers
    for poi_dict in result.pois:
        color = category_colors.get(poi_dict['category'], 'lightgray')
        
        folium.Marker(
            location=[poi_dict['lat'], poi_dict['lon']],
            popup=f"<b>{poi_dict['name']}</b><br>{poi_dict['category'].title()}<br>{poi_dict['distance']:.0f}m",
            tooltip=f"{poi_dict['name']} ({poi_dict['distance']:.0f}m)",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)
    
    # Add search radius
    folium.Circle(
        location=[result.property_data.lat, result.property_data.lon],
        radius=1000,
        popup="Raio de análise (1km)",
        color='blue',
        fill=True,
        fillOpacity=0.1
    ).add_to(m)
    
    return m

def display_advanced_map(map_viz, key_suffix=""):
    """Display advanced map visualization"""
    if map_viz and map_viz.map_html:
        st.markdown(f'<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🗺️ {map_viz.title}</h4>', unsafe_allow_html=True)
        st.markdown(f'<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">{map_viz.description}</p>', unsafe_allow_html=True)
        
        # Display the map HTML directly
        st.components.v1.html(map_viz.map_html, height=600, scrolling=True)
    else:
        st.warning("Mapa não disponível")

# Custom CSS for professional design
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles - fundo claro = texto preto */
    .main {
        font-family: 'Inter', sans-serif;
        color: #000;
    }
    
    /* Header com fundo escuro = texto branco */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
    }
    
    .main-header h1 {
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
        color: white;
    }
    
    .main-header p {
        font-size: 1.2rem;
        font-weight: 300;
        margin-bottom: 0;
        position: relative;
        z-index: 1;
        color: white;
    }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        text-align: center;
        border: 1px solid rgba(0,0,0,0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    /* Custom Metrics - fundo claro = texto preto */
    .custom-metric {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .custom-metric h3 {
        color: #000;
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .custom-metric .value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #000;
    }
    
    .custom-metric .grade {
        font-size: 0.8rem;
        font-weight: 500;
        color: #333;
        text-transform: uppercase;
    }
    
    /* Insight Boxes - fundo claro = texto preto */
    .insight-box {
        background: linear-gradient(145deg, #f8f9fa, #e9ecef);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    
    .insight-box h4 {
        color: #000;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    
    .insight-box p {
        color: #000;
        font-weight: 500;
        line-height: 1.6;
    }
    
    /* POI Categories - fundo escuro = texto branco */
    .poi-category {
        display: inline-block;
        background: linear-gradient(145deg, #667eea, #764ba2);
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-size: 0.85rem;
        font-weight: 500;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Sidebar - fundo escuro = texto branco */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Ensure all sidebar text is white */
    .css-1d391kg * {
        color: white !important;
    }
    
    /* Sidebar markdown text */
    .css-1d391kg .stMarkdown p {
        color: white !important;
    }
    
    .css-1d391kg .stMarkdown li {
        color: white !important;
    }
    
    .css-1d391kg .stMarkdown h1, 
    .css-1d391kg .stMarkdown h2, 
    .css-1d391kg .stMarkdown h3, 
    .css-1d391kg .stMarkdown h4, 
    .css-1d391kg .stMarkdown h5, 
    .css-1d391kg .stMarkdown h6 {
        color: white !important;
    }
    
    /* Force sidebar headings to be white */
    .css-1d391kg .stMarkdown h3[style] {
        color: white !important;
    }
    
    .css-1d391kg .stMarkdown h4[style] {
        color: white !important;
    }
    
    /* Specific sidebar selectors */
    .css-1d391kg .element-container {
        color: white !important;
    }
    
    .css-1d391kg .element-container * {
        color: white !important;
    }
    
    /* Alternative sidebar classes */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown h4 {
        color: white !important;
    }
    
    /* Force white text on all sidebar elements */
    .css-1d391kg div, 
    .css-1d391kg span, 
    .css-1d391kg p, 
    .css-1d391kg h1, 
    .css-1d391kg h2, 
    .css-1d391kg h3, 
    .css-1d391kg h4, 
    .css-1d391kg h5, 
    .css-1d391kg h6 {
        color: white !important;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Button Styling - fundo escuro = texto branco */
    .stButton > button {
        background: linear-gradient(145deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.7rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }
    
    /* Status Cards - fundo claro = texto preto */
    .status-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
        color: #000;
        font-weight: 500;
    }
    
    /* Footer - fundo claro = texto preto */
    .footer {
        text-align: center;
        color: #000;
        background: linear-gradient(145deg, #f8f9fa, #ffffff);
        padding: 2.5rem;
        border-radius: 20px;
        margin-top: 3rem;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
    }
    
    .footer h3 {
        color: #000;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .footer span {
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .footer span:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Loading Animation */
    .loading-animation {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    /* Score Colors */
    .score-excellent { color: #2E8B57; }
    .score-good { color: #FFD700; }
    .score-fair { color: #FF8C00; }
    .score-poor { color: #DC143C; }
    
    /* Map Container */
    .map-container {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    }
    
    /* Analysis Summary */
    .analysis-summary {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    /* Progress Bar Custom */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}

    /* Enhanced text visibility - fundo claro = texto preto */
    .stMarkdown p {
        color: #000 !important;
        font-weight: 500;
    }
    
    .stMarkdown li {
        color: #000 !important;
        font-weight: 500;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: #000 !important;
        font-weight: 600;
    }
    
    /* Ensure all text in containers - fundo claro = texto preto */
    .element-container {
        color: #000;
    }
    
    /* Info boxes and warnings - fundo claro = texto preto */
    .stAlert {
        color: #000 !important;
    }
    
    /* Dataframe text - fundo claro = texto preto */
    .stDataFrame {
        color: #000;
    }
    
    /* Global text visibility improvements */
    .main .stMarkdown p, 
    .main .stMarkdown li,
    .main .stMarkdown span {
        color: #000 !important;
        font-weight: 500;
    }
    
    /* Tab content text visibility */
    .stTabs .tab-content p,
    .stTabs .tab-content li,
    .stTabs .tab-content span {
        color: #000 !important;
    }
    
    /* Metric card improvements */
    .element-container .stMetric {
        color: #000 !important;
    }
    
    /* Progress text */
    .stProgress + div {
        color: #000 !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #2c3e50;
        background: linear-gradient(145deg, #f8f9fa, #ffffff);
        padding: 2.5rem;
        border-radius: 20px;
        margin-top: 3rem;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="main-header">
    <h1>🏙️ UrbanSight</h1>
    <p>Inteligência Imobiliária com Tecnologia de Ponta</p>
    <p style="font-size: 1rem; margin-top: 0.5rem; opacity: 0.9;">
        Análise profunda de propriedades usando OpenStreetMap, IA e Multi-Agentes
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<h3 style="color: white;">🎛️ Painel de Controle</h3>', unsafe_allow_html=True)
    
    # Quick Stats
    if st.session_state.analysis_results:
        st.markdown('<h4 style="color: white;">📊 Estatísticas Rápidas</h4>', unsafe_allow_html=True)
        total_analyses = len(st.session_state.analysis_results)
        successful = sum(1 for r in st.session_state.analysis_results.values() if r.success)
        success_rate = (successful / total_analyses) * 100
        
        st.markdown(f"""
        <div class="status-card">
            <strong>Total de Análises:</strong> {total_analyses}<br>
            <strong>Taxa de Sucesso:</strong> {success_rate:.1f}%<br>
            <strong>Última Análise:</strong> {datetime.now().strftime('%H:%M')}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Analysis history
    if st.session_state.analysis_results:
        st.markdown('<h4 style="color: white;">📋 Histórico de Análises</h4>', unsafe_allow_html=True)
        for address in st.session_state.analysis_results.keys():
            if st.button(f"📍 {address[:25]}...", key=f"hist_{address}", use_container_width=True):
                st.session_state.current_analysis = address
                st.experimental_rerun()
    
    st.markdown("---")

    # Features
    st.markdown('<h4 style="color: white;">✨ Funcionalidades</h4>', unsafe_allow_html=True)
    st.markdown("""
    <div style="color: white;">
    • 🎯 <strong>Análise Instantânea</strong><br>
    • 🗺️ <strong>Mapas Interativos</strong><br>
    • 📊 <strong>Métricas Avançadas</strong><br>
    • 🤖 <strong>Insights com IA</strong><br>
    • 🚶‍♂️ <strong>Walk Score</strong><br>
    • ♿ <strong>Acessibilidade</strong><br>
    • 🌍 <strong>Dados OpenStreetMap</strong><br>
    • 📈 <strong>Relatórios Profissionais</strong>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # About
    st.markdown('<h4 style="color: white;">ℹ️ Sobre o UrbanSight</h4>', unsafe_allow_html=True)
    st.markdown("""
    <div style="color: white;">
    <strong>Versão:</strong> 2.0 Professional<br><br>
    <strong>Tecnologias:</strong><br>
    • OpenStreetMap API<br>
    • Multi-Agentes IA<br>
    • Streamlit<br>
    • Python
    </div>
    """, unsafe_allow_html=True)

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<h3 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🏠 Central de Análise Imobiliária</h3>', unsafe_allow_html=True)
    
    # Search container
    with st.container():
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 2rem;">
            <h4 style="color: #000; margin-bottom: 1rem; font-weight: 600;">🔍 Digite o endereço para análise</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Address input with enhanced styling
        address = st.text_input(
            "Endereço para análise",
            placeholder="Ex: Avenida Paulista, 1000, Bela Vista, São Paulo, SP",
            help="💡 Dica: Quanto mais específico o endereço, mais precisa será a análise",
            label_visibility="collapsed"
        )
        
        # Analysis button with custom styling
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            analyze_button = st.button(
                "🚀 Iniciar Análise UrbanSight", 
                type="primary", 
                use_container_width=True
            )

with col2:
    st.markdown('<h3 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📈 Dashboard</h3>', unsafe_allow_html=True)
    
    if st.session_state.analysis_results:
        # Recent analysis preview
        latest_address = list(st.session_state.analysis_results.keys())[-1]
        latest_result = st.session_state.analysis_results[latest_address]
        
        if latest_result.success:
            st.markdown(f"""
            <div class="custom-metric">
                <h3>Última Análise</h3>
                <div class="value" style="color: {get_score_color(latest_result.metrics.total_score)};">
                    {latest_result.metrics.total_score:.1f}
                </div>
                <div class="grade">Score Geral</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="custom-metric">
            <h3>Status do Sistema</h3>
            <div class="value" style="color: #2E8B57;">🟢</div>
            <div class="grade">Online</div>
        </div>
        """, unsafe_allow_html=True)

# Analysis execution
if analyze_button and address:
    with st.spinner(""):
        # Custom loading message
        st.markdown("""
        <div class="loading-animation">
            <div style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin: 1rem 0;">
                <h3 style="color: white; margin-bottom: 0.5rem;">🤖 UrbanSight em Ação</h3>
                <p style="color: white; margin: 0;">Coletando e analisando dados geográficos...</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Data Collection
                status_text.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">🗺️ Coletando dados do OpenStreetMap...</p>', unsafe_allow_html=True)
                progress_bar.progress(25)
                time.sleep(0.5)
                
                # Run analysis
                result = asyncio.run(orchestrator.analyze_property(address))
                
                # Step 2: Neighborhood Analysis
                status_text.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">🏘️ Analisando características da vizinhança...</p>', unsafe_allow_html=True)
                progress_bar.progress(50)
                time.sleep(0.5)
                
                # Step 3: Advanced Metrics
                status_text.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">📊 Calculando métricas avançadas...</p>', unsafe_allow_html=True)
                progress_bar.progress(75)
                time.sleep(0.5)
                
                # Step 4: AI Insights
                status_text.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">🧠 Gerando insights com IA...</p>', unsafe_allow_html=True)
                progress_bar.progress(100)
                time.sleep(0.5)
                    
                # Store result
                st.session_state.analysis_results[address] = result
                st.session_state.current_analysis = address
                    
                # Clear progress
                progress_bar.empty()
                status_text.empty()
                progress_container.empty()
                    
                if result.success:
                    st.success("✅ Análise UrbanSight concluída com sucesso!")
                    st.balloons()
                else:
                    st.error(f"❌ Erro na análise: {result.error_message}")
                        
        except Exception as e:
            st.error(f"❌ Erro inesperado: {str(e)}")

elif analyze_button and not address:
    st.warning("⚠️ Por favor, digite um endereço válido para análise")

# Results Display
if st.session_state.current_analysis and st.session_state.current_analysis in st.session_state.analysis_results:
    result = st.session_state.analysis_results[st.session_state.current_analysis]
    
    if result.success:
        st.markdown("---")
        
        # Analysis Header
        st.markdown(f"""
        <div class="analysis-summary">
            <h2>📋 Relatório UrbanSight</h2>
            <h3>📍 {result.property_data.address}</h3>
            <p style="color: #333; margin-top: 0.5rem; font-weight: 500;">
                Análise realizada em {datetime.now().strftime('%d/%m/%Y às %H:%M')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Enhanced Metrics Overview
        st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🎯 Painel de Métricas Principais</h4>', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            score = result.metrics.total_score
            color = get_score_color(score)
            st.markdown(f"""
            <div class="custom-metric">
                <h3>Score Total</h3>
                <div class="value" style="color: {color};">{score:.1f}</div>
                <div class="grade">Nota: {get_score_grade(score)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            walk_score = result.metrics.walk_score.overall_score
            color = get_score_color(walk_score)
            st.markdown(f"""
            <div class="custom-metric">
                <h3>Walk Score</h3>
                <div class="value" style="color: {color};">{walk_score:.1f}</div>
                <div class="grade">{result.metrics.walk_score.grade}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            access_score = result.metrics.accessibility_score
            color = get_score_color(access_score)
            st.markdown(f"""
            <div class="custom-metric">
                <h3>Acessibilidade</h3>
                <div class="value" style="color: {color};">{access_score:.1f}</div>
                <div class="grade">Transporte</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            conv_score = result.metrics.convenience_score
            color = get_score_color(conv_score)
            st.markdown(f"""
            <div class="custom-metric">
                <h3>Conveniência</h3>
                <div class="value" style="color: {color};">{conv_score:.1f}</div>
                <div class="grade">Serviços</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            if result.pedestrian_score:
                ped_score = result.pedestrian_score.overall_score
                color = get_score_color(ped_score)
                st.markdown(f"""
                <div class="custom-metric">
                    <h3>Pedestrian</h3>
                    <div class="value" style="color: {color};">{ped_score:.1f}</div>
                    <div class="grade">{result.pedestrian_score.grade}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="custom-metric">
                    <h3>Pedestrian</h3>
                    <div class="value" style="color: #999;">N/A</div>
                    <div class="grade">Sem dados</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Enhanced Tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Resumo Executivo", 
            "🗺️ Mapa Interativo", 
            "📈 Dashboard de Métricas", 
            "💡 Insights & IA", 
            "🔬 Análise Avançada",
            "🌍 Geo-Visualizações",
            "🚶‍♂️ Infraestrutura Urbana"
        ])
        
        with tab1:
            # Enhanced Executive Summary
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📄 Resumo Executivo</h4>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="insight-box">
                <h4>🎯 Análise Geral</h4>
                {result.insights.executive_summary}
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced Strengths and Concerns
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">✅ Pontos Fortes</h4>', unsafe_allow_html=True)
                for i, strength in enumerate(result.insights.strengths, 1):
                    st.markdown(f"""
                    <div style="background: #d4edda; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #28a745;">
                        <strong>{i}.</strong> {strength}
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">⚠️ Pontos de Atenção</h4>', unsafe_allow_html=True)
                for i, concern in enumerate(result.insights.concerns, 1):
                    st.markdown(f"""
                    <div style="background: #f8d7da; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #dc3545;">
                        <strong>{i}.</strong> {concern}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Enhanced Ideal Resident Profile
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">👥 Perfil Ideal do Morador</h4>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="insight-box">
                <h4>🎯 Recomendação UrbanSight</h4>
                {result.insights.ideal_resident_profile}
            </div>
            """, unsafe_allow_html=True)
        
        with tab2:
            # Enhanced Interactive Map
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🗺️ Mapa Interativo UrbanSight</h4>', unsafe_allow_html=True)
            
            # Map controls
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;">🎛️ Controles do Mapa</p>', unsafe_allow_html=True)
                st.markdown("""
                <div style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px;">
                • 🏠 <strong>Vermelho</strong>: Propriedade<br>
                • 🔵 <strong>Azul</strong>: Educação<br>
                • 🟢 <strong>Verde</strong>: Saúde<br>
                • 🟠 <strong>Laranja</strong>: Compras<br>
                • 🟣 <strong>Roxo</strong>: Transporte
                </div>
                """, unsafe_allow_html=True)
            
            with col1:
                # Create and display map
                m = create_folium_map(result)
                folium_static(m, width=800, height=600)
            
            # Enhanced POI Categories
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📍 Distribuição de Pontos de Interesse</h4>', unsafe_allow_html=True)
            categories = result.metrics.category_counts
            
            # Create visual POI summary
            poi_cols = st.columns(len(categories))
            for i, (category, count) in enumerate(categories.items()):
                with poi_cols[i]:
                    st.markdown(f"""
                        <div class="poi-category">
                            {category.title()}: {count}
                        </div>
                    """, unsafe_allow_html=True)
        
        with tab3:
            # Enhanced Metrics Dashboard
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📊 Dashboard Completo de Métricas</h4>', unsafe_allow_html=True)
            
            # Score breakdown with enhanced visualization
            scores_data = {
                'Métrica': ['Walk Score', 'Acessibilidade', 'Conveniência', 'Segurança', 'Qualidade de Vida'],
                'Pontuação': [
                    result.metrics.walk_score.overall_score,
                    result.metrics.accessibility_score,
                    result.metrics.convenience_score,
                    result.metrics.safety_score,
                    result.metrics.quality_of_life_score
                ]
            }
            
            # Enhanced bar chart
            fig = px.bar(
                scores_data,
                x='Métrica',
                y='Pontuação',
                title='🎯 Breakdown Detalhado de Pontuações',
                color='Pontuação',
                color_continuous_scale='RdYlGn',
                text='Pontuação'
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(
                height=500,
                showlegend=False,
                title_font_size=16,
                title_x=0.5
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Enhanced POI density visualization
            if result.metrics.poi_density:
                col1, col2 = st.columns(2)
                
                with col1:
                    density_df = pd.DataFrame(
                        list(result.metrics.poi_density.items()),
                        columns=['Categoria', 'Densidade (por km²)']
                    )
                    
                    fig2 = px.pie(
                        density_df,
                        values='Densidade (por km²)',
                        names='Categoria',
                        title='🥧 Distribuição de Densidade por Categoria',
                        hole=0.4
                    )
                    fig2.update_layout(height=400)
                    st.plotly_chart(fig2, use_container_width=True)
                
                with col2:
                    # Enhanced closest POIs table
                    st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📍 POIs Mais Próximos</h4>', unsafe_allow_html=True)
            
                    closest_data = []
                    for category, poi in result.metrics.closest_pois.items():
                        closest_data.append({
                            'Categoria': category.title(),
                            'Nome': poi.name,
                            'Distância': f"{poi.distance:.0f}m",
                            'Tipo': poi.subcategory.replace('_', ' ').title()
                        })
                    
                    if closest_data:
                        closest_df = pd.DataFrame(closest_data)
                        st.dataframe(
                            closest_df, 
                            use_container_width=True,
                            hide_index=True
                        )
        
        with tab4:
            # Enhanced AI Insights
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🧠 Insights Gerados por IA</h4>', unsafe_allow_html=True)
            
            # Neighborhood description with enhanced styling
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🏘️ Análise da Vizinhança</h4>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="insight-box">
                <h4>📍 Características Locais</h4>
                {result.insights.neighborhood_description}
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced recommendations
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">💡 Recomendações Estratégicas</h4>', unsafe_allow_html=True)
            for i, rec in enumerate(result.insights.recommendations, 1):
                st.markdown(f"""
                <div style="background: #e7f3ff; padding: 1rem; border-radius: 10px; margin: 0.5rem 0; border-left: 4px solid #0066cc;">
                    <strong>💡 Recomendação {i}:</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
            
            # Market positioning with enhanced design
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📈 Posicionamento no Mercado</h4>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="insight-box">
                    <h4>💰 Análise de Mercado</h4>
                    {result.insights.market_positioning}
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">💎 Potencial de Investimento</h4>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="insight-box">
                    <h4>📊 Projeção de Investimento</h4>
                    {result.insights.investment_potential}
                </div>
                """, unsafe_allow_html=True)
        
        with tab5:
            # Enhanced Advanced Metrics
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🔬 Métricas Avançadas UrbanSight</h4>', unsafe_allow_html=True)
            
            if result.advanced_metrics:
                # Service density with enhanced visualization
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📊 Análise de Densidade de Serviços</h4>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    score = result.advanced_metrics.service_density.service_variety_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Variedade</h3>
                        <div class="value" style="color: {color};">{score:.1f}</div>
                        <div class="grade">Diversidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    score = result.advanced_metrics.service_density.completeness_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Completude</h3>
                        <div class="value" style="color: {color};">{score:.1f}</div>
                        <div class="grade">Cobertura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    total = result.advanced_metrics.service_density.total_services
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Total</h3>
                        <div class="value" style="color: #2E8B57;">{total}</div>
                        <div class="grade">Serviços</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    density = result.advanced_metrics.service_density.total_services / 1.0  # per km²
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Densidade</h3>
                        <div class="value" style="color: #667eea;">{density:.0f}</div>
                        <div class="grade">por km²</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Enhanced urban diversity
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🌆 Diversidade Urbana</h4>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    shannon = result.advanced_metrics.urban_diversity.shannon_diversity_index
                    color = get_score_color(shannon)
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Índice Shannon</h3>
                        <div class="value" style="color: {color};">{shannon:.1f}</div>
                        <div class="grade">Diversidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    dominant = result.advanced_metrics.urban_diversity.dominant_category
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Categoria Dominante</h3>
                        <div class="value" style="color: #764ba2; font-size: 1.2rem;">{dominant.title()}</div>
                        <div class="grade">Principal</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Enhanced lifestyle metrics
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🎯 Métricas de Estilo de Vida</h4>', unsafe_allow_html=True)
                
                lifestyle_aspects = ['Vida Cotidiana', 'Entretenimento', 'Família', 'Profissional']
                lifestyle_scores = [
                    result.advanced_metrics.lifestyle.daily_life_score,
                    result.advanced_metrics.lifestyle.entertainment_score,
                    result.advanced_metrics.lifestyle.family_friendliness,
                    result.advanced_metrics.lifestyle.professional_score
                ]
                
                # Create radar chart using plotly.graph_objects
                fig = go.Figure()
                
                fig.add_trace(go.Scatterpolar(
                    r=lifestyle_scores,
                    theta=lifestyle_aspects,
                    fill='toself',
                    name='Scores de Estilo de Vida',
                    line_color='rgba(102, 126, 234, 0.8)',
                    fillcolor='rgba(102, 126, 234, 0.3)'
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )),
                    showlegend=False,
                    title="🎯 Radar de Estilo de Vida",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Enhanced other metrics
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🌱 Indicadores Ambientais e Urbanos</h4>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    green_score = result.advanced_metrics.green_space_score
                    color = get_score_color(green_score)
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Espaços Verdes</h3>
                        <div class="value" style="color: {color};">{green_score:.1f}</div>
                        <div class="grade">Sustentabilidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    urban_score = result.advanced_metrics.urban_intensity_score
                    color = get_score_color(urban_score)
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>Intensidade Urbana</h3>
                        <div class="value" style="color: {color};">{urban_score:.1f}</div>
                        <div class="grade">Densidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
            else:
                st.warning("⚠️ Métricas avançadas não disponíveis para esta análise.")
        
        with tab6:
            # Enhanced Geographic Visualizations
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🌍 Centro de Visualizações Geográficas</h4>', unsafe_allow_html=True)
            
            if hasattr(result, 'advanced_maps') and result.advanced_maps:
                # Enhanced map selector
                st.markdown("""
                <div style="background: linear-gradient(145deg, #f8f9fa, #e9ecef); padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
                    <h4 style="color: #333; margin-bottom: 1rem;">🗺️ Selecione uma Visualização</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Available maps with enhanced options
                map_options = {
                    'distance_zones': '📏 Zonas de Proximidade',
                    'service_clusters': '🎯 Clusters Inteligentes',
                    'walkability_directions': '🧭 Análise Direcional',
                    'service_gaps': '⚠️ Gaps de Cobertura',
                    'heatmap_food': '🍽️ Heatmap: Alimentação',
                    'heatmap_transport': '🚌 Heatmap: Transporte',
                    'heatmap_healthcare': '🏥 Heatmap: Saúde',
                    'heatmap_education': '🎓 Heatmap: Educação',
                    'heatmap_shopping': '🛍️ Heatmap: Compras'
                }
                
                # Filter available maps
                available_maps = {k: v for k, v in map_options.items() if k in result.advanced_maps}
                
                if available_maps:
                    selected_map = st.selectbox(
                        "",
                        options=list(available_maps.keys()),
                        format_func=lambda x: available_maps[x],
                        key="map_selector",
                        label_visibility="collapsed"
                    )
                    
                    # Display selected map with enhanced container
                    if selected_map in result.advanced_maps:
                        st.markdown('<div class="map-container">', unsafe_allow_html=True)
                        display_advanced_map(result.advanced_maps[selected_map])
                        st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    st.warning("🗺️ Nenhuma visualização avançada disponível para esta análise.")
            
            else:
                st.markdown("""
                <div class="insight-box">
                    <h4>🗺️ Visualizações Disponíveis</h4>
                    <p>Para acessar as visualizações geográficas avançadas, realize uma nova análise.</p>
                    
                    <h5>📍 Tipos de Visualização:</h5>
                    <ul>
                        <li><strong>📏 Zonas de Proximidade:</strong> POIs organizados por distância</li>
                        <li><strong>🎯 Clusters Inteligentes:</strong> Agrupamentos de serviços</li>
                        <li><strong>🧭 Análise Direcional:</strong> Distribuição por direção</li>
                        <li><strong>⚠️ Gaps de Cobertura:</strong> Lacunas de serviços</li>
                        <li><strong>🔥 Heatmaps:</strong> Densidade por categoria</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        with tab7:
            # Enhanced Pedestrian Infrastructure
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🚶‍♂️ Centro de Análise de Infraestrutura Pedestre</h4>', unsafe_allow_html=True)
            
            if result.pedestrian_score:
                # Enhanced overall pedestrian score
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🏆 Pontuação Geral de Caminhabilidade</h4>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    score = result.pedestrian_score.overall_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Pedestrian Score</h3>
                        <h4 style="color: {color}; margin: 0;">{result.pedestrian_score.grade}</h4>
                        <p style="color: #333; margin-top: 1rem; font-weight: 500;">{result.pedestrian_score.description}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Enhanced detailed scores with icons
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">📊 Análise Detalhada por Categoria</h4>', unsafe_allow_html=True)
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                pedestrian_metrics = [
                    ("🛤️", "Calçadas", result.pedestrian_score.sidewalk_score, "Infraestrutura"),
                    ("🚦", "Travessias", result.pedestrian_score.crossing_score, "Segurança"),
                    ("🛡️", "Proteção", result.pedestrian_score.safety_score, "Iluminação"),
                    ("♿", "Acessibilidade", result.pedestrian_score.accessibility_score, "Inclusão"),
                    ("😊", "Conforto", result.pedestrian_score.comfort_score, "Qualidade")
                ]
                
                for i, (icon, title, score, subtitle) in enumerate(pedestrian_metrics):
                    with [col1, col2, col3, col4, col5][i]:
                        color = get_score_color(score)
                        st.markdown(f"""
                        <div class="custom-metric">
                            <h3>{icon} {title}</h3>
                            <div class="value" style="color: {color};">{score:.1f}</div>
                            <div class="grade">{subtitle}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Enhanced pedestrian features analysis
                st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🔍 Análise Técnica da Infraestrutura</h4>', unsafe_allow_html=True)
                
                st.markdown("""
                <div class="insight-box">
                    <h4>🛤️ Metodologia UrbanSight</h4>
                    <p>Nossa análise utiliza dados reais do OpenStreetMap para avaliar a qualidade da infraestrutura pedestre:</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Technical details in columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px;">
                    <strong>🛤️ Análise de Calçadas:</strong><br>
                    • Presença e continuidade<br>
                    • Qualidade da superfície<br>
                    • Largura adequada<br>
                    • Iluminação pública<br>
                    • Acessibilidade universal<br><br>
                    
                    <strong>🚦 Segurança em Travessias:</strong><br>
                    • Faixas de pedestres sinalizadas<br>
                    • Semáforos inteligentes<br>
                    • Tempo de travessia adequado<br>
                    • Piso tátil para deficientes visuais
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px;">
                    <strong>🛡️ Fatores de Segurança:</strong><br>
                    • Velocidade das vias (≤30 km/h ideal)<br>
                    • Densidade de iluminação pública<br>
                    • Separação do tráfego veicular<br>
                    • Visibilidade em cruzamentos<br><br>
                    
                    <strong>♿ Acessibilidade Universal:</strong><br>
                    • Rampas e meio-fios rebaixados<br>
                    • Sinalização tátil adequada<br>
                    • Obstáculos na via<br>
                    • Largura mínima de passagem
                    </div>
                    """, unsafe_allow_html=True)
                
            else:
                st.markdown("""
                <div class="insight-box">
                    <h4>⚠️ Dados de Infraestrutura Indisponíveis</h4>
                    <p>Os dados de infraestrutura pedestre não estão disponíveis para esta região.</p>
                    
                    <h5>🔍 Possíveis Motivos:</h5>
                    <ul>
                        <li><strong>Cobertura Limitada:</strong> Região com poucos dados no OpenStreetMap</li>
                        <li><strong>Área Rural:</strong> Foco urbano da análise</li>
                        <li><strong>Dados Incompletos:</strong> Mapeamento colaborativo em andamento</li>
                    </ul>
                    
                    <h5>💡 Sugestões:</h5>
                    <ul>
                        <li>Teste um endereço em área urbana consolidada</li>
                        <li>Contribua para o OpenStreetMap com dados locais</li>
                        <li>Aguarde futuras atualizações do mapeamento</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

# Enhanced Footer
st.markdown("---")

# Footer com componentes nativos do Streamlit
st.markdown('<h3 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; text-align: center; margin-bottom: 1rem;">🏙️ UrbanSight - Inteligência Imobiliária</h3>', unsafe_allow_html=True)
st.markdown('<p style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 1.5rem;">Versão 2.0 Professional</p>', unsafe_allow_html=True)

# Tecnologias usando columns
st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; text-align: center;">🚀 Tecnologias Utilizadas</h4>', unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(145deg, #667eea, #764ba2); color: white; padding: 0.8rem; border-radius: 15px; margin: 0.2rem;">
        <strong>🗺️<br>OpenStreetMap</strong>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(145deg, #667eea, #764ba2); color: white; padding: 0.8rem; border-radius: 15px; margin: 0.2rem;">
        <strong>🤖<br>Multi-Agentes</strong>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(145deg, #667eea, #764ba2); color: white; padding: 0.8rem; border-radius: 15px; margin: 0.2rem;">
        <strong>📊<br>Analytics</strong>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(145deg, #667eea, #764ba2); color: white; padding: 0.8rem; border-radius: 15px; margin: 0.2rem;">
        <strong>🌍<br>Geo-Intelligence</strong>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(145deg, #667eea, #764ba2); color: white; padding: 0.8rem; border-radius: 15px; margin: 0.2rem;">
        <strong>💡<br>IA Generativa</strong>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Informações finais centralizadas
st.markdown("""
<div style="text-align: center; margin-top: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px;">
    <p style="font-size: 0.9rem; color: white; font-weight: 500;">
        © UrbanSight • Análise Imobiliária Inteligente • Dados OpenStreetMap
    </p>
</div>
""", unsafe_allow_html=True) 