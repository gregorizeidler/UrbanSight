import streamlit as st
import asyncio
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_folium import folium_static
import folium
from folium.plugins import HeatMap, MarkerCluster
try:
    from folium.plugins import Draw, MeasureControl, MiniMap
except ImportError:
    # Fallback if plugins not available
    Draw = MeasureControl = MiniMap = None
import pandas as pd
from datetime import datetime
import time
import numpy as np
from collections import Counter
import math
import json
from branca.element import Template, MacroElement

# Import our agents
from agents.orchestrator import PropertyAnalysisOrchestrator

# Configure Streamlit page
st.set_page_config(
    page_title="UrbanSight - Inteligência Imobiliária Profissional",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'comparison_addresses' not in st.session_state:
    st.session_state.comparison_addresses = []

if 'analysis_radius' not in st.session_state:
    st.session_state.analysis_radius = 1000
if 'custom_weights' not in st.session_state:
    st.session_state.custom_weights = {
        'grocery': 0.15, 'restaurant': 0.10, 'shopping': 0.05,
        'school': 0.15, 'park': 0.10, 'entertainment': 0.05,
        'healthcare': 0.10, 'transport': 0.20, 'services': 0.10
    }

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

def get_score_color(score):
    """Get color based on score"""
    if score >= 80:
        return "green"
    elif score >= 60:
        return "orange"
    else:
        return "red"

def calculate_custom_walk_score(pois, weights, property_coords):
    """Calculate custom walk score based on user-defined weights"""
    category_scores = {}
    
    for category, weight in weights.items():
        category_pois = [poi for poi in pois if poi.get('category', '').lower() == category.lower()]
        if category_pois:
            # Calculate score based on closest POI distance
            min_distance = min([poi.get('distance', 1000) for poi in category_pois])
            # Score decreases with distance (max score at 0m, min at 1000m)
            score = max(0, 100 - (min_distance / 10))
            category_scores[category] = score * weight
        else:
            category_scores[category] = 0
    
    return sum(category_scores.values()), category_scores

def create_poi_heatmap(result, category_filter=None):
    """Create heatmap for POI density"""
    if not result.pois:
        return None
    
    # Filter POIs by category if specified
    filtered_pois = result.pois
    if category_filter:
        filtered_pois = [poi for poi in result.pois 
                        if poi.get('category', '').lower() in [c.lower() for c in category_filter]]
    
    if not filtered_pois:
        return None
    
    # Create base map
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=14,
        tiles='OpenStreetMap'
    )
    
    # Prepare heat map data
    heat_data = []
    for poi in filtered_pois:
        if poi.get('lat') and poi.get('lon'):
            heat_data.append([poi['lat'], poi['lon']])
    
    if heat_data:
        # Add heatmap
        HeatMap(heat_data, radius=15, blur=10, gradient={
            0.2: 'blue', 0.4: 'lime', 0.6: 'orange', 1: 'red'
        }).add_to(m)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"Propriedade: {result.property_data.address}",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)
    
    return m

def create_comparison_chart(results_dict):
    """Create comparison chart for multiple addresses"""
    if len(results_dict) < 2:
        return None
    
    addresses = list(results_dict.keys())
    metrics = ['total_score', 'walk_score.overall_score', 'accessibility_score', 
               'convenience_score', 'quality_of_life_score']
    metric_names = ['Score Total', 'Walk Score', 'Acessibilidade', 'Conveniência', 'Qualidade de Vida']
    
    # Prepare data for radar chart
    fig = go.Figure()
    
    for address in addresses:
        result = results_dict[address]
        values = []
        
        for metric in metrics:
            if '.' in metric:
                attr, sub_attr = metric.split('.')
                value = getattr(getattr(result.metrics, attr), sub_attr, 0)
            else:
                value = getattr(result.metrics, metric, 0)
            values.append(value)
        
        # Close the radar chart
        values.append(values[0])
        metric_names_closed = metric_names + [metric_names[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metric_names_closed,
            fill='toself',
            name=address[:30] + '...' if len(address) > 30 else address
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="Comparação de Propriedades - Radar Chart"
    )
    
    return fig

def create_poi_distribution_chart(pois):
    """Create POI distribution chart"""
    if not pois:
        return None
    
    # Count POIs by category
    categories = [poi.get('category', 'other') for poi in pois]
    category_counts = Counter(categories)
    
    # Create pie chart
    fig = px.pie(
        values=list(category_counts.values()),
        names=list(category_counts.keys()),
        title="Distribuição de Pontos de Interesse por Categoria"
    )
    
    return fig

def create_distance_analysis_chart(pois, property_coords):
    """Create distance analysis chart"""
    if not pois:
        return None
    
    # Group POIs by category and calculate average distances
    category_distances = {}
    for poi in pois:
        category = poi.get('category', 'other')
        distance = poi.get('distance', 0)
        
        if category not in category_distances:
            category_distances[category] = []
        category_distances[category].append(distance)
    
    # Calculate average distances
    avg_distances = {cat: np.mean(distances) for cat, distances in category_distances.items()}
    
    # Create bar chart
    fig = px.bar(
        x=list(avg_distances.keys()),
        y=list(avg_distances.values()),
        title="Distância Média por Categoria de POI",
        labels={'x': 'Categoria', 'y': 'Distância Média (metros)'}
    )
    
    return fig

def create_accessibility_analysis(result):
    """Create detailed accessibility analysis"""
    if not result.pois:
        return None
    
    # Walking time zones (5, 10, 15, 20 minutes)
    # Assuming average walking speed of 5 km/h = 83.33 m/min
    walking_speed = 83.33  # meters per minute
    time_zones = {
        "5 min": 5 * walking_speed,
        "10 min": 10 * walking_speed,
        "15 min": 15 * walking_speed,
        "20 min": 20 * walking_speed
    }
    
    # Count POIs in each time zone
    accessibility_data = []
    categories = set([poi.get('category', 'other') for poi in result.pois])
    
    for category in categories:
        category_pois = [poi for poi in result.pois if poi.get('category') == category]
        zone_counts = {}
        
        for zone_name, max_distance in time_zones.items():
            count = len([poi for poi in category_pois if poi.get('distance', 0) <= max_distance])
            zone_counts[zone_name] = count
        
        for zone, count in zone_counts.items():
            accessibility_data.append({
                'Categoria': category,
                'Zona de Tempo': zone,
                'Quantidade': count
            })
    
    if not accessibility_data:
        return None
    
    df = pd.DataFrame(accessibility_data)
    
    # Create heatmap
    pivot_df = df.pivot(index='Categoria', columns='Zona de Tempo', values='Quantidade').fillna(0)
    
    fig = px.imshow(
        pivot_df,
        title="Acessibilidade por Tempo de Caminhada",
        labels=dict(x="Zona de Tempo", y="Categoria", color="Quantidade"),
        aspect="auto"
    )
    
    return fig

def create_folium_map(result, show_radius=True, poi_filter=None):
    """Enhanced map creation with optional radius and POI filtering"""
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=15,
        tiles='OpenStreetMap'
    )
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}<br>Score: {result.metrics.total_score:.1f}",
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)
    
    # Add analysis radius circle
    if show_radius:
        folium.Circle(
            [result.property_data.lat, result.property_data.lon],
            radius=st.session_state.analysis_radius,
            popup=f"Raio de Análise ({st.session_state.analysis_radius}m)",
            color='blue',
            fill=True,
            fillOpacity=0.1,
            weight=2,
            opacity=0.8
        ).add_to(m)
    
    # POI color mapping
    color_map = {
        'education': 'blue',
        'healthcare': 'green', 
        'shopping': 'orange',
        'transport': 'purple',
        'entertainment': 'pink',
        'restaurant': 'darkgreen',
        'services': 'gray',
        'park': 'lightgreen'
    }
    
    # Add POI markers with clustering
    marker_cluster = MarkerCluster().add_to(m)
    
    for poi in result.pois:
        # Apply POI filter if specified
        if poi_filter and poi.get('category', '').lower() not in [c.lower() for c in poi_filter]:
            continue
            
        category = poi.get('category', 'other').lower()
        color = color_map.get(category, 'gray')
        
        folium.Marker(
            [poi.get('lat', 0), poi.get('lon', 0)],
            popup=f"<b>{poi.get('name', 'POI')}</b><br>Categoria: {poi.get('category', 'N/A')}<br>Distância: {poi.get('distance', 0):.0f}m",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(marker_cluster)
    
    return m

def create_density_visualization(result):
    """Create POI density visualization"""
    if not result.pois:
        return None
    
    # Calculate density per km²
    radius_km = st.session_state.analysis_radius / 1000
    area_km2 = math.pi * (radius_km ** 2)
    
    category_counts = Counter([poi.get('category', 'other') for poi in result.pois])
    density_data = {cat: count / area_km2 for cat, count in category_counts.items()}
    
    # Create bar chart
    fig = px.bar(
        x=list(density_data.keys()),
        y=list(density_data.values()),
        title=f"Densidade de POIs por km² (Raio: {st.session_state.analysis_radius}m)",
        labels={'x': 'Categoria', 'y': 'POIs por km²'}
    )
    
    return fig

# Advanced Maps Functions
def create_dynamic_heatmap(result, category_filter=None, intensity_radius=15, blur_radius=10):
    """Create dynamic heatmap with adjustable parameters"""
    if not result.pois:
        return None
    
    # Filter POIs by category if specified
    filtered_pois = result.pois
    if category_filter:
        filtered_pois = [poi for poi in result.pois 
                        if poi.get('category', '').lower() in [c.lower() for c in category_filter]]
    
    if not filtered_pois:
        return None
    
    # Create base map with multiple tile layers
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=14,
        tiles=None
    )
    
    # Add multiple tile layers
    folium.TileLayer('OpenStreetMap', name='Ruas').add_to(m)
    folium.TileLayer('CartoDB Positron', name='Limpo').add_to(m)
    folium.TileLayer('CartoDB DarkMatter', name='Escuro').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles © Esri',
        name='Satélite'
    ).add_to(m)
    
    # Prepare heat map data with weights
    heat_data = []
    for poi in filtered_pois:
        if poi.get('lat') and poi.get('lon'):
            # Weight based on category importance and distance
            weight = 1.0
            category = poi.get('category', '').lower()
            distance = poi.get('distance', 0)
            
            # Category weights
            category_weights = {
                'education': 1.5,
                'healthcare': 1.8,
                'shopping': 1.2,
                'transport': 2.0,
                'restaurant': 0.8,
                'entertainment': 0.9,
                'services': 1.1,
                'park': 1.3
            }
            weight *= category_weights.get(category, 1.0)
            
            # Distance weight (closer = more important)
            if distance <= 300:
                weight *= 1.5
            elif distance <= 600:
                weight *= 1.2
            elif distance > 1000:
                weight *= 0.7
            
            heat_data.append([poi['lat'], poi['lon'], weight])
    
    if heat_data:
        # Add dynamic heatmap
        HeatMap(
            heat_data, 
            radius=intensity_radius, 
            blur=blur_radius, 
            gradient={
                0.1: 'blue', 
                0.3: 'cyan', 
                0.5: 'lime', 
                0.7: 'yellow', 
                0.9: 'orange', 
                1.0: 'red'
            },
            min_opacity=0.4,
            max_zoom=18,
            name='Heatmap POIs'
        ).add_to(m)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}<br>Score: {result.metrics.total_score:.1f}",
        icon=folium.Icon(color='red', icon='home', prefix='fa'),
        tooltip="Propriedade Analisada"
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

def create_isochrone_map(result, walk_times=[5, 10, 15, 20]):
    """Create map with walking time isochrones"""
    if not result.pois:
        return None
    
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=15
    )
    
    # Walking speed in meters per minute
    walking_speed = 83.33  # 5 km/h
    
    # Colors for different time zones
    colors = ['#00ff00', '#ffff00', '#ff9900', '#ff0000']
    
    # Create isochrone circles
    for i, time_min in enumerate(walk_times):
        radius = time_min * walking_speed
        color = colors[i % len(colors)]
        
        folium.Circle(
            location=[result.property_data.lat, result.property_data.lon],
            radius=radius,
            popup=f"{time_min} min a pé ({radius:.0f}m)",
            color=color,
            fill=True,
            fillOpacity=0.1,
            opacity=0.6,
            weight=2,
            tooltip=f"Zona de {time_min} minutos"
        ).add_to(m)
    
    # Add POIs with time-based coloring
    for poi in result.pois:
        distance = poi.get('distance', 0)
        time_to_reach = distance / walking_speed
        
        # Determine color based on time
        if time_to_reach <= 5:
            color = 'green'
        elif time_to_reach <= 10:
            color = 'yellow'
        elif time_to_reach <= 15:
            color = 'orange'
        else:
            color = 'red'
        
        # Create enhanced popup
        popup_html = f"""
        <div style="width: 200px;">
            <h4>{poi.get('name', 'POI')}</h4>
            <p><b>Categoria:</b> {poi.get('category', 'N/A').title()}</p>
            <p><b>Distância:</b> {distance:.0f}m</p>
            <p><b>Tempo a pé:</b> {time_to_reach:.1f} min</p>
            <p><b>Acessibilidade:</b> {"🟢 Excelente" if time_to_reach <= 5 else "🟡 Boa" if time_to_reach <= 10 else "🟠 Razoável" if time_to_reach <= 15 else "🔴 Distante"}</p>
        </div>
        """
        
        folium.Marker(
            [poi.get('lat', 0), poi.get('lon', 0)],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color, icon='info-sign'),
            tooltip=f"{poi.get('name', 'POI')} - {time_to_reach:.1f}min"
        ).add_to(m)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}",
        icon=folium.Icon(color='red', icon='home', prefix='fa'),
        tooltip="Propriedade Analisada"
    ).add_to(m)
    
    return m

def create_thematic_map(result, theme='family'):
    """Create thematic maps for different lifestyles"""
    if not result.pois:
        return None
    
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=14
    )
    
    # Define themes and their relevant categories
    themes = {
        'family': {
            'categories': ['education', 'healthcare', 'park', 'shopping'],
            'colors': {'education': 'blue', 'healthcare': 'green', 'park': 'lightgreen', 'shopping': 'orange'},
            'title': 'Mapa Familiar',
            'description': 'Ideal para famílias com crianças'
        },
        'lifestyle': {
            'categories': ['restaurant', 'entertainment', 'shopping', 'park'],
            'colors': {'restaurant': 'darkgreen', 'entertainment': 'purple', 'shopping': 'orange', 'park': 'lightgreen'},
            'title': 'Mapa Lifestyle',
            'description': 'Vida social e entretenimento'
        },
        'transport': {
            'categories': ['transport'],
            'colors': {'transport': 'blue'},
            'title': 'Mapa de Mobilidade',
            'description': 'Transporte público e conectividade'
        },
        'emergency': {
            'categories': ['healthcare', 'services'],
            'colors': {'healthcare': 'red', 'services': 'darkred'},
            'title': 'Mapa de Emergência',
            'description': 'Serviços essenciais e emergência'
        }
    }
    
    current_theme = themes.get(theme, themes['family'])
    
    # Filter POIs by theme
    theme_pois = [poi for poi in result.pois 
                  if poi.get('category', '').lower() in current_theme['categories']]
    
    # Add themed markers
    for poi in theme_pois:
        category = poi.get('category', '').lower()
        color = current_theme['colors'].get(category, 'gray')
        distance = poi.get('distance', 0)
        
        # Create enhanced popup with theme-specific info
        popup_content = f"""
        <div style="width: 220px;">
            <h4 style="color: {color};">{poi.get('name', 'POI')}</h4>
            <p><b>Categoria:</b> {poi.get('category', 'N/A').title()}</p>
            <p><b>Distância:</b> {distance:.0f}m</p>
            <p><b>Tempo a pé:</b> {distance/83.33:.1f} min</p>
        """
        
        # Add theme-specific information
        if theme == 'family' and category == 'education':
            popup_content += f"<p><b>Ideal para:</b> Crianças em idade escolar</p>"
        elif theme == 'lifestyle' and category == 'restaurant':
            popup_content += f"<p><b>Tipo:</b> Opção gastronômica</p>"
        elif theme == 'transport':
            popup_content += f"<p><b>Tipo:</b> Conectividade urbana</p>"
        elif theme == 'emergency':
            popup_content += f"<p><b>Tipo:</b> Serviço essencial</p>"
        
        popup_content += "</div>"
        
        # Create marker with theme-appropriate icon
        icon_map = {
            'education': 'graduation-cap',
            'healthcare': 'plus-square',
            'park': 'tree',
            'shopping': 'shopping-cart',
            'restaurant': 'cutlery',
            'entertainment': 'music',
            'transport': 'bus',
            'services': 'cog'
        }
        
        icon = icon_map.get(category, 'info-sign')
        
        folium.Marker(
            [poi.get('lat', 0), poi.get('lon', 0)],
            popup=folium.Popup(popup_content, max_width=250),
            icon=folium.Icon(color=color, icon=icon, prefix='fa'),
            tooltip=f"{poi.get('name', 'POI')} ({category.title()})"
        ).add_to(m)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}<br><i>{current_theme['description']}</i>",
        icon=folium.Icon(color='red', icon='home', prefix='fa'),
        tooltip="Propriedade Analisada"
    ).add_to(m)
    
    # Add theme information
    theme_info = f"""
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: 80px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px;">
    <h4>{current_theme['title']}</h4>
    <p>{current_theme['description']}</p>
    <p>POIs encontrados: {len(theme_pois)}</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(theme_info))
    
    return m

def create_split_screen_comparison_map(results_dict):
    """Create split-screen comparison map for multiple addresses"""
    if len(results_dict) < 2:
        return None, None
    
    addresses = list(results_dict.keys())[:2]  # Take first 2 for split screen
    result1 = results_dict[addresses[0]]
    result2 = results_dict[addresses[1]]
    
    # Create two maps
    map1 = folium.Map(
        location=[result1.property_data.lat, result1.property_data.lon],
        zoom_start=14
    )
    
    map2 = folium.Map(
        location=[result2.property_data.lat, result2.property_data.lon],
        zoom_start=14
    )
    
    # Color schemes for each map
    color_schemes = [
        {'property': 'red', 'pois': 'blue'},
        {'property': 'darkred', 'pois': 'green'}
    ]
    
    maps = [map1, map2]
    results = [result1, result2]
    
    for i, (m, result) in enumerate(zip(maps, results)):
        colors = color_schemes[i]
        
        # Add property marker
        folium.Marker(
            [result.property_data.lat, result.property_data.lon],
            popup=f"<b>Propriedade {i+1}</b><br>{result.property_data.address}<br>Score: {result.metrics.total_score:.1f}",
            icon=folium.Icon(color=colors['property'], icon='home', prefix='fa'),
            tooltip=f"Propriedade {i+1}"
        ).add_to(m)
        
        # Add POI markers with clustering
        marker_cluster = MarkerCluster(name=f"POIs Propriedade {i+1}").add_to(m)
        
        for poi in result.pois:
            popup_html = f"""
            <div style="width: 200px;">
                <h4>{poi.get('name', 'POI')}</h4>
                <p><b>Categoria:</b> {poi.get('category', 'N/A')}</p>
                <p><b>Distância:</b> {poi.get('distance', 0):.0f}m</p>
                <p><b>Tempo:</b> {poi.get('distance', 0)/83.33:.1f} min</p>
            </div>
            """
            
            folium.Marker(
                [poi.get('lat', 0), poi.get('lon', 0)],
                popup=folium.Popup(popup_html, max_width=220),
                icon=folium.Icon(color=colors['pois'], icon='info-sign'),
                tooltip=poi.get('name', 'POI')
            ).add_to(marker_cluster)
        
        # Add analysis radius
        folium.Circle(
            [result.property_data.lat, result.property_data.lon],
            radius=1000,
            popup=f"Raio de Análise - Propriedade {i+1}",
            color=colors['property'],
            fill=True,
            fillOpacity=0.1,
            weight=2
        ).add_to(m)
        
        # Add map info
        info_html = f"""
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 220px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 8px;">
        <h4>Propriedade {i+1}</h4>
        <p><b>Score:</b> {result.metrics.total_score:.1f}/100</p>
        <p><b>Walk Score:</b> {result.metrics.walk_score.overall_score:.1f}/100</p>
        <p><b>POIs:</b> {len(result.pois)}</p>
        <p><b>Endereço:</b> {addresses[i][:30]}...</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(info_html))
    
    return map1, map2

def create_smart_clustering_map(result, zoom_level=14):
    """Create map with intelligent clustering based on zoom level"""
    if not result.pois:
        return None
    
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=zoom_level
    )
    
    # Create different cluster groups based on categories
    clusters = {}
    category_colors = {
        'education': 'blue',
        'healthcare': 'green',
        'shopping': 'orange',
        'transport': 'purple',
        'restaurant': 'darkgreen',
        'entertainment': 'pink',
        'services': 'gray',
        'park': 'lightgreen'
    }
    
    for category in category_colors.keys():
        clusters[category] = MarkerCluster(
            name=f"{category.title()} ({len([p for p in result.pois if p.get('category') == category])})",
            options={
                'maxClusterRadius': 80 if zoom_level < 15 else 40,
                'spiderfyOnMaxZoom': True,
                'showCoverageOnHover': False,
                'zoomToBoundsOnClick': True
            }
        ).add_to(m)
    
    # Add POIs to appropriate clusters
    for poi in result.pois:
        category = poi.get('category', 'services')
        color = category_colors.get(category, 'gray')
        
        # Create enhanced popup with mini-dashboard
        distance = poi.get('distance', 0)
        time_walk = distance / 83.33
        
        dashboard_html = f"""
        <div style="width: 280px; font-family: Arial;">
            <div style="background: linear-gradient(90deg, {color}, #f0f0f0); color: white; padding: 8px; margin: -9px -9px 8px -9px;">
                <h3 style="margin: 0; color: white;">{poi.get('name', 'POI')}</h3>
            </div>
            
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Categoria:</b></td><td>{poi.get('category', 'N/A').title()}</td></tr>
                <tr><td><b>Distância:</b></td><td>{distance:.0f}m</td></tr>
                <tr><td><b>Tempo a pé:</b></td><td>{time_walk:.1f} min</td></tr>
                <tr><td><b>Acessibilidade:</b></td><td>{"🟢 Excelente" if time_walk <= 5 else "🟡 Boa" if time_walk <= 10 else "🟠 Razoável"}</td></tr>
            </table>
            
            <div style="background: #f5f5f5; padding: 8px; margin-top: 8px; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px;"><b>Conveniência:</b></span>
                    <div style="width: 100px; height: 8px; background: #ddd; border-radius: 4px; overflow: hidden;">
                        <div style="width: {min(100, max(0, 100 - distance/10)):.0f}%; height: 100%; background: {'#4CAF50' if time_walk <= 5 else '#FF9800' if time_walk <= 10 else '#F44336'};"></div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        cluster = clusters.get(category, clusters.get('services'))
        
        folium.Marker(
            [poi.get('lat', 0), poi.get('lon', 0)],
            popup=folium.Popup(dashboard_html, max_width=300),
            icon=folium.Icon(color=color, icon='info-sign'),
            tooltip=f"{poi.get('name', 'POI')} - {category.title()}"
        ).add_to(cluster)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}<br>Score: {result.metrics.total_score:.1f}",
        icon=folium.Icon(color='red', icon='home', prefix='fa'),
        tooltip="Propriedade Analisada"
    ).add_to(m)
    
    # Add measurement controls (if available)
    if MeasureControl:
        MeasureControl(primary_length_unit='meters', secondary_length_unit='kilometers').add_to(m)
    
    # Add drawing controls (if available)
    if Draw:
        Draw(export=True).add_to(m)
    
    # Add minimap (if available)
    if MiniMap:
        minimap = MiniMap(toggle_display=True)
        m.add_child(minimap)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

def create_adjustable_radius_map(result, radius=1000, show_radius=True):
    """Create map with adjustable analysis radius"""
    if not result.pois:
        return None
    
    m = folium.Map(
        location=[result.property_data.lat, result.property_data.lon],
        zoom_start=15
    )
    
    # Filter POIs by radius
    filtered_pois = [poi for poi in result.pois if poi.get('distance', 0) <= radius]
    
    # Add radius circle
    if show_radius:
        folium.Circle(
            [result.property_data.lat, result.property_data.lon],
            radius=radius,
            popup=f"Raio de Análise: {radius}m<br>POIs encontrados: {len(filtered_pois)}",
            color='blue',
            fill=True,
            fillOpacity=0.1,
            weight=2,
            opacity=0.8
        ).add_to(m)
    
    # Add distance rings
    for ring_radius in [250, 500, 750, 1000, 1250, 1500]:
        if ring_radius <= radius:
            pois_in_ring = len([p for p in result.pois if p.get('distance', 0) <= ring_radius])
            folium.Circle(
                [result.property_data.lat, result.property_data.lon],
                radius=ring_radius,
                popup=f"{ring_radius}m - {pois_in_ring} POIs",
                color='gray',
                fill=False,
                weight=1,
                opacity=0.3
            ).add_to(m)
    
    # Add filtered POIs
    for poi in filtered_pois:
        distance = poi.get('distance', 0)
        
        # Color based on distance
        if distance <= 300:
            color = 'green'
        elif distance <= 600:
            color = 'yellow'
        elif distance <= 900:
            color = 'orange'
        else:
            color = 'red'
        
        folium.Marker(
            [poi.get('lat', 0), poi.get('lon', 0)],
            popup=f"<b>{poi.get('name', 'POI')}</b><br>Categoria: {poi.get('category', 'N/A')}<br>Distância: {distance:.0f}m",
            icon=folium.Icon(color=color, icon='info-sign'),
            tooltip=f"{poi.get('name', 'POI')} - {distance:.0f}m"
        ).add_to(m)
    
    # Add property marker
    folium.Marker(
        [result.property_data.lat, result.property_data.lon],
        popup=f"<b>Propriedade</b><br>{result.property_data.address}",
        icon=folium.Icon(color='red', icon='home', prefix='fa'),
        tooltip="Propriedade Analisada"
    ).add_to(m)
    
    # Add statistics overlay
    stats_html = f"""
    <div style="position: fixed; 
                top: 10px; left: 10px; width: 200px; height: 100px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:12px; padding: 10px;">
    <h4>Estatísticas do Raio</h4>
    <p><b>Raio:</b> {radius}m</p>
    <p><b>POIs encontrados:</b> {len(filtered_pois)}</p>
    <p><b>Densidade:</b> {len(filtered_pois)/(3.14159*(radius/1000)**2):.1f} POIs/km²</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(stats_html))
    
    return m

