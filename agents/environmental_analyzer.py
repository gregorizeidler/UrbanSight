import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import overpy
import numpy as np
from geopy.distance import geodesic
import math

from agents.osm_data_collector import PropertyData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MicroclimateFactor:
    """Fator de microclima"""
    factor_type: str
    distance: float
    impact_score: float
    description: str

@dataclass
class WaterFeature:
    """Recurso hídrico"""
    id: str
    name: str
    feature_type: str  # river, stream, canal, lake, fountain
    distance: float
    size_category: str  # small, medium, large
    recreational_value: float
    flood_risk: float

@dataclass
class MicroclimateMetrics:
    """Métricas de microclima"""
    tree_coverage_score: float
    water_proximity_score: float
    heat_island_risk: float
    wind_corridor_score: float
    overall_climate_score: float
    climate_factors: List[MicroclimateFactor]

@dataclass
class WaterFeaturesMetrics:
    """Métricas de recursos hídricos"""
    water_features: List[WaterFeature]
    landscape_quality_score: float
    recreational_water_score: float
    flood_risk_score: float
    humidity_impact_score: float
    overall_water_score: float

@dataclass
class EnvironmentalMetrics:
    """Métricas ambientais completas"""
    microclimate: MicroclimateMetrics
    water_features: WaterFeaturesMetrics
    environmental_score: float
    green_space_index: float
    air_quality_estimate: float

