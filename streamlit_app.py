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
from agents.profile_chatbot import ProfileChatbot, ProfileChatbotResult
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
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'show_profile_chatbot' not in st.session_state:
    st.session_state.show_profile_chatbot = False

# Initialize orchestrator
@st.cache_resource
def get_orchestrator():
    return PropertyAnalysisOrchestrator()

orchestrator = get_orchestrator()

@st.cache_resource
def get_profile_chatbot():
    return ProfileChatbot()

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
                st.rerun()
    
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
        
        # Profile Chatbot Button
        st.markdown("---")
        col_profile1, col_profile2, col_profile3 = st.columns([1, 2, 1])
        with col_profile2:
            if st.button("🤖 Definir Meu Perfil Primeiro", use_container_width=True):
                st.session_state.show_profile_chatbot = True

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

# Profile Chatbot Section
if st.session_state.show_profile_chatbot:
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin: 1rem 0;">
        <h2 style="color: white; text-align: center; margin: 0;">🤖 Chatbot de Perfil UrbanSight</h2>
        <p style="color: white; text-align: center; margin: 0.5rem 0;">Vamos conhecer suas preferências para personalizar suas análises</p>
    </div>
    """, unsafe_allow_html=True)
    
    profile_chatbot = get_profile_chatbot()
    questions = profile_chatbot.get_questions()
    
    # Initialize responses in session state
    if 'chatbot_responses' not in st.session_state:
        st.session_state.chatbot_responses = {}
    
    # Display questions
    for question in questions:
        st.markdown(f"### {question.question}")
        
        if question.question_type == "single":
            response = st.radio(
                "Selecione uma opção:",
                question.options,
                key=f"q_{question.id}",
                label_visibility="collapsed"
            )
            st.session_state.chatbot_responses[question.id] = response
            
        elif question.question_type == "multiple":
            responses = st.multiselect(
                "Selecione uma ou mais opções:",
                question.options,
                key=f"q_{question.id}",
                default=st.session_state.chatbot_responses.get(question.id, [])
            )
            st.session_state.chatbot_responses[question.id] = responses
        
        st.markdown("---")
    
    # Process profile button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ Finalizar Perfil", type="primary", use_container_width=True):
            try:
                profile_result = profile_chatbot.process_responses(st.session_state.chatbot_responses)
                if profile_result.success:
                    st.session_state.user_profile = profile_result
                    st.session_state.show_profile_chatbot = False
                    st.success("✅ Perfil criado com sucesso!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ Erro ao processar perfil: {profile_result.error_message}")
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")
    
    # Close chatbot button
    if st.button("❌ Pular por enquanto"):
        st.session_state.show_profile_chatbot = False
        st.rerun()

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
        
        # Enhanced Tabs with New Specialized Analyses
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
            "📊 Resumo Executivo", 
            "🗺️ Mapa Interativo", 
            "📈 Dashboard Original", 
            "🌿 Análise Ambiental",
            "🚗 Mobilidade Avançada",
            "🏗️ Infraestrutura Urbana", 
            "🛡️ Segurança & Emergência",
            "💼 Economia Local",
            "✨ Características Especiais",
            "🤖 Insights com IA",
            "🚶‍♂️ Infraestrutura Pedestre",
            "💰 Análise de Investimento",
            "📈 Tendências Urbanas",
            "👤 Recomendações Personalizadas"
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
                        "Selecione o tipo de mapa:",
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
        
        with tab4:
            # Análise Ambiental
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #4CAF50 0%, #8BC34A 100%); padding: 1rem; border-radius: 10px; text-align: center;">🌿 Análise Ambiental Completa</h4>', unsafe_allow_html=True)
            
            if result.environmental_metrics:
                env = result.environmental_metrics
                
                # Score geral ambiental
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = env.environmental_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Score Ambiental</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas detalhadas
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌳 Microclima</h3>
                        <div class="value" style="color: {get_score_color(env.microclimate.overall_climate_score)};">{env.microclimate.overall_climate_score:.1f}</div>
                        <div class="grade">Conforto Térmico</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>💧 Recursos Hídricos</h3>
                        <div class="value" style="color: {get_score_color(env.water_features.overall_water_score)};">{env.water_features.overall_water_score:.1f}</div>
                        <div class="grade">Qualidade da Paisagem</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌲 Espaços Verdes</h3>
                        <div class="value" style="color: {get_score_color(env.green_space_index)};">{env.green_space_index:.1f}</div>
                        <div class="grade">Índice Verde</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌬️ Qualidade do Ar</h3>
                        <div class="value" style="color: {get_score_color(env.air_quality_estimate)};">{env.air_quality_estimate:.1f}</div>
                        <div class="grade">Estimativa</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏝️ Ilha de Calor</h3>
                        <div class="value" style="color: {get_score_color(100 - env.microclimate.heat_island_risk)};">{env.microclimate.heat_island_risk:.1f}%</div>
                        <div class="grade">Risco</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detalhes dos recursos hídricos
                if env.water_features.water_features:
                    st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px;">💧 Recursos Hídricos Próximos</h5>')
                    for feature in env.water_features.water_features[:5]:
                        st.markdown(f"""
                        <div style="background: #F0F8F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            <strong>{feature.name}</strong> - {feature.feature_type.title()} ({feature.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados ambientais não disponíveis para esta localização")
        
        with tab5:
            # Mobilidade Avançada
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #2196F3 0%, #03A9F4 100%); padding: 1rem; border-radius: 10px; text-align: center;">🚗 Análise de Mobilidade Avançada</h4>', unsafe_allow_html=True)
            
            if result.mobility_metrics:
                mob = result.mobility_metrics
                
                # Score geral de mobilidade
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = mob.overall_mobility_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Score de Mobilidade</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas de mobilidade
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚌 Transporte Público</h3>
                        <div class="value" style="color: {get_score_color(mob.public_transport_metrics.overall_transport_score)};">{mob.public_transport_metrics.overall_transport_score:.1f}</div>
                        <div class="grade">Cobertura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚲 Ciclabilidade</h3>
                        <div class="value" style="color: {get_score_color(mob.bike_metrics.overall_bike_score)};">{mob.bike_metrics.overall_bike_score:.1f}</div>
                        <div class="grade">Infraestrutura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🅿️ Estacionamento</h3>
                        <div class="value" style="color: {get_score_color(mob.parking_metrics.overall_parking_score)};">{mob.parking_metrics.overall_parking_score:.1f}</div>
                        <div class="grade">Disponibilidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌱 Sustentabilidade</h3>
                        <div class="value" style="color: {get_score_color(mob.sustainable_mobility_score)};">{mob.sustainable_mobility_score:.1f}</div>
                        <div class="grade">Mobilidade Verde</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚗 Dependência</h3>
                        <div class="value" style="color: {get_score_color(100 - mob.car_dependency_score)};">{mob.car_dependency_score:.1f}%</div>
                        <div class="grade">Carros</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detalhes do transporte público
                if mob.public_transport_metrics.transport_stops:
                    st.markdown('<h5 style="background: #E3F2FD; padding: 0.8rem; border-radius: 8px;">🚌 Paradas de Transporte Próximas</h5>')
                    for stop in mob.public_transport_metrics.transport_stops[:5]:
                        st.markdown(f"""
                        <div style="background: #F0F4F8; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            <strong>{stop.name}</strong> - {stop.transport_type.title()} ({stop.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de mobilidade não disponíveis para esta localização")
        
        with tab6:
            # Infraestrutura Urbana
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); padding: 1rem; border-radius: 10px; text-align: center;">🏗️ Análise de Infraestrutura Urbana</h4>', unsafe_allow_html=True)
            
            if result.urban_metrics:
                urban = result.urban_metrics
                
                # Score geral urbano
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = urban.livability_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Habitabilidade Urbana</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas urbanas
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏢 Densidade</h3>
                        <div class="value" style="color: {get_score_color(min(urban.building_metrics.building_density/10, 100))};">{urban.building_metrics.building_density:.0f}</div>
                        <div class="grade">Edif./km²</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🔊 Ruído</h3>
                        <div class="value" style="color: {get_score_color(urban.noise_metrics.overall_noise_score)};">{urban.noise_metrics.estimated_noise_level:.0f}dB</div>
                        <div class="grade">Nível Estimado</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>⚡ Infraestrutura</h3>
                        <div class="value" style="color: {get_score_color(urban.infrastructure_metrics.overall_infrastructure_score)};">{urban.infrastructure_metrics.overall_infrastructure_score:.1f}</div>
                        <div class="grade">Qualidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌆 Desenvolvimento</h3>
                        <div class="value" style="color: {get_score_color(urban.urban_development_score)};">{urban.urban_development_score:.1f}</div>
                        <div class="grade">Urbano</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚀 Potencial</h3>
                        <div class="value" style="color: {get_score_color(urban.future_development_potential)};">{urban.future_development_potential:.1f}</div>
                        <div class="grade">Futuro</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Análise de ruído
                st.markdown('<h5 style="background: #FFF3E0; padding: 0.8rem; border-radius: 8px;">🔊 Análise de Ruído Urbano</h5>')
                noise_zones = urban.noise_metrics.noise_zones
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: #E8F5E8; padding: 1rem; border-radius: 8px; text-align: center;">
                        <h4>🔇 Zona Silenciosa</h4>
                        <h3>{noise_zones['quiet']:.1f}%</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: #FFF8E1; padding: 1rem; border-radius: 8px; text-align: center;">
                        <h4>🔉 Zona Moderada</h4>
                        <h3>{noise_zones['moderate']:.1f}%</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background: #FFEBEE; padding: 1rem; border-radius: 8px; text-align: center;">
                        <h4>🔊 Zona Ruidosa</h4>
                        <h3>{noise_zones['noisy']:.1f}%</h3>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de infraestrutura urbana não disponíveis para esta localização")
        
        with tab7:
            # Segurança & Emergência
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #F44336 0%, #E91E63 100%); padding: 1rem; border-radius: 10px; text-align: center;">🛡️ Análise de Segurança & Emergência</h4>', unsafe_allow_html=True)
            
            if result.safety_metrics:
                safety = result.safety_metrics
                
                # Score geral de segurança
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = safety.overall_safety_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Score de Segurança</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas de segurança
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚨 Emergência</h3>
                        <div class="value" style="color: {get_score_color(safety.emergency_metrics.overall_emergency_score)};">{safety.emergency_metrics.overall_emergency_score:.1f}</div>
                        <div class="grade">Cobertura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🔦 Iluminação</h3>
                        <div class="value" style="color: {get_score_color(safety.crime_prevention_metrics.lighting_coverage)};">{safety.crime_prevention_metrics.lighting_coverage:.1f}</div>
                        <div class="grade">Cobertura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>👁️ Vigilância</h3>
                        <div class="value" style="color: {get_score_color(safety.crime_prevention_metrics.surveillance_coverage)};">{safety.crime_prevention_metrics.surveillance_coverage:.1f}</div>
                        <div class="grade">Câmeras</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>👮 Polícia</h3>
                        <div class="value" style="color: {get_score_color(safety.crime_prevention_metrics.police_presence)};">{safety.crime_prevention_metrics.police_presence:.1f}</div>
                        <div class="grade">Presença</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>👁️‍🗨️ Visibilidade</h3>
                        <div class="value" style="color: {get_score_color(safety.crime_prevention_metrics.visibility_score)};">{safety.crime_prevention_metrics.visibility_score:.1f}</div>
                        <div class="grade">Urbana</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Serviços de emergência próximos
                if safety.emergency_metrics.emergency_services:
                    st.markdown('<h5 style="background: #FFEBEE; padding: 0.8rem; border-radius: 8px;">🚨 Serviços de Emergência Próximos</h5>')
                    for service in safety.emergency_metrics.emergency_services[:5]:
                        icon = "🏥" if service.service_type == "hospital" else "👮" if service.service_type == "police" else "🚒"
                        st.markdown(f"""
                        <div style="background: #F8F8F8; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            {icon} <strong>{service.name}</strong> - {service.service_type.title()} ({service.distance:.0f}m) - ⏱️ {service.response_time_estimate:.1f}min
                        </div>
                        """, unsafe_allow_html=True)
                
                # Recomendações de segurança
                if safety.safety_recommendations:
                    st.markdown('<h5 style="background: #FFEBEE; padding: 0.8rem; border-radius: 8px;">💡 Recomendações de Segurança</h5>')
                    for i, rec in enumerate(safety.safety_recommendations, 1):
                        st.markdown(f"""
                        <div style="background: #FFF8F8; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #F44336;">
                            <strong>{i}.</strong> {rec}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de segurança não disponíveis para esta localização")
        

        
        with tab8:
            # Economia Local
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #607D8B 0%, #455A64 100%); padding: 1rem; border-radius: 10px; text-align: center;">💼 Análise de Economia Local</h4>', unsafe_allow_html=True)
            
            if result.economy_metrics:
                economy = result.economy_metrics
                
                # Score geral de economia
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = economy.overall_local_economy_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Economia Local</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas econômicas
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏪 Vitalidade</h3>
                        <div class="value" style="color: {get_score_color(economy.economy_vitality_metrics.overall_economy_score)};">{economy.economy_vitality_metrics.overall_economy_score:.1f}</div>
                        <div class="grade">Negócios</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🎨 Cultura</h3>
                        <div class="value" style="color: {get_score_color(economy.cultural_richness_metrics.overall_cultural_score)};">{economy.cultural_richness_metrics.overall_cultural_score:.1f}</div>
                        <div class="grade">Riqueza Cultural</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🛒 Varejo</h3>
                        <div class="value" style="color: {get_score_color(economy.retail_accessibility_metrics.overall_retail_score)};">{economy.retail_accessibility_metrics.overall_retail_score:.1f}</div>
                        <div class="grade">Acessibilidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏘️ Caráter Local</h3>
                        <div class="value" style="color: {get_score_color(economy.local_character_score)};">{economy.local_character_score:.1f}</div>
                        <div class="grade">Identidade</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>💪 Resiliência</h3>
                        <div class="value" style="color: {get_score_color(economy.economic_resilience_score)};">{economy.economic_resilience_score:.1f}</div>
                        <div class="grade">Econômica</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Estabelecimentos comerciais
                if economy.economy_vitality_metrics.economic_establishments:
                    st.markdown('<h5 style="background: #ECEFF1; padding: 0.8rem; border-radius: 8px;">🏪 Estabelecimentos Comerciais</h5>')
                    establishments = economy.economy_vitality_metrics.economic_establishments[:5]
                    for est in establishments:
                        icon = "🛒" if est.business_type == "shop" else "🏢" if est.business_type == "office" else "🔨"
                        st.markdown(f"""
                        <div style="background: #F5F5F5; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            {icon} <strong>{est.name}</strong> - {est.business_category.title()} ({est.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
                
                # Locais culturais
                if economy.cultural_richness_metrics.cultural_venues:
                    st.markdown('<h5 style="background: #ECEFF1; padding: 0.8rem; border-radius: 8px;">🎨 Locais Culturais</h5>')
                    venues = economy.cultural_richness_metrics.cultural_venues[:5]
                    for venue in venues:
                        icon = "🏛️" if venue.venue_type == "museum" else "🎭" if venue.venue_type == "theatre" else "🖼️"
                        st.markdown(f"""
                        <div style="background: #F5F5F5; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            {icon} <strong>{venue.name}</strong> - {venue.venue_type.title()} ({venue.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de economia local não disponíveis para esta localização")
        
        with tab9:
            # Características Especiais
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #795548 0%, #5D4037 100%); padding: 1rem; border-radius: 10px; text-align: center;">✨ Características Especiais</h4>', unsafe_allow_html=True)
            
            if result.special_features_metrics:
                special = result.special_features_metrics
                
                # Score geral de características especiais
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = special.overall_special_features_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Características Especiais</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas especiais
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>💻 Digital</h3>
                        <div class="value" style="color: {get_score_color(special.digital_infrastructure_metrics.overall_digital_score)};">{special.digital_infrastructure_metrics.overall_digital_score:.1f}</div>
                        <div class="grade">Infraestrutura</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>♿ Acessibilidade</h3>
                        <div class="value" style="color: {get_score_color(special.universal_accessibility_metrics.overall_accessibility_score)};">{special.universal_accessibility_metrics.overall_accessibility_score:.1f}</div>
                        <div class="grade">Universal</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🌙 Vida Noturna</h3>
                        <div class="value" style="color: {get_score_color(special.nightlife_metrics.overall_nightlife_score)};">{special.nightlife_metrics.overall_nightlife_score:.1f}</div>
                        <div class="grade">& 24h</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚀 Inovação</h3>
                        <div class="value" style="color: {get_score_color(special.innovation_index)};">{special.innovation_index:.1f}</div>
                        <div class="grade">Índice</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🤝 Inclusão Social</h3>
                        <div class="value" style="color: {get_score_color(special.social_inclusion_score)};">{special.social_inclusion_score:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Infraestrutura digital
                if special.digital_infrastructure_metrics.digital_infrastructure:
                    st.markdown('<h5 style="background: #EFEBE9; padding: 0.8rem; border-radius: 8px;">💻 Infraestrutura Digital</h5>')
                    digital_infra = special.digital_infrastructure_metrics.digital_infrastructure[:5]
                    for infra in digital_infra:
                        icon = "📶" if infra.infrastructure_type == "wifi_hotspot" else "☕" if infra.infrastructure_type == "internet_cafe" else "🏢"
                        st.markdown(f"""
                        <div style="background: #F3F0F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            {icon} <strong>{infra.name}</strong> - {infra.infrastructure_type.replace('_', ' ').title()} ({infra.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
                
                # Vida noturna
                if special.nightlife_metrics.nightlife_venues:
                    st.markdown('<h5 style="background: #EFEBE9; padding: 0.8rem; border-radius: 8px;">🌙 Vida Noturna & Serviços 24h</h5>')
                    nightlife = special.nightlife_metrics.nightlife_venues[:5]
                    for venue in nightlife:
                        icon = "🍺" if venue.venue_type == "bar" else "🏪" if "24h" in venue.venue_type else "🌙"
                        st.markdown(f"""
                        <div style="background: #F3F0F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                            {icon} <strong>{venue.name}</strong> - {venue.venue_type.replace('_', ' ').title()} ({venue.distance:.0f}m)
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de características especiais não disponíveis para esta localização")
        
        with tab10:
            # Insights com IA
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); padding: 1rem; border-radius: 10px; text-align: center;">🤖 Insights Avançados com Inteligência Artificial</h4>', unsafe_allow_html=True)
            
            if result.insights:
                insights = result.insights
                
                # Resumo Executivo com IA
                st.markdown('<h5 style="background: #FFF3E0; padding: 0.8rem; border-radius: 8px; color: #E65100;">🎯 Análise Executiva da IA</h5>')
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #FFF8E1 0%, #FFF3E0 100%); padding: 1.5rem; border-radius: 15px; border-left: 5px solid #FF6B35; margin: 1rem 0;">
                    <h4 style="color: #E65100; margin-top: 0;">📋 Resumo Inteligente</h4>
                    <p style="color: #333; font-size: 1.1rem; line-height: 1.6;">{insights.executive_summary}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Análise Detalhada de Pontos Fortes
                st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px; color: #2E7D32;">✅ Análise de Pontos Fortes</h5>')
                col1, col2 = st.columns(2)
                
                with col1:
                    for i, strength in enumerate(insights.strengths[:3], 1):
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%); padding: 1rem; border-radius: 12px; margin: 0.8rem 0; border-left: 4px solid #4CAF50;">
                            <h6 style="color: #2E7D32; margin: 0; font-weight: bold;">💪 Força #{i}</h6>
                            <p style="color: #1B5E20; margin: 0.5rem 0 0 0; font-size: 0.95rem;">{strength}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    for i, strength in enumerate(insights.strengths[3:6], 4):
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%); padding: 1rem; border-radius: 12px; margin: 0.8rem 0; border-left: 4px solid #4CAF50;">
                            <h6 style="color: #2E7D32; margin: 0; font-weight: bold;">💪 Força #{i}</h6>
                            <p style="color: #1B5E20; margin: 0.5rem 0 0 0; font-size: 0.95rem;">{strength}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Análise Detalhada de Pontos de Atenção
                st.markdown('<h5 style="background: #FFEBEE; padding: 0.8rem; border-radius: 8px; color: #C62828;">⚠️ Análise de Pontos de Atenção</h5>')
                col1, col2 = st.columns(2)
                
                with col1:
                    for i, concern in enumerate(insights.concerns[:3], 1):
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%); padding: 1rem; border-radius: 12px; margin: 0.8rem 0; border-left: 4px solid #F44336;">
                            <h6 style="color: #C62828; margin: 0; font-weight: bold;">🚨 Atenção #{i}</h6>
                            <p style="color: #B71C1C; margin: 0.5rem 0 0 0; font-size: 0.95rem;">{concern}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    for i, concern in enumerate(insights.concerns[3:6], 4):
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%); padding: 1rem; border-radius: 12px; margin: 0.8rem 0; border-left: 4px solid #F44336;">
                            <h6 style="color: #C62828; margin: 0; font-weight: bold;">🚨 Atenção #{i}</h6>
                            <p style="color: #B71C1C; margin: 0.5rem 0 0 0; font-size: 0.95rem;">{concern}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Perfil Ideal do Morador com IA
                st.markdown('<h5 style="background: #E3F2FD; padding: 0.8rem; border-radius: 8px; color: #1565C0;">👥 Perfil Ideal do Morador (IA)</h5>')
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); padding: 1.5rem; border-radius: 15px; border-left: 5px solid #2196F3; margin: 1rem 0;">
                    <h4 style="color: #1565C0; margin-top: 0;">🎯 Recomendação Inteligente</h4>
                    <p style="color: #0D47A1; font-size: 1.1rem; line-height: 1.6; font-weight: 500;">{insights.ideal_resident_profile}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Metodologia da IA
                st.markdown('<h5 style="background: #F3E5F5; padding: 0.8rem; border-radius: 8px; color: #7B1FA2;">🧠 Como a IA Analisa</h5>', unsafe_allow_html=True)
                
                st.markdown("""
                <div style="background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%); padding: 1.5rem; border-radius: 15px; border-left: 5px solid #9C27B0;">
                    <h4 style="color: #7B1FA2; margin-top: 0;">🔬 Metodologia UrbanSight AI</h4>
                    <p style="color: #4A148C; margin-bottom: 1rem;">Nossa IA utiliza análise avançada de dados urbanos para gerar insights personalizados:</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Criar os cards usando colunas do Streamlit em vez de CSS Grid
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 3px solid #7B1FA2;">
                        <h6 style="color: #7B1FA2; margin: 0 0 0.5rem 0;">🔍 Análise Multimodal</h6>
                        <p style="color: #4A148C; margin: 0; font-size: 0.9rem;">Combina dados de mobilidade, segurança, meio ambiente e economia</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("""
                    <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 3px solid #7B1FA2;">
                        <h6 style="color: #7B1FA2; margin: 0 0 0.5rem 0;">🎯 Personalização</h6>
                        <p style="color: #4A148C; margin: 0; font-size: 0.9rem;">Adapta recomendações baseadas no contexto urbano específico</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 3px solid #7B1FA2;">
                        <h6 style="color: #7B1FA2; margin: 0 0 0.5rem 0;">📊 Processamento OpenStreetMap</h6>
                        <p style="color: #4A148C; margin: 0; font-size: 0.9rem;">Extrai padrões de 200+ pontos de interesse georreferenciados</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("""
                    <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 10px; margin-bottom: 1rem; border-left: 3px solid #7B1FA2;">
                        <h6 style="color: #7B1FA2; margin: 0 0 0.5rem 0;">🚀 Tempo Real</h6>
                        <p style="color: #4A148C; margin: 0; font-size: 0.9rem;">Análise instantânea com dados atualizados do OpenStreetMap</p>
                    </div>
                    """, unsafe_allow_html=True)
                
            else:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%); padding: 2rem; border-radius: 15px; text-align: center; border-left: 5px solid #F44336;">
                    <h3 style="color: #C62828; margin: 0 0 1rem 0;">🤖 IA Temporariamente Indisponível</h3>
                    <p style="color: #B71C1C; font-size: 1.1rem; margin: 0;">Os insights com inteligência artificial não estão disponíveis no momento.</p>
                    
                    <h5 style="color: #C62828; margin: 1.5rem 0 0.5rem 0;">🔍 Possíveis Motivos:</h5>
                    <ul style="color: #B71C1C; text-align: left; max-width: 500px; margin: 0 auto;">
                        <li><strong>Configuração de API:</strong> Chave OpenAI não configurada</li>
                        <li><strong>Limite de Uso:</strong> Cota da API temporariamente esgotada</li>
                        <li><strong>Conectividade:</strong> Problemas de rede temporários</li>
                    </ul>
                    
                    <h5 style="color: #C62828; margin: 1.5rem 0 0.5rem 0;">💡 Solução:</h5>
                    <p style="color: #B71C1C; margin: 0;">Configure sua chave da API OpenAI no arquivo de configuração para ativar os insights avançados com IA.</p>
                </div>
                """, unsafe_allow_html=True)
        
        with tab11:
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
        
        with tab12:
            # Análise de Investimento
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #4CAF50 0%, #8BC34A 100%); padding: 1rem; border-radius: 10px; text-align: center;">💰 Análise Completa de Investimento Imobiliário</h4>', unsafe_allow_html=True)
            
            if result.investment_analysis:
                investment = result.investment_analysis
                
                # Score geral de investimento
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score = investment.metrics.overall_investment_score
                    color = get_score_color(score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Score de Investimento</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Recomendação principal
                recommendation_colors = {
                    "BUY": "#4CAF50",
                    "HOLD": "#FF9800", 
                    "AVALIAR": "#F44336"
                }
                rec_color = recommendation_colors.get(investment.recommendations.buy_hold_sell, "#666")
                
                st.markdown(f"""
                <div style="text-align: center; background: {rec_color}; color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
                    <h2>🎯 Recomendação: {investment.recommendations.buy_hold_sell}</h2>
                    <h4>{investment.recommendations.optimal_timeline}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Métricas detalhadas
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🎯 ROI Potential</h3>
                        <div class="value" style="color: {get_score_color(investment.metrics.roi_potential)};">{investment.metrics.roi_potential:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>📈 Valorização</h3>
                        <div class="value" style="color: {get_score_color(investment.metrics.appreciation_forecast * 10)};">{investment.metrics.appreciation_forecast:.1f}%</div>
                        <div class="grade">Anual</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏠 Rental Yield</h3>
                        <div class="value" style="color: {get_score_color(investment.metrics.rental_yield_estimate * 10)};">{investment.metrics.rental_yield_estimate:.1f}%</div>
                        <div class="grade">Anual</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>💧 Liquidez</h3>
                        <div class="value" style="color: {get_score_color(investment.metrics.liquidity_score)};">{investment.metrics.liquidity_score:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>⚠️ Risco</h3>
                        <div class="value" style="color: {get_score_color(100 - investment.metrics.risk_score)};">{investment.metrics.risk_score:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Análise de mercado
                st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px;">📊 Análise de Mercado</h5>')
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div style="background: #F0F8F0; padding: 1rem; border-radius: 8px;">
                        <h6><strong>🏗️ Tendência do Bairro:</strong></h6>
                        <p>{investment.market_comparison.neighborhood_growth_trend}</p>
                        
                        <h6><strong>📈 Saturação do Mercado:</strong></h6>
                        <p>{investment.market_comparison.market_saturation_level}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<h6><strong>🎯 Vantagens Competitivas:</strong></h6>', unsafe_allow_html=True)
                    for advantage in investment.market_comparison.competitive_advantage:
                        st.markdown(f"• {advantage}")
                
                # Recomendações de financiamento
                st.markdown('<h5 style="background: #E3F2FD; padding: 0.8rem; border-radius: 8px;">💳 Estratégias de Financiamento</h5>')
                for suggestion in investment.recommendations.financing_suggestions:
                    st.markdown(f"""
                    <div style="background: #F0F4F8; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0;">
                        💡 {suggestion}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Fatores de risco
                st.markdown('<h5 style="background: #FFEBEE; padding: 0.8rem; border-radius: 8px;">⚠️ Fatores de Risco</h5>')
                for risk in investment.risk_factors:
                    st.markdown(f"""
                    <div style="background: #FFEBEE; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #F44336;">
                        🚨 {risk}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Insights de IA
                if investment.ai_insights:
                    st.markdown('<h5 style="background: #F3E5F5; padding: 0.8rem; border-radius: 8px;">🤖 Análise de IA</h5>')
                    st.markdown(f"""
                    <div style="background: #F8F4F9; padding: 1rem; border-radius: 8px; border-left: 4px solid #9C27B0;">
                        {investment.ai_insights}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de análise de investimento não disponíveis para esta localização")
        
        with tab13:
            # Tendências Urbanas
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #9C27B0 0%, #673AB7 100%); padding: 1rem; border-radius: 10px; text-align: center;">📈 Análise de Tendências Urbanas</h4>', unsafe_allow_html=True)
            
            if result.urban_trends:
                trends = result.urban_trends
                
                # Padrão de desenvolvimento
                pattern_colors = {
                    "Gentrification": "#4CAF50",
                    "Emerging": "#FF9800",
                    "Stable": "#2196F3",
                    "Underdeveloped": "#9E9E9E"
                }
                pattern_color = pattern_colors.get(trends.development_pattern.pattern_type, "#666")
                
                st.markdown(f"""
                <div style="text-align: center; background: {pattern_color}; color: white; padding: 2rem; border-radius: 20px; margin: 1rem 0;">
                    <h2>🏗️ Padrão: {trends.development_pattern.pattern_type}</h2>
                    <h4>⏱️ {trends.development_pattern.timeline_estimate}</h4>
                    <p>Confiança: {trends.development_pattern.confidence_level:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Indicadores de crescimento
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏪 Crescimento Comercial</h3>
                        <div class="value" style="color: {get_score_color(trends.growth_indicators.commercial_growth_rate)};">{trends.growth_indicators.commercial_growth_rate:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏗️ Infraestrutura</h3>
                        <div class="value" style="color: {get_score_color(trends.growth_indicators.infrastructure_development)};">{trends.growth_indicators.infrastructure_development:.1f}</div>
                        <div class="grade">Desenvolvimento</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🏠 Apelo Residencial</h3>
                        <div class="value" style="color: {get_score_color(trends.growth_indicators.residential_appeal)};">{trends.growth_indicators.residential_appeal:.1f}</div>
                        <div class="grade">Score</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="custom-metric">
                        <h3>🚀 Inovação</h3>
                        <div class="value" style="color: {get_score_color(trends.growth_indicators.innovation_index)};">{trends.growth_indicators.innovation_index:.1f}</div>
                        <div class="grade">Índice</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Previsões futuras
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<h5 style="background: #E3F2FD; padding: 0.8rem; border-radius: 8px;">🔮 Projeção 5 Anos</h5>')
                    st.markdown(f"""
                    <div style="background: #F0F4F8; padding: 1rem; border-radius: 8px;">
                        {trends.future_predictions.five_year_outlook}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px;">🌟 Projeção 10 Anos</h5>')
                    st.markdown(f"""
                    <div style="background: #F0F8F0; padding: 1rem; border-radius: 8px;">
                        {trends.future_predictions.ten_year_projection}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Oportunidades emergentes
                st.markdown('<h5 style="background: #FFF3E0; padding: 0.8rem; border-radius: 8px;">🌟 Oportunidades Emergentes</h5>')
                for opportunity in trends.future_predictions.emerging_opportunities:
                    st.markdown(f"""
                    <div style="background: #FFF8F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #FF9800;">
                        🚀 {opportunity}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Desafios potenciais
                st.markdown('<h5 style="background: #FFEBEE; padding: 0.8rem; border-radius: 8px;">⚠️ Desafios Potenciais</h5>')
                for challenge in trends.future_predictions.potential_challenges:
                    st.markdown(f"""
                    <div style="background: #FFF0F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #F44336;">
                        🚧 {challenge}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Janelas de investimento
                st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px;">💰 Janelas de Investimento</h5>')
                for window in trends.future_predictions.investment_windows:
                    st.markdown(f"""
                    <div style="background: #F0F8F0; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #4CAF50;">
                        💎 {window}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Análise de IA
                if trends.ai_analysis:
                    st.markdown('<h5 style="background: #F3E5F5; padding: 0.8rem; border-radius: 8px;">🤖 Análise Especializada de IA</h5>')
                    st.markdown(f"""
                    <div style="background: #F8F4F9; padding: 1rem; border-radius: 8px; border-left: 4px solid #9C27B0;">
                        {trends.ai_analysis}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Resumo das tendências
                st.markdown('<h5 style="background: #ECEFF1; padding: 0.8rem; border-radius: 8px;">📋 Resumo Executivo</h5>')
                st.markdown(f"""
                <div style="background: #F5F5F5; padding: 1rem; border-radius: 8px; white-space: pre-line;">
                {trends.trend_summary}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("❌ Dados de tendências urbanas não disponíveis para esta localização")
        
        with tab14:
            # Recomendações Personalizadas
            st.markdown('<h4 style="color: white; background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); padding: 1rem; border-radius: 10px; text-align: center;">👤 Recomendações Personalizadas</h4>', unsafe_allow_html=True)
            
            if st.session_state.user_profile and st.session_state.user_profile.success:
                profile = st.session_state.user_profile.user_profile
                
                # Exibir resumo do perfil
                st.markdown('<h5 style="background: #E3F2FD; padding: 0.8rem; border-radius: 8px;">👤 Seu Perfil</h5>')
                st.markdown(f"""
                <div style="background: #F0F4F8; padding: 1rem; border-radius: 8px; white-space: pre-line;">
                {st.session_state.user_profile.profile_summary}
                </div>
                """, unsafe_allow_html=True)
                
                # Calcular compatibilidade personalizada
                compatibility_score = 0
                if hasattr(result.metrics, 'total_score'):
                    # Aplicar pesos personalizados
                    weights = profile.compatibility_weights
                    compatibility_score = (
                        getattr(result.metrics, 'safety_score', 70) * weights.get('safety_score', 0.1) +
                        getattr(result.metrics, 'accessibility_score', 70) * weights.get('accessibility_score', 0.15) +
                        getattr(result.metrics, 'convenience_score', 70) * weights.get('convenience_score', 0.15) +
                        getattr(result.metrics.walk_score, 'overall_score', 70) * weights.get('walk_score', 0.15) +
                        getattr(result.metrics, 'quality_of_life_score', 70) * weights.get('quality_of_life_score', 0.15) +
                        getattr(result.metrics, 'total_score', 70) * weights.get('total_score', 0.3)
                    )
                
                # Score de compatibilidade personalizado
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    color = get_score_color(compatibility_score)
                    st.markdown(f"""
                    <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: {color}; font-size: 3rem; margin: 0;">{compatibility_score:.1f}</h2>
                        <h3 style="color: #000; margin: 0.5rem 0;">Compatibilidade Personalizada</h3>
                        <h4 style="color: {color}; margin: 0;">{get_score_grade(compatibility_score)}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Recomendações personalizadas
                st.markdown('<h5 style="background: #FFF3E0; padding: 0.8rem; border-radius: 8px;">💡 Suas Recomendações Personalizadas</h5>')
                for i, rec in enumerate(st.session_state.user_profile.personalized_recommendations, 1):
                    st.markdown(f"""
                    <div style="background: #FFF8F0; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #FF9800;">
                        <strong>💡 Recomendação {i}:</strong> {rec}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Análise de compatibilidade detalhada
                st.markdown('<h5 style="background: #E8F5E8; padding: 0.8rem; border-radius: 8px;">🎯 Análise de Compatibilidade Detalhada</h5>')
                
                # Mostrar como cada fator se alinha com o perfil
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<h6><strong>✅ Fatores Alinhados ao Seu Perfil:</strong></h6>', unsafe_allow_html=True)
                    
                    # Verificar alinhamentos baseados no perfil
                    alignments = []
                    
                    if "Segurança" in profile.priority_factors:
                        safety_score = getattr(result.metrics, 'safety_score', 70)
                        if safety_score >= 70:
                            alignments.append(f"Segurança: {safety_score:.1f}/100 ✅")
                    
                    if "Transporte público" in profile.priority_factors:
                        access_score = getattr(result.metrics, 'accessibility_score', 70)
                        if access_score >= 70:
                            alignments.append(f"Transporte: {access_score:.1f}/100 ✅")
                    
                    if profile.has_children:
                        education_pois = len([poi for poi in result.pois if poi.get('category') == 'education'])
                        if education_pois >= 3:
                            alignments.append(f"Escolas próximas: {education_pois} encontradas ✅")
                    
                    if profile.has_pets:
                        leisure_pois = len([poi for poi in result.pois if poi.get('category') == 'leisure'])
                        if leisure_pois >= 3:
                            alignments.append(f"Áreas de lazer: {leisure_pois} encontradas ✅")
                    
                    for alignment in alignments:
                        st.markdown(f"• {alignment}")
                    
                    if not alignments:
                        st.markdown("• Área com potencial de melhoria")
                
                with col2:
                    st.markdown('<h6><strong>⚠️ Pontos de Atenção:</strong></h6>', unsafe_allow_html=True)
                    
                    # Verificar desalinhamentos
                    concerns = []
                    
                    if "Silêncio/tranquilidade" in profile.priority_factors:
                        if profile.noise_tolerance == "Preciso de muito silêncio":
                            concerns.append("Área urbana pode ter ruído acima do ideal")
                    
                    if profile.budget_range == "Até R$ 400k":
                        investment_score = getattr(result, 'investment_analysis', None)
                        if investment_score and investment_score.metrics.overall_investment_score >= 80:
                            concerns.append("Área valorizada pode estar acima do orçamento")
                    
                    if profile.has_elderly and not profile.accessibility_needs:
                        ped_score = getattr(result, 'pedestrian_score', None)
                        if ped_score and ped_score.accessibility_score < 60:
                            concerns.append("Acessibilidade limitada para idosos")
                    
                    for concern in concerns:
                        st.markdown(f"• {concern}")
                    
                    if not concerns:
                        st.markdown("• Nenhum ponto crítico identificado")
                
                # Sugestões de busca refinada
                st.markdown('<h5 style="background: #F3E5F5; padding: 0.8rem; border-radius: 8px;">🔍 Sugestões para Refinar sua Busca</h5>')
                
                search_suggestions = []
                
                if compatibility_score < 70:
                    search_suggestions.append("Considere expandir o raio de busca")
                    search_suggestions.append("Explore bairros adjacentes com características similares")
                
                if profile.investment_purpose == "Para investimento/aluguel":
                    search_suggestions.append("Foque em áreas com alta densidade de transporte público")
                    search_suggestions.append("Considere proximidade a universidades e centros comerciais")
                
                if profile.has_children:
                    search_suggestions.append("Priorize áreas com rating alto em educação")
                    search_suggestions.append("Verifique proximidade a pediatras e hospitais infantis")
                
                for suggestion in search_suggestions:
                    st.markdown(f"""
                    <div style="background: #F8F4F9; padding: 0.5rem; border-radius: 5px; margin: 0.3rem 0; border-left: 3px solid #9C27B0;">
                        🎯 {suggestion}
                    </div>
                    """, unsafe_allow_html=True)
                
            else:
                st.markdown("""
                <div style="text-align: center; background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%); padding: 2rem; border-radius: 15px;">
                    <h3 style="color: #E65100;">🤖 Crie Seu Perfil Primeiro</h3>
                    <p style="color: #BF360C; margin: 1rem 0;">Para receber recomendações personalizadas, complete o chatbot de perfil.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🚀 Criar Meu Perfil Agora", type="primary"):
                    st.session_state.show_profile_chatbot = True
                    st.rerun()

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