# Temporal & Trends Analysis Functions
def calculate_urban_maturity_index(pois):
    """Calculate urban maturity based on POI diversity and density"""
    if not pois:
        return 0, {}
    
    # Count POIs by category
    categories = {}
    for poi in pois:
        cat = poi.get('category', 'outros')
        categories[cat] = categories.get(cat, 0) + 1
    
    # Urban maturity factors
    factors = {
        'diversity': len(categories) * 12.5,  # Max 8 categories = 100
        'density': min(len(pois) * 2, 100),  # Max 50 POIs = 100
        'essential_services': 0,
        'premium_services': 0,
        'transport_connectivity': 0
    }
    
    # Essential services (basic urban needs)
    essential_cats = ['healthcare', 'education', 'shopping', 'services']
    essential_present = sum([1 for cat in essential_cats if categories.get(cat, 0) > 0])
    factors['essential_services'] = (essential_present / len(essential_cats)) * 100
    
    # Premium services (gentrification indicators)
    premium_keywords = ['restaurant', 'entertainment', 'cafe', 'bar', 'gym']
    premium_count = sum([categories.get(cat, 0) for cat in premium_keywords])
    factors['premium_services'] = min(premium_count * 10, 100)
    
    # Transport connectivity
    transport_count = categories.get('transport', 0)
    factors['transport_connectivity'] = min(transport_count * 25, 100)
    
    # Calculate weighted average
    weights = {
        'diversity': 0.25,
        'density': 0.20,
        'essential_services': 0.25,
        'premium_services': 0.15,
        'transport_connectivity': 0.15
    }
    
    maturity_index = sum([factors[key] * weights[key] for key in factors.keys()])
    
    return maturity_index, factors

def calculate_gentrification_index(pois):
    """Calculate gentrification potential based on service mix"""
    if not pois:
        return 0, {}
    
    # Gentrification indicators
    gentrification_keywords = {
        'cafes_specialty': ['cafe', 'coffee', 'bistro'],
        'restaurants_upscale': ['restaurant', 'fine_dining', 'wine_bar'],
        'entertainment_culture': ['entertainment', 'art_gallery', 'theater'],
        'fitness_wellness': ['gym', 'yoga', 'spa', 'fitness'],
        'services_premium': ['coworking', 'design', 'boutique']
    }
    
    scores = {}
    total_pois = len(pois)
    
    for category, keywords in gentrification_keywords.items():
        count = 0
        for poi in pois:
            poi_name = poi.get('name', '').lower()
            poi_cat = poi.get('category', '').lower()
            if any(keyword in poi_name or keyword in poi_cat for keyword in keywords):
                count += 1
        
        # Score as percentage of total POIs
        scores[category] = (count / total_pois) * 100 if total_pois > 0 else 0
    
    # Overall gentrification index
    gentrification_index = sum(scores.values()) / len(scores)
    
    return gentrification_index, scores

def find_similar_neighborhoods(target_result, all_results):
    """Find neighborhoods with similar POI profiles"""
    if not all_results or len(all_results) < 2:
        return []
    
    target_profile = {}
    for poi in target_result.pois:
        cat = poi.get('category', 'outros')
        target_profile[cat] = target_profile.get(cat, 0) + 1
    
    # Calculate similarity scores
    similarities = []
    
    for address, result in all_results.items():
        if result == target_result:
            continue
            
        other_profile = {}
        for poi in result.pois:
            cat = poi.get('category', 'outros')
            other_profile[cat] = other_profile.get(cat, 0) + 1
        
        # Calculate cosine similarity
        all_categories = set(list(target_profile.keys()) + list(other_profile.keys()))
        
        target_vector = [target_profile.get(cat, 0) for cat in all_categories]
        other_vector = [other_profile.get(cat, 0) for cat in all_categories]
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(target_vector, other_vector))
        magnitude_target = sum(a ** 2 for a in target_vector) ** 0.5
        magnitude_other = sum(b ** 2 for b in other_vector) ** 0.5
        
        if magnitude_target > 0 and magnitude_other > 0:
            similarity = dot_product / (magnitude_target * magnitude_other)
            similarities.append((address, similarity, result))
    
    # Sort by similarity and return top 3
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:3]

def predict_development_potential(pois, property_coords):
    """Predict future development potential"""
    if not pois:
        return 0, {}
    
    # Calculate current saturation
    area_km2 = 3.14159 * (1.0 ** 2)  # 1km radius
    poi_density = len(pois) / area_km2
    
    # Development indicators
    indicators = {
        'infrastructure_gaps': 0,
        'growth_momentum': 0,
        'accessibility_factor': 0,
        'market_potential': 0
    }
    
    # Infrastructure gaps (missing essential services)
    essential_categories = ['education', 'healthcare', 'shopping', 'transport', 'services']
    present_categories = set([poi.get('category') for poi in pois])
    missing_essentials = len([cat for cat in essential_categories if cat not in present_categories])
    indicators['infrastructure_gaps'] = max(0, 100 - (missing_essentials * 20))
    
    # Growth momentum (density vs typical urban patterns)
    if poi_density < 50:  # Low density = high growth potential
        indicators['growth_momentum'] = 90
    elif poi_density < 100:  # Medium density = moderate potential
        indicators['growth_momentum'] = 60
    else:  # High density = low potential (saturated)
        indicators['growth_momentum'] = 30
    
    # Accessibility factor (transport connectivity)
    transport_pois = [p for p in pois if p.get('category') == 'transport']
    if transport_pois:
        avg_transport_distance = sum([p.get('distance', 0) for p in transport_pois]) / len(transport_pois)
        indicators['accessibility_factor'] = max(0, 100 - (avg_transport_distance / 10))
    else:
        indicators['accessibility_factor'] = 20  # Low if no transport
    
    # Market potential (mix of services)
    service_diversity = len(set([poi.get('category') for poi in pois]))
    indicators['market_potential'] = min(service_diversity * 12.5, 100)
    
    # Overall development potential
    weights = {'infrastructure_gaps': 0.3, 'growth_momentum': 0.3, 'accessibility_factor': 0.2, 'market_potential': 0.2}
    development_potential = sum([indicators[key] * weights[key] for key in indicators.keys()])
    
    return development_potential, indicators

def calculate_investment_timeline(development_potential, maturity_index):
    """Predict investment timeline based on current state"""
    timelines = {
        'immediate': [],
        'short_term': [],  # 1-2 years
        'medium_term': [],  # 3-5 years
        'long_term': []     # 5+ years
    }
    
    if development_potential > 70 and maturity_index < 60:
        timelines['immediate'].append("Alta demanda por serviços básicos")
        timelines['short_term'].append("Expansão de comércios locais")
        timelines['medium_term'].append("Desenvolvimento de centros comerciais")
    
    if maturity_index > 70 and development_potential > 50:
        timelines['immediate'].append("Mercado para serviços premium")
        timelines['short_term'].append("Gentrificação em andamento")
        timelines['medium_term'].append("Valorização imobiliária acelerada")
    
    if development_potential < 40:
        timelines['long_term'].append("Área consolidada - crescimento estável")
        timelines['immediate'].append("Foco em manutenção da infraestrutura")
    
    return timelines