class EnvironmentalAnalyzer:
    """Agente especializado em análise ambiental e climática"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_environmental_query(self, lat: float, lon: float, radius: int = 1500) -> str:
        """Construir query para dados ambientais"""
        query = f"""
        [out:json][timeout:30];
        (
          // Árvores e vegetação
          node["natural"="tree"](around:{radius},{lat},{lon});
          way["natural"="tree_row"](around:{radius},{lat},{lon});
          way["landuse"="forest"](around:{radius},{lat},{lon});
          way["landuse"="grass"](around:{radius},{lat},{lon});
          way["landuse"="meadow"](around:{radius},{lat},{lon});
          way["natural"="wood"](around:{radius},{lat},{lon});
          
          // Recursos hídricos
          way["waterway"~"^(river|stream|canal)$"](around:{radius},{lat},{lon});
          way["natural"="water"](around:{radius},{lat},{lon});
          relation["natural"="water"](around:{radius},{lat},{lon});
          node["amenity"="fountain"](around:{radius},{lat},{lon});
          
          // Parques e áreas verdes
          way["leisure"="park"](around:{radius},{lat},{lon});
          way["leisure"="garden"](around:{radius},{lat},{lon});
          relation["leisure"="park"](around:{radius},{lat},{lon});
          
          // Edifícios para análise de ilhas de calor
          way["building"](around:{radius},{lat},{lon});
          
          // Vias para análise de corredores de vento
          way["highway"~"^(primary|secondary|tertiary|residential)$"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def collect_environmental_data(self, property_data: PropertyData, radius: int = 1500) -> EnvironmentalMetrics:
        """Coletar dados ambientais"""
        try:
            logger.info(f"Coletando dados ambientais para {property_data.address} (raio: {radius}m)")
            query = self._build_environmental_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar microclima
            microclimate = self._analyze_microclimate(result, property_data, radius)
            
            # Analisar recursos hídricos
            water_features = self._analyze_water_features(result, property_data)
            
            # Calcular score ambiental geral
            environmental_score = self._calculate_environmental_score(microclimate, water_features)
            
            # Calcular índice de espaços verdes
            green_space_index = self._calculate_green_space_index(result, property_data, radius)
            
            # Estimar qualidade do ar
            air_quality_estimate = self._estimate_air_quality(result, property_data)
            
            return EnvironmentalMetrics(
                microclimate=microclimate,
                water_features=water_features,
                environmental_score=environmental_score,
                green_space_index=green_space_index,
                air_quality_estimate=air_quality_estimate
            )
            
        except Exception as e:
            logger.error(f"Erro coletando dados ambientais: {str(e)}")
            return self._create_empty_environmental_metrics()
    
    def _analyze_microclimate(self, result, property_data: PropertyData, radius: int) -> MicroclimateMetrics:
        """Analisar fatores de microclima"""
        climate_factors = []
        
        # 1. Cobertura arbórea
        trees = []
        tree_areas = []
        
        for node in result.nodes:
            if node.tags.get('natural') == 'tree':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                trees.append(distance)
        
        for way in result.ways:
            if way.tags.get('natural') in ['tree_row', 'wood'] or way.tags.get('landuse') in ['forest', 'grass', 'meadow']:
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    tree_areas.append(distance)
        
        # Score de cobertura arbórea
        tree_coverage_score = self._calculate_tree_coverage_score(trees, tree_areas, radius)
        
        if trees or tree_areas:
            climate_factors.append(MicroclimateFactor(
                factor_type="tree_coverage",
                distance=min(trees + tree_areas) if trees or tree_areas else radius,
                impact_score=tree_coverage_score,
                description=f"Cobertura arbórea: {len(trees)} árvores individuais, {len(tree_areas)} áreas verdes"
            ))
        
        # 2. Proximidade à água
        water_bodies = []
        for way in result.ways:
            if way.tags.get('waterway') or way.tags.get('natural') == 'water':
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    water_bodies.append(distance)
        
        water_proximity_score = self._calculate_water_proximity_score(water_bodies)
        
        if water_bodies:
            climate_factors.append(MicroclimateFactor(
                factor_type="water_proximity",
                distance=min(water_bodies),
                impact_score=water_proximity_score,
                description=f"Proximidade à água: {len(water_bodies)} corpos d'água"
            ))
        
        # 3. Risco de ilha de calor
        buildings = []
        for way in result.ways:
            if 'building' in way.tags:
                buildings.append(way)
        
        heat_island_risk = self._calculate_heat_island_risk(buildings, property_data, radius)
        
        climate_factors.append(MicroclimateFactor(
            factor_type="heat_island",
            distance=0,
            impact_score=100 - heat_island_risk,
            description=f"Densidade de edifícios: {len(buildings)} construções na área"
        ))
        
        # 4. Corredores de vento
        major_streets = []
        for way in result.ways:
            if way.tags.get('highway') in ['primary', 'secondary', 'tertiary']:
                major_streets.append(way)
        
        wind_corridor_score = self._calculate_wind_corridor_score(major_streets, buildings, property_data)
        
        climate_factors.append(MicroclimateFactor(
            factor_type="wind_corridors",
            distance=0,
            impact_score=wind_corridor_score,
            description=f"Corredores de vento: {len(major_streets)} vias principais"
        ))
        
        # Score geral de microclima
        overall_climate_score = (
            tree_coverage_score * 0.3 +
            water_proximity_score * 0.25 +
            (100 - heat_island_risk) * 0.25 +
            wind_corridor_score * 0.2
        )
        
        return MicroclimateMetrics(
            tree_coverage_score=tree_coverage_score,
            water_proximity_score=water_proximity_score,
            heat_island_risk=heat_island_risk,
            wind_corridor_score=wind_corridor_score,
            overall_climate_score=overall_climate_score,
            climate_factors=climate_factors
        )
    
    def _analyze_water_features(self, result, property_data: PropertyData) -> WaterFeaturesMetrics:
        """Analisar recursos hídricos"""
        water_features = []
        
        # Processar corpos d'água (ways)
        for way in result.ways:
            if way.tags.get('waterway') or way.tags.get('natural') == 'water':
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    # Determinar tipo
                    feature_type = way.tags.get('waterway', way.tags.get('natural', 'water'))
                    
                    # Estimar tamanho baseado no número de nós
                    if len(way.nodes) > 20:
                        size_category = "large"
                    elif len(way.nodes) > 10:
                        size_category = "medium"
                    else:
                        size_category = "small"
                    
                    # Calcular valores
                    recreational_value = self._calculate_recreational_value(feature_type, size_category, distance)
                    flood_risk = self._calculate_flood_risk(feature_type, distance)
                    
                    water_features.append(WaterFeature(
                        id=str(way.id),
                        name=way.tags.get('name', feature_type.title()),
                        feature_type=feature_type,
                        distance=distance,
                        size_category=size_category,
                        recreational_value=recreational_value,
                        flood_risk=flood_risk
                    ))
        
        # Processar fontes (nodes)
        for node in result.nodes:
            if node.tags.get('amenity') == 'fountain':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                water_features.append(WaterFeature(
                    id=str(node.id),
                    name=node.tags.get('name', 'Fonte'),
                    feature_type='fountain',
                    distance=distance,
                    size_category='small',
                    recreational_value=30,  # Valor estético
                    flood_risk=0
                ))
        
        # Calcular métricas
        landscape_quality_score = self._calculate_landscape_quality(water_features)
        recreational_water_score = self._calculate_recreational_water_score(water_features)
        flood_risk_score = self._calculate_flood_risk_score(water_features)
        humidity_impact_score = self._calculate_humidity_impact(water_features)
        
        overall_water_score = (
            landscape_quality_score * 0.3 +
            recreational_water_score * 0.3 +
            humidity_impact_score * 0.25 +
            (100 - flood_risk_score) * 0.15
        )
        
        return WaterFeaturesMetrics(
            water_features=water_features,
            landscape_quality_score=landscape_quality_score,
            recreational_water_score=recreational_water_score,
            flood_risk_score=flood_risk_score,
            humidity_impact_score=humidity_impact_score,
            overall_water_score=overall_water_score
        )
    
    def _calculate_tree_coverage_score(self, trees: List[float], tree_areas: List[float], radius: int) -> float:
        """Calcular score de cobertura arbórea"""
        if not trees and not tree_areas:
            return 0
        
        # Score baseado em proximidade e densidade
        proximity_score = 0
        if trees:
            closest_tree = min(trees)
            proximity_score += max(0, 50 - (closest_tree / 10))  # 50 pontos max por proximidade
        
        if tree_areas:
            closest_area = min(tree_areas)
            proximity_score += max(0, 50 - (closest_area / 20))  # Áreas verdes têm alcance maior
        
        # Score baseado em densidade
        density_score = min(len(trees + tree_areas) * 5, 50)  # 50 pontos max por densidade
        
        return min(proximity_score + density_score, 100)
    
    def _calculate_water_proximity_score(self, water_bodies: List[float]) -> float:
        """Calcular score de proximidade à água"""
        if not water_bodies:
            return 0
        
        closest_water = min(water_bodies)
        
        # Score decai exponencialmente com a distância
        if closest_water <= 100:
            return 100
        elif closest_water <= 300:
            return 80
        elif closest_water <= 500:
            return 60
        elif closest_water <= 1000:
            return 40
        else:
            return max(0, 20 - (closest_water - 1000) / 100)
    
    def _calculate_heat_island_risk(self, buildings: List, property_data: PropertyData, radius: int) -> float:
        """Calcular risco de ilha de calor urbano"""
        if not buildings:
            return 0
        
        area_km2 = math.pi * (radius / 1000) ** 2
        building_density = len(buildings) / area_km2
        
        # Normalizar para 0-100 (assumindo 2000 edifícios/km² como máximo urbano)
        risk_score = min((building_density / 2000) * 100, 100)
        
        return risk_score
    
    def _calculate_wind_corridor_score(self, major_streets: List, buildings: List, property_data: PropertyData) -> float:
        """Calcular score de corredores de vento"""
        if not major_streets:
            return 30  # Score médio sem vias principais
        
        # Mais vias principais = melhores corredores de vento
        street_score = min(len(major_streets) * 15, 60)
        
        # Densidade de edifícios reduz eficiência dos corredores
        building_penalty = min(len(buildings) / 20, 20)
        
        return max(0, street_score - building_penalty + 20)  # Base de 20 pontos
    
    def _calculate_recreational_value(self, feature_type: str, size_category: str, distance: float) -> float:
        """Calcular valor recreativo do recurso hídrico"""
        base_values = {
            'river': 70,
            'stream': 50,
            'canal': 40,
            'water': 80,  # Lagos, represas
            'fountain': 30
        }
        
        size_multipliers = {
            'large': 1.3,
            'medium': 1.0,
            'small': 0.7
        }
        
        base_value = base_values.get(feature_type, 40)
        size_multiplier = size_multipliers.get(size_category, 1.0)
        
        # Penalidade por distância
        distance_penalty = min(distance / 20, 30)
        
        return max(0, base_value * size_multiplier - distance_penalty)
    
    def _calculate_flood_risk(self, feature_type: str, distance: float) -> float:
        """Calcular risco de enchente"""
        risk_factors = {
            'river': 80,
            'stream': 60,
            'canal': 70,
            'water': 30,  # Lagos têm menor risco
            'fountain': 0
        }
        
        base_risk = risk_factors.get(feature_type, 30)
        
        # Risco diminui com distância
        if distance > 500:
            return 0
        elif distance > 200:
            return base_risk * 0.3
        elif distance > 100:
            return base_risk * 0.6
        else:
            return base_risk
    
    def _calculate_landscape_quality(self, water_features: List[WaterFeature]) -> float:
        """Calcular qualidade da paisagem"""
        if not water_features:
            return 0
        
        # Score baseado em variedade e qualidade dos recursos
        quality_score = 0
        feature_types = set()
        
        for feature in water_features:
            if feature.distance <= 1000:  # Apenas recursos próximos
                feature_types.add(feature.feature_type)
                
                # Valor baseado no tipo e tamanho
                if feature.feature_type in ['water', 'river']:
                    quality_score += 25
                elif feature.feature_type == 'stream':
                    quality_score += 15
                elif feature.feature_type == 'fountain':
                    quality_score += 10
        
        # Bônus por diversidade
        diversity_bonus = len(feature_types) * 10
        
        return min(quality_score + diversity_bonus, 100)
    
    def _calculate_recreational_water_score(self, water_features: List[WaterFeature]) -> float:
        """Calcular score de recreação aquática"""
        if not water_features:
            return 0
        
        recreational_value = sum(feature.recreational_value for feature in water_features if feature.distance <= 2000)
        return min(recreational_value, 100)
    
    def _calculate_flood_risk_score(self, water_features: List[WaterFeature]) -> float:
        """Calcular score de risco de enchente"""
        if not water_features:
            return 0
        
        max_risk = max(feature.flood_risk for feature in water_features)
        return max_risk
    
    def _calculate_humidity_impact(self, water_features: List[WaterFeature]) -> float:
        """Calcular impacto na umidade local"""
        if not water_features:
            return 0
        
        humidity_impact = 0
        for feature in water_features:
            if feature.distance <= 500:  # Apenas recursos muito próximos afetam umidade
                impact = 30 - (feature.distance / 20)  # Decai com distância
                if feature.feature_type in ['water', 'river']:
                    impact *= 1.5  # Corpos d'água maiores têm mais impacto
                humidity_impact += max(0, impact)
        
        return min(humidity_impact, 100)
    
    def _calculate_environmental_score(self, microclimate: MicroclimateMetrics, water_features: WaterFeaturesMetrics) -> float:
        """Calcular score ambiental geral"""
        return (microclimate.overall_climate_score * 0.6 + water_features.overall_water_score * 0.4)
    
    def _calculate_green_space_index(self, result, property_data: PropertyData, radius: int) -> float:
        """Calcular índice de espaços verdes"""
        green_areas = 0
        total_area = math.pi * (radius ** 2)  # Área total em m²
        
        for way in result.ways:
            if (way.tags.get('leisure') in ['park', 'garden'] or 
                way.tags.get('landuse') in ['forest', 'grass', 'meadow'] or
                way.tags.get('natural') in ['wood']):
                # Estimativa simples de área baseada no número de nós
                estimated_area = len(way.nodes) * 100  # m² por nó
                green_areas += estimated_area
        
        green_percentage = (green_areas / total_area) * 100
        return min(green_percentage * 2, 100)  # Multiplicador para normalizar
    
    def _estimate_air_quality(self, result, property_data: PropertyData) -> float:
        """Estimar qualidade do ar"""
        # Fatores positivos
        green_count = 0
        water_count = 0
        
        # Fatores negativos
        major_road_count = 0
        
        for way in result.ways:
            if (way.tags.get('landuse') in ['forest', 'grass'] or 
                way.tags.get('leisure') == 'park'):
                green_count += 1
            elif way.tags.get('waterway') or way.tags.get('natural') == 'water':
                water_count += 1
            elif way.tags.get('highway') in ['primary', 'trunk', 'motorway']:
                major_road_count += 1
        
        # Score baseado em fatores
        positive_score = min((green_count * 5) + (water_count * 3), 70)
        negative_score = min(major_road_count * 10, 40)
        
        air_quality = max(30, positive_score - negative_score + 30)  # Base de 30
        return min(air_quality, 100)
    
    def _create_empty_environmental_metrics(self) -> EnvironmentalMetrics:
        """Criar métricas ambientais vazias em caso de erro"""
        return EnvironmentalMetrics(
            microclimate=MicroclimateMetrics(
                tree_coverage_score=0,
                water_proximity_score=0,
                heat_island_risk=50,
                wind_corridor_score=30,
                overall_climate_score=20,
                climate_factors=[]
            ),
            water_features=WaterFeaturesMetrics(
                water_features=[],
                landscape_quality_score=0,
                recreational_water_score=0,
                flood_risk_score=0,
                humidity_impact_score=0,
                overall_water_score=0
            ),
            environmental_score=20,
            green_space_index=0,
            air_quality_estimate=30
        ) 