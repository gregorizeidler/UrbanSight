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
class Building:
    """Informações de edifício"""
    id: str
    distance: float
    building_type: str
    levels: int
    height: float
    area_estimate: float

@dataclass
class NoiseSource:
    """Fonte de ruído"""
    id: str
    source_type: str  # highway, railway, aeroway
    distance: float
    noise_level: int  # dB estimado
    traffic_category: str  # low, medium, high

@dataclass
class InfrastructureElement:
    """Elemento de infraestrutura urbana"""
    id: str
    element_type: str  # power, communication, utility
    distance: float
    visual_impact: str  # low, medium, high

@dataclass
class BuildingMetrics:
    """Métricas de densidade e altura de edifícios"""
    buildings: List[Building]
    building_density: float
    average_height: float
    height_variance: float
    verticalization_potential: float
    architectural_diversity: float
    urban_compactness: float

@dataclass
class NoiseMetrics:
    """Métricas de poluição sonora"""
    noise_sources: List[NoiseSource]
    estimated_noise_level: int
    noise_zones: Dict[str, float]  # quiet, moderate, noisy
    peak_hours_impact: float
    noise_barriers_present: bool
    overall_noise_score: float

@dataclass
class InfrastructureMetrics:
    """Métricas de infraestrutura urbana"""
    infrastructure_elements: List[InfrastructureElement]
    power_infrastructure_density: float
    communication_infrastructure: float
    visual_quality_score: float
    infrastructure_modernity: float
    overall_infrastructure_score: float

@dataclass
class UrbanMetrics:
    """Métricas urbanas completas"""
    building_metrics: BuildingMetrics
    noise_metrics: NoiseMetrics
    infrastructure_metrics: InfrastructureMetrics
    urban_development_score: float
    livability_score: float
    future_development_potential: float