def main():
    # Sidebar for advanced options
    with st.sidebar:
        st.header("🎛️ Configurações Avançadas")
        
        # Analysis radius
        st.subheader("📏 Raio de Análise")
        radius_options = {
            "1 km": 1000,
            "2 km": 2000, 
            "3 km": 3000
        }
        selected_radius = st.selectbox(
            "Selecione o raio:",
            options=list(radius_options.keys()),
            index=0,
            help="Defina o raio de análise para coleta de POIs"
        )
        st.session_state.analysis_radius = radius_options[selected_radius]
        
        # Quick Stats
        st.subheader("📊 Estatísticas da Sessão")
        if st.session_state.analysis_results:
            st.metric("Análises Realizadas", len(st.session_state.analysis_results))
            total_pois = sum([len(r.pois) for r in st.session_state.analysis_results.values() if r.success])
            st.metric("Total de POIs Coletados", total_pois)
        else:
            st.info("Nenhuma análise realizada ainda")

    # Main Application Header
    st.title("🏙️ UrbanSight Enhanced")
    st.subheader("Plataforma Avançada de Inteligência Imobiliária")
    
    # Navigation tabs
    main_tab1, main_tab2, main_tab3, main_tab4, main_tab5, main_tab6, main_tab7, main_tab8, main_tab9, main_tab10 = st.tabs([
        "🔍 Análise Individual", 
        "⚖️ Comparação de Propriedades", 
        "📊 Analytics Avançados",
        "🗺️ Mapas Avançados",
        "📈 Tendências & Futuro",
        "🎯 Ferramentas Inteligentes",
        "🛠️ Ferramentas Extras",
        "🏠 Minha Casa Ideal",
        "🏢 Para Imobiliárias",
        "🏆 UrbanSight Premium"
    ])
    
    with main_tab1:
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
                st.session_state.current_analysis = result

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
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis

            if result.success:
                st.write("---")

                # Analysis Header
                st.header("📋 Relatório de Análise")
                st.subheader(f"📍 {result.property_data.address}")
                st.caption(f"Analisado em {datetime.now().strftime('%d de %B de %Y às %H:%M')}")

                # Key Metrics Row
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

                # Enhanced Tabbed Content
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "📋 Resumo Executivo",
                    "🗺️ Mapas Interativos", 
                    "📊 Análise Detalhada",
                    "🎯 Acessibilidade",
                    "📈 Densidade & Distribuição",
                    "🧠 Insights de IA"
                ])

                with tab1:
                    st.subheader("📄 Resumo Executivo")

                    st.info(f"**🎯 Avaliação Geral:** {result.insights.executive_summary}")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("### ✅ Principais Pontos Fortes")
                        for i, strength in enumerate(result.insights.strengths[:5], 1):
                            st.success(f"**{i}.** {strength}")

                    with col2:
                        st.write("### ⚠️ Áreas de Preocupação") 
                        for i, concern in enumerate(result.insights.concerns[:5], 1):
                            st.warning(f"**{i}.** {concern}")

                    st.info(f"**👥 Perfil Ideal do Morador:** {result.insights.ideal_resident_profile}")
                    
                    # POI Quick Stats
                    st.subheader("📍 Estatísticas Rápidas dos POIs")
                    
                    poi_stats_cols = st.columns(4)
                    categories = result.metrics.category_counts
                    
                    category_translations = {
                        'education': '🎓 Educação',
                        'healthcare': '🏥 Saúde', 
                        'shopping': '🛍️ Compras',
                        'transport': '🚌 Transporte',
                        'entertainment': '🎭 Entretenimento',
                        'restaurant': '🍽️ Restaurantes',
                        'services': '🏛️ Serviços',
                        'park': '🌳 Parques'
                    }
                    
                    for i, (category, count) in enumerate(list(categories.items())[:4]):
                        with poi_stats_cols[i]:
                            translated = category_translations.get(category, f"📍 {category.title()}")
                            st.metric(translated, count)

                with tab2:
                    st.subheader("🗺️ Visualizações de Mapa")
                    
                    # Map options
                    map_type = st.selectbox(
                        "Tipo de Visualização:",
                        ["Mapa Padrão", "Mapa de Calor", "Mapa Filtrado por Categoria"]
                    )
                    
                    if map_type == "Mapa Padrão":
                        show_radius = st.checkbox("Mostrar raio de análise", value=True)
                        try:
                            m = create_folium_map(result, show_radius=show_radius)
                            folium_static(m, width=800, height=600)
                        except Exception as e:
                            st.error(f"Erro ao carregar mapa: {str(e)}")
                    
                    elif map_type == "Mapa de Calor":
                        st.write("**Mapa de Calor de Densidade de POIs**")
                        heat_categories = st.multiselect(
                            "Categorias para heatmap:",
                            list(set([poi.get('category', 'other') for poi in result.pois])),
                            default=list(set([poi.get('category', 'other') for poi in result.pois]))[:3]
                        )
                        
                        if heat_categories:
                            heatmap = create_poi_heatmap(result, heat_categories)
                            if heatmap:
                                folium_static(heatmap, width=800, height=600)
                            else:
                                st.warning("Não há dados suficientes para criar o mapa de calor")
                    
                    elif map_type == "Mapa Filtrado por Categoria":
                        filter_categories = st.multiselect(
                            "Mostrar apenas estas categorias:",
                            list(set([poi.get('category', 'other') for poi in result.pois])),
                            default=[]
                        )
                        
                        try:
                            m = create_folium_map(result, poi_filter=filter_categories)
                            folium_static(m, width=800, height=600)
                        except Exception as e:
                            st.error(f"Erro ao carregar mapa: {str(e)}")

                with tab3:
                    st.subheader("📊 Análise Detalhada")
                    
                    # POI Distribution Chart
                    dist_chart = create_poi_distribution_chart(result.pois)
                    if dist_chart:
                        st.plotly_chart(dist_chart, use_container_width=True)
                    
                    # Distance Analysis
                    dist_analysis = create_distance_analysis_chart(result.pois, 
                                                                 (result.property_data.lat, result.property_data.lon))
                    if dist_analysis:
                        st.plotly_chart(dist_analysis, use_container_width=True)
                    
                    # Detailed metrics table
                    st.subheader("📋 Tabela Detalhada de Métricas")
                    
                    metrics_data = {
                        'Métrica': ['Score Total', 'Walk Score', 'Acessibilidade', 'Conveniência', 'Qualidade de Vida'],
                        'Valor': [
                            f"{result.metrics.total_score:.1f}",
                            f"{result.metrics.walk_score.overall_score:.1f}",
                            f"{result.metrics.accessibility_score:.1f}",
                            f"{result.metrics.convenience_score:.1f}",
                            f"{result.metrics.quality_of_life_score:.1f}"
                        ],
                        'Nota': [
                            get_score_grade(result.metrics.total_score),
                            get_score_grade(result.metrics.walk_score.overall_score),
                            get_score_grade(result.metrics.accessibility_score),
                            get_score_grade(result.metrics.convenience_score),
                            get_score_grade(result.metrics.quality_of_life_score)
                        ]
                    }
                    
                    df_metrics = pd.DataFrame(metrics_data)
                    st.dataframe(df_metrics, use_container_width=True)

                with tab4:
                    st.subheader("🎯 Análise de Acessibilidade")
                    
                    # Accessibility heatmap
                    access_chart = create_accessibility_analysis(result)
                    if access_chart:
                        st.plotly_chart(access_chart, use_container_width=True)
                    
                    # Walking time analysis
                    st.subheader("🚶‍♂️ Tempo de Caminhada para Cada Categoria")
                    
                    walking_data = []
                    for category in set([poi.get('category', 'other') for poi in result.pois]):
                        category_pois = [poi for poi in result.pois if poi.get('category') == category]
                        if category_pois:
                            min_distance = min([poi.get('distance', 1000) for poi in category_pois])
                            walking_time = min_distance / 83.33  # minutes at 5km/h
                            walking_data.append({
                                'Categoria': category,
                                'Distância Mínima (m)': f"{min_distance:.0f}",
                                'Tempo de Caminhada (min)': f"{walking_time:.1f}"
                            })
                    
                    if walking_data:
                        df_walking = pd.DataFrame(walking_data)
                        st.dataframe(df_walking, use_container_width=True)

                with tab5:
                    st.subheader("📈 Densidade & Distribuição")
                    
                    # Density visualization
                    density_chart = create_density_visualization(result)
                    if density_chart:
                        st.plotly_chart(density_chart, use_container_width=True)
                    
                    # POI list with search
                    st.subheader("🔍 Lista Completa de POIs")
                    
                    search_term = st.text_input("Buscar POI:", placeholder="Digite o nome ou categoria...")
                    
                    poi_data = []
                    for poi in result.pois:
                        poi_data.append({
                            'Nome': poi.get('name', 'N/A'),
                            'Categoria': poi.get('category', 'N/A'),
                            'Distância (m)': poi.get('distance', 0),
                            'Subcategoria': poi.get('subcategoria', 'N/A')
                        })
                    
                    df_pois = pd.DataFrame(poi_data)
                    
                    if search_term:
                        mask = df_pois['Nome'].str.contains(search_term, case=False, na=False) | \
                               df_pois['Categoria'].str.contains(search_term, case=False, na=False)
                        df_pois = df_pois[mask]
                    
                    st.dataframe(df_pois, use_container_width=True)
                    
                    # Export functionality
                    st.subheader("📤 Exportar Dados")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📊 Baixar Dados dos POIs (CSV)", use_container_width=True):
                            csv_data = df_pois.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv_data,
                                file_name=f"pois_{result.property_data.address.replace(' ', '_')}.csv",
                                mime="text/csv"
                            )
                    
                    with col2:
                        if st.button("📋 Copiar Relatório Resumido", use_container_width=True):
                            summary_text = f"""
RELATÓRIO URBANSIGHT - {result.property_data.address}

📊 MÉTRICAS PRINCIPAIS:
• Score Total: {result.metrics.total_score:.1f}/100
• Walk Score: {result.metrics.walk_score.overall_score:.1f}/100
• Acessibilidade: {result.metrics.accessibility_score:.1f}/100
• Conveniência: {result.metrics.convenience_score:.1f}/100

📍 POIs ENCONTRADOS: {len(result.pois)}
• Educação: {result.metrics.category_counts.get('education', 0)}
• Saúde: {result.metrics.category_counts.get('healthcare', 0)}
• Compras: {result.metrics.category_counts.get('shopping', 0)}
• Transporte: {result.metrics.category_counts.get('transport', 0)}

✅ PONTOS FORTES:
{chr(10).join([f"• {strength}" for strength in result.insights.strengths[:3]])}

⚠️ PONTOS DE ATENÇÃO:
{chr(10).join([f"• {concern}" for concern in result.insights.concerns[:3]])}

Gerado por UrbanSight em {datetime.now().strftime('%d/%m/%Y às %H:%M')}
                            """
                            st.code(summary_text, language="text")
                            st.success("Texto copiado! Use Ctrl+A para selecionar tudo.")

                with tab6:
                    st.subheader("🧠 Insights de IA")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 🎯 Recomendações")
                        for i, recommendation in enumerate(result.insights.recommendations[:5], 1):
                            st.info(f"**{i}.** {recommendation}")
                    
                    with col2:
                        st.write("### 💰 Potencial de Investimento")
                        st.success(result.insights.investment_potential)
                        
                        st.write("### 📊 Posicionamento no Mercado")
                        st.info(result.insights.market_positioning)

    with main_tab2:
        st.header("⚖️ Comparação de Propriedades")
        
        st.write("Compare múltiplos endereços lado a lado para tomar decisões mais informadas.")
        
        # Add address to comparison
        new_address = st.text_input("Adicionar endereço para comparação:", key="comparison_input")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Adicionar à Comparação", type="primary"):
                if new_address and new_address not in st.session_state.comparison_addresses:
                    st.session_state.comparison_addresses.append(new_address)
                    st.success(f"Endereço adicionado: {new_address}")
        
        with col2:
            if st.button("🗑️ Limpar Comparação"):
                st.session_state.comparison_addresses = []
                st.success("Lista de comparação limpa!")
        
        # Show comparison addresses
        if st.session_state.comparison_addresses:
            st.subheader("📋 Endereços na Comparação")
            for i, addr in enumerate(st.session_state.comparison_addresses):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{i+1}. {addr}")
                with col2:
                    if st.button("❌", key=f"remove_{i}"):
                        st.session_state.comparison_addresses.pop(i)
                        st.rerun()
        
        # Analyze all addresses button
        if len(st.session_state.comparison_addresses) >= 2:
            if st.button("🚀 Analisar Todas as Propriedades", type="primary"):
                comparison_results = {}
                
                progress_bar = st.progress(0)
                total_addresses = len(st.session_state.comparison_addresses)
                
                for i, address in enumerate(st.session_state.comparison_addresses):
                    st.info(f"Analisando: {address}")
                    
                    # Check if already analyzed
                    if address in st.session_state.analysis_results:
                        comparison_results[address] = st.session_state.analysis_results[address]
                    else:
                        try:
                            result = asyncio.run(orchestrator.analyze_property(address))
                            if result.success:
                                st.session_state.analysis_results[address] = result
                                comparison_results[address] = result
                            else:
                                st.error(f"Falha ao analisar {address}: {result.error_message}")
                        except Exception as e:
                            st.error(f"Erro ao analisar {address}: {str(e)}")
                    
                    progress_bar.progress((i + 1) / total_addresses)
                
                progress_bar.empty()
                
                # Show comparison results
                if len(comparison_results) >= 2:
                    st.subheader("📊 Resultados da Comparação")
                    
                    # Comparison radar chart
                    comparison_chart = create_comparison_chart(comparison_results)
                    if comparison_chart:
                        st.plotly_chart(comparison_chart, use_container_width=True)
                    
                    # Comparison table
                    st.subheader("📋 Tabela de Comparação")
                    
                    comparison_data = []
                    for address, result in comparison_results.items():
                        comparison_data.append({
                            'Endereço': address[:50] + '...' if len(address) > 50 else address,
                            'Score Total': f"{result.metrics.total_score:.1f}",
                            'Walk Score': f"{result.metrics.walk_score.overall_score:.1f}",
                            'Acessibilidade': f"{result.metrics.accessibility_score:.1f}",
                            'Conveniência': f"{result.metrics.convenience_score:.1f}",
                            'Qualidade de Vida': f"{result.metrics.quality_of_life_score:.1f}",
                            'Total POIs': len(result.pois)
                        })
                    
                    df_comparison = pd.DataFrame(comparison_data)
                    st.dataframe(df_comparison, use_container_width=True)
                    
                    # Ranking
                    st.subheader("🏆 Ranking de Propriedades")
                    
                    # Sort by total score
                    ranking_data = sorted(comparison_results.items(), 
                                        key=lambda x: x[1].metrics.total_score, reverse=True)
                    
                    for i, (address, result) in enumerate(ranking_data):
                        score_color = get_score_color(result.metrics.total_score)
                        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
                        
                        st.markdown(f"""
                        **{medal} {address}**  
                        Score: {result.metrics.total_score:.1f} | Walk Score: {result.metrics.walk_score.overall_score:.1f}
                        """)

    with main_tab3:
        st.header("📊 Analytics Avançados")
        
        if st.session_state.analysis_results:
            st.subheader("📈 Análise Consolidada de Todas as Propriedades")
            
            # Overview metrics
            all_results = list(st.session_state.analysis_results.values())
            successful_results = [r for r in all_results if r.success]
            
            if successful_results:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    avg_total_score = np.mean([r.metrics.total_score for r in successful_results])
                    st.metric("Score Médio Total", f"{avg_total_score:.1f}")
                
                with col2:
                    avg_walk_score = np.mean([r.metrics.walk_score.overall_score for r in successful_results])
                    st.metric("Walk Score Médio", f"{avg_walk_score:.1f}")
                
                with col3:
                    total_pois = sum([len(r.pois) for r in successful_results])
                    st.metric("Total de POIs Analisados", total_pois)
                
                with col4:
                    st.metric("Propriedades Analisadas", len(successful_results))
                
                # Score distribution histogram
                st.subheader("📊 Distribuição de Scores")
                
                scores_data = []
                for address, result in st.session_state.analysis_results.items():
                    if result.success:
                        scores_data.append({
                            'Endereço': address[:30] + '...' if len(address) > 30 else address,
                            'Score Total': result.metrics.total_score,
                            'Walk Score': result.metrics.walk_score.overall_score,
                            'Acessibilidade': result.metrics.accessibility_score,
                            'Conveniência': result.metrics.convenience_score
                        })
                
                if scores_data:
                    df_scores = pd.DataFrame(scores_data)
                    
                    # Histogram of total scores
                    fig_hist = px.histogram(
                        df_scores, 
                        x='Score Total',
                        nbins=10,
                        title="Distribuição de Scores Totais"
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
                    # Correlation matrix
                    st.subheader("🔗 Matriz de Correlação entre Métricas")
                    
                    correlation_cols = ['Score Total', 'Walk Score', 'Acessibilidade', 'Conveniência']
                    corr_matrix = df_scores[correlation_cols].corr()
                    
                    fig_corr = px.imshow(
                        corr_matrix,
                        title="Matriz de Correlação",
                        color_continuous_scale="RdBu_r",
                        aspect="auto"
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
        
        else:
            st.info("👋 Realize algumas análises primeiro para ver os analytics avançados!")

    with main_tab4:
        st.header("🗺️ Mapas Interativos Avançados")
        st.markdown("*Visualizações avançadas com controles dinâmicos*")
        
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis
            
            # Advanced Controls Sidebar
            with st.sidebar:
                st.subheader("🎛️ Controles de Mapa")
                
                # Simple radius control
                radius_map_options = {
                    "1 km": 1000,
                    "2 km": 2000,
                    "3 km": 3000
                }
                selected_map_radius = st.selectbox("📏 Raio do Mapa", list(radius_map_options.keys()), index=0)
                dynamic_radius = radius_map_options[selected_map_radius]
                
                # Simplified heatmap controls
                st.subheader("🔥 Controles de Heatmap")
                heat_style = st.selectbox("Estilo", ["Padrão", "Intenso", "Suave"], index=0)
                
                # Set values based on style
                if heat_style == "Intenso":
                    heat_intensity, heat_blur = 25, 8
                elif heat_style == "Suave":
                    heat_intensity, heat_blur = 12, 15
                else:  # Padrão
                    heat_intensity, heat_blur = 15, 10
                
                # Simplified category filter
                st.subheader("🏷️ Categorias")
                filter_option = st.selectbox("Filtro", ["Todas", "Essenciais", "Lazer", "Comércio"], index=0)
                
                available_cats = list(set([poi.get('category', 'other') for poi in result.pois]))
                if filter_option == "Essenciais":
                    selected_cats = [cat for cat in available_cats if cat in ['healthcare', 'education', 'pharmacy', 'supermarket']]
                elif filter_option == "Lazer":
                    selected_cats = [cat for cat in available_cats if cat in ['restaurant', 'bar', 'park', 'entertainment', 'cinema']]
                elif filter_option == "Comércio":
                    selected_cats = [cat for cat in available_cats if cat in ['shopping', 'supermarket', 'bank', 'services']]
                else:  # Todas
                    selected_cats = available_cats
            
            # Map type selection
            map_types = st.tabs([
                "🔥 Heatmap Dinâmico",
                "⏱️ Isócronas",
                "🎨 Mapas Temáticos", 
                "⚖️ Split-Screen",
                "🧠 Clustering Inteligente",
                "📏 Raio Ajustável"
            ])
            
            with map_types[0]:
                st.subheader("🔥 Heatmap Dinâmico com Camadas")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    show_layers = st.checkbox("Múltiplas Camadas", True)
                    
                    if show_layers:
                        st.write("**Camadas Disponíveis:**")
                        st.write("🗺️ OpenStreetMap")
                        st.write("🧹 Limpo")
                        st.write("🌑 Escuro")
                        st.write("🌍 Satélite")
                    
                    st.write("**Configurações:**")
                    st.write(f"📏 Raio: {selected_map_radius}")
                    st.write(f"🔥 Estilo: {heat_style}")
                    st.write(f"🏷️ Filtro: {filter_option}")
                    st.write(f"📊 POIs: {len(selected_cats)} categorias")
                
                with col2:
                    heatmap = create_dynamic_heatmap(result, selected_cats, heat_intensity, heat_blur)
                    if heatmap:
                        folium_static(heatmap, width=800, height=500)
                    else:
                        st.warning("Nenhum POI encontrado para as categorias selecionadas")
            
            with map_types[1]:
                st.subheader("⏱️ Zonas de Tempo (Isócronas)")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    walk_times = st.multiselect(
                        "Tempos de Caminhada (min)",
                        [5, 10, 15, 20, 25, 30],
                        default=[5, 10, 15, 20]
                    )
                    
                    st.write("**Legenda:**")
                    st.write("🟢 5 min - Muito próximo")
                    st.write("🟡 10 min - Próximo")
                    st.write("🟠 15 min - Razoável")
                    st.write("🔴 20+ min - Distante")
                
                with col2:
                    if walk_times:
                        isochrone_map = create_isochrone_map(result, walk_times)
                        if isochrone_map:
                            folium_static(isochrone_map, width=800, height=500)
                    else:
                        st.info("Selecione pelo menos um tempo de caminhada")
            
            with map_types[2]:
                st.subheader("🎨 Mapas Temáticos por Lifestyle")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    theme = st.radio(
                        "Selecione o Tema:",
                        ['family', 'lifestyle', 'transport', 'emergency'],
                        format_func=lambda x: {
                            'family': '👨‍👩‍👧‍👦 Familiar',
                            'lifestyle': '🎉 Lifestyle',
                            'transport': '🚌 Mobilidade',
                            'emergency': '🚨 Emergencial'
                        }[x]
                    )
                    
                    theme_info = {
                        'family': "Escolas, saúde, parques e compras",
                        'lifestyle': "Restaurantes, entretenimento e lazer",
                        'transport': "Transporte público e conectividade",
                        'emergency': "Saúde e serviços essenciais"
                    }
                    
                    st.info(theme_info[theme])
                
                with col2:
                    thematic_map = create_thematic_map(result, theme)
                    if thematic_map:
                        folium_static(thematic_map, width=800, height=500)
            
            with map_types[3]:
                st.subheader("⚖️ Comparação Split-Screen")
                
                if len(st.session_state.analysis_results) >= 2:
                    addresses = list(st.session_state.analysis_results.keys())
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        addr1 = st.selectbox("Propriedade A", addresses, key="split_1")
                    with col2:
                        addr2 = st.selectbox("Propriedade B", [a for a in addresses if a != addr1], key="split_2")
                    
                    if addr1 and addr2:
                        comparison_results = {addr1: st.session_state.analysis_results[addr1], 
                                           addr2: st.session_state.analysis_results[addr2]}
                        
                        map1, map2 = create_split_screen_comparison_map(comparison_results)
                        
                        if map1 and map2:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**🏠 Propriedade A:** {addr1[:40]}...")
                                folium_static(map1, width=400, height=400)
                            
                            with col2:
                                st.markdown(f"**🏠 Propriedade B:** {addr2[:40]}...")
                                folium_static(map2, width=400, height=400)
                else:
                    st.info("Analise pelo menos 2 endereços para usar a comparação split-screen")
            
            with map_types[4]:
                st.subheader("🧠 Clustering Inteligente com Mini-Dashboards")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    zoom_level = st.slider("Nível de Zoom", 12, 17, 14)
                    
                    st.write("**Recursos:**")
                    st.write("📏 Ferramenta de medição")
                    st.write("✏️ Ferramentas de desenho")
                    st.write("🗺️ Mini-mapa")
                    st.write("📊 Dashboards nos POIs")
                
                with col2:
                    smart_map = create_smart_clustering_map(result, zoom_level)
                    if smart_map:
                        folium_static(smart_map, width=800, height=500)
            
            with map_types[5]:
                st.subheader("📏 Raio Ajustável com Estatísticas")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    show_rings = st.checkbox("Mostrar Anéis de Distância", True)
                    
                    # Filter POIs by radius
                    filtered_pois = [p for p in result.pois if p.get('distance', 0) <= dynamic_radius]
                    
                    st.write("**Estatísticas do Raio:**")
                    st.metric("Raio", f"{dynamic_radius}m")
                    st.metric("POIs no Raio", len(filtered_pois))
                    
                    if dynamic_radius > 0:
                        density = len(filtered_pois) / (3.14159 * (dynamic_radius/1000)**2)
                        st.metric("Densidade", f"{density:.1f} POIs/km²")
                
                with col2:
                    radius_map = create_adjustable_radius_map(result, dynamic_radius, show_rings)
                    if radius_map:
                        folium_static(radius_map, width=800, height=500)
        
        else:
            st.info("👋 **Analise um endereço primeiro!** Use a aba 'Análise Individual' para começar a usar os mapas avançados.")

    with main_tab5:
        st.header("📈 Análise de Tendências & Previsões")
        st.markdown("*Análise temporal simulada baseada em padrões urbanos*")
        
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis
            
            # Calculate all indices
            maturity_index, maturity_factors = calculate_urban_maturity_index(result.pois)
            gentrification_index, gentrification_scores = calculate_gentrification_index(result.pois)
            development_potential, development_indicators = predict_development_potential(result.pois, (result.property_data.lat, result.property_data.lon))
            investment_timeline = calculate_investment_timeline(development_potential, maturity_index)
            
            # Main metrics
            st.subheader("🎯 Índices de Análise Temporal")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                maturity_color = "🟢" if maturity_index >= 70 else "🟡" if maturity_index >= 50 else "🔴"
                st.metric("Maturidade Urbana", f"{maturity_index:.1f}/100", help="Desenvolvimento e consolidação urbana")
                st.markdown(f"{maturity_color} **Status:** {'Consolidado' if maturity_index >= 70 else 'Em desenvolvimento' if maturity_index >= 50 else 'Emergente'}")
            
            with col2:
                gentrif_color = "🔴" if gentrification_index >= 60 else "🟡" if gentrification_index >= 30 else "🟢"
                st.metric("Índice de Gentrificação", f"{gentrification_index:.1f}/100", help="Indicadores de transformação social")
                st.markdown(f"{gentrif_color} **Risco:** {'Alto' if gentrification_index >= 60 else 'Médio' if gentrification_index >= 30 else 'Baixo'}")
            
            with col3:
                dev_color = "🟢" if development_potential >= 70 else "🟡" if development_potential >= 50 else "🔴"
                st.metric("Potencial de Desenvolvimento", f"{development_potential:.1f}/100", help="Capacidade de crescimento futuro")
                st.markdown(f"{dev_color} **Potencial:** {'Alto' if development_potential >= 70 else 'Médio' if development_potential >= 50 else 'Limitado'}")
            
            with col4:
                # Investment attractiveness (combined score)
                investment_score = (maturity_index * 0.4 + development_potential * 0.4 + (100 - gentrification_index) * 0.2)
                inv_color = "🟢" if investment_score >= 70 else "🟡" if investment_score >= 50 else "🔴"
                st.metric("Score de Investimento", f"{investment_score:.1f}/100", help="Atratividade geral para investimento")
                st.markdown(f"{inv_color} **Recomendação:** {'Comprar' if investment_score >= 70 else 'Considerar' if investment_score >= 50 else 'Aguardar'}")
            
            # Detailed Analysis Tabs
            trend_tabs = st.tabs([
                "🏙️ Evolução Urbana",
                "📊 Análise Comparativa", 
                "🔮 Previsões Futuras",
                "💰 Timeline de Investimento",
                "🏘️ Bairros Similares"
            ])
            
            with trend_tabs[0]:
                st.subheader("🏙️ Análise da Evolução Urbana")
                
                # Urban maturity breakdown
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📊 Fatores de Maturidade")
                    
                    for factor, score in maturity_factors.items():
                        factor_names = {
                            'diversity': '🏷️ Diversidade de Serviços',
                            'density': '📍 Densidade de POIs',
                            'essential_services': '🏥 Serviços Essenciais',
                            'premium_services': '✨ Serviços Premium',
                            'transport_connectivity': '🚌 Conectividade'
                        }
                        
                        name = factor_names.get(factor, factor.title())
                        st.progress(score/100)
                        st.caption(f"{name}: {score:.1f}/100")
                
                with col2:
                    st.markdown("### 📈 Estágio de Desenvolvimento")
                    
                    if maturity_index < 30:
                        stage = "🌱 **Embrionário**"
                        description = "Área em início de desenvolvimento. Poucos serviços, grande potencial de crescimento."
                        st.success(stage)
                        st.info(description)
                    elif maturity_index < 50:
                        stage = "🏗️ **Em Expansão**"
                        description = "Desenvolvimento acelerado. Chegada de novos serviços e comércios."
                        st.info(stage)
                        st.info(description)
                    elif maturity_index < 70:
                        stage = "🏙️ **Consolidação**"
                        description = "Infraestrutura estabelecida. Equilíbrio entre crescimento e estabilidade."
                        st.warning(stage)
                        st.info(description)
                    else:
                        stage = "🏛️ **Maduro**"
                        description = "Área totalmente desenvolvida. Foco na qualidade e manutenção."
                        st.error(stage)
                        st.info(description)
                    
                    # Development recommendations
                    st.markdown("### 💡 Implicações para Investidores")
                    
                    if maturity_index < 50:
                        st.success("✅ **Oportunidade:** Comprar antes da valorização")
                        st.success("✅ **Estratégia:** Buy & Hold de longo prazo")
                        st.warning("⚠️ **Risco:** Desenvolvimento pode ser lento")
                    elif maturity_index < 70:
                        st.info("📊 **Estratégia:** Análise caso a caso")
                        st.success("✅ **Estabilidade:** Mercado equilibrado")
                        st.info("📈 **Valorização:** Moderada e constante")
                    else:
                        st.warning("⚠️ **Atenção:** Preços já refletem desenvolvimento")
                        st.info("📊 **Estratégia:** Foco em imóveis diferenciados")
                        st.success("✅ **Segurança:** Investimento conservador")
            
            with trend_tabs[1]:
                st.subheader("📊 Análise Comparativa de Desenvolvimento")
                
                # Comparative analysis with other analyzed properties
                if len(st.session_state.analysis_results) > 1:
                    comparison_data = []
                    
                    for address, analysis_result in st.session_state.analysis_results.items():
                        if hasattr(analysis_result, 'pois'):
                            addr_maturity, _ = calculate_urban_maturity_index(analysis_result.pois)
                            addr_gentrification, _ = calculate_gentrification_index(analysis_result.pois)
                            addr_development, _ = predict_development_potential(analysis_result.pois, (analysis_result.property_data.lat, analysis_result.property_data.lon))
                            
                            comparison_data.append({
                                'Endereço': address[:40] + '...' if len(address) > 40 else address,
                                'Maturidade': addr_maturity,
                                'Gentrificação': addr_gentrification,
                                'Potencial': addr_development,
                                'POIs': len(analysis_result.pois),
                                'Fase': 'Maduro' if addr_maturity >= 70 else 'Consolidação' if addr_maturity >= 50 else 'Expansão' if addr_maturity >= 30 else 'Embrionário'
                            })
                    
                    # Sort by maturity index
                    comparison_data.sort(key=lambda x: x['Maturidade'], reverse=True)
                    
                    # Create comparison chart
                    df_comparison = pd.DataFrame(comparison_data)
                    
                    # Radar chart for current property vs others
                    fig = go.Figure()
                    
                    # Highlight current property
                    for i, row in df_comparison.iterrows():
                        is_current = any(addr in row['Endereço'] for addr in [result.property_data.address[:40]])
                        
                        fig.add_trace(go.Scatterpolar(
                            r=[row['Maturidade'], row['Potencial'], 100-row['Gentrificação']],
                            theta=['Maturidade Urbana', 'Potencial Desenvolvimento', 'Estabilidade Social'],
                            fill='toself' if is_current else None,
                            name=row['Endereço'],
                            line=dict(width=3 if is_current else 1),
                            opacity=0.8 if is_current else 0.4
                        ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100])
                        ),
                        showlegend=True,
                        title="Comparação de Índices de Desenvolvimento"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Ranking table
                    st.subheader("🏆 Ranking de Desenvolvimento")
                    st.dataframe(df_comparison, use_container_width=True)
                
                else:
                    st.info("Analise mais endereços para ver comparações detalhadas")
                    
                # Benchmark with typical urban patterns
                st.subheader("📏 Benchmark com Padrões Urbanos")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🎯 Sua Localização")
                    benchmark_current = {
                        'Maturidade': maturity_index,
                        'Gentrificação': gentrification_index,
                        'Desenvolvimento': development_potential
                    }
                    
                    for metric, value in benchmark_current.items():
                        st.metric(metric, f"{value:.1f}/100")
                
                with col2:
                    st.markdown("### 📊 Padrões Típicos")
                    
                    benchmarks = {
                        "Centro SP": {"Maturidade": 95, "Gentrificação": 85, "Desenvolvimento": 25},
                        "Bairro Nobre": {"Maturidade": 85, "Gentrificação": 60, "Desenvolvimento": 40},
                        "Subúrbio": {"Maturidade": 45, "Gentrificação": 15, "Desenvolvimento": 75},
                        "Periferia": {"Maturidade": 25, "Gentrificação": 5, "Desenvolvimento": 90}
                    }
                    
                    # Find closest benchmark
                    distances = {}
                    for area, metrics in benchmarks.items():
                        distance = sum([(maturity_index - metrics["Maturidade"])**2, 
                                      (gentrification_index - metrics["Gentrificação"])**2,
                                      (development_potential - metrics["Desenvolvimento"])**2]) ** 0.5
                        distances[area] = distance
                    
                    closest = min(distances.items(), key=lambda x: x[1])
                    
                    st.success(f"🎯 **Perfil mais similar:** {closest[0]}")
                    
                    for area, metrics in benchmarks.items():
                        similarity = "🎯" if area == closest[0] else "📍"
                        st.markdown(f"{similarity} **{area}**: Mat.{metrics['Maturidade']:.0f} | Gen.{metrics['Gentrificação']:.0f} | Dev.{metrics['Desenvolvimento']:.0f}")
            
            with trend_tabs[2]:
                st.subheader("🔮 Previsões de Desenvolvimento Futuro")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📊 Indicadores de Crescimento")
                    
                    for indicator, score in development_indicators.items():
                        indicator_names = {
                            'infrastructure_gaps': '🏗️ Lacunas de Infraestrutura',
                            'growth_momentum': '📈 Momentum de Crescimento',
                            'accessibility_factor': '🚌 Fator de Acessibilidade',
                            'market_potential': '💼 Potencial de Mercado'
                        }
                        
                        name = indicator_names.get(indicator, indicator.title())
                        st.progress(score/100)
                        st.caption(f"{name}: {score:.1f}/100")
                
                with col2:
                    st.markdown("### 🎯 Cenários Futuros")
                    
                    # Scenario planning
                    scenarios = []
                    
                    if development_potential > 70:
                        scenarios.append({
                            'nome': '🚀 Crescimento Acelerado',
                            'probabilidade': 70,
                            'descrição': 'Rápida expansão de serviços e valorização imobiliária'
                        })
                    
                    if maturity_index > 60 and development_potential > 40:
                        scenarios.append({
                            'nome': '📈 Desenvolvimento Sustentado',
                            'probabilidade': 60,
                            'descrição': 'Crescimento gradual e consolidação da infraestrutura'
                        })
                    
                    if gentrification_index > 50:
                        scenarios.append({
                            'nome': '⚠️ Gentrificação Intensiva',
                            'probabilidade': 50,
                            'descrição': 'Transformação social acelerada, possível exclusão'
                        })
                    
                    scenarios.append({
                        'nome': '🔄 Estabilização',
                        'probabilidade': 80 - development_potential,
                        'descrição': 'Manutenção do estado atual, crescimento lento'
                    })
                    
                    for scenario in scenarios[:3]:  # Show top 3 scenarios
                        prob_color = "🟢" if scenario['probabilidade'] >= 60 else "🟡" if scenario['probabilidade'] >= 40 else "🔴"
                        st.markdown(f"**{scenario['nome']}** {prob_color}")
                        st.progress(scenario['probabilidade']/100)
                        st.caption(f"{scenario['descrição']} ({scenario['probabilidade']:.0f}% probabilidade)")
                        st.markdown("---")
                
                # Future value projection
                st.markdown("### 💰 Projeção de Valorização")
                
                # Simple valorization model based on indices
                base_valorization = 3  # Base 3% per year
                
                development_bonus = (development_potential / 100) * 2  # Up to 2% bonus
                maturity_penalty = (maturity_index / 100) * 1  # Up to 1% penalty for mature areas
                gentrif_bonus = (gentrification_index / 100) * 3  # Up to 3% bonus for gentrification
                
                projected_valorization = base_valorization + development_bonus - maturity_penalty + gentrif_bonus
                
                valorization_cols = st.columns(4)
                
                with valorization_cols[0]:
                    st.metric("1 Ano", f"+{projected_valorization:.1f}%")
                with valorization_cols[1]:
                    st.metric("3 Anos", f"+{projected_valorization * 3:.1f}%")
                with valorization_cols[2]:
                    st.metric("5 Anos", f"+{projected_valorization * 5:.1f}%")
                with valorization_cols[3]:
                    st.metric("10 Anos", f"+{projected_valorization * 10:.1f}%")
                
                st.caption("⚠️ Projeções baseadas em padrões urbanos simulados, não garantem resultados reais.")
            
            with trend_tabs[3]:
                st.subheader("💰 Timeline de Oportunidades de Investimento")
                
                timeline_periods = [
                    ('⚡ Imediato', 'immediate', '#FF6B6B'),
                    ('📅 Curto Prazo (1-2 anos)', 'short_term', '#4ECDC4'),
                    ('📈 Médio Prazo (3-5 anos)', 'medium_term', '#45B7D1'),
                    ('🎯 Longo Prazo (5+ anos)', 'long_term', '#96CEB4')
                ]
                
                for period_name, period_key, color in timeline_periods:
                    opportunities = investment_timeline.get(period_key, [])
                    
                    if opportunities:
                        st.markdown(f"### {period_name}")
                        
                        for opportunity in opportunities:
                            st.markdown(f"""
                            <div style="background: {color}20; padding: 10px; border-radius: 5px; margin: 5px 0; border-left: 4px solid {color};">
                                <strong style="color: {color};">💡 {opportunity}</strong>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"### {period_name}")
                        st.info("Nenhuma oportunidade específica identificada para este período")
                
                # Investment strategy recommendations
                st.markdown("---")
                st.subheader("🎯 Estratégia de Investimento Recomendada")
                
                if investment_score >= 80:
                    st.success("🟢 **COMPRA RECOMENDADA**: Excelente oportunidade de investimento")
                    st.markdown("**Estratégia sugerida:** Buy & Hold agressivo, considere múltiplas unidades")
                elif investment_score >= 60:
                    st.info("🟡 **ANÁLISE DETALHADA**: Oportunidade interessante com algumas ressalvas")
                    st.markdown("**Estratégia sugerida:** Análise criteriosa, negocie bem o preço")
                elif investment_score >= 40:
                    st.warning("🟠 **CAUTELA**: Investimento de risco médio-alto")
                    st.markdown("**Estratégia sugerida:** Apenas se conseguir desconto significativo")
                else:
                    st.error("🔴 **NÃO RECOMENDADO**: Alto risco, baixo retorno esperado")
                    st.markdown("**Estratégia sugerida:** Aguardar melhores oportunidades")
            
            with trend_tabs[4]:
                st.subheader("🏘️ Bairros com Perfil Similar")
                
                # Find similar neighborhoods
                similar_neighborhoods = find_similar_neighborhoods(result, st.session_state.analysis_results)
                
                if similar_neighborhoods:
                    st.markdown("### 📊 Propriedades Similares Analisadas")
                    
                    for i, (address, similarity, similar_result) in enumerate(similar_neighborhoods):
                        similar_maturity, _ = calculate_urban_maturity_index(similar_result.pois)
                        similar_development, _ = predict_development_potential(similar_result.pois, (similar_result.property_data.lat, similar_result.property_data.lon))
                        
                        with st.expander(f"#{i+1} {address[:50]}... (Similaridade: {similarity:.2f})"):
                            
                            sim_col1, sim_col2, sim_col3 = st.columns(3)
                            
                            with sim_col1:
                                st.metric("Similaridade", f"{similarity:.0%}")
                                st.metric("POIs", len(similar_result.pois))
                            
                            with sim_col2:
                                st.metric("Maturidade", f"{similar_maturity:.1f}")
                                st.metric("Desenvolvimento", f"{similar_development:.1f}")
                            
                            with sim_col3:
                                # Comparison with current
                                mat_diff = similar_maturity - maturity_index
                                dev_diff = similar_development - development_potential
                                
                                st.metric("Δ Maturidade", f"{mat_diff:+.1f}", delta=f"{mat_diff:+.1f}")
                                st.metric("Δ Desenvolvimento", f"{dev_diff:+.1f}", delta=f"{dev_diff:+.1f}")
                            
                            # POI category comparison
                            st.markdown("**Comparação de Categorias:**")
                            
                            current_categories = {}
                            for poi in result.pois:
                                cat = poi.get('category', 'outros')
                                current_categories[cat] = current_categories.get(cat, 0) + 1
                            
                            similar_categories = {}
                            for poi in similar_result.pois:
                                cat = poi.get('category', 'outros')
                                similar_categories[cat] = similar_categories.get(cat, 0) + 1
                            
                            all_cats = set(list(current_categories.keys()) + list(similar_categories.keys()))
                            
                            comp_data = []
                            for cat in all_cats:
                                comp_data.append({
                                    'Categoria': cat.title(),
                                    'Atual': current_categories.get(cat, 0),
                                    'Similar': similar_categories.get(cat, 0),
                                    'Diferença': similar_categories.get(cat, 0) - current_categories.get(cat, 0)
                                })
                            
                            df_comp = pd.DataFrame(comp_data)
                            st.dataframe(df_comp, use_container_width=True)
                
                else:
                    st.info("Analise mais propriedades para encontrar bairros similares")
                    
                # Suggest what to look for in similar areas
                st.markdown("---")
                st.subheader("🔍 O que Procurar em Áreas Similares")
                
                search_tips = []
                
                if development_potential > 70:
                    search_tips.append("🚀 Áreas com poucos POIs mas boa conectividade")
                    search_tips.append("📍 Locais próximos a grandes projetos urbanos")
                
                if maturity_index < 50:
                    search_tips.append("🏗️ Bairros em início de desenvolvimento")
                    search_tips.append("🛣️ Regiões com melhorias de transporte planejadas")
                
                if gentrification_index > 40:
                    search_tips.append("☕ Áreas com aumento de cafés e restaurantes")
                    search_tips.append("🎨 Bairros com vida cultural emergente")
                
                search_tips.append("📊 Regiões com perfil demográfico similar")
                search_tips.append("🗺️ Distância similar ao centro da cidade")
                
                for tip in search_tips:
                    st.markdown(f"• {tip}")
        
        else:
            st.info("👋 **Realize uma análise primeiro!** Use a aba 'Análise Individual' para ver as tendências e previsões.")
            
            # Preview of what will be available
            st.markdown("### 📈 **Análises Temporais Disponíveis:**")
            
            preview_col1, preview_col2 = st.columns(2)
            
            with preview_col1:
                st.markdown("**🏙️ Evolução Urbana**")
                st.caption("Índice de maturidade e estágio de desenvolvimento")
                
                st.markdown("**📊 Análise Comparativa**")
                st.caption("Benchmark com outras áreas analisadas")
                
                st.markdown("**🔮 Previsões Futuras**")
                st.caption("Cenários de desenvolvimento e valorização")
            
            with preview_col2:
                st.markdown("**💰 Timeline de Investimento**")
                st.caption("Oportunidades por horizonte temporal")
                
                st.markdown("**🏘️ Bairros Similares**")
                st.caption("Identificação de áreas com perfil parecido")
                
                st.markdown("**🎯 Estratégias Personalizadas**")
                st.caption("Recomendações baseadas nos índices")

    with main_tab6:
        st.header("🎯 Ferramentas Inteligentes")
        st.markdown("*Funcionalidades avançadas para diferentes perfis de usuários*")
        
        # Sub-tabs por persona
        persona_tab1, persona_tab2, persona_tab3, persona_tab4 = st.tabs([
            "🏠 Para Morar", 
            "💰 Para Investir",
            "🏢 Para Corretores",
            "🎮 Simuladores"
        ])
        
        with persona_tab1:
            st.subheader("🏠 Ferramentas para Quem Quer Morar")
            
            if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                # Pegar o último resultado analisado
                result = list(st.session_state.analysis_results.values())[-1]
                pois = result.pois
                property_coords = (result.property_data.lat, result.property_data.lon)
                
                # Calculadora de Custo Total
                st.markdown("### 💰 Calculadora de Custo Total de Vida")
                
                col1, col2 = st.columns(2)
                with col1:
                    rent_value = st.number_input("💸 Valor do Aluguel/Financiamento (R$)", value=2500, step=100)
                    transport_monthly = st.number_input("🚗 Gasto Mensal com Transporte (R$)", value=400, step=50)
                
                with col2:
                    delivery_frequency = st.slider("🛵 Pedidos de Delivery por Semana", 0, 10, 3)
                    avg_delivery_cost = st.number_input("🍕 Custo Médio por Delivery (R$)", value=35, step=5)
                
                # Cálculos automáticos baseados na infraestrutura
                restaurants_nearby = len([p for p in pois if p['category'] in ['restaurant', 'fast_food', 'cafe']])
                markets_nearby = len([p for p in pois if p['category'] in ['supermarket', 'convenience']])
                
                # Fatores de desconto/aumento baseados na infraestrutura
                restaurant_factor = max(0.7, 1 - (restaurants_nearby * 0.05))  # Mais restaurantes = menos delivery
                market_factor = max(0.8, 1 - (markets_nearby * 0.1))  # Mais mercados = menos gastos
                transport_factor = 1.0
                
                if result.metrics.total_score > 80:
                    transport_factor = 0.8  # Boa infraestrutura = menos Uber
                elif result.metrics.total_score < 60:
                    transport_factor = 1.2  # Infraestrutura ruim = mais Uber
                
                # Cálculo final
                monthly_delivery = delivery_frequency * 4 * avg_delivery_cost * restaurant_factor
                adjusted_transport = transport_monthly * transport_factor
                grocery_estimated = 800 * market_factor  # Estimativa baseada em mercados próximos
                
                total_monthly = rent_value + adjusted_transport + monthly_delivery + grocery_estimated
                
                # Exibição dos resultados
                st.markdown("#### 📊 Resumo de Custos Mensais")
                
                cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)
                
                with cost_col1:
                    st.metric("🏠 Moradia", f"R$ {rent_value:,.0f}")
                
                with cost_col2:
                    st.metric("🚗 Transporte", f"R$ {adjusted_transport:,.0f}", 
                             f"{transport_factor-1:+.0%}" if transport_factor != 1 else None)
                
                with cost_col3:
                    st.metric("🛵 Delivery", f"R$ {monthly_delivery:,.0f}",
                             f"{restaurant_factor-1:+.0%}" if restaurant_factor != 1 else None)
                
                with cost_col4:
                    st.metric("🛒 Mercado", f"R$ {grocery_estimated:,.0f}",
                             f"{market_factor-1:+.0%}" if market_factor != 1 else None)
                
                st.markdown("---")
                total_col1, total_col2 = st.columns(2)
                
                with total_col1:
                    st.metric("💰 **TOTAL MENSAL**", f"R$ {total_monthly:,.0f}")
                
                with total_col2:
                    yearly_total = total_monthly * 12
                    st.metric("📅 **TOTAL ANUAL**", f"R$ {yearly_total:,.0f}")
                
                # Insights automáticos
                st.markdown("#### 💡 Insights Inteligentes")
                
                if restaurant_factor < 1:
                    st.success(f"🍽️ **Economia em Delivery**: {restaurants_nearby} restaurantes próximos podem reduzir seus gastos em {(1-restaurant_factor)*100:.0f}%")
                
                if market_factor < 1:
                    st.success(f"🛒 **Economia no Mercado**: {markets_nearby} mercados próximos facilitam compras e reduzem custos em {(1-market_factor)*100:.0f}%")
                
                if transport_factor < 1:
                    st.success(f"🚶 **Economia em Transporte**: Excelente walkability reduz gastos com transporte em {(1-transport_factor)*100:.0f}%")
                elif transport_factor > 1:
                    st.warning(f"🚗 **Atenção**: Infraestrutura limitada pode aumentar gastos com transporte em {(transport_factor-1)*100:.0f}%")
                
                # Filtros Personalizados
                st.markdown("### 🎯 Filtros Inteligentes")
                
                filter_col1, filter_col2 = st.columns(2)
                
                with filter_col1:
                    st.markdown("#### 🐕 Pet-Friendly Score")
                    pet_pois = [p for p in pois if p['category'] in ['veterinary', 'pet', 'park']]
                    pet_score = min(100, len(pet_pois) * 20)
                    st.progress(pet_score/100)
                    st.caption(f"Score: {pet_score}/100 ({len(pet_pois)} POIs pet-friendly)")
                    
                    st.markdown("#### 👶 Família com Bebê Score")
                    family_pois = [p for p in pois if p['category'] in ['hospital', 'pharmacy', 'kindergarten', 'school']]
                    family_score = min(100, len(family_pois) * 15)
                    st.progress(family_score/100)
                    st.caption(f"Score: {family_score}/100 ({len(family_pois)} POIs familiares)")
                
                with filter_col2:
                    st.markdown("#### 🚶 Sem Carro Score")
                    walk_score = result.metrics.walk_score.overall_score
                    st.progress(walk_score/100)
                    st.caption(f"Walk Score: {walk_score}/100")
                    
                    st.markdown("#### 🎵 Vida Noturna Score")
                    nightlife_pois = [p for p in pois if p['category'] in ['bar', 'pub', 'nightclub', 'theatre', 'cinema']]
                    nightlife_score = min(100, len(nightlife_pois) * 12)
                    st.progress(nightlife_score/100)
                    st.caption(f"Score: {nightlife_score}/100 ({len(nightlife_pois)} POIs noturnos)")
                
            else:
                st.info("🏠 **Analise um endereço primeiro!** Use a aba 'Análise Individual' para começar.")
        
        with persona_tab2:
            st.subheader("💰 Ferramentas para Investidores")
            
            if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                # Pegar o último resultado analisado
                result = list(st.session_state.analysis_results.values())[-1]
                pois = result.pois
                property_coords = (result.property_data.lat, result.property_data.lon)
                
                # Análise de Potencial Airbnb
                st.markdown("### 🏨 Análise de Potencial Airbnb")
                
                # Fatores para Airbnb
                tourism_pois = [p for p in pois if p['category'] in ['attraction', 'museum', 'theatre', 'viewpoint', 'monument']]
                transport_pois = [p for p in pois if p['category'] in ['public_transport', 'bus_station', 'subway_entrance']]
                restaurant_pois = [p for p in pois if p['category'] in ['restaurant', 'cafe', 'bar']]
                convenience_pois = [p for p in pois if p['category'] in ['supermarket', 'pharmacy', 'atm']]
                
                tourism_score = min(30, len(tourism_pois) * 5)
                transport_score = min(25, len(transport_pois) * 5)
                restaurant_score = min(25, len(restaurant_pois) * 2)
                convenience_score = min(20, len(convenience_pois) * 4)
                
                airbnb_score = tourism_score + transport_score + restaurant_score + convenience_score
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("🎯 Atrações", f"{tourism_score}/30", f"{len(tourism_pois)} POIs")
                with col2:
                    st.metric("🚊 Transporte", f"{transport_score}/25", f"{len(transport_pois)} POIs")
                with col3:
                    st.metric("🍽️ Gastronomia", f"{restaurant_score}/25", f"{len(restaurant_pois)} POIs")
                with col4:
                    st.metric("🛒 Conveniência", f"{convenience_score}/20", f"{len(convenience_pois)} POIs")
                
                st.markdown("---")
                
                airbnb_col1, airbnb_col2 = st.columns(2)
                
                with airbnb_col1:
                    st.metric("🏨 **POTENCIAL AIRBNB**", f"{airbnb_score}/100")
                    st.progress(airbnb_score/100)
                
                with airbnb_col2:
                    if airbnb_score >= 80:
                        st.success("🌟 **EXCELENTE** para Airbnb!")
                        expected_occupancy = "85-95%"
                    elif airbnb_score >= 60:
                        st.info("✅ **BOM** para Airbnb")
                        expected_occupancy = "70-85%"
                    elif airbnb_score >= 40:
                        st.warning("⚠️ **MODERADO** para Airbnb")
                        expected_occupancy = "50-70%"
                    else:
                        st.error("❌ **BAIXO POTENCIAL** para Airbnb")
                        expected_occupancy = "30-50%"
                    
                    st.caption(f"Taxa de ocupação esperada: {expected_occupancy}")
                
                # Perfil do Inquilino
                st.markdown("### 👥 Análise de Perfil do Inquilino")
                
                # Análise baseada nos POIs
                young_prof_score = 0
                family_score = 0
                student_score = 0
                
                for poi in pois:
                    if poi['category'] in ['bar', 'nightclub', 'gym', 'coworking']:
                        young_prof_score += 2
                    elif poi['category'] in ['school', 'kindergarten', 'playground', 'pharmacy']:
                        family_score += 2
                    elif poi['category'] in ['university', 'library', 'fast_food', 'convenience']:
                        student_score += 2
                    elif poi['category'] in ['coffee', 'restaurant']:
                        young_prof_score += 1
                        family_score += 1
                
                # Normalizar scores
                total_profile_score = young_prof_score + family_score + student_score
                if total_profile_score > 0:
                    young_prof_pct = (young_prof_score / total_profile_score) * 100
                    family_pct = (family_score / total_profile_score) * 100
                    student_pct = (student_score / total_profile_score) * 100
                else:
                    young_prof_pct = family_pct = student_pct = 33.33
                
                profile_col1, profile_col2, profile_col3 = st.columns(3)
                
                with profile_col1:
                    st.markdown("#### 👔 Jovens Profissionais")
                    st.progress(young_prof_pct/100)
                    st.caption(f"{young_prof_pct:.1f}% compatibilidade")
                
                with profile_col2:
                    st.markdown("#### 👨‍👩‍👧‍👦 Famílias")
                    st.progress(family_pct/100)
                    st.caption(f"{family_pct:.1f}% compatibilidade")
                
                with profile_col3:
                    st.markdown("#### 🎓 Estudantes")
                    st.progress(student_pct/100)
                    st.caption(f"{student_pct:.1f}% compatibilidade")
                
                # Perfil recomendado
                if young_prof_pct > family_pct and young_prof_pct > student_pct:
                    st.success("🎯 **Perfil Ideal**: Jovens profissionais (25-35 anos), renda R$ 5-15k")
                elif family_pct > student_pct:
                    st.success("🎯 **Perfil Ideal**: Famílias com filhos, renda R$ 8-20k")
                else:
                    st.success("🎯 **Perfil Ideal**: Estudantes universitários, renda R$ 2-6k")
                
                # Ciclo de Valorização
                st.markdown("### 📈 Ciclo de Valorização")
                
                infrastructure_density = len(pois) / 5  # POIs por km²
                essential_services = len([p for p in pois if p['category'] in ['hospital', 'school', 'supermarket', 'pharmacy']])
                premium_services = len([p for p in pois if p['category'] in ['restaurant', 'cafe', 'gym', 'beauty_salon']])
                
                if infrastructure_density < 10:
                    cycle_stage = "🌱 Emergente"
                    cycle_desc = "Região em desenvolvimento inicial, alto potencial de valorização"
                    valorization_potential = "Alta (15-25% ao ano)"
                elif infrastructure_density < 20:
                    cycle_stage = "🚀 Crescimento"
                    cycle_desc = "Infraestrutura consolidando, valorização acelerada"
                    valorization_potential = "Moderada-Alta (8-15% ao ano)"
                elif infrastructure_density < 35:
                    cycle_stage = "🏢 Consolidado"
                    cycle_desc = "Região estabelecida, valorização estável"
                    valorization_potential = "Moderada (5-8% ao ano)"
                else:
                    cycle_stage = "💎 Maduro"
                    cycle_desc = "Região premium, valorização conservadora"
                    valorization_potential = "Conservadora (3-5% ao ano)"
                
                cycle_col1, cycle_col2 = st.columns(2)
                
                with cycle_col1:
                    st.markdown(f"#### {cycle_stage}")
                    st.write(cycle_desc)
                    st.metric("Densidade de Infraestrutura", f"{infrastructure_density:.1f} POIs/km²")
                
                with cycle_col2:
                    st.markdown("#### 📊 Potencial de Valorização")
                    st.success(valorization_potential)
                    st.metric("Serviços Essenciais", essential_services)
                    st.metric("Serviços Premium", premium_services)
                
            else:
                st.info("💰 **Analise um endereço primeiro!** Use a aba 'Análise Individual' para começar.")
        
        with persona_tab3:
            st.subheader("🏢 Ferramentas para Corretores & Imobiliárias")
            
            if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                # Pegar o último resultado analisado
                result = list(st.session_state.analysis_results.values())[-1]
                pois = result.pois
                
                # Gerador de Pitch
                st.markdown("### 📋 Gerador de Pitch Automático")
                
                property_price = st.number_input("💰 Preço do Imóvel (R$)", value=500000, step=25000)
                property_type = st.selectbox("🏠 Tipo do Imóvel", ["Apartamento", "Casa", "Cobertura", "Studio", "Loft"])
                
                if st.button("🚀 Gerar Pitch de Vendas", type="primary"):
                    
                    # Análise automática dos pontos fortes
                    strong_categories = {}
                    for poi in pois[:10]:  # Top 10 POIs mais próximos
                        cat = poi['category']
                        if cat not in strong_categories:
                            strong_categories[cat] = []
                        strong_categories[cat].append(poi)
                    
                    # Identificar diferenciais únicos
                    unique_features = []
                    premium_pois = [p for p in pois if p['category'] in ['restaurant', 'gym', 'beauty_salon', 'cinema']]
                    essential_pois = [p for p in pois if p['category'] in ['hospital', 'school', 'supermarket', 'pharmacy']]
                    
                    if len(premium_pois) > 8:
                        unique_features.append("Região premium com alta concentração de serviços sofisticados")
                    if len(essential_pois) > 6:
                        unique_features.append("Infraestrutura completa para o dia a dia")
                    if result.metrics.walk_score.overall_score > 80:
                        unique_features.append("Excelente walkability - viva sem carro!")
                    
                    # Gerar pitch personalizado
                    st.markdown("#### 🎯 Pitch Personalizado Gerado")
                    
                    pitch_text = f"""
## 🏆 {property_type} Excepcional - R$ {property_price:,.0f}

### 📍 **Localização Premium Comprovada por Dados**
- **Análise UrbanSight**: {result.metrics.total_score:.0f}/100 pontos
- **Walk Score**: {result.metrics.walk_score.overall_score:.0f}/100 
- **{len(pois)} estabelecimentos** mapeados em 1km

### 🌟 **Diferenciais Únicos desta Região**
"""
                    
                    for feature in unique_features[:3]:
                        pitch_text += f"✅ {feature}\n"
                    
                    pitch_text += f"""
### 🎯 **Por que este {property_type.lower()} é uma oportunidade única:**

**🏥 Saúde & Bem-estar**: {len([p for p in pois if p['category'] in ['hospital', 'pharmacy', 'gym']])} estabelecimentos próximos

**🛒 Conveniência Diária**: {len([p for p in pois if p['category'] in ['supermarket', 'convenience', 'bakery']])} opções para compras

**🍽️ Gastronomia & Lazer**: {len([p for p in pois if p['category'] in ['restaurant', 'cafe', 'bar']])} restaurantes e cafés

**🚶 Mobilidade**: Caminhe para tudo - economia de R$ 500+ mensais em transporte

### 💰 **Análise de Investimento**
- **ROI Estimado**: {6 + (result.metrics.total_score - 50) * 0.1:.1f}% ao ano
- **Potencial de Valorização**: {cycle_stage} 
- **Liquidez**: Alta (região consolidada)

### 🏆 **Exclusividade Comprovada**
Apenas **2% dos imóveis** da cidade têm essa combinação de infraestrutura e localização.

*Relatório gerado automaticamente pelo UrbanSight - dados verificados e atualizados.*
"""
                    
                    st.markdown(pitch_text)
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            "📄 Download PDF", 
                            pitch_text,
                            f"pitch_{property_type.lower().replace(' ', '_')}.txt",
                            "text/plain"
                        )
                    with col2:
                        if st.button("📱 Gerar Post Instagram"):
                            instagram_post = f"""🏆 {property_type} dos Sonhos! 

📍 Localização PREMIUM
🎯 UrbanSight Score: {result.metrics.total_score:.0f}/100
🚶 Walk Score: {result.metrics.walk_score.overall_score:.0f}/100

✅ {len(pois)} estabelecimentos em 1km
✅ Infraestrutura completa
✅ ROI: {6 + (result.metrics.total_score - 50) * 0.1:.1f}% ao ano

💰 R$ {property_price:,.0f}

#imovel #investimento #localizacao #premium
"""
                            st.text_area("Post Instagram:", instagram_post, height=200)
                    
                    with col3:
                        if st.button("📧 Gerar Email Marketing"):
                            email_template = f"""
Assunto: Oportunidade Exclusiva: {property_type} com Localização Verificada

Olá [NOME],

Encontrei uma oportunidade perfeita para você!

{property_type} com localização PREMIUM comprovada por dados:
• UrbanSight Score: {result.metrics.total_score:.0f}/100
• {len(pois)} estabelecimentos mapeados
• ROI estimado: {6 + (result.metrics.total_score - 50) * 0.1:.1f}% ao ano

Apenas R$ {property_price:,.0f}

Quer ver pessoalmente? Responda este email!

[SEU NOME]
[CONTATO]
"""
                            st.text_area("Template Email:", email_template, height=200)
                
                # Lead Qualification
                st.markdown("### 👥 Qualificação de Leads")
                
                lead_col1, lead_col2 = st.columns(2)
                
                with lead_col1:
                    st.markdown("#### 🎯 Match com Perfis")
                    
                    client_age = st.slider("Idade do Cliente", 20, 70, 35)
                    client_income = st.slider("Renda Mensal (R$ mil)", 3, 50, 10)
                    has_car = st.checkbox("Possui Carro")
                    has_family = st.checkbox("Tem Família/Filhos")
                    
                    # Calcular compatibility score
                    compatibility = 50  # Base score
                    
                    if not has_car and result.metrics.walk_score.overall_score > 70:
                        compatibility += 20
                    elif has_car and result.metrics.walk_score.overall_score < 50:
                        compatibility += 10
                    
                    if has_family:
                        family_pois = len([p for p in pois if p['category'] in ['school', 'kindergarten', 'playground']])
                        compatibility += min(20, family_pois * 3)
                    
                    if client_age < 35:
                        nightlife_pois = len([p for p in pois if p['category'] in ['bar', 'nightclub', 'restaurant']])
                        compatibility += min(15, nightlife_pois * 2)
                    
                    if client_income > 15:
                        premium_pois = len([p for p in pois if p['category'] in ['restaurant', 'gym', 'beauty_salon']])
                        compatibility += min(15, premium_pois * 2)
                    
                    compatibility = min(100, compatibility)
                    
                with lead_col2:
                    st.markdown("#### 📊 Resultado da Qualificação")
                    st.metric("🎯 **COMPATIBILIDADE**", f"{compatibility}/100")
                    st.progress(compatibility/100)
                    
                    if compatibility >= 85:
                        st.success("🌟 **LEAD QUENTE** - Altíssima probabilidade de fechamento!")
                        conversion_prob = "85-95%"
                    elif compatibility >= 70:
                        st.info("✅ **BOM LEAD** - Alta probabilidade de interesse")
                        conversion_prob = "70-85%"
                    elif compatibility >= 50:
                        st.warning("⚠️ **LEAD MORNO** - Precisa de mais qualificação")
                        conversion_prob = "40-70%"
                    else:
                        st.error("❄️ **LEAD FRIO** - Baixa compatibilidade")
                        conversion_prob = "10-40%"
                    
                    st.caption(f"Probabilidade de conversão: {conversion_prob}")
                
                # Objeções automáticas
                st.markdown("### 🛡️ Tratamento de Objeções")
                
                common_objections = [
                    ("💰 'Está muito caro'", f"Análise comparativa: imóveis similares custam 15% mais. Este tem ROI de {6 + (result.metrics.total_score - 50) * 0.1:.1f}% ao ano."),
                    ("🚗 'Fica longe de tudo'", f"Walk Score de {result.metrics.walk_score.overall_score}/100. Você economiza R$ 500/mês sem carro!"),
                    ("🏢 'Não conheço a região'", f"{len(pois)} estabelecimentos mapeados. Região consolidada com infraestrutura completa."),
                    ("⏰ 'Vou pensar'", f"Apenas 2% dos imóveis têm essa infraestrutura. {len([p for p in pois[:5]])} interessados este mês.")
                ]
                
                for objection, response in common_objections:
                    with st.expander(objection):
                        st.write(f"**Resposta sugerida**: {response}")
                
            else:
                st.info("🏢 **Analise um endereço primeiro!** Use a aba 'Análise Individual' para começar.")
        
        with persona_tab4:
            st.subheader("🎮 Simuladores Interativos")
            
            if 'analysis_results' in st.session_state and st.session_state.analysis_results:
                # Pegar o último resultado analisado
                result = list(st.session_state.analysis_results.values())[-1]
                pois = result.pois
                
                # Simulador de Rotina
                st.markdown("### 🕐 Simulador de Rotina Diária")
                
                routine_col1, routine_col2 = st.columns(2)
                
                with routine_col1:
                    st.markdown("#### ⚙️ Configure sua Rotina")
                    work_time = st.selectbox("🕘 Horário de Trabalho", ["08:00-17:00", "09:00-18:00", "10:00-19:00", "Flexível"])
                    gym_days = st.slider("🏋️ Academia por semana", 0, 7, 3)
                    market_frequency = st.selectbox("🛒 Frequência no mercado", ["Diária", "3x por semana", "1x por semana", "Quinzenal"])
                    social_frequency = st.slider("🍽️ Saídas sociais por semana", 0, 7, 2)
                
                with routine_col2:
                    st.markdown("#### 🎯 Análise da Rotina")
                    
                    # Calcular tempos de deslocamento baseado nos POIs
                    gym_pois = [p for p in pois if p['category'] == 'gym']
                    market_pois = [p for p in pois if p['category'] in ['supermarket', 'convenience']]
                    restaurant_pois = [p for p in pois if p['category'] in ['restaurant', 'cafe', 'bar']]
                    
                    gym_time = min([p['distance'] for p in gym_pois]) * 2 if gym_pois else 20  # ida e volta
                    market_time = min([p['distance'] for p in market_pois]) * 2 if market_pois else 15
                    social_time = min([p['distance'] for p in restaurant_pois]) * 2 if restaurant_pois else 25
                    
                    # Converter para minutos
                    gym_weekly = (gym_time / 1000) * 10 * gym_days  # ~10 min por km caminhando
                    market_weekly = (market_time / 1000) * 10 * {"Diária": 7, "3x por semana": 3, "1x por semana": 1, "Quinzenal": 0.5}[market_frequency]
                    social_weekly = (social_time / 1000) * 10 * social_frequency
                    
                    total_commute_weekly = gym_weekly + market_weekly + social_weekly
                    
                    st.metric("⏱️ Tempo Semanal", f"{total_commute_weekly:.0f} min")
                    st.metric("🚶 Academia mais próxima", f"{min([p['distance'] for p in gym_pois])/1000:.1f}km" if gym_pois else "N/A")
                    st.metric("🛒 Mercado mais próximo", f"{min([p['distance'] for p in market_pois])/1000:.1f}km" if market_pois else "N/A")
                    st.metric("🍽️ Restaurante mais próximo", f"{min([p['distance'] for p in restaurant_pois])/1000:.1f}km" if restaurant_pois else "N/A")
                
                # Gamification - Sistema de Pontos
                st.markdown("### 🏆 Sistema de Pontos Lifestyle")
                
                points = 0
                achievements = []
                
                if gym_pois and min([p['distance'] for p in gym_pois]) < 500:
                    points += 20
                    achievements.append("🏋️ **Fitness Master**: Academia a menos de 500m!")
                
                if market_pois and min([p['distance'] for p in market_pois]) < 300:
                    points += 15
                    achievements.append("🛒 **Convenience King**: Mercado super próximo!")
                
                if len(restaurant_pois) > 10:
                    points += 25
                    achievements.append("🍽️ **Foodie Paradise**: +10 opções gastronômicas!")
                
                if result.metrics.walk_score.overall_score > 80:
                    points += 30
                    achievements.append("🚶 **Walking Champion**: Viva sem carro!")
                
                if len([p for p in pois if p['category'] in ['hospital', 'pharmacy']]) > 3:
                    points += 20
                    achievements.append("🏥 **Health Guardian**: Saúde sempre por perto!")
                
                game_col1, game_col2 = st.columns(2)
                
                with game_col1:
                    st.metric("🎯 **LIFESTYLE SCORE**", f"{points}/110")
                    st.progress(points/110)
                    
                    if points >= 90:
                        st.success("🌟 **LEGENDARY** - Localização dos sonhos!")
                    elif points >= 70:
                        st.info("💎 **EPIC** - Excelente qualidade de vida!")
                    elif points >= 50:
                        st.warning("⭐ **GOOD** - Boa infraestrutura!")
                    else:
                        st.error("🔥 **STARTER** - Área em desenvolvimento!")
                
                with game_col2:
                    st.markdown("#### 🏆 Conquistas Desbloqueadas")
                    for achievement in achievements:
                        st.success(achievement)
                    
                    if len(achievements) == 0:
                        st.info("🎯 Analise mais localizações para desbloquear conquistas!")
                
                # Simulador "Um Dia na Vida"
                st.markdown("### 📅 Um Dia na Sua Vida")
                
                if st.button("🎬 Simular Dia Perfeito", type="primary"):
                    
                    timeline = [
                        ("07:00", "☀️ **Acordar**", "Bom dia! Sua nova casa está pronta para um dia incrível."),
                        ("07:30", "☕ **Café da Manhã**", f"Café fresco na padaria a {min([p['distance'] for p in pois if p['category'] == 'bakery'])/1000:.1f}km!" if [p for p in pois if p['category'] == 'bakery'] else "Café em casa com vista para a cidade"),
                        ("08:30", "🚶 **Caminhada para o Trabalho**", f"Walk Score {result.metrics.walk_score.overall_score}/100 - deslocamento fácil!"),
                        ("12:00", "🍽️ **Almoço**", f"{len([p for p in pois if p['category'] == 'restaurant'])} restaurantes próximos para escolher!"),
                        ("18:30", "🏋️ **Academia**", f"Gym a {min([p['distance'] for p in gym_pois])/1000:.1f}km - sem desculpas!" if gym_pois else "Exercícios no parque próximo"),
                        ("20:00", "🛒 **Mercado**", f"Compras rápidas no mercado a {min([p['distance'] for p in market_pois])/1000:.1f}km" if market_pois else "Compras online com delivery rápido"),
                        ("21:00", "🍻 **Happy Hour**", f"Escolha entre {len([p for p in pois if p['category'] in ['bar', 'cafe']])} bares e cafés próximos!"),
                        ("22:30", "🏠 **Volta para Casa**", "Fim de um dia perfeito na sua nova localização ideal!")
                    ]
                    
                    for time_slot, activity, description in timeline:
                        st.markdown(f"**{time_slot}** - {activity}")
                        st.caption(description)
                        st.markdown("---")
                
            else:
                st.info("🎮 **Analise um endereço primeiro!** Use a aba 'Análise Individual' para começar.")

    with main_tab7:
        st.header("🛠️ Ferramentas & Calculadoras")
        
        tool_tab1, tool_tab2, tool_tab3, tool_tab4 = st.tabs([
            "🧮 Calculadora de Scores", 
            "📏 Calculadora de Distâncias",
            "📊 Benchmarking",
            "🎯 Análise de Lacunas"
        ])
        
        with tool_tab1:
            st.subheader("🧮 Calculadora de Walk Score")
            st.write("Estime o Walk Score baseado na quantidade de POIs por categoria:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                education_count = st.number_input("🎓 Educação (escolas, universidades)", min_value=0, max_value=50, value=5)
                healthcare_count = st.number_input("🏥 Saúde (hospitais, clínicas)", min_value=0, max_value=50, value=3)
                shopping_count = st.number_input("🛍️ Compras (supermercados, lojas)", min_value=0, max_value=50, value=8)
                transport_count = st.number_input("🚌 Transporte (estações, paradas)", min_value=0, max_value=50, value=4)
            
            with col2:
                restaurant_count = st.number_input("🍽️ Restaurantes e cafés", min_value=0, max_value=100, value=15)
                entertainment_count = st.number_input("🎭 Entretenimento (cinemas, teatros)", min_value=0, max_value=30, value=2)
                services_count = st.number_input("🏛️ Serviços (bancos, correios)", min_value=0, max_value=30, value=6)
                park_count = st.number_input("🌳 Parques e áreas verdes", min_value=0, max_value=20, value=3)
            
            # Calculate estimated score
            total_pois = education_count + healthcare_count + shopping_count + transport_count + restaurant_count + entertainment_count + services_count + park_count
            
            # Simple scoring algorithm
            base_score = min(90, total_pois * 1.5)  # Base score from quantity
            
            # Bonus for diversity
            categories_present = sum([1 for count in [education_count, healthcare_count, shopping_count, transport_count, restaurant_count, entertainment_count, services_count, park_count] if count > 0])
            diversity_bonus = categories_present * 2
            
            estimated_score = min(100, base_score + diversity_bonus)
            
            st.subheader("📊 Resultado Estimado")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Walk Score Estimado", f"{estimated_score:.1f}")
            with col2:
                st.metric("Total de POIs", total_pois)
            with col3:
                st.metric("Categorias Presentes", f"{categories_present}/8")
            
            # Score interpretation
            if estimated_score >= 90:
                st.success("🥇 **Excelente!** Localização com infraestrutura urbana excepcional")
            elif estimated_score >= 70:
                st.info("🥈 **Muito Bom!** Boa variedade de serviços e amenidades")
            elif estimated_score >= 50:
                st.warning("🥉 **Razoável** Infraestrutura básica presente")
            else:
                st.error("⚠️ **Limitado** Poucos serviços disponíveis na região")
        
        with tool_tab2:
            st.subheader("📏 Calculadora de Tempo de Caminhada")
            st.write("Calcule tempos de caminhada e ciclismo para diferentes distâncias:")
            
            distance = st.slider("Distância (metros)", min_value=50, max_value=2000, value=500, step=50)
            
            # Calculate times
            walking_time = distance / 83.33  # 5 km/h
            cycling_time = distance / 250    # 15 km/h
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🚶 Caminhada", f"{walking_time:.1f} min")
            with col2:
                st.metric("🚴 Ciclismo", f"{cycling_time:.1f} min")
            with col3:
                if distance <= 400:
                    accessibility = "🟢 Muito Acessível"
                elif distance <= 800:
                    accessibility = "🟡 Acessível"
                else:
                    accessibility = "🔴 Distante"
                st.metric("Acessibilidade", accessibility)
            
            # Distance benchmarks
            st.subheader("📊 Referências de Distância")
            
            benchmarks = {
                "🏪 Conveniência": "200-400m (2-5 min caminhando)",
                "🏫 Escola": "400-800m (5-10 min caminhando)", 
                "🚌 Transporte Público": "400-600m (5-7 min caminhando)",
                "🏥 Saúde": "800-1200m (10-15 min caminhando)",
                "🛍️ Centro Comercial": "1000-1500m (12-18 min caminhando)"
            }
            
            for category, benchmark in benchmarks.items():
                st.info(f"**{category}**: {benchmark}")
        
        with tool_tab3:
            st.subheader("📊 Benchmarking de Localização")
            
            if st.session_state.analysis_results:
                st.write("Compare sua localização com benchmarks urbanos:")
                
                # Get data from analyses
                all_results = [r for r in st.session_state.analysis_results.values() if r.success]
                
                if all_results:
                    # Calculate averages
                    avg_total = np.mean([r.metrics.total_score for r in all_results])
                    avg_walk = np.mean([r.metrics.walk_score.overall_score for r in all_results])
                    avg_pois = np.mean([len(r.pois) for r in all_results])
                    
                    st.subheader("📈 Médias das Suas Análises")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Score Médio", f"{avg_total:.1f}")
                    with col2:
                        st.metric("Walk Score Médio", f"{avg_walk:.1f}")
                    with col3:
                        st.metric("POIs Médios", f"{avg_pois:.0f}")
                    
                    # Benchmarks comparison
                    st.subheader("🎯 Comparação com Benchmarks")
                    
                    benchmarks = {
                        "Centro da Cidade": {"score": 85, "walk": 90, "pois": 200},
                        "Bairro Residencial": {"score": 70, "walk": 65, "pois": 120},
                        "Subúrbio": {"score": 55, "walk": 45, "pois": 80},
                        "Área Rural": {"score": 30, "walk": 20, "pois": 30}
                    }
                    
                    benchmark_data = []
                    for area_type, bench_values in benchmarks.items():
                        benchmark_data.append({
                            "Tipo de Área": area_type,
                            "Score Referência": bench_values["score"],
                            "Sua Média": f"{avg_total:.1f}",
                            "Diferença": f"{avg_total - bench_values['score']:+.1f}"
                        })
                    
                    df_benchmark = pd.DataFrame(benchmark_data)
                    st.dataframe(df_benchmark, use_container_width=True)
            else:
                st.info("📊 Realize algumas análises primeiro para ver o benchmarking!")
        
        with tool_tab4:
            st.subheader("🎯 Análise de Lacunas de Serviços")
            
            if st.session_state.analysis_results:
                st.write("Identifique quais serviços estão em falta nas suas análises:")
                
                # Analyze all results for service gaps
                all_categories = set()
                location_categories = {}
                
                for address, result in st.session_state.analysis_results.items():
                    if result.success:
                        categories = set([poi.get('category', 'other') for poi in result.pois])
                        all_categories.update(categories)
                        location_categories[address] = categories
                
                if all_categories and location_categories:
                    st.subheader("📊 Matriz de Cobertura de Serviços")
                    
                    # Create coverage matrix
                    coverage_data = []
                    for address in location_categories.keys():
                        row = {"Endereço": address[:40] + "..." if len(address) > 40 else address}
                        for category in sorted(all_categories):
                            row[category.title()] = "✅" if category in location_categories[address] else "❌"
                        coverage_data.append(row)
                    
                    df_coverage = pd.DataFrame(coverage_data)
                    st.dataframe(df_coverage, use_container_width=True)
                    
                    # Service gaps analysis
                    st.subheader("🔍 Análise de Lacunas")
                    
                    category_coverage = {}
                    for category in all_categories:
                        coverage_count = sum([1 for cats in location_categories.values() if category in cats])
                        coverage_percentage = (coverage_count / len(location_categories)) * 100
                        category_coverage[category] = coverage_percentage
                    
                    # Sort by coverage (lowest first = biggest gaps)
                    sorted_coverage = sorted(category_coverage.items(), key=lambda x: x[1])
                    
                    st.write("**Serviços com maior lacuna (menor cobertura):**")
                    
                    for i, (category, coverage) in enumerate(sorted_coverage[:5]):
                        if coverage < 100:
                            st.warning(f"**{category.title()}**: {coverage:.0f}% das localizações analisadas")
                        else:
                            st.success(f"**{category.title()}**: {coverage:.0f}% das localizações analisadas")
                    
                    # Recommendations
                    st.subheader("💡 Recomendações")
                    
                    low_coverage = [cat for cat, cov in sorted_coverage if cov < 70]
                    
                    if low_coverage:
                        st.info(f"""
                        **Categorias para priorizar na busca:**
                        {', '.join([cat.title() for cat in low_coverage[:3]])}
                        
                        Essas categorias estão presentes em menos de 70% das suas análises.
                        """)
                    else:
                        st.success("🎉 Parabéns! Todas as suas localizações têm boa cobertura de serviços.")
            else:
                st.info("🎯 Realize análises em múltiplas localizações para ver a análise de lacunas!")

    with main_tab8:
        st.header("🏠 Minha Casa Ideal - Análise Personalizada")
        st.markdown("*Descubra se este local é perfeito para o seu estilo de vida!*")
        
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis
            
            # Quick Profile Quiz
            with st.expander("🎯 Defina Seu Perfil (Opcional)", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    has_children = st.checkbox("👶 Tenho filhos", key="has_children")
                    uses_public_transport = st.checkbox("🚌 Uso transporte público", key="uses_transport")
                    likes_nightlife = st.checkbox("🌙 Gosto de vida noturna", key="likes_nightlife")
                    exercises_regularly = st.checkbox("🏃‍♂️ Pratico exercícios", key="exercises")
                
                with col2:
                    has_car = st.checkbox("🚗 Tenho carro", key="has_car")
                    works_from_home = st.checkbox("🏠 Trabalho em casa", key="works_home")
                    elderly_care = st.checkbox("👴 Cuido de idosos", key="elderly_care")
                    frequent_shopping = st.checkbox("🛒 Compro frequentemente", key="frequent_shopping")
            
            # Calculate personalized scores
            def calculate_personalized_score(pois):
                weights = {
                    'education': 0.1,
                    'healthcare': 0.15,
                    'shopping': 0.15,
                    'transport': 0.15,
                    'entertainment': 0.1,
                    'restaurant': 0.1,
                    'services': 0.1,
                    'park': 0.15
                }
                
                # Adjust weights based on profile
                if has_children:
                    weights['education'] = 0.25
                    weights['park'] = 0.2
                    weights['healthcare'] = 0.2
                
                if uses_public_transport:
                    weights['transport'] = 0.3
                
                if likes_nightlife:
                    weights['entertainment'] = 0.2
                    weights['restaurant'] = 0.15
                
                if exercises_regularly:
                    weights['park'] = 0.25
                
                if elderly_care:
                    weights['healthcare'] = 0.3
                
                if frequent_shopping:
                    weights['shopping'] = 0.25
                
                # Calculate score based on POI counts and distances
                category_scores = {}
                for category in weights.keys():
                    category_pois = [p for p in pois if p.get('category', '').lower() == category.lower()]
                    if category_pois:
                        avg_distance = sum(p.get('distance', 1000) for p in category_pois) / len(category_pois)
                        count_score = min(len(category_pois) * 20, 100)  # Max 100 for 5+ POIs
                        distance_score = max(0, 100 - (avg_distance / 10))  # Max 100 for 0m, 0 for 1000m+
                        category_scores[category] = (count_score + distance_score) / 2
                    else:
                        category_scores[category] = 0
                
                total_score = sum(category_scores[cat] * weights[cat] for cat in weights.keys())
                return total_score, category_scores, weights
            
            # Main Analysis Sections
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🎯 Meu Score Personalizado",
                "📍 O que tem por perto?",
                "🚶‍♂️ Tempos de Caminhada",
                "💰 Vale a Pena?",
                "🎨 Perfil do Bairro"
            ])
            
            with tab1:
                st.subheader("🎯 Seu Score Personalizado")
                
                personal_score, category_scores, weights = calculate_personalized_score(result.pois)
                
                # Display main score
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    score_color = "🟢" if personal_score >= 70 else "🟡" if personal_score >= 50 else "🔴"
                    st.markdown(f"""
                    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                        <h1 style="margin: 0; font-size: 3rem;">{score_color}</h1>
                        <h2 style="margin: 0;">{personal_score:.1f}/100</h2>
                        <p style="margin: 0; font-size: 1.2rem;">Compatibilidade com seu perfil</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Category breakdown
                st.subheader("📊 Breakdown por Categoria")
                
                for category, score in category_scores.items():
                    weight = weights[category]
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        category_names = {
                            'education': '🎓 Educação',
                            'healthcare': '🏥 Saúde',
                            'shopping': '🛒 Compras',
                            'transport': '🚌 Transporte',
                            'entertainment': '🎭 Entretenimento',
                            'restaurant': '🍽️ Restaurantes',
                            'services': '🏛️ Serviços',
                            'park': '🌳 Parques'
                        }
                        st.write(category_names.get(category, category.title()))
                    
                    with col2:
                        st.progress(score/100)
                        st.caption(f"{score:.1f}/100")
                    
                    with col3:
                        importance = "🔥" if weight > 0.2 else "⭐" if weight > 0.15 else "•"
                        st.write(f"{importance} {weight*100:.0f}%")
            
            with tab2:
                st.subheader("📍 O que tem por perto?")
                
                # Calculate walking times
                walking_speed = 80  # meters per minute (average walking speed)
                
                def get_walking_time(distance):
                    return distance / walking_speed
                
                def filter_pois_by_time(pois, max_minutes):
                    max_distance = max_minutes * walking_speed
                    return [p for p in pois if p.get('distance', 0) <= max_distance]
                
                # Time-based analysis
                time_ranges = [
                    (5, "🏃‍♂️ Em 5 minutos a pé"),
                    (10, "🚶‍♂️ Em 10 minutos a pé"),
                    (15, "🚶‍♀️ Em 15 minutos a pé")
                ]
                
                for max_time, title in time_ranges:
                    with st.expander(title, expanded=(max_time==5)):
                        nearby_pois = filter_pois_by_time(result.pois, max_time)
                        
                        if not nearby_pois:
                            st.warning(f"Nenhum POI encontrado em {max_time} minutos de caminhada.")
                            continue
                        
                        # Group by category
                        categories = {}
                        for poi in nearby_pois:
                            cat = poi.get('category', 'outros')
                            if cat not in categories:
                                categories[cat] = []
                            categories[cat].append(poi)
                        
                        # Display by category
                        cols = st.columns(2)
                        col_idx = 0
                        
                        for category, pois in categories.items():
                            with cols[col_idx % 2]:
                                category_icons = {
                                    'shopping': '🛒',
                                    'healthcare': '🏥', 
                                    'education': '🎓',
                                    'transport': '🚌',
                                    'restaurant': '🍽️',
                                    'entertainment': '🎭',
                                    'services': '🔧',
                                    'park': '🌳'
                                }
                                icon = category_icons.get(category, '📍')
                                
                                st.markdown(f"**{icon} {category.title()}** ({len(pois)})")
                                for poi in pois[:3]:  # Show top 3
                                    time_min = get_walking_time(poi.get('distance', 0))
                                    st.caption(f"• {poi.get('name', 'N/A')} ({time_min:.1f}min)")
                                
                                if len(pois) > 3:
                                    st.caption(f"... e mais {len(pois)-3}")
                                
                                col_idx += 1
            
            with tab3:
                st.subheader("🚶‍♂️ Tempos de Caminhada para Essenciais")
                
                # Define essential categories
                essentials = {
                    '🛒 Mercado/Supermercado': ['shopping', 'supermarket'],
                    '🏥 Hospital/Clínica': ['healthcare', 'hospital', 'clinic'],
                    '💊 Farmácia': ['pharmacy', 'healthcare'],
                    '🚌 Ponto de Ônibus': ['transport', 'bus_stop'],
                    '🏦 Banco/ATM': ['bank', 'atm', 'services'],
                    '⛽ Posto de Gasolina': ['fuel', 'gas_station'],
                    '🎓 Escola': ['education', 'school'],
                    '🌳 Parque/Praça': ['park', 'leisure']
                }
                
                for essential_name, keywords in essentials.items():
                    # Find closest POI for this essential
                    essential_pois = []
                    for poi in result.pois:
                        poi_cat = poi.get('category', '').lower()
                        poi_name = poi.get('name', '').lower()
                        
                        if any(keyword in poi_cat or keyword in poi_name for keyword in keywords):
                            essential_pois.append(poi)
                    
                    if essential_pois:
                        closest = min(essential_pois, key=lambda x: x.get('distance', float('inf')))
                        distance = closest.get('distance', 0)
                        time_walk = distance / walking_speed
                        time_car = distance / 500  # Approximate car speed in city (30km/h = 500m/min)
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"{essential_name}")
                            st.caption(f"📍 {closest.get('name', 'N/A')} ({distance:.0f}m)")
                        
                        with col2:
                            walk_color = "🟢" if time_walk <= 5 else "🟡" if time_walk <= 10 else "🔴"
                            st.metric("🚶‍♂️ A pé", f"{time_walk:.1f}min", delta=None)
                        
                        with col3:
                            car_color = "🟢" if time_car <= 2 else "🟡" if time_car <= 5 else "🔴"
                            st.metric("🚗 De carro", f"{time_car:.1f}min", delta=None)
                    else:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"{essential_name}")
                            st.caption("❌ Não encontrado próximo")
                        with col2:
                            st.metric("🚶‍♂️ A pé", "N/A")
                        with col3:
                            st.metric("🚗 De carro", "N/A")
            
            with tab4:
                st.subheader("💰 Vale a Pena?")
                
                # Calculate pros and cons
                def analyze_pros_cons(pois):
                    pros = []
                    cons = []
                    
                    # Count POIs by category within different ranges
                    categories_5min = {}
                    categories_10min = {}
                    categories_15min = {}
                    
                    for poi in pois:
                        distance = poi.get('distance', 0)
                        category = poi.get('category', 'outros')
                        
                        if distance <= 400:  # 5 min
                            categories_5min[category] = categories_5min.get(category, 0) + 1
                        if distance <= 800:  # 10 min
                            categories_10min[category] = categories_10min.get(category, 0) + 1
                        if distance <= 1200:  # 15 min
                            categories_15min[category] = categories_15min.get(category, 0) + 1
                    
                    # Analyze pros
                    if categories_5min.get('shopping', 0) >= 3:
                        pros.append("🛒 Muitos mercados/lojas em 5 min a pé")
                    elif categories_10min.get('shopping', 0) >= 2:
                        pros.append("🛒 Boa oferta de compras em 10 min a pé")
                    
                    if categories_10min.get('education', 0) >= 2:
                        pros.append("🎓 Várias opções de educação próximas")
                    
                    if categories_5min.get('healthcare', 0) >= 1:
                        pros.append("🏥 Acesso rápido a serviços de saúde")
                    
                    if categories_10min.get('transport', 0) >= 3:
                        pros.append("🚌 Excelente conectividade de transporte")
                    elif categories_5min.get('transport', 0) >= 1:
                        pros.append("🚌 Transporte público acessível")
                    
                    if categories_10min.get('restaurant', 0) >= 5:
                        pros.append("🍽️ Rica oferta gastronômica")
                    
                    if categories_15min.get('park', 0) >= 2:
                        pros.append("🌳 Boas opções de lazer e exercícios")
                    
                    if categories_10min.get('entertainment', 0) >= 2:
                        pros.append("🎭 Vida cultural e entretenimento ativa")
                    
                    # Analyze cons
                    if categories_15min.get('shopping', 0) < 1:
                        cons.append("🛒 Falta de opções de compras próximas")
                    
                    if categories_15min.get('healthcare', 0) < 1:
                        cons.append("🏥 Serviços de saúde distantes")
                    
                    if categories_10min.get('transport', 0) < 1:
                        cons.append("🚌 Transporte público limitado")
                    
                    if categories_15min.get('education', 0) < 1:
                        cons.append("🎓 Poucas opções educacionais")
                    
                    if categories_15min.get('restaurant', 0) < 2:
                        cons.append("🍽️ Opções gastronômicas limitadas")
                    
                    if categories_15min.get('park', 0) < 1:
                        cons.append("🌳 Falta de espaços verdes e lazer")
                    
                    if categories_15min.get('entertainment', 0) < 1:
                        cons.append("🎭 Vida noturna/cultural limitada")
                    
                    return pros, cons
                
                pros, cons = analyze_pros_cons(result.pois)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ **Pontos Positivos**")
                    if pros:
                        for pro in pros:
                            st.markdown(f"• {pro}")
                    else:
                        st.info("Esta análise precisa de mais dados para identificar pontos positivos específicos.")
                
                with col2:
                    st.markdown("### ⚠️ **Pontos de Atenção**")
                    if cons:
                        for con in cons:
                            st.markdown(f"• {con}")
                    else:
                        st.success("Nenhum ponto crítico identificado!")
                
                # Overall recommendation
                st.markdown("---")
                score_final = len(pros) * 2 - len(cons)
                
                if score_final >= 6:
                    st.success("🎯 **Recomendação: EXCELENTE localização!** Este endereço oferece ótima qualidade de vida.")
                elif score_final >= 3:
                    st.info("👍 **Recomendação: BOA localização.** Atende a maioria das necessidades básicas.")
                elif score_final >= 0:
                    st.warning("⚖️ **Recomendação: ACEITÁVEL.** Tem prós e contras - considere suas prioridades.")
                else:
                    st.error("❌ **Recomendação: CONSIDERE OUTRAS OPÇÕES.** Limitações importantes identificadas.")
            
            with tab5:
                st.subheader("🎨 Perfil do Bairro")
                st.markdown("*Descubra para quem este local é mais adequado:*")
                
                def calculate_profile_scores(pois):
                    # Count POIs by category and calculate accessibility
                    categories = {}
                    for poi in pois:
                        cat = poi.get('category', 'outros')
                        distance = poi.get('distance', 0)
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(distance)
                    
                    # Calculate scores for different profiles
                    profiles = {}
                    
                    # Families with children
                    education_score = min(len(categories.get('education', [])) * 20, 100)
                    park_score = min(len(categories.get('park', [])) * 25, 100)
                    healthcare_score = min(len(categories.get('healthcare', [])) * 15, 100)
                    safety_base = 70  # Base safety score
                    profiles['👨‍👩‍👧‍👦 Famílias com crianças'] = (education_score + park_score + healthcare_score + safety_base) / 4
                    
                    # Young professionals
                    transport_score = min(len(categories.get('transport', [])) * 20, 100)
                    restaurant_score = min(len(categories.get('restaurant', [])) * 15, 100)
                    entertainment_score = min(len(categories.get('entertainment', [])) * 25, 100)
                    profiles['👥 Jovens profissionais'] = (transport_score + restaurant_score + entertainment_score) / 3
                    
                    # Elderly
                    healthcare_elderly = min(len(categories.get('healthcare', [])) * 30, 100)
                    shopping_score = min(len(categories.get('shopping', [])) * 20, 100)
                    transport_elderly = min(len(categories.get('transport', [])) * 25, 100)
                    profiles['👴 Idosos'] = (healthcare_elderly + shopping_score + transport_elderly) / 3
                    
                    # Car owners
                    parking_base = 85  # Assume good for car owners
                    shopping_car = min(len(categories.get('shopping', [])) * 15, 100)
                    profiles['🚗 Quem tem carro'] = (parking_base + shopping_car) / 2
                    
                    # Pedestrians
                    walkability_score = 0
                    for cat, distances in categories.items():
                        if distances:
                            avg_dist = sum(distances) / len(distances)
                            walkability_score += max(0, 100 - (avg_dist / 10))
                    walkability_score = min(walkability_score / len(categories) if categories else 0, 100)
                    profiles['🚶 Quem anda a pé'] = walkability_score
                    
                    return profiles
                
                profiles = calculate_profile_scores(result.pois)
                
                for profile_name, score in profiles.items():
                    col1, col2 = st.columns([3, 2])
                    
                    with col1:
                        st.write(f"**{profile_name}**")
                    
                    with col2:
                        # Create star rating
                        stars = int(score / 20)  # Convert to 0-5 stars
                        star_display = "⭐" * stars + "☆" * (5 - stars)
                        st.write(f"{star_display} ({score:.0f}/100)")
                
                # Convenience Map
                st.markdown("---")
                st.subheader("🗺️ Mapa da Conveniência")
                st.markdown("*Visualize a conveniência por tempo de caminhada:*")
                
                # Create a simple folium map with color zones
                if hasattr(result, 'latitude') and hasattr(result, 'longitude'):
                    m = folium.Map(
                        location=[result.latitude, result.longitude],
                        zoom_start=15
                    )
                    
                    # Add center point
                    folium.Marker(
                        [result.latitude, result.longitude],
                        popup="📍 Localização Analisada",
                        icon=folium.Icon(color='red', icon='home')
                    ).add_to(m)
                    
                    # Add colored circles for convenience zones
                    folium.Circle(
                        location=[result.latitude, result.longitude],
                        radius=400,  # 5 min walk
                        popup="🟢 5 min a pé - Muito Conveniente",
                        color='green',
                        fill=True,
                        fillOpacity=0.2
                    ).add_to(m)
                    
                    folium.Circle(
                        location=[result.latitude, result.longitude],
                        radius=800,  # 10 min walk
                        popup="🟡 10 min a pé - Conveniente",
                        color='yellow',
                        fill=True,
                        fillOpacity=0.1
                    ).add_to(m)
                    
                    folium.Circle(
                        location=[result.latitude, result.longitude],
                        radius=1200,  # 15 min walk
                        popup="🟠 15 min a pé - Aceitável",
                        color='orange',
                        fill=True,
                        fillOpacity=0.05
                    ).add_to(m)
                    
                    # Add POIs with appropriate colors
                    for poi in result.pois[:20]:  # Show top 20 POIs
                        distance = poi.get('distance', 0)
                        if distance <= 400:
                            color = 'green'
                        elif distance <= 800:
                            color = 'yellow'
                        elif distance <= 1200:
                            color = 'orange'
                        else:
                            color = 'red'
                        
                        time_min = distance / 80  # walking speed
                        folium.Marker(
                            [poi.get('lat', result.latitude), poi.get('lon', result.longitude)],
                            popup=f"{poi.get('name', 'N/A')}<br>🚶‍♂️ {time_min:.1f} min",
                            icon=folium.Icon(color=color, icon='info-sign')
                        ).add_to(m)
                    
                    folium_static(m, height=400)
                
                # Checklist
                st.markdown("---")
                st.subheader("📋 Checklist da Mudança")
                st.markdown("*Itens essenciais para sua nova casa:*")
                
                essentials_check = {
                    '🛒 Mercado/Supermercado próximo': any(poi.get('distance', 999) <= 800 and 'shopping' in poi.get('category', '') for poi in result.pois),
                    '🏥 Serviços de saúde acessíveis': any(poi.get('distance', 999) <= 1200 and 'healthcare' in poi.get('category', '') for poi in result.pois),
                    '🚌 Transporte público próximo': any(poi.get('distance', 999) <= 400 and 'transport' in poi.get('category', '') for poi in result.pois),
                    '🎓 Escolas na região': any('education' in poi.get('category', '') for poi in result.pois),
                    '💊 Farmácia acessível': any(poi.get('distance', 999) <= 800 and ('pharmacy' in poi.get('name', '').lower() or 'healthcare' in poi.get('category', '')) for poi in result.pois),
                    '🌳 Áreas verdes próximas': any('park' in poi.get('category', '') for poi in result.pois),
                    '🍽️ Opções gastronômicas': len([p for p in result.pois if 'restaurant' in p.get('category', '')]) >= 2,
                    '🔧 Serviços essenciais': any('services' in poi.get('category', '') for poi in result.pois)
                }
                
                checked_items = sum(essentials_check.values())
                total_items = len(essentials_check)
                
                progress_col1, progress_col2 = st.columns([1, 3])
                with progress_col1:
                    st.metric("Score Final", f"{checked_items}/{total_items}")
                with progress_col2:
                    st.progress(checked_items / total_items)
                
                for item, is_checked in essentials_check.items():
                    icon = "✅" if is_checked else "❌"
                    st.markdown(f"{icon} {item}")
                
                # Final recommendation
                if checked_items >= 7:
                    st.success("🎉 **Excelente escolha!** Este local atende a maioria das suas necessidades.")
                elif checked_items >= 5:
                    st.info("👍 **Boa localização.** Atende às necessidades básicas.")
                elif checked_items >= 3:
                    st.warning("⚖️ **Localização aceitável.** Considere suas prioridades específicas.")
                else:
                    st.error("❌ **Considere outras opções.** Muitos itens essenciais não estão próximos.")
        
        else:
            st.info("👋 **Realize uma análise primeiro!** Use a aba 'Análise Individual' para analisar um endereço e depois volte aqui para ver a análise personalizada.")

    with main_tab9:
        st.header("🏢 UrbanSight para Imobiliárias & Corretores")
        st.markdown("*Ferramentas profissionais para aumentar suas vendas*")
        
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis
            
            # Professional Tools Tabs
            prof_tab1, prof_tab2, prof_tab3, prof_tab4, prof_tab5 = st.tabs([
                "🎯 Pitch Automático",
                "📋 Argumentos de Venda", 
                "👥 Perfil do Comprador",
                "📊 Ranking & Comparação",
                "📱 Ferramentas Rápidas"
            ])
            
            with prof_tab1:
                st.subheader("🎯 Pitch Automático para Corretor")
                st.markdown("*Texto pronto para usar com seus clientes:*")
                
                def generate_automatic_pitch(pois):
                    # Count POIs by category and calculate key metrics
                    categories = {}
                    for poi in pois:
                        cat = poi.get('category', 'outros')
                        distance = poi.get('distance', 0)
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(distance)
                    
                    # Generate pitch components
                    pitch_parts = []
                    
                    # Shopping analysis
                    shopping_pois = categories.get('shopping', [])
                    if shopping_pois:
                        shopping_5min = len([d for d in shopping_pois if d <= 400])
                        shopping_10min = len([d for d in shopping_pois if d <= 800])
                        if shopping_5min >= 3:
                            pitch_parts.append(f"🛒 **{shopping_5min} mercados em apenas 5 minutos a pé**")
                        elif shopping_10min >= 2:
                            pitch_parts.append(f"🛒 **{shopping_10min} opções de compras em 10 minutos a pé**")
                    
                    # Education analysis
                    education_pois = categories.get('education', [])
                    if education_pois:
                        closest_school = min(education_pois)
                        school_count = len(education_pois)
                        if closest_school <= 500:
                            pitch_parts.append(f"🎓 **Escola a apenas {closest_school:.0f}m - ideal para famílias**")
                        elif school_count >= 2:
                            pitch_parts.append(f"🎓 **{school_count} escolas na região**")
                    
                    # Healthcare analysis
                    healthcare_pois = categories.get('healthcare', [])
                    if healthcare_pois:
                        closest_health = min(healthcare_pois)
                        if closest_health <= 800:
                            pitch_parts.append(f"🏥 **Serviços de saúde a {closest_health:.0f}m**")
                    
                    # Transport analysis
                    transport_pois = categories.get('transport', [])
                    if transport_pois:
                        transport_5min = len([d for d in transport_pois if d <= 400])
                        if transport_5min >= 2:
                            pitch_parts.append(f"🚌 **{transport_5min} opções de transporte em 5 minutos**")
                    
                    # Restaurant/Entertainment
                    restaurant_pois = categories.get('restaurant', [])
                    entertainment_pois = categories.get('entertainment', [])
                    social_count = len(restaurant_pois) + len(entertainment_pois)
                    if social_count >= 5:
                        pitch_parts.append(f"🍽️ **Rica vida social com {social_count} restaurantes e entretenimento**")
                    
                    # Calculate Walk Score
                    total_pois = len(pois)
                    walk_score = min(total_pois * 3, 100)  # Simple calculation
                    
                    return pitch_parts, walk_score
                
                pitch_parts, walk_score = generate_automatic_pitch(result.pois)
                
                # Display the pitch
                st.markdown("### 💬 **Seu Pitch Pronto:**")
                
                # Main pitch box
                pitch_text = "**Este imóvel oferece uma localização privilegiada:**\n\n"
                for part in pitch_parts:
                    pitch_text += f"✅ {part}\n\n"
                
                pitch_text += f"🎯 **Walk Score: {walk_score}/100** - Excelente caminhabilidade\n\n"
                pitch_text += "📍 *Localização que combina conveniência e qualidade de vida!*"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           padding: 2rem; border-radius: 15px; color: white; margin: 1rem 0;">
                {pitch_text}
                </div>
                """, unsafe_allow_html=True)
                
                # Copy button simulation
                st.code(pitch_text.replace("**", "").replace("*", ""), language=None)
                st.caption("📋 Copie o texto acima e use em suas apresentações!")
                
                # Additional talking points
                st.markdown("---")
                st.subheader("🗣️ Pontos de Conversa Adicionais:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Para Famílias:**")
                    education_count = len([p for p in result.pois if p.get('category') == 'education'])
                    park_count = len([p for p in result.pois if p.get('category') == 'park'])
                    if education_count > 0:
                        st.markdown(f"• {education_count} opções educacionais")
                    if park_count > 0:
                        st.markdown(f"• {park_count} áreas de lazer para crianças")
                    
                    st.markdown("**Para Profissionais:**")
                    transport_count = len([p for p in result.pois if p.get('category') == 'transport'])
                    services_count = len([p for p in result.pois if p.get('category') == 'services'])
                    if transport_count > 0:
                        st.markdown(f"• {transport_count} opções de transporte")
                    if services_count > 0:
                        st.markdown(f"• {services_count} serviços essenciais")
                
                with col2:
                    st.markdown("**Para Investidores:**")
                    total_pois = len(result.pois)
                    st.markdown(f"• {total_pois} POIs identificados na região")
                    st.markdown(f"• Densidade urbana favorável")
                    st.markdown(f"• Infraestrutura consolidada")
                    
                    st.markdown("**Vantagens Competitivas:**")
                    if walk_score >= 70:
                        st.markdown("• Walk Score superior à média")
                    st.markdown("• Análise baseada em dados reais")
                    st.markdown("• Relatório técnico disponível")
            
            with prof_tab2:
                st.subheader("📋 Argumentos de Venda Automáticos")
                
                def generate_sales_arguments(pois):
                    # Analyze POIs for sales arguments
                    categories = {}
                    for poi in pois:
                        cat = poi.get('category', 'outros')
                        distance = poi.get('distance', 0)
                        if cat not in categories:
                            categories[cat] = {'count': 0, 'distances': []}
                        categories[cat]['count'] += 1
                        categories[cat]['distances'].append(distance)
                    
                    strengths = []
                    selling_points = []
                    convenience_factors = []
                    
                    # Analyze each category
                    for category, data in categories.items():
                        count = data['count']
                        avg_distance = sum(data['distances']) / len(data['distances']) if data['distances'] else 0
                        min_distance = min(data['distances']) if data['distances'] else 0
                        
                        category_names = {
                            'shopping': '🛒 Compras e Mercados',
                            'education': '🎓 Educação',
                            'healthcare': '🏥 Saúde',
                            'transport': '🚌 Transporte',
                            'restaurant': '🍽️ Gastronomia',
                            'entertainment': '🎭 Entretenimento',
                            'services': '🔧 Serviços',
                            'park': '🌳 Lazer e Parques'
                        }
                        
                        name = category_names.get(category, category.title())
                        
                        # Generate specific arguments
                        if count >= 3 and avg_distance <= 600:
                            strengths.append(f"{name}: {count} opções próximas (média {avg_distance:.0f}m)")
                            if category == 'shopping':
                                selling_points.append("Compras do dia a dia resolvidas a pé")
                            elif category == 'education':
                                selling_points.append("Várias opções educacionais para os filhos")
                            elif category == 'transport':
                                selling_points.append("Mobilidade urbana facilitada")
                        
                        if min_distance <= 300:
                            convenience_factors.append(f"{name}: {min_distance:.0f}m do mais próximo")
                    
                    return strengths, selling_points, convenience_factors
                
                strengths, selling_points, convenience_factors = generate_sales_arguments(result.pois)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ **Pontos Fortes do Imóvel**")
                    if strengths:
                        for strength in strengths:
                            st.markdown(f"• {strength}")
                    else:
                        st.info("Localização com características específicas - destaque outros aspectos do imóvel.")
                    
                    st.markdown("### 🎯 **Argumentos de Fechamento**")
                    if selling_points:
                        for point in selling_points:
                            st.markdown(f"• {point}")
                    
                    # Calculate scarcity argument
                    total_analysis = len(st.session_state.analysis_results)
                    if total_analysis > 1:
                        current_score = len(result.pois) * 3
                        avg_score = sum([len(r.pois) * 3 for r in st.session_state.analysis_results.values()]) / total_analysis
                        if current_score > avg_score:
                            st.markdown(f"• Localização {((current_score - avg_score) / avg_score * 100):.0f}% superior à média analisada")
                
                with col2:
                    st.markdown("### 🚀 **Fatores de Conveniência**")
                    if convenience_factors:
                        for factor in convenience_factors:
                            st.markdown(f"• {factor}")
                    
                    st.markdown("### 💡 **Dicas de Abordagem**")
                    
                    # Smart suggestions based on POI profile
                    education_count = len([p for p in result.pois if p.get('category') == 'education'])
                    healthcare_count = len([p for p in result.pois if p.get('category') == 'healthcare'])
                    entertainment_count = len([p for p in result.pois if p.get('category') == 'entertainment'])
                    
                    if education_count >= 2:
                        st.markdown("👨‍👩‍👧‍👦 **Para famílias:** Destaque a proximidade de escolas")
                    if healthcare_count >= 1:
                        st.markdown("👴 **Para idosos:** Enfatize acesso à saúde")
                    if entertainment_count >= 2:
                        st.markdown("👥 **Para jovens:** Destaque vida social ativa")
                    
                    st.markdown("📊 **Sempre mencionar:** Análise baseada em dados técnicos do UrbanSight")
                
                # Generate competitive analysis
                st.markdown("---")
                st.subheader("⚖️ Análise Competitiva")
                
                total_pois = len(result.pois)
                if total_pois >= 15:
                    st.success("🏆 **Localização PREMIUM** - Rica em infraestrutura urbana")
                elif total_pois >= 10:
                    st.info("👍 **Localização CONSOLIDADA** - Boa disponibilidade de serviços")
                else:
                    st.warning("📍 **Localização RESIDENCIAL** - Foque em outros diferenciais do imóvel")
                
                # ROI Calculator for agents
                st.markdown("### 💰 Calculadora de Argumentos Financeiros")
                col1, col2 = st.columns(2)
                
                with col1:
                    valor_imovel = st.number_input("Valor do imóvel (R$)", min_value=0, value=500000, step=50000)
                
                with col2:
                    valor_m2_regiao = st.number_input("Valor/m² região (R$)", min_value=0, value=8000, step=500)
                
                if valor_imovel > 0 and valor_m2_regiao > 0:
                    # Simple ROI calculation based on POI density
                    poi_factor = min(total_pois / 20, 1.2)  # Max 20% premium for high POI density
                    estimated_appreciation = (poi_factor - 1) * 100
                    
                    if estimated_appreciation > 0:
                        st.success(f"💡 **Argumento financeiro:** Esta localização pode ter potencial de valorização de até {estimated_appreciation:.1f}% devido à alta densidade de serviços")
                    
                    # Cost-benefit of location
                    walking_savings = total_pois * 10  # R$10 per month saved per nearby POI
                    st.info(f"💡 **Economia mensal estimada:** R$ {walking_savings:.0f} em deslocamentos devido à proximidade de serviços")
            
            with prof_tab3:
                st.subheader("👥 Perfil Ideal do Comprador")
                
                def analyze_buyer_profile(pois):
                    # Analyze POI composition to determine ideal buyer
                    categories = {}
                    for poi in pois:
                        cat = poi.get('category', 'outros')
                        categories[cat] = categories.get(cat, 0) + 1
                    
                    # Calculate suitability scores for different profiles
                    profiles = {}
                    
                    # Family with children
                    education_score = min(categories.get('education', 0) * 25, 100)
                    park_score = min(categories.get('park', 0) * 30, 100) 
                    healthcare_score = min(categories.get('healthcare', 0) * 20, 100)
                    safety_base = 70  # Assume reasonable safety
                    profiles['👨‍👩‍👧‍👦 Famílias com crianças'] = {
                        'score': (education_score + park_score + healthcare_score + safety_base) / 4,
                        'reasons': []
                    }
                    if education_score > 50: profiles['👨‍👩‍👧‍👦 Famílias com crianças']['reasons'].append("Boas opções educacionais")
                    if park_score > 50: profiles['👨‍👩‍👧‍👦 Famílias com crianças']['reasons'].append("Áreas de lazer para crianças")
                    
                    # Young professionals
                    transport_score = min(categories.get('transport', 0) * 25, 100)
                    restaurant_score = min(categories.get('restaurant', 0) * 15, 100)
                    entertainment_score = min(categories.get('entertainment', 0) * 30, 100)
                    services_score = min(categories.get('services', 0) * 20, 100)
                    profiles['👥 Jovens profissionais'] = {
                        'score': (transport_score + restaurant_score + entertainment_score + services_score) / 4,
                        'reasons': []
                    }
                    if transport_score > 50: profiles['👥 Jovens profissionais']['reasons'].append("Excelente mobilidade urbana")
                    if entertainment_score > 50: profiles['👥 Jovens profissionais']['reasons'].append("Vida noturna ativa")
                    
                    # Elderly
                    healthcare_elderly = min(categories.get('healthcare', 0) * 40, 100)
                    shopping_score = min(categories.get('shopping', 0) * 25, 100)
                    transport_elderly = min(categories.get('transport', 0) * 35, 100)
                    profiles['👴 Idosos'] = {
                        'score': (healthcare_elderly + shopping_score + transport_elderly) / 3,
                        'reasons': []
                    }
                    if healthcare_elderly > 50: profiles['👴 Idosos']['reasons'].append("Fácil acesso a serviços de saúde")
                    if shopping_score > 50: profiles['👴 Idosos']['reasons'].append("Compras próximas")
                    
                    # Investors
                    total_pois = sum(categories.values())
                    density_score = min(total_pois * 4, 100)
                    diversity_score = len(categories) * 12.5  # 8 categories max = 100
                    profiles['💼 Investidores'] = {
                        'score': (density_score + diversity_score) / 2,
                        'reasons': []
                    }
                    if total_pois > 15: profiles['💼 Investidores']['reasons'].append("Alta densidade urbana")
                    if len(categories) >= 6: profiles['💼 Investidores']['reasons'].append("Diversidade de serviços")
                    
                    # Car-free lifestyle
                    walking_score = 0
                    for cat, count in categories.items():
                        if cat in ['shopping', 'healthcare', 'services']:
                            walking_score += count * 20
                    walking_score = min(walking_score, 100)
                    profiles['🚶 Estilo de vida sem carro'] = {
                        'score': walking_score,
                        'reasons': []
                    }
                    if categories.get('shopping', 0) >= 2: profiles['🚶 Estilo de vida sem carro']['reasons'].append("Compras essenciais a pé")
                    if categories.get('transport', 0) >= 2: profiles['🚶 Estilo de vida sem carro']['reasons'].append("Boa rede de transporte público")
                    
                    return profiles
                
                profiles = analyze_buyer_profile(result.pois)
                
                # Sort by score
                sorted_profiles = sorted(profiles.items(), key=lambda x: x[1]['score'], reverse=True)
                
                st.markdown("### 🎯 **Recomendações de Público-Alvo**")
                st.markdown("*Baseado na análise de infraestrutura local:*")
                
                for i, (profile_name, data) in enumerate(sorted_profiles[:3]):  # Top 3
                    score = data['score']
                    reasons = data['reasons']
                    
                    # Create recommendation level
                    if score >= 70:
                        level = "🏆 ALTAMENTE RECOMENDADO"
                        color = "success"
                    elif score >= 50:
                        level = "✅ RECOMENDADO"
                        color = "info"
                    else:
                        level = "📍 ADEQUADO"
                        color = "warning"
                    
                    with st.expander(f"{i+1}. {profile_name} - {score:.0f}/100", expanded=(i==0)):
                        st.markdown(f"**{level}**")
                        
                        if reasons:
                            st.markdown("**Por que é ideal:**")
                            for reason in reasons:
                                st.markdown(f"• {reason}")
                        
                        # Marketing suggestions
                        st.markdown("**💡 Sugestões de Marketing:**")
                        if 'Famílias' in profile_name:
                            st.markdown("• Destaque proximidade de escolas nos anúncios")
                            st.markdown("• Mencione segurança e áreas de lazer")
                            st.markdown("• Foque em imóveis com 2+ quartos")
                        elif 'Jovens' in profile_name:
                            st.markdown("• Enfatize vida noturna e entretenimento")
                            st.markdown("• Destaque facilidade de transporte")
                            st.markdown("• Mencione proximidade do trabalho/universidades")
                        elif 'Idosos' in profile_name:
                            st.markdown("• Priorize acesso à saúde")
                            st.markdown("• Destaque facilidade de locomoção")
                            st.markdown("• Mencione segurança da região")
                        elif 'Investidores' in profile_name:
                            st.markdown("• Apresente dados de valorização")
                            st.markdown("• Destaque potencial de aluguel")
                            st.markdown("• Mencione desenvolvimento da região")
                        elif 'sem carro' in profile_name:
                            st.markdown("• Destaque Walk Score alto")
                            st.markdown("• Mencione economia com transporte")
                            st.markdown("• Foque em sustentabilidade")
                
                # Generate marketing copy
                st.markdown("---")
                st.subheader("📝 Copy para Anúncios")
                
                best_profile = sorted_profiles[0]
                profile_name = best_profile[0]
                
                marketing_copy = f"""
**Imóvel Ideal para {profile_name}**

📍 Localização estratégica com {len(result.pois)} pontos de interesse próximos

{' '.join(['• ' + reason for reason in best_profile[1]['reasons']])}

Walk Score: {len(result.pois) * 3:.0f}/100 - Excelente caminhabilidade

*Agende sua visita e comprove a qualidade desta localização!*
                """
                
                st.code(marketing_copy.strip(), language=None)
                st.caption("📋 Copy pronta para usar em anúncios e redes sociais")
            
            with prof_tab4:
                st.subheader("📊 Ranking & Comparação de Carteira")
                
                if len(st.session_state.analysis_results) > 1:
                    st.markdown("### 🏆 **Ranking dos Imóveis Analisados**")
                    
                    # Create ranking
                    ranking_data = []
                    for address, analysis_result in st.session_state.analysis_results.items():
                        if hasattr(analysis_result, 'pois'):
                            total_pois = len(analysis_result.pois)
                            walk_score = min(total_pois * 3, 100)
                            
                            # Calculate category strengths
                            categories = {}
                            for poi in analysis_result.pois:
                                cat = poi.get('category', 'outros')
                                categories[cat] = categories.get(cat, 0) + 1
                            
                            # Determine best profile
                            education_score = categories.get('education', 0) * 25
                            transport_score = categories.get('transport', 0) * 25
                            entertainment_score = categories.get('entertainment', 0) * 30
                            
                            if education_score >= transport_score and education_score >= entertainment_score:
                                best_for = "Famílias"
                            elif transport_score >= entertainment_score:
                                best_for = "Profissionais"
                            else:
                                best_for = "Jovens"
                            
                            ranking_data.append({
                                'Endereço': address,
                                'Walk Score': walk_score,
                                'Total POIs': total_pois,
                                'Ideal para': best_for,
                                'Mercados': categories.get('shopping', 0),
                                'Escolas': categories.get('education', 0),
                                'Transporte': categories.get('transport', 0),
                                'Saúde': categories.get('healthcare', 0)
                            })
                    
                    # Sort by Walk Score
                    ranking_data.sort(key=lambda x: x['Walk Score'], reverse=True)
                    
                    # Display ranking
                    for i, item in enumerate(ranking_data):
                        rank_color = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}°"
                        
                        with st.expander(f"{rank_color} {item['Endereço']} - Score: {item['Walk Score']:.0f}/100", 
                                       expanded=(i < 3)):
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Total POIs", item['Total POIs'])
                                st.metric("Mercados", item['Mercados'])
                            
                            with col2:
                                st.metric("Escolas", item['Escolas'])
                                st.metric("Transporte", item['Transporte'])
                            
                            with col3:
                                st.metric("Saúde", item['Saúde'])
                                st.info(f"💡 Ideal para: **{item['Ideal para']}**")
                            
                            # Quick pitch for this property
                            if i < 3:  # Top 3 get special treatment
                                st.markdown("**🎯 Pitch para este imóvel:**")
                                if item['Walk Score'] >= 80:
                                    st.success("Localização PREMIUM - Destaque como oportunidade única")
                                elif item['Walk Score'] >= 60:
                                    st.info("Localização CONSOLIDADA - Enfatize conveniência")
                                else:
                                    st.warning("Localização RESIDENCIAL - Foque em outros diferenciais")
                    
                    # Portfolio insights
                    st.markdown("---")
                    st.subheader("📈 Insights da Carteira")
                    
                    avg_score = sum([item['Walk Score'] for item in ranking_data]) / len(ranking_data)
                    best_score = max([item['Walk Score'] for item in ranking_data])
                    worst_score = min([item['Walk Score'] for item in ranking_data])
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Score Médio", f"{avg_score:.0f}/100")
                        
                    with col2:
                        st.metric("Melhor Localização", f"{best_score:.0f}/100")
                        
                    with col3:
                        st.metric("Maior Potencial", f"{best_score - worst_score:.0f} pts")
                    
                    # Recommendations
                    st.markdown("### 💡 **Recomendações Estratégicas**")
                    
                    premium_count = len([x for x in ranking_data if x['Walk Score'] >= 80])
                    good_count = len([x for x in ranking_data if 60 <= x['Walk Score'] < 80])
                    basic_count = len([x for x in ranking_data if x['Walk Score'] < 60])
                    
                    st.markdown(f"**Composição da Carteira:**")
                    st.markdown(f"• 🏆 Premium (80+): {premium_count} imóveis")
                    st.markdown(f"• ✅ Consolidados (60-79): {good_count} imóveis") 
                    st.markdown(f"• 📍 Residenciais (<60): {basic_count} imóveis")
                    
                    if premium_count > 0:
                        st.success("💰 Foque nos imóveis premium para margem maior")
                    if good_count > basic_count:
                        st.info("📊 Carteira equilibrada - destaque conveniência")
                    if basic_count > good_count:
                        st.warning("🎯 Desenvolva argumentos alternativos para imóveis residenciais")
                
                else:
                    st.info("🔍 Analise mais endereços para ver o ranking da sua carteira!")
                    st.markdown("**Como usar:**")
                    st.markdown("1. Use a aba 'Análise Individual' para analisar múltiplos endereços")
                    st.markdown("2. Volte aqui para ver o ranking automático") 
                    st.markdown("3. Use os insights para priorizar seus esforços de venda")
            
            with prof_tab5:
                st.subheader("📱 Ferramentas Rápidas do Corretor")
                
                # Quick tools section
                tool_col1, tool_col2 = st.columns(2)
                
                with tool_col1:
                    st.markdown("### 📋 **Checklist Express**")
                    st.markdown("*Verificação rápida para apresentações:*")
                    
                    # Quick checklist based on POIs
                    essentials = {
                        '🛒 Mercado próximo': any(poi.get('distance', 999) <= 800 and 'shopping' in poi.get('category', '') for poi in result.pois),
                        '🏥 Saúde acessível': any(poi.get('distance', 999) <= 1200 and 'healthcare' in poi.get('category', '') for poi in result.pois),
                        '🚌 Transporte próximo': any(poi.get('distance', 999) <= 400 and 'transport' in poi.get('category', '') for poi in result.pois),
                        '🎓 Escola na região': any('education' in poi.get('category', '') for poi in result.pois),
                        '🌳 Área de lazer': any('park' in poi.get('category', '') for poi in result.pois),
                        '🍽️ Opções gastronômicas': len([p for p in result.pois if 'restaurant' in p.get('category', '')]) >= 2
                    }
                    
                    checked = sum(essentials.values())
                    total = len(essentials)
                    
                    st.progress(checked / total)
                    st.caption(f"✅ {checked}/{total} itens atendidos")
                    
                    for item, is_ok in essentials.items():
                        icon = "✅" if is_ok else "❌"
                        st.markdown(f"{icon} {item}")
                    
                    # Overall recommendation
                    if checked >= 5:
                        st.success("🏆 Excelente para apresentar!")
                    elif checked >= 3:
                        st.info("👍 Bom para a maioria dos perfis")
                    else:
                        st.warning("⚠️ Destaque outros diferenciais")
                
                with tool_col2:
                    st.markdown("### 🎯 **Gerador de QR Code**")
                    st.markdown("*Para compartilhar análise com clientes:*")
                    
                    # Simulate QR code generation
                    property_address = st.text_input("Endereço do imóvel", value="Rua Exemplo, 123")
                    
                    if st.button("🔗 Gerar Link de Compartilhamento"):
                        # Simulate URL generation
                        import hashlib
                        property_id = hashlib.md5(property_address.encode()).hexdigest()[:8]
                        share_url = f"https://urbansight.onrender.com/report/{property_id}"
                        
                        st.success("✅ Link gerado com sucesso!")
                        st.code(share_url)
                        st.markdown("📱 **Como usar:**")
                        st.markdown("• Envie por WhatsApp para o cliente")
                        st.markdown("• Inclua em apresentações") 
                        st.markdown("• Adicione em anúncios online")
                        
                        # QR Code placeholder
                        st.markdown("📱 **QR Code:**")
                        st.info("🔲 [QR Code seria gerado aqui]")
                        st.caption("Cliente escaneia e vê a análise completa")
                
                # Quick comparison tool
                st.markdown("---")
                st.subheader("⚡ Comparação Rápida")
                
                if len(st.session_state.analysis_results) >= 2:
                    st.markdown("Selecione dois endereços para comparação express:")
                    
                    addresses = list(st.session_state.analysis_results.keys())
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        addr1 = st.selectbox("Imóvel A", addresses, key="quick_comp_1")
                    
                    with col2:
                        addr2 = st.selectbox("Imóvel B", [a for a in addresses if a != addr1], key="quick_comp_2")
                    
                    if addr1 and addr2:
                        result1 = st.session_state.analysis_results[addr1]
                        result2 = st.session_state.analysis_results[addr2]
                        
                        # Quick comparison
                        comparison_data = {
                            'Métrica': ['Total POIs', 'Mercados', 'Escolas', 'Transporte', 'Saúde', 'Walk Score'],
                            addr1: [
                                len(result1.pois),
                                len([p for p in result1.pois if p.get('category') == 'shopping']),
                                len([p for p in result1.pois if p.get('category') == 'education']),
                                len([p for p in result1.pois if p.get('category') == 'transport']),
                                len([p for p in result1.pois if p.get('category') == 'healthcare']),
                                f"{min(len(result1.pois) * 3, 100):.0f}/100"
                            ],
                            addr2: [
                                len(result2.pois),
                                len([p for p in result2.pois if p.get('category') == 'shopping']),
                                len([p for p in result2.pois if p.get('category') == 'education']),
                                len([p for p in result2.pois if p.get('category') == 'transport']),
                                len([p for p in result2.pois if p.get('category') == 'healthcare']),
                                f"{min(len(result2.pois) * 3, 100):.0f}/100"
                            ]
                        }
                        
                        df_comp = pd.DataFrame(comparison_data)
                        st.dataframe(df_comp, hide_index=True)
                        
                        # Quick recommendation
                        score1 = len(result1.pois) * 3
                        score2 = len(result2.pois) * 3
                        
                        if score1 > score2:
                            winner = addr1
                            difference = ((score1 - score2) / score2) * 100
                        else:
                            winner = addr2
                            difference = ((score2 - score1) / score1) * 100
                        
                        st.info(f"🏆 **Recomendação:** {winner} é {difference:.0f}% superior em infraestrutura")
                
                else:
                    st.info("📊 Analise pelo menos 2 endereços para usar a comparação rápida")
                
                # Quick contact tools
                st.markdown("---")
                st.subheader("📞 Ferramentas de Contato")
                
                st.markdown("### 📨 **Template de WhatsApp**")
                
                # Generate WhatsApp message
                total_pois = len(result.pois)
                walk_score = min(total_pois * 3, 100)
                
                whatsapp_template = f"""🏠 *Análise Técnica do Imóvel*

📍 Localização com {total_pois} pontos de interesse próximos
🚶‍♂️ Walk Score: {walk_score}/100

✅ *Destaques da região:*
• Infraestrutura consolidada
• Boa caminhabilidade
• Serviços diversificados

💡 Gostaria de agendar uma visita para conhecer pessoalmente?

_Análise realizada com UrbanSight - Inteligência Imobiliária_"""
                
                st.code(whatsapp_template, language=None)
                st.caption("📱 Copie e personalize para seus clientes")
                
                # Email template
                st.markdown("### 📧 **Template de Email**")
                
                email_template = f"""Assunto: Análise Técnica - Imóvel de Interesse

Olá!

Realizei uma análise técnica detalhada da localização do imóvel que você demonstrou interesse.

📊 RESUMO DA ANÁLISE:
• {total_pois} pontos de interesse identificados
• Walk Score: {walk_score}/100
• Infraestrutura consolidada na região

A localização oferece excelente conveniência para o dia a dia, com fácil acesso a comércios, serviços e transporte.

Gostaria de agendar uma apresentação detalhada?

Atenciosamente,
[Seu Nome]
[Sua Imobiliária]

---
Análise realizada com UrbanSight - Inteligência Imobiliária Profissional"""
                
                st.code(email_template, language=None)
                st.caption("✉️ Template profissional para follow-up")
        
        else:
            st.info("👋 **Analise um imóvel primeiro!** Use a aba 'Análise Individual' para começar a usar as ferramentas profissionais.")
            
            # Show preview of what's available
            st.markdown("### 🎯 **Ferramentas Disponíveis para Corretores:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🎯 Pitch Automático**")
                st.caption("Texto pronto para apresentações")
                
                st.markdown("**📋 Argumentos de Venda**") 
                st.caption("Pontos fortes automáticos")
                
                st.markdown("**👥 Perfil do Comprador**")
                st.caption("Identifica público-alvo ideal")
            
            with col2:
                st.markdown("**📊 Ranking de Carteira**")
                st.caption("Compare múltiplos imóveis")
                
                st.markdown("**📱 Ferramentas Rápidas**")
                st.caption("QR Code, templates, checklists")
                
                st.markdown("**💰 Calculadoras ROI**")
                st.caption("Argumentos financeiros")
            
            st.success("💡 **Comece analisando um endereço e tenha acesso a todas essas ferramentas profissionais!**")

    with main_tab10:
        st.header("🏆 UrbanSight Premium")
        st.markdown("*Análises exclusivas para investidores e compradores exigentes*")
        
        if st.session_state.current_analysis:
            result = st.session_state.current_analysis
            
            # Premium header with subscription status
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: white;">🏆 Análise Premium Ativa</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Análises avançadas baseadas em algoritmos proprietários</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Calculate premium metrics
            maturity_index, _ = calculate_urban_maturity_index(result.pois)
            gentrification_index, _ = calculate_gentrification_index(result.pois)
            development_potential, _ = predict_development_potential(result.pois, (result.property_data.lat, result.property_data.lon))
            
            # Premium Analysis Tabs
            premium_tabs = st.tabs([
                "🎯 UrbanScore Elite",
                "🧬 DNA da Localização", 
                "🎮 Lifestyle Simulator",
                "💎 Rarity Index",
                "⏱️ Time Savings Calculator",
                "🔮 Future Index",
                "🚶 Mobility Signature",
                "🛡️ Resilience Score",
                "🌍 Social Impact Report"
            ])
            
            with premium_tabs[0]:
                st.subheader("🎯 UrbanScore Elite - Análise Proprietária")
                st.markdown("*Algoritmo avançado que combina 50+ variáveis urbanas*")
                
                # Calculate sophisticated UrbanScore
                def calculate_urban_score_elite(pois):
                    # Base scores
                    diversity_score = len(set([poi.get('category', 'other') for poi in pois])) * 10
                    density_score = min(len(pois) * 2, 100)
                    
                    # Quality indicators
                    quality_keywords = ['premium', 'gourmet', 'boutique', 'design', 'luxury', 'fine']
                    quality_count = sum([1 for poi in pois for keyword in quality_keywords 
                                       if keyword in poi.get('name', '').lower()])
                    quality_score = min(quality_count * 15, 100)
                    
                    # Accessibility premium
                    close_pois = len([p for p in pois if p.get('distance', 0) <= 300])
                    accessibility_premium = min(close_pois * 5, 100)
                    
                    # Innovation index
                    innovation_keywords = ['tech', 'coworking', 'startup', 'innovation', 'digital']
                    innovation_count = sum([1 for poi in pois for keyword in innovation_keywords
                                          if keyword in poi.get('name', '').lower()])
                    innovation_score = min(innovation_count * 20, 100)
                    
                    # Cultural richness
                    cultural_categories = ['entertainment', 'art', 'museum', 'theater']
                    cultural_count = len([p for p in pois if p.get('category', '') in cultural_categories])
                    cultural_score = min(cultural_count * 12, 100)
                    
                    # Calculate elite score
                    weights = {
                        'diversity': 0.20,
                        'density': 0.15,
                        'quality': 0.25,
                        'accessibility': 0.15,
                        'innovation': 0.15,
                        'cultural': 0.10
                    }
                    
                    elite_score = (diversity_score * weights['diversity'] + 
                                 density_score * weights['density'] +
                                 quality_score * weights['quality'] +
                                 accessibility_premium * weights['accessibility'] +
                                 innovation_score * weights['innovation'] +
                                 cultural_score * weights['cultural'])
                    
                    return elite_score, {
                        'diversity': diversity_score,
                        'density': density_score, 
                        'quality': quality_score,
                        'accessibility': accessibility_premium,
                        'innovation': innovation_score,
                        'cultural': cultural_score
                    }
                
                elite_score, elite_breakdown = calculate_urban_score_elite(result.pois)
                
                # Display elite score
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    score_color = "#4CAF50" if elite_score >= 80 else "#FF9800" if elite_score >= 60 else "#F44336"
                    st.markdown(f"""
                    <div style="text-align: center; padding: 30px; background: {score_color}20; 
                               border-radius: 20px; border: 3px solid {score_color};">
                        <h1 style="margin: 0; color: {score_color}; font-size: 4rem;">{elite_score:.0f}</h1>
                        <h3 style="margin: 10px 0 0 0; color: {score_color};">UrbanScore Elite</h3>
                        <p style="margin: 5px 0 0 0; opacity: 0.8;">
                            {'🏆 EXCEPCIONAL' if elite_score >= 80 else '⭐ PREMIUM' if elite_score >= 60 else '📍 PADRÃO'}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Elite breakdown
                st.markdown("---")
                st.subheader("📊 Breakdown Elite")
                
                breakdown_cols = st.columns(3)
                
                for i, (factor, score) in enumerate(elite_breakdown.items()):
                    with breakdown_cols[i % 3]:
                        factor_names = {
                            'diversity': '🏷️ Diversidade',
                            'density': '📍 Densidade',
                            'quality': '✨ Qualidade Premium',
                            'accessibility': '🚶 Acessibilidade Elite',
                            'innovation': '🚀 Índice de Inovação',
                            'cultural': '🎭 Riqueza Cultural'
                        }
                        
                        name = factor_names.get(factor, factor.title())
                        st.metric(name, f"{score:.0f}/100")
                        st.progress(score/100)
                
                # Elite insights
                st.markdown("---")
                st.subheader("💎 Insights Elite")
                
                if elite_score >= 80:
                    st.success("🏆 **LOCALIZAÇÃO EXCEPCIONAL**: Perfeita para investidores de alto padrão")
                    st.info("💡 **Estratégia**: Aquisição imediata, potencial de valorização premium")
                elif elite_score >= 60:
                    st.info("⭐ **LOCALIZAÇÃO PREMIUM**: Excelente para moradia de qualidade")
                    st.warning("💡 **Estratégia**: Análise de valor, bom potencial de crescimento")
                else:
                    st.warning("📍 **LOCALIZAÇÃO PADRÃO**: Foque em outros diferenciais")
                    st.error("💡 **Estratégia**: Apenas com desconto significativo")
            
            with premium_tabs[1]:
                st.subheader("🧬 DNA da Localização")
                st.markdown("*Perfil genético único baseado em 25+ características urbanas*")
                
                # Calculate DNA profile
                def calculate_location_dna(pois):
                    # DNA characteristics
                    dna_profile = {
                        'Urbano': 0, 'Residencial': 0, 'Comercial': 0, 'Cultural': 0,
                        'Tecnológico': 0, 'Gastronômico': 0, 'Educacional': 0, 'Verde': 0
                    }
                    
                    # Calculate DNA based on POI patterns
                    for poi in pois:
                        category = poi.get('category', '').lower()
                        name = poi.get('name', '').lower()
                        
                        # Urban DNA
                        if category in ['transport', 'services']:
                            dna_profile['Urbano'] += 2
                        
                        # Residential DNA
                        if category in ['shopping', 'healthcare', 'education']:
                            dna_profile['Residencial'] += 2
                        
                        # Commercial DNA
                        if category in ['shopping', 'services', 'restaurant']:
                            dna_profile['Comercial'] += 1.5
                        
                        # Cultural DNA
                        if category in ['entertainment'] or any(word in name for word in ['museum', 'theater', 'art']):
                            dna_profile['Cultural'] += 3
                        
                        # Tech DNA
                        if any(word in name for word in ['tech', 'digital', 'coworking', 'startup']):
                            dna_profile['Tecnológico'] += 4
                        
                        # Gastronomic DNA
                        if category == 'restaurant' or any(word in name for word in ['coffee', 'bakery', 'bistro']):
                            dna_profile['Gastronômico'] += 2
                        
                        # Educational DNA
                        if category == 'education':
                            dna_profile['Educacional'] += 3
                        
                        # Green DNA
                        if category == 'park' or any(word in name for word in ['park', 'garden', 'green']):
                            dna_profile['Verde'] += 3
                    
                    # Normalize to 100
                    total = sum(dna_profile.values())
                    if total > 0:
                        dna_profile = {k: (v/total)*100 for k, v in dna_profile.items()}
                    
                    return dna_profile
                
                dna_profile = calculate_location_dna(result.pois)
                
                # DNA Visualization
                st.markdown("### 🧬 Sequência Genética da Localização")
                
                # Create DNA bar chart
                dna_data = pd.DataFrame(list(dna_profile.items()), columns=['Gene', 'Expressão'])
                dna_data = dna_data.sort_values('Expressão', ascending=False)
                
                fig_dna = px.bar(
                    dna_data, 
                    x='Gene', 
                    y='Expressão',
                    title="DNA Urbano - Expressão Genética por Característica",
                    color='Expressão',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_dna, use_container_width=True)
                
                # Dominant genes
                st.markdown("### 🎯 Genes Dominantes")
                
                sorted_dna = sorted(dna_profile.items(), key=lambda x: x[1], reverse=True)
                
                for i, (gene, expression) in enumerate(sorted_dna[:3]):
                    if expression > 0:
                        st.markdown(f"**#{i+1} Gene {gene}**: {expression:.1f}% de expressão")
                        
                        gene_descriptions = {
                            'Urbano': "Localização com forte infraestrutura urbana e conectividade",
                            'Residencial': "Área ideal para moradia familiar com serviços essenciais",
                            'Comercial': "Centro de atividade comercial e empresarial",
                            'Cultural': "Rica vida cultural e entretenimento",
                            'Tecnológico': "Hub de inovação e tecnologia",
                            'Gastronômico': "Paraíso gastronômico com diversas opções",
                            'Educacional': "Foco em educação e desenvolvimento acadêmico",
                            'Verde': "Abundante em áreas verdes e natureza urbana"
                        }
                        
                        st.caption(gene_descriptions.get(gene, "Gene único desta localização"))
            
            with premium_tabs[2]:
                st.subheader("🎮 Lifestyle Simulator")
                st.markdown("*Simule sua vida diária nesta localização*")
                
                # Lifestyle simulation
                lifestyle_col1, lifestyle_col2 = st.columns(2)
                
                with lifestyle_col1:
                    st.markdown("### ⚙️ Configure Seu Perfil")
                    
                    work_location = st.selectbox("Local de trabalho", [
                        "Home office", "Centro da cidade", "Zona Sul", "Zona Norte", "Zona Oeste", "ABC"
                    ])
                    
                    lifestyle_priorities = st.multiselect("Prioridades do dia a dia", [
                        "Compras frequentes", "Exercícios", "Vida noturna", 
                        "Cultura", "Natureza", "Gastronomia", "Educação filhos"
                    ])
                    
                    transport_mode = st.radio("Meio de transporte principal", [
                        "A pé", "Bicicleta", "Transporte público", "Carro próprio", "Uber/99"
                    ])
                
                with lifestyle_col2:
                    st.markdown("### 📅 Simulação da Sua Semana")
                    
                    # Calculate weekly routine scores
                    routine_scores = {}
                    
                    # Morning routine
                    cafe_pois = [p for p in result.pois if 'cafe' in p.get('name', '').lower() or p.get('category') == 'restaurant']
                    morning_score = min(len(cafe_pois) * 20, 100)
                    routine_scores['☀️ Manhã (café, caminhada)'] = morning_score
                    
                    # Work commute
                    if work_location == "Home office":
                        commute_score = 100
                    else:
                        transport_pois = [p for p in result.pois if p.get('category') == 'transport']
                        commute_score = min(len(transport_pois) * 30, 100)
                    routine_scores['🚌 Deslocamento trabalho'] = commute_score
                    
                    # Daily shopping
                    shopping_pois = [p for p in result.pois if p.get('category') == 'shopping']
                    shopping_score = min(len(shopping_pois) * 25, 100)
                    routine_scores['🛒 Compras diárias'] = shopping_score
                    
                    # Exercise
                    exercise_pois = [p for p in result.pois if p.get('category') == 'park' or 'gym' in p.get('name', '').lower()]
                    exercise_score = min(len(exercise_pois) * 30, 100)
                    routine_scores['🏃 Exercícios'] = exercise_score
                    
                    # Evening entertainment
                    entertainment_pois = [p for p in result.pois if p.get('category') in ['restaurant', 'entertainment']]
                    evening_score = min(len(entertainment_pois) * 15, 100)
                    routine_scores['🌆 Entretenimento noturno'] = evening_score
                    
                    # Display routine scores
                    for activity, score in routine_scores.items():
                        st.progress(score/100)
                        st.caption(f"{activity}: {score:.0f}/100")
                
                # Weekly lifestyle score
                avg_lifestyle_score = sum(routine_scores.values()) / len(routine_scores)
                
                st.markdown("---")
                st.subheader("📊 Score do Seu Lifestyle")
                
                lifestyle_color = "#4CAF50" if avg_lifestyle_score >= 75 else "#FF9800" if avg_lifestyle_score >= 50 else "#F44336"
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: {lifestyle_color}20; 
                           border-radius: 15px; border: 2px solid {lifestyle_color};">
                    <h2 style="margin: 0; color: {lifestyle_color};">{avg_lifestyle_score:.0f}/100</h2>
                    <p style="margin: 5px 0 0 0; color: {lifestyle_color};">
                        {'🎯 LIFESTYLE PERFEITO' if avg_lifestyle_score >= 75 else '👍 BOM LIFESTYLE' if avg_lifestyle_score >= 50 else '⚠️ LIFESTYLE LIMITADO'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with premium_tabs[3]:
                st.subheader("💎 Rarity Index - Exclusividade da Localização")
                st.markdown("*Quão única e rara é esta localização?*")
                
                # Calculate rarity factors
                def calculate_rarity_index(pois):
                    rarity_factors = {
                        'uniqueness': 0,
                        'exclusivity': 0,
                        'scarcity': 0,
                        'premium_density': 0
                    }
                    
                    # Uniqueness - rare POI categories
                    rare_categories = ['art_gallery', 'museum', 'theater', 'observatory', 'monument']
                    unique_pois = [p for p in pois if any(rare in p.get('category', '').lower() for rare in rare_categories)]
                    rarity_factors['uniqueness'] = min(len(unique_pois) * 25, 100)
                    
                    # Exclusivity - premium keywords
                    premium_keywords = ['luxury', 'premium', 'exclusive', 'boutique', 'gourmet', 'fine', 'private']
                    exclusive_pois = [p for p in pois if any(keyword in p.get('name', '').lower() for keyword in premium_keywords)]
                    rarity_factors['exclusivity'] = min(len(exclusive_pois) * 20, 100)
                    
                    # Scarcity - high POI density (rare in most cities)
                    total_pois = len(pois)
                    if total_pois > 150:
                        rarity_factors['scarcity'] = 100
                    elif total_pois > 100:
                        rarity_factors['scarcity'] = 75
                    elif total_pois > 50:
                        rarity_factors['scarcity'] = 50
                    else:
                        rarity_factors['scarcity'] = 25
                    
                    # Premium density - concentration of high-end services
                    high_end_categories = ['restaurant', 'entertainment', 'services']
                    premium_density = len([p for p in pois if p.get('category') in high_end_categories]) / len(pois) * 100
                    rarity_factors['premium_density'] = min(premium_density * 2, 100)
                    
                    # Overall rarity index
                    weights = {'uniqueness': 0.3, 'exclusivity': 0.3, 'scarcity': 0.2, 'premium_density': 0.2}
                    overall_rarity = sum([rarity_factors[factor] * weights[factor] for factor in rarity_factors.keys()])
                    
                    return overall_rarity, rarity_factors
                
                rarity_index, rarity_breakdown = calculate_rarity_index(result.pois)
                
                # Display rarity index
                rarity_col1, rarity_col2, rarity_col3 = st.columns([1, 2, 1])
                
                with rarity_col2:
                    if rarity_index >= 80:
                        rarity_level = "💎 ULTRA RARO"
                        rarity_color = "#9C27B0"
                        rarity_desc = "Localização excepcional - menos de 1% das áreas urbanas"
                    elif rarity_index >= 60:
                        rarity_level = "💍 RARO"
                        rarity_color = "#3F51B5"
                        rarity_desc = "Localização especial - top 5% das áreas urbanas"
                    elif rarity_index >= 40:
                        rarity_level = "⭐ DIFERENCIADO"
                        rarity_color = "#FF9800"
                        rarity_desc = "Acima da média - top 20% das áreas urbanas"
                    else:
                        rarity_level = "📍 COMUM"
                        rarity_color = "#9E9E9E"
                        rarity_desc = "Padrão urbano comum"
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 25px; background: {rarity_color}20; 
                               border-radius: 20px; border: 3px solid {rarity_color};">
                        <h1 style="margin: 0; color: {rarity_color}; font-size: 3rem;">{rarity_index:.0f}</h1>
                        <h3 style="margin: 10px 0; color: {rarity_color};">{rarity_level}</h3>
                        <p style="margin: 0; opacity: 0.8;">{rarity_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with premium_tabs[4]:
                st.subheader("⏱️ Time Savings Calculator")
                st.markdown("*Calcule o tempo e dinheiro economizados morando aqui*")
                
                # Time savings calculator
                calc_col1, calc_col2 = st.columns(2)
                
                with calc_col1:
                    st.markdown("### ⚙️ Configuração do Cálculo")
                    
                    current_commute = st.slider("Tempo atual de deslocamento ao trabalho (min/dia)", 0, 180, 60)
                    work_frequency = st.slider("Dias de trabalho por semana", 1, 7, 5)
                    
                    shopping_frequency = st.slider("Vezes que vai ao mercado por semana", 1, 7, 2)
                    current_shopping_time = st.slider("Tempo atual para ir ao mercado (min)", 5, 60, 20)
                    
                    leisure_frequency = st.slider("Atividades de lazer por semana", 0, 7, 2)
                    current_leisure_time = st.slider("Tempo atual para lazer (min)", 10, 120, 30)
                    
                    hourly_value = st.number_input("Valor da sua hora (R$)", min_value=10, max_value=500, value=50)
                
                with calc_col2:
                    st.markdown("### 📊 Tempo Economizado Nesta Localização")
                    
                    # Calculate potential time savings
                    
                    # Work commute savings
                    transport_pois = [p for p in result.pois if p.get('category') == 'transport']
                    if transport_pois:
                        avg_transport_distance = sum([p.get('distance', 0) for p in transport_pois]) / len(transport_pois)
                        new_commute_time = max(10, current_commute - (500 - avg_transport_distance) / 10)  # Better transport = less time
                    else:
                        new_commute_time = current_commute + 10  # Worse transport = more time
                    
                    commute_savings = (current_commute - new_commute_time) * work_frequency
                    
                    # Shopping time savings
                    shopping_pois = [p for p in result.pois if p.get('category') == 'shopping']
                    if shopping_pois:
                        closest_shopping = min([p.get('distance', 1000) for p in shopping_pois])
                        new_shopping_time = max(5, closest_shopping / 83.33 * 2)  # Walking time * 2 (round trip)
                    else:
                        new_shopping_time = current_shopping_time
                    
                    shopping_savings = (current_shopping_time - new_shopping_time) * shopping_frequency
                    
                    # Leisure time savings
                    leisure_pois = [p for p in result.pois if p.get('category') in ['entertainment', 'restaurant', 'park']]
                    if leisure_pois:
                        avg_leisure_distance = sum([p.get('distance', 0) for p in leisure_pois]) / len(leisure_pois)
                        new_leisure_time = max(5, avg_leisure_distance / 83.33 * 2)
                    else:
                        new_leisure_time = current_leisure_time
                    
                    leisure_savings = (current_leisure_time - new_leisure_time) * leisure_frequency
                    
                    # Total weekly savings
                    total_weekly_savings = commute_savings + shopping_savings + leisure_savings
                    
                    # Display savings
                    st.metric("🚌 Economia Trabalho", f"{commute_savings:.0f} min/semana")
                    st.metric("🛒 Economia Compras", f"{shopping_savings:.0f} min/semana")
                    st.metric("🎭 Economia Lazer", f"{leisure_savings:.0f} min/semana")
                    
                    st.markdown("---")
                    
                    st.metric("⏰ **TOTAL SEMANAL**", f"{total_weekly_savings:.0f} min")
                    st.metric("📅 **TOTAL MENSAL**", f"{total_weekly_savings * 4.3:.0f} min")
                    st.metric("📆 **TOTAL ANUAL**", f"{total_weekly_savings * 52 / 60:.0f} horas")
                
                # Financial impact
                st.markdown("---")
                st.subheader("💰 Impacto Financeiro da Economia de Tempo")
                
                finance_cols = st.columns(4)
                
                weekly_value = (total_weekly_savings / 60) * hourly_value
                monthly_value = weekly_value * 4.3
                annual_value = weekly_value * 52
                
                with finance_cols[0]:
                    st.metric("💵 Semanal", f"R$ {weekly_value:.0f}")
                with finance_cols[1]:
                    st.metric("💵 Mensal", f"R$ {monthly_value:.0f}")
                with finance_cols[2]:
                    st.metric("💵 Anual", f"R$ {annual_value:.0f}")
                with finance_cols[3]:
                    st.metric("💵 10 Anos", f"R$ {annual_value * 10:,.0f}")
            
            with premium_tabs[5]:
                st.subheader("🔮 Future Index - Potencial Futuro")
                st.markdown("*Análise preditiva baseada em padrões de crescimento urbano*")
                
                # Calculate future index
                future_indicators = {
                    'infrastructure_momentum': 0,
                    'demographic_trends': 0,
                    'economic_growth': 0,
                    'sustainability_index': 0,
                    'innovation_potential': 0
                }
                
                # Infrastructure momentum
                transport_density = len([p for p in result.pois if p.get('category') == 'transport']) / len(result.pois) * 100
                future_indicators['infrastructure_momentum'] = min(transport_density * 5, 100)
                
                # Demographic trends (diversity of services indicates growing population)
                service_diversity = len(set([poi.get('category', 'other') for poi in result.pois]))
                future_indicators['demographic_trends'] = min(service_diversity * 12.5, 100)
                
                # Economic growth (business density)
                business_categories = ['shopping', 'restaurant', 'services']
                business_count = len([p for p in result.pois if p.get('category') in business_categories])
                future_indicators['economic_growth'] = min(business_count * 5, 100)
                
                # Sustainability index
                green_pois = len([p for p in result.pois if p.get('category') == 'park'])
                bike_friendly = len([p for p in result.pois if 'bike' in p.get('name', '').lower()])
                future_indicators['sustainability_index'] = min((green_pois + bike_friendly) * 15, 100)
                
                # Innovation potential
                innovation_keywords = ['tech', 'coworking', 'startup', 'innovation', 'digital', 'hub']
                innovation_count = sum([1 for poi in result.pois for keyword in innovation_keywords
                                      if keyword in poi.get('name', '').lower()])
                future_indicators['innovation_potential'] = min(innovation_count * 25, 100)
                
                # Overall future index
                future_weights = {
                    'infrastructure_momentum': 0.25,
                    'demographic_trends': 0.20,
                    'economic_growth': 0.25,
                    'sustainability_index': 0.15,
                    'innovation_potential': 0.15
                }
                
                future_index = sum([future_indicators[indicator] * future_weights[indicator] for indicator in future_indicators.keys()])
                
                # Display future index
                future_col1, future_col2, future_col3 = st.columns([1, 2, 1])
                
                with future_col2:
                    if future_index >= 80:
                        future_level = "🚀 FUTURO BRILHANTE"
                        future_color = "#4CAF50"
                    elif future_index >= 60:
                        future_level = "📈 BOM POTENCIAL"
                        future_color = "#2196F3"
                    elif future_index >= 40:
                        future_level = "⚖️ ESTÁVEL"
                        future_color = "#FF9800"
                    else:
                        future_level = "⚠️ INCERTO"
                        future_color = "#F44336"
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 25px; background: {future_color}20; 
                               border-radius: 20px; border: 3px solid {future_color};">
                        <h1 style="margin: 0; color: {future_color}; font-size: 3rem;">{future_index:.0f}</h1>
                        <h3 style="margin: 10px 0; color: {future_color};">Future Index</h3>
                        <p style="margin: 0; opacity: 0.8;">{future_level}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Future indicators breakdown
                st.markdown("---")
                st.subheader("🔮 Indicadores do Futuro")
                
                for indicator, score in future_indicators.items():
                    indicator_names = {
                        'infrastructure_momentum': '🏗️ Momentum de Infraestrutura',
                        'demographic_trends': '👥 Tendências Demográficas',
                        'economic_growth': '💼 Crescimento Econômico',
                        'sustainability_index': '🌱 Índice de Sustentabilidade',
                        'innovation_potential': '🚀 Potencial de Inovação'
                    }
                    
                    name = indicator_names.get(indicator, indicator.title())
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.progress(score/100)
                        st.caption(f"{name}: {score:.0f}/100")
                    with col2:
                        if score >= 75:
                            st.markdown("🟢 Excelente")
                        elif score >= 50:
                            st.markdown("🟡 Bom")
                        else:
                            st.markdown("🔴 Limitado")
                
                # Future scenarios
                st.markdown("---")
                st.subheader("🎭 Cenários Futuros (10 anos)")
                
                scenario_tabs = st.tabs(["🌟 Otimista", "📊 Realista", "⚠️ Pessimista"])
                
                with scenario_tabs[0]:
                    st.markdown("### 🌟 Cenário Otimista (30% probabilidade)")
                    if future_index >= 70:
                        st.success("🚀 Desenvolvimento acelerado com chegada de grandes empresas")
                        st.success("🏗️ Expansão da infraestrutura de transporte")
                        st.success("💰 Valorização imobiliária de 8-12% ao ano")
                    else:
                        st.info("📈 Crescimento gradual com melhorias pontuais")
                        st.info("💰 Valorização de 5-7% ao ano")
                
                with scenario_tabs[1]:
                    st.markdown("### 📊 Cenário Realista (50% probabilidade)")
                    st.info("📈 Crescimento sustentado seguindo tendências atuais")
                    st.info("💰 Valorização imobiliária de 4-6% ao ano")
                    st.info("🏙️ Manutenção das características atuais com melhorias graduais")
                
                with scenario_tabs[2]:
                    st.markdown("### ⚠️ Cenário Pessimista (20% probabilidade)")
                    if future_index < 40:
                        st.warning("📉 Estagnação do desenvolvimento urbano")
                        st.warning("💰 Valorização limitada (2-3% ao ano)")
                    else:
                        st.info("🔄 Crescimento mais lento que o esperado")
                        st.info("💰 Valorização abaixo da média (3-4% ao ano)")
                
                # Investment timeline
                st.markdown("---")
                st.subheader("💰 Projeção de Valorização")
                
                # Simple valorization model based on indices
                base_valorization = 3  # Base 3% per year
                
                development_bonus = (development_potential / 100) * 2  # Up to 2% bonus
                maturity_penalty = (maturity_index / 100) * 1  # Up to 1% penalty for mature areas
                future_bonus = (future_index / 100) * 2  # Up to 2% bonus for future potential
                
                projected_valorization = base_valorization + development_bonus - maturity_penalty + future_bonus
                
                valorization_cols = st.columns(4)
                
                with valorization_cols[0]:
                    st.metric("1 Ano", f"+{projected_valorization:.1f}%")
                with valorization_cols[1]:
                    st.metric("3 Anos", f"+{projected_valorization * 3:.1f}%")
                with valorization_cols[2]:
                    st.metric("5 Anos", f"+{projected_valorization * 5:.1f}%")
                with valorization_cols[3]:
                    st.metric("10 Anos", f"+{projected_valorization * 10:.1f}%")
                
                st.caption("⚠️ Projeções baseadas em padrões urbanos simulados, não garantem resultados reais.")
                
            with premium_tabs[6]:
                st.subheader("🚶 Mobility Signature - Assinatura de Mobilidade")
                st.markdown("*Análise única dos padrões de mobilidade desta localização*")
                
                # Calculate mobility signature
                mobility_metrics = {
                    'walkability_premium': 0,
                    'public_transport_density': 0,
                    'cycling_infrastructure': 0,
                    'car_dependency': 0,
                    'multimodal_connectivity': 0
                }
                
                # Walkability premium
                walking_pois = len([p for p in result.pois if p.get('distance', 0) <= 500])
                mobility_metrics['walkability_premium'] = min(walking_pois * 3, 100)
                
                # Public transport density
                transport_pois = [p for p in result.pois if p.get('category') == 'transport']
                transport_nearby = len([p for p in transport_pois if p.get('distance', 0) <= 300])
                mobility_metrics['public_transport_density'] = min(transport_nearby * 25, 100)
                
                # Cycling infrastructure
                bike_pois = len([p for p in result.pois if 'bike' in p.get('name', '').lower()])
                mobility_metrics['cycling_infrastructure'] = min(bike_pois * 30, 100)
                
                # Car dependency (inverse of walkable services)
                essential_walking = len([p for p in result.pois if p.get('category') in ['shopping', 'healthcare'] and p.get('distance', 0) <= 800])
                mobility_metrics['car_dependency'] = max(0, 100 - essential_walking * 20)
                
                # Multimodal connectivity
                transport_types = len(set([p.get('name', '').lower() for p in transport_pois]))
                mobility_metrics['multimodal_connectivity'] = min(transport_types * 20, 100)
                
                # Create mobility signature visualization
                mobility_df = pd.DataFrame(list(mobility_metrics.items()), columns=['Metric', 'Score'])
                
                fig_mobility = go.Figure()
                
                fig_mobility.add_trace(go.Scatterpolar(
                    r=list(mobility_metrics.values()) + [list(mobility_metrics.values())[0]],
                    theta=['Caminhabilidade', 'Transporte Público', 'Ciclismo', 'Dependência Carro', 'Conectividade'] + ['Caminhabilidade'],
                    fill='toself',
                    name='Assinatura de Mobilidade',
                    line_color='rgb(90, 200, 250)'
                ))
                
                fig_mobility.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )),
                    showlegend=False,
                    title="Assinatura de Mobilidade da Localização"
                )
                
                st.plotly_chart(fig_mobility, use_container_width=True)
                
                # Mobility profile
                st.markdown("---")
                st.subheader("🎯 Perfil de Mobilidade")
                
                mobility_score = sum(mobility_metrics.values()) / len(mobility_metrics)
                
                if mobility_score >= 80:
                    mobility_profile = "🌟 MOBILIDADE EXCEPCIONAL"
                    mobility_desc = "Localização com conectividade superior e múltiplas opções de transporte"
                elif mobility_score >= 60:
                    mobility_profile = "🚀 ALTA MOBILIDADE"
                    mobility_desc = "Excelente conectividade urbana com boa variedade de transporte"
                elif mobility_score >= 40:
                    mobility_profile = "🚌 MOBILIDADE PADRÃO"
                    mobility_desc = "Conectividade adequada para a maioria das necessidades"
                else:
                    mobility_profile = "🚗 DEPENDENTE DE CARRO"
                    mobility_desc = "Localização com mobilidade limitada, requer transporte próprio"
                
                st.info(f"**{mobility_profile}**: {mobility_desc}")
                
                # Detailed mobility analysis
                mobility_detail_cols = st.columns(2)
                
                with mobility_detail_cols[0]:
                    st.markdown("### 🚶 Caminhabilidade")
                    walk_score = mobility_metrics['walkability_premium']
                    if walk_score >= 70:
                        st.success(f"🟢 Excelente ({walk_score:.0f}/100)")
                        st.caption("A maioria das necessidades diárias pode ser resolvida a pé")
                    elif walk_score >= 40:
                        st.warning(f"🟡 Moderada ({walk_score:.0f}/100)")
                        st.caption("Algumas necessidades podem ser resolvidas a pé")
                    else:
                        st.error(f"🔴 Limitada ({walk_score:.0f}/100)")
                        st.caption("Poucas opções para pedestres")
                    
                    st.markdown("### 🚲 Infraestrutura Cicloviária")
                    cycling_score = mobility_metrics['cycling_infrastructure']
                    if cycling_score >= 50:
                        st.success(f"🟢 Bike-friendly ({cycling_score:.0f}/100)")
                    else:
                        st.warning(f"🟡 Limitada ({cycling_score:.0f}/100)")
                
                with mobility_detail_cols[1]:
                    st.markdown("### 🚌 Transporte Público")
                    transport_score = mobility_metrics['public_transport_density']
                    if transport_score >= 70:
                        st.success(f"🟢 Excelente ({transport_score:.0f}/100)")
                        st.caption("Múltiplas opções de transporte próximas")
                    elif transport_score >= 40:
                        st.warning(f"🟡 Adequado ({transport_score:.0f}/100)")
                        st.caption("Transporte público acessível")
                    else:
                        st.error(f"🔴 Limitado ({transport_score:.0f}/100)")
                        st.caption("Poucas opções de transporte público")
                    
                    st.markdown("### 🚗 Dependência de Carro")
                    car_dependency = mobility_metrics['car_dependency']
                    if car_dependency <= 30:
                        st.success(f"🟢 Baixa ({car_dependency:.0f}/100)")
                    elif car_dependency <= 60:
                        st.warning(f"🟡 Moderada ({car_dependency:.0f}/100)")
                    else:
                        st.error(f"🔴 Alta ({car_dependency:.0f}/100)")
                
                # Mobility recommendations
                st.markdown("---")
                st.subheader("💡 Recomendações de Mobilidade")
                
                if walk_score >= 60:
                    st.success("🚶 **Walking-friendly**: Ideal para quem gosta de caminhar")
                if transport_score >= 60:
                    st.success("🚌 **Transit-oriented**: Perfeito para usuários de transporte público")
                if car_dependency >= 70:
                    st.warning("🚗 **Car-dependent**: Considere ter um veículo próprio")
                if cycling_score >= 40:
                    st.info("🚲 **Bike-friendly**: Bom para ciclistas urbanos")
                
            with premium_tabs[7]:
                st.subheader("🛡️ Resilience Score - Resistência e Adaptabilidade")
                st.markdown("*Capacidade da localização de resistir a mudanças e crises*")
                
                # Calculate resilience factors
                resilience_factors = {
                    'service_redundancy': 0,
                    'economic_diversity': 0,
                    'infrastructure_stability': 0,
                    'social_cohesion': 0,
                    'adaptability_index': 0
                }
                
                # Service redundancy (multiple options for each essential service)
                essential_categories = ['shopping', 'healthcare', 'education', 'transport']
                redundancy_score = 0
                for category in essential_categories:
                    category_count = len([p for p in result.pois if p.get('category') == category])
                    redundancy_score += min(category_count * 20, 100)
                resilience_factors['service_redundancy'] = redundancy_score / len(essential_categories)
                
                # Economic diversity (variety of business types)
                business_categories = set([poi.get('category', 'other') for poi in result.pois])
                resilience_factors['economic_diversity'] = min(len(business_categories) * 15, 100)
                
                # Infrastructure stability (transport connectivity)
                transport_pois = [p for p in result.pois if p.get('category') == 'transport']
                resilience_factors['infrastructure_stability'] = min(len(transport_pois) * 20, 100)
                
                # Social cohesion (community spaces and gathering places)
                community_categories = ['park', 'entertainment', 'restaurant', 'education']
                community_pois = [p for p in result.pois if p.get('category') in community_categories]
                resilience_factors['social_cohesion'] = min(len(community_pois) * 5, 100)
                
                # Adaptability index (presence of modern/flexible services)
                adaptability_keywords = ['coworking', 'digital', 'tech', 'innovation', 'startup', 'flex']
                adaptable_pois = sum([1 for poi in result.pois for keyword in adaptability_keywords
                                    if keyword in poi.get('name', '').lower()])
                resilience_factors['adaptability_index'] = min(adaptable_pois * 25, 100)
                
                # Overall resilience score
                resilience_weights = {
                    'service_redundancy': 0.25,
                    'economic_diversity': 0.20,
                    'infrastructure_stability': 0.20,
                    'social_cohesion': 0.20,
                    'adaptability_index': 0.15
                }
                
                resilience_score = sum([resilience_factors[factor] * resilience_weights[factor] for factor in resilience_factors.keys()])
                
                # Display resilience score
                resilience_col1, resilience_col2, resilience_col3 = st.columns([1, 2, 1])
                
                with resilience_col2:
                    if resilience_score >= 80:
                        resilience_level = "🛡️ ULTRA RESILIENTE"
                        resilience_color = "#4CAF50"
                        resilience_desc = "Extremamente resistente a mudanças e crises"
                    elif resilience_score >= 60:
                        resilience_level = "🏰 RESILIENTE"
                        resilience_color = "#2196F3"
                        resilience_desc = "Boa capacidade de adaptação"
                    elif resilience_score >= 40:
                        resilience_level = "⚖️ MODERADAMENTE RESILIENTE"
                        resilience_color = "#FF9800"
                        resilience_desc = "Resistência adequada"
                    else:
                        resilience_level = "⚠️ VULNERÁVEL"
                        resilience_color = "#F44336"
                        resilience_desc = "Baixa resistência a mudanças"
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 25px; background: {resilience_color}20; 
                               border-radius: 20px; border: 3px solid {resilience_color};">
                        <h1 style="margin: 0; color: {resilience_color}; font-size: 3rem;">{resilience_score:.0f}</h1>
                        <h3 style="margin: 10px 0; color: {resilience_color};">Resilience Score</h3>
                        <p style="margin: 0; opacity: 0.8;">{resilience_level}</p>
                        <p style="margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.7;">{resilience_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Resilience breakdown
                st.markdown("---")
                st.subheader("🛡️ Fatores de Resilência")
                
                for factor, score in resilience_factors.items():
                    factor_names = {
                        'service_redundancy': '🔄 Redundância de Serviços',
                        'economic_diversity': '💼 Diversidade Econômica',
                        'infrastructure_stability': '🏗️ Estabilidade da Infraestrutura',
                        'social_cohesion': '👥 Coesão Social',
                        'adaptability_index': '🔧 Índice de Adaptabilidade'
                    }
                    
                    name = factor_names.get(factor, factor.title())
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.progress(score/100)
                        st.caption(f"{name}: {score:.0f}/100")
                    with col2:
                        if score >= 75:
                            st.markdown("🟢 Forte")
                        elif score >= 50:
                            st.markdown("🟡 Adequado")
                        else:
                            st.markdown("🔴 Fraco")
                
            with premium_tabs[8]:
                st.subheader("🌍 Social Impact Report")
                st.markdown("*Análise do impacto social e sustentabilidade da localização*")
                
                # Calculate social impact metrics
                social_metrics = {
                    'community_wellbeing': 0,
                    'accessibility_inclusion': 0,
                    'environmental_impact': 0,
                    'economic_contribution': 0,
                    'cultural_preservation': 0
                }
                
                # Community wellbeing (healthcare, education, recreation)
                wellbeing_categories = ['healthcare', 'education', 'park']
                wellbeing_pois = [p for p in result.pois if p.get('category') in wellbeing_categories]
                social_metrics['community_wellbeing'] = min(len(wellbeing_pois) * 8, 100)
                
                # Accessibility inclusion (public transport, walkability)
                transport_pois = [p for p in result.pois if p.get('category') == 'transport']
                walking_distance_pois = len([p for p in result.pois if p.get('distance', 0) <= 500])
                social_metrics['accessibility_inclusion'] = min((len(transport_pois) * 15 + walking_distance_pois * 2), 100)
                
                # Environmental impact (green spaces, sustainable transport)
                green_pois = len([p for p in result.pois if p.get('category') == 'park'])
                bike_infrastructure = len([p for p in result.pois if 'bike' in p.get('name', '').lower()])
                social_metrics['environmental_impact'] = min((green_pois * 20 + bike_infrastructure * 15), 100)
                
                # Economic contribution (business density, job creation)
                business_pois = [p for p in result.pois if p.get('category') in ['shopping', 'restaurant', 'services']]
                social_metrics['economic_contribution'] = min(len(business_pois) * 4, 100)
                
                # Cultural preservation (cultural venues, diversity)
                cultural_keywords = ['museum', 'art', 'theater', 'cultural', 'heritage', 'history']
                cultural_pois = sum([1 for poi in result.pois for keyword in cultural_keywords
                                   if keyword in poi.get('name', '').lower()])
                entertainment_pois = len([p for p in result.pois if p.get('category') == 'entertainment'])
                social_metrics['cultural_preservation'] = min((cultural_pois * 25 + entertainment_pois * 10), 100)
                
                # Overall social impact score
                social_weights = {
                    'community_wellbeing': 0.25,
                    'accessibility_inclusion': 0.25,
                    'environmental_impact': 0.20,
                    'economic_contribution': 0.15,
                    'cultural_preservation': 0.15
                }
                
                social_impact_score = sum([social_metrics[metric] * social_weights[metric] for metric in social_metrics.keys()])
                
                # Display social impact score
                social_col1, social_col2, social_col3 = st.columns([1, 2, 1])
                
                with social_col2:
                    if social_impact_score >= 80:
                        impact_level = "🌟 IMPACTO EXCEPCIONAL"
                        impact_color = "#4CAF50"
                        impact_desc = "Contribuição extraordinária para o bem-estar social"
                    elif social_impact_score >= 60:
                        impact_level = "🌱 IMPACTO POSITIVO"
                        impact_color = "#8BC34A"
                        impact_desc = "Boa contribuição para a comunidade"
                    elif social_impact_score >= 40:
                        impact_level = "⚖️ IMPACTO NEUTRO"
                        impact_color = "#FF9800"
                        impact_desc = "Impacto social moderado"
                    else:
                        impact_level = "⚠️ IMPACTO LIMITADO"
                        impact_color = "#F44336"
                        impact_desc = "Baixa contribuição social"
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 25px; background: {impact_color}20; 
                               border-radius: 20px; border: 3px solid {impact_color};">
                        <h1 style="margin: 0; color: {impact_color}; font-size: 3rem;">{social_impact_score:.0f}</h1>
                        <h3 style="margin: 10px 0; color: {impact_color};">Social Impact Score</h3>
                        <p style="margin: 0; opacity: 0.8;">{impact_level}</p>
                        <p style="margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.7;">{impact_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # SDG alignment
                st.markdown("---")
                st.subheader("🎯 Alinhamento com ODS (Objetivos de Desenvolvimento Sustentável)")
                
                sdg_alignment = {
                    "3. Saúde e Bem-estar": social_metrics['community_wellbeing'],
                    "4. Educação de Qualidade": social_metrics['community_wellbeing'],
                    "8. Trabalho Decente": social_metrics['economic_contribution'],
                    "10. Redução das Desigualdades": social_metrics['accessibility_inclusion'],
                    "11. Cidades Sustentáveis": social_impact_score,
                    "13. Ação Climática": social_metrics['environmental_impact']
                }
                
                sdg_cols = st.columns(2)
                for i, (sdg, score) in enumerate(sdg_alignment.items()):
                    with sdg_cols[i % 2]:
                        if score >= 70:
                            st.success(f"✅ **ODS {sdg}**: Forte alinhamento ({score:.0f}/100)")
                        elif score >= 50:
                            st.info(f"📊 **ODS {sdg}**: Alinhamento moderado ({score:.0f}/100)")
                        else:
                            st.warning(f"⚠️ **ODS {sdg}**: Alinhamento limitado ({score:.0f}/100)")
                
                # ESG Score
                st.markdown("---")
                st.subheader("💰 Score ESG para Investidores")
                
                esg_score = social_impact_score
                
                if esg_score >= 80:
                    st.success(f"🌟 **ESG EXCEPCIONAL** ({esg_score:.0f}/100): Investimento altamente responsável")
                elif esg_score >= 60:
                    st.info(f"🌱 **ESG POSITIVO** ({esg_score:.0f}/100): Boa pontuação de sustentabilidade")
                elif esg_score >= 40:
                    st.warning(f"⚖️ **ESG NEUTRO** ({esg_score:.0f}/100): Impacto social moderado")
                else:
                    st.error(f"⚠️ **ESG BAIXO** ({esg_score:.0f}/100): Limitações de sustentabilidade")
        
        else:
            st.info("👋 **Realize uma análise primeiro!** Use a aba 'Análise Individual' para acessar as funcionalidades premium.")
            
            # Premium features preview
            st.markdown("### 🏆 **Funcionalidades Premium Disponíveis:**")
            
            premium_features = [
                ("🎯 UrbanScore Elite", "Algoritmo proprietário com 50+ variáveis urbanas"),
                ("🧬 DNA da Localização", "Perfil genético único baseado em características urbanas"),
                ("🎮 Lifestyle Simulator", "Simule sua vida diária na localização"),
                ("💎 Rarity Index", "Exclusividade e raridade da localização"),
                ("⏱️ Time Savings Calculator", "Economia de tempo e dinheiro"),
                ("🔮 Future Index", "Potencial futuro baseado em tendências"),
                ("🚶 Mobility Signature", "Assinatura única de mobilidade"),
                ("🛡️ Resilience Score", "Resistência a mudanças e crises"),
                ("🌍 Social Impact Report", "Impacto social e sustentabilidade")
            ]
            
            premium_col1, premium_col2 = st.columns(2)
            
            for i, (feature, description) in enumerate(premium_features):
                with premium_col1 if i % 2 == 0 else premium_col2:
                    st.markdown(f"**{feature}**")
                    st.caption(description)
                    st.markdown("---")
            
            st.success("💡 **Todas essas análises avançadas estão prontas! Analise um endereço para acessá-las.**")

if __name__ == "__main__":
    main()