class UrbanInfrastructureAnalyzer:
    """Agente especializado em análise de infraestrutura urbana"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_urban_query(self, lat: float, lon: float, radius: int = 1200) -> str:
        """Construir query para dados urbanos"""
        query = f"""
        [out:json][timeout:30];
        (
          // Edifícios
          way["building"](around:{radius},{lat},{lon});
          relation["building"](around:{radius},{lat},{lon});
          
          // Vias para análise de ruído
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|living_street)$"](around:{radius},{lat},{lon});
          
          // Ferrovias
          way["railway"~"^(rail|light_rail|subway|tram)$"](around:{radius},{lat},{lon});
          
          // Aeroportos
          way["aeroway"~"^(runway|taxiway)$"](around:{radius},{lat},{lon});
          
          // Infraestrutura elétrica
          node["power"~"^(pole|tower)$"](around:{radius},{lat},{lon});
          way["power"="line"](around:{radius},{lat},{lon});
          node["man_made"="mast"](around:{radius},{lat},{lon});
          
          // Telecomunicações
          node["communication"="tower"](around:{radius},{lat},{lon});
          node["man_made"="tower"](around:{radius},{lat},{lon});
          
          // Outras infraestruturas
          node["man_made"~"^(water_tower|chimney|antenna)$"](around:{radius},{lat},{lon});
          way["man_made"="pipeline"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def analyze_urban_infrastructure(self, property_data: PropertyData, radius: int = 1200) -> UrbanMetrics:
        """Analisar infraestrutura urbana"""
        try:
            logger.info(f"Analisando infraestrutura urbana para {property_data.address} (raio: {radius}m)")
            query = self._build_urban_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar edifícios
            building_metrics = self._analyze_buildings(result, property_data, radius)
            
            # Analisar ruído
            noise_metrics = self._analyze_noise_pollution(result, property_data)
            
            # Analisar infraestrutura
            infrastructure_metrics = self._analyze_infrastructure(result, property_data)
            
            # Calcular scores gerais
            urban_development_score = self._calculate_urban_development_score(building_metrics, infrastructure_metrics)
            livability_score = self._calculate_livability_score(building_metrics, noise_metrics, infrastructure_metrics)
            future_development_potential = self._calculate_development_potential(building_metrics, infrastructure_metrics)
            
            return UrbanMetrics(
                building_metrics=building_metrics,
                noise_metrics=noise_metrics,
                infrastructure_metrics=infrastructure_metrics,
                urban_development_score=urban_development_score,
                livability_score=livability_score,
                future_development_potential=future_development_potential
            )
            
        except Exception as e:
            logger.error(f"Erro analisando infraestrutura urbana: {str(e)}")
            return self._create_empty_urban_metrics()
    
    def _analyze_buildings(self, result, property_data: PropertyData, radius: int) -> BuildingMetrics:
        """Analisar densidade e características dos edifícios"""
        buildings = []
        
        for way in result.ways:
            if 'building' in way.tags:
                if len(way.nodes) >= 3:  # Polígono válido
                    # Calcular centro do edifício
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    # Extrair características
                    tags = way.tags
                    building_type = tags.get('building', 'yes')
                    
                    # Processar níveis
                    levels = 1  # Padrão
                    if tags.get('building:levels'):
                        try:
                            levels = int(tags['building:levels'])
                        except:
                            levels = 1
                    
                    # Processar altura
                    height = levels * 3.0  # Estimativa padrão: 3m por andar
                    if tags.get('height'):
                        try:
                            height_str = tags['height'].replace('m', '').replace(' ', '')
                            height = float(height_str)
                        except:
                            height = levels * 3.0
                    
                    # Estimar área do edifício
                    area_estimate = len(way.nodes) * 50  # Estimativa grosseira
                    
                    buildings.append(Building(
                        id=str(way.id),
                        distance=distance,
                        building_type=building_type,
                        levels=levels,
                        height=height,
                        area_estimate=area_estimate
                    ))
        
        # Calcular métricas
        area_km2 = math.pi * (radius / 1000) ** 2
        building_density = len(buildings) / area_km2
        
        if buildings:
            heights = [b.height for b in buildings]
            average_height = np.mean(heights)
            height_variance = np.var(heights)
            
            # Diversidade arquitetônica
            building_types = set(b.building_type for b in buildings)
            architectural_diversity = min(len(building_types) * 10, 100)
            
            # Potencial de verticalização
            low_buildings = sum(1 for b in buildings if b.levels <= 2)
            verticalization_potential = (low_buildings / len(buildings)) * 100
            
            # Compacidade urbana
            total_area = sum(b.area_estimate for b in buildings)
            urban_compactness = min((total_area / (area_km2 * 1000000)) * 100, 100)
            
        else:
            average_height = 0
            height_variance = 0
            architectural_diversity = 0
            verticalization_potential = 0
            urban_compactness = 0
        
        return BuildingMetrics(
            buildings=buildings,
            building_density=building_density,
            average_height=average_height,
            height_variance=height_variance,
            verticalization_potential=verticalization_potential,
            architectural_diversity=architectural_diversity,
            urban_compactness=urban_compactness
        )
    
    def _analyze_noise_pollution(self, result, property_data: PropertyData) -> NoiseMetrics:
        """Analisar poluição sonora"""
        noise_sources = []
        
        # Analisar vias (principal fonte de ruído)
        for way in result.ways:
            highway_type = way.tags.get('highway')
            if highway_type:
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    # Calcular nível de ruído baseado no tipo de via
                    noise_level, traffic_category = self._estimate_traffic_noise(highway_type)
                    
                    # Aplicar atenuação por distância
                    attenuated_noise = self._calculate_noise_attenuation(noise_level, distance)
                    
                    noise_sources.append(NoiseSource(
                        id=str(way.id),
                        source_type='highway',
                        distance=distance,
                        noise_level=attenuated_noise,
                        traffic_category=traffic_category
                    ))
        
        # Analisar ferrovias
        for way in result.ways:
            railway_type = way.tags.get('railway')
            if railway_type:
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    # Nível de ruído ferroviário
                    if railway_type in ['rail', 'light_rail']:
                        base_noise = 70
                    elif railway_type in ['subway', 'tram']:
                        base_noise = 60
                    else:
                        base_noise = 65
                    
                    attenuated_noise = self._calculate_noise_attenuation(base_noise, distance)
                    
                    noise_sources.append(NoiseSource(
                        id=str(way.id),
                        source_type='railway',
                        distance=distance,
                        noise_level=attenuated_noise,
                        traffic_category='medium'
                    ))
        
        # Analisar aeroportos
        for way in result.ways:
            aeroway_type = way.tags.get('aeroway')
            if aeroway_type in ['runway', 'taxiway']:
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    base_noise = 80  # Aeroportos são muito ruidosos
                    attenuated_noise = self._calculate_noise_attenuation(base_noise, distance)
                    
                    noise_sources.append(NoiseSource(
                        id=str(way.id),
                        source_type='aeroway',
                        distance=distance,
                        noise_level=attenuated_noise,
                        traffic_category='high'
                    ))
        
        # Calcular métricas de ruído
        if noise_sources:
            # Nível estimado de ruído (combinando fontes)
            nearby_sources = [s for s in noise_sources if s.distance <= 500]
            if nearby_sources:
                # Combinação logarítmica de fontes de ruído
                noise_levels = [10**(s.noise_level/10) for s in nearby_sources]
                combined_noise = 10 * math.log10(sum(noise_levels))
                estimated_noise_level = min(int(combined_noise), 100)
            else:
                estimated_noise_level = 35  # Ruído de fundo urbano
        else:
            estimated_noise_level = 35
        
        # Categorizar zonas de ruído
        if estimated_noise_level < 45:
            noise_zones = {"quiet": 80, "moderate": 20, "noisy": 0}
        elif estimated_noise_level < 60:
            noise_zones = {"quiet": 20, "moderate": 70, "noisy": 10}
        else:
            noise_zones = {"quiet": 0, "moderate": 30, "noisy": 70}
        
        # Impacto em horários de pico
        high_traffic_sources = [s for s in noise_sources if s.traffic_category == 'high' and s.distance <= 300]
        peak_hours_impact = min(len(high_traffic_sources) * 20, 100)
        
        # Presença de barreiras de ruído (edifícios altos podem atuar como barreiras)
        noise_barriers_present = False  # Simplificado por agora
        
        # Score geral de ruído (invertido - menor ruído = melhor score)
        overall_noise_score = max(0, 100 - estimated_noise_level)
        
        return NoiseMetrics(
            noise_sources=noise_sources,
            estimated_noise_level=estimated_noise_level,
            noise_zones=noise_zones,
            peak_hours_impact=peak_hours_impact,
            noise_barriers_present=noise_barriers_present,
            overall_noise_score=overall_noise_score
        )
    
    def _analyze_infrastructure(self, result, property_data: PropertyData) -> InfrastructureMetrics:
        """Analisar infraestrutura urbana"""
        infrastructure_elements = []
        
        # Infraestrutura elétrica
        for node in result.nodes:
            tags = node.tags
            
            if tags.get('power') in ['pole', 'tower'] or tags.get('man_made') == 'mast':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                # Determinar impacto visual
                if tags.get('power') == 'tower' or 'tower' in tags.get('man_made', ''):
                    visual_impact = 'high'
                else:
                    visual_impact = 'medium'
                
                infrastructure_elements.append(InfrastructureElement(
                    id=str(node.id),
                    element_type='power',
                    distance=distance,
                    visual_impact=visual_impact
                ))
        
        # Linhas de energia
        for way in result.ways:
            if way.tags.get('power') == 'line':
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    infrastructure_elements.append(InfrastructureElement(
                        id=str(way.id),
                        element_type='power_line',
                        distance=distance,
                        visual_impact='medium'
                    ))
        
        # Torres de comunicação
        for node in result.nodes:
            tags = node.tags
            
            if (tags.get('communication') == 'tower' or 
                tags.get('man_made') in ['tower', 'antenna']):
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                infrastructure_elements.append(InfrastructureElement(
                    id=str(node.id),
                    element_type='communication',
                    distance=distance,
                    visual_impact='high'
                ))
        
        # Outras infraestruturas
        for node in result.nodes:
            tags = node.tags
            
            if tags.get('man_made') in ['water_tower', 'chimney']:
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                infrastructure_elements.append(InfrastructureElement(
                    id=str(node.id),
                    element_type='utility',
                    distance=distance,
                    visual_impact='high'
                ))
        
        # Calcular métricas
        area_km2 = math.pi * (1.2) ** 2  # 1.2km radius
        
        power_elements = [e for e in infrastructure_elements if e.element_type.startswith('power')]
        power_infrastructure_density = len(power_elements) / area_km2
        
        comm_elements = [e for e in infrastructure_elements if e.element_type == 'communication']
        communication_infrastructure = len(comm_elements) / area_km2
        
        # Score de qualidade visual (menos infraestrutura visível = melhor)
        high_impact_elements = [e for e in infrastructure_elements if e.visual_impact == 'high' and e.distance <= 500]
        visual_quality_score = max(0, 100 - len(high_impact_elements) * 15)
        
        # Modernidade da infraestrutura (estimativa baseada na densidade)
        total_density = len(infrastructure_elements) / area_km2
        infrastructure_modernity = min(total_density * 10, 100)
        
        # Score geral de infraestrutura
        overall_infrastructure_score = (
            min(infrastructure_modernity, 80) * 0.4 +  # Cap para evitar over-score
            visual_quality_score * 0.6
        )
        
        return InfrastructureMetrics(
            infrastructure_elements=infrastructure_elements,
            power_infrastructure_density=power_infrastructure_density,
            communication_infrastructure=communication_infrastructure,
            visual_quality_score=visual_quality_score,
            infrastructure_modernity=infrastructure_modernity,
            overall_infrastructure_score=overall_infrastructure_score
        )
    
    def _estimate_traffic_noise(self, highway_type: str) -> Tuple[int, str]:
        """Estimar ruído de tráfego baseado no tipo de via"""
        noise_levels = {
            'motorway': (75, 'high'),
            'trunk': (70, 'high'),
            'primary': (65, 'medium'),
            'secondary': (60, 'medium'),
            'tertiary': (55, 'medium'),
            'residential': (45, 'low'),
            'living_street': (40, 'low')
        }
        
        return noise_levels.get(highway_type, (50, 'medium'))
    
    def _calculate_noise_attenuation(self, base_noise: int, distance: float) -> int:
        """Calcular atenuação do ruído com a distância"""
        if distance <= 10:
            return base_noise
        
        # Atenuação aproximada: -6 dB por duplicação da distância
        attenuation = 6 * math.log2(distance / 10)
        attenuated_noise = base_noise - attenuation
        
        return max(int(attenuated_noise), 30)  # Mínimo de 30 dB (ruído de fundo)
    
    def _calculate_urban_development_score(self, building_metrics: BuildingMetrics, infrastructure_metrics: InfrastructureMetrics) -> float:
        """Calcular score de desenvolvimento urbano"""
        # Densidade balanceada (nem muito baixa, nem muito alta)
        if building_metrics.building_density < 500:
            density_score = building_metrics.building_density / 10  # Favorecer densidades médias
        else:
            density_score = max(0, 100 - (building_metrics.building_density - 500) / 20)
        
        # Infraestrutura moderna
        infrastructure_score = infrastructure_metrics.infrastructure_modernity
        
        # Diversidade arquitetônica
        diversity_score = building_metrics.architectural_diversity
        
        return (density_score * 0.4 + infrastructure_score * 0.3 + diversity_score * 0.3)
    
    def _calculate_livability_score(self, building_metrics: BuildingMetrics, noise_metrics: NoiseMetrics, infrastructure_metrics: InfrastructureMetrics) -> float:
        """Calcular score de habitabilidade"""
        # Ruído é fator crítico
        noise_score = noise_metrics.overall_noise_score
        
        # Qualidade visual
        visual_score = infrastructure_metrics.visual_quality_score
        
        # Compacidade moderada (nem muito densa, nem muito esparsa)
        compactness = building_metrics.urban_compactness
        if compactness < 30:
            compactness_score = compactness * 2  # Favorecer compacidade moderada
        else:
            compactness_score = max(0, 100 - (compactness - 30) * 2)
        
        return (noise_score * 0.4 + visual_score * 0.3 + compactness_score * 0.3)
    
    def _calculate_development_potential(self, building_metrics: BuildingMetrics, infrastructure_metrics: InfrastructureMetrics) -> float:
        """Calcular potencial de desenvolvimento futuro"""
        # Alto potencial de verticalização
        vertical_potential = building_metrics.verticalization_potential
        
        # Infraestrutura moderna suporta desenvolvimento
        infrastructure_support = infrastructure_metrics.infrastructure_modernity
        
        # Baixa densidade atual = mais espaço para crescer
        density_potential = max(0, 100 - building_metrics.building_density / 10)
        
        return (vertical_potential * 0.4 + infrastructure_support * 0.3 + density_potential * 0.3)
    
    def _create_empty_urban_metrics(self) -> UrbanMetrics:
        """Criar métricas urbanas vazias em caso de erro"""
        return UrbanMetrics(
            building_metrics=BuildingMetrics([], 0, 0, 0, 0, 0, 0),
            noise_metrics=NoiseMetrics([], 35, {"quiet": 50, "moderate": 40, "noisy": 10}, 0, False, 65),
            infrastructure_metrics=InfrastructureMetrics([], 0, 0, 70, 30, 50),
            urban_development_score=30,
            livability_score=50,
            future_development_potential=40
        ) 