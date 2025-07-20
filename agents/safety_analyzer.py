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
class EmergencyService:
    """Serviço de emergência"""
    id: str
    name: str
    service_type: str  # hospital, police, fire_station, emergency
    distance: float
    response_time_estimate: float  # minutos
    capacity_estimate: str  # small, medium, large
    accessibility: str

@dataclass
class SafetyFeature:
    """Característica de segurança"""
    id: str
    feature_type: str  # street_lamp, surveillance, police, visibility
    distance: float
    coverage_radius: float
    effectiveness_score: float

@dataclass
class EmergencyMetrics:
    """Métricas de cobertura de emergência"""
    emergency_services: List[EmergencyService]
    response_time_score: float
    coverage_completeness: float
    service_diversity: float
    accessibility_score: float
    overall_emergency_score: float

@dataclass
class CrimePreventionMetrics:
    """Métricas de prevenção ao crime"""
    safety_features: List[SafetyFeature]
    lighting_coverage: float
    surveillance_coverage: float
    police_presence: float
    visibility_score: float
    overall_prevention_score: float

@dataclass
class SafetyMetrics:
    """Métricas de segurança completas"""
    emergency_metrics: EmergencyMetrics
    crime_prevention_metrics: CrimePreventionMetrics
    overall_safety_score: float
    vulnerability_assessment: Dict[str, float]
    safety_recommendations: List[str]

class SafetyEmergencyAnalyzer:
    """Agente especializado em análise de segurança e emergência"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_safety_query(self, lat: float, lon: float, radius: int = 2000) -> str:
        """Construir query para dados de segurança e emergência"""
        query = f"""
        [out:json][timeout:30];
        (
          // Serviços de emergência
          node["amenity"="hospital"](around:{radius},{lat},{lon});
          way["amenity"="hospital"](around:{radius},{lat},{lon});
          node["amenity"="clinic"](around:{radius},{lat},{lon});
          node["amenity"="police"](around:{radius},{lat},{lon});
          way["amenity"="police"](around:{radius},{lat},{lon});
          node["amenity"="fire_station"](around:{radius},{lat},{lon});
          way["amenity"="fire_station"](around:{radius},{lat},{lon});
          node["emergency"](around:{radius},{lat},{lon});
          
          // Características de segurança
          node["highway"="street_lamp"](around:{radius//2},{lat},{lon});
          node["man_made"="surveillance"](around:{radius//2},{lat},{lon});
          node["surveillance"](around:{radius//2},{lat},{lon});
          
          // Vias para análise de visibilidade
          way["highway"~"^(primary|secondary|tertiary|residential|pedestrian)$"](around:{radius//2},{lat},{lon});
          
          // Áreas que afetam segurança
          way["landuse"="industrial"](around:{radius},{lat},{lon});
          way["landuse"="commercial"](around:{radius},{lat},{lon});
          way["amenity"="parking"](around:{radius//2},{lat},{lon});
          
          // Locais de risco
          node["amenity"="bar"](around:{radius//2},{lat},{lon});
          node["amenity"="nightclub"](around:{radius//2},{lat},{lon});
          way["leisure"="park"](around:{radius//2},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def analyze_safety(self, property_data: PropertyData, radius: int = 2000) -> SafetyMetrics:
        """Analisar segurança e emergência"""
        try:
            logger.info(f"Analisando segurança para {property_data.address} (raio: {radius}m)")
            query = self._build_safety_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar serviços de emergência
            emergency_metrics = self._analyze_emergency_services(result, property_data)
            
            # Analisar prevenção ao crime
            crime_prevention_metrics = self._analyze_crime_prevention(result, property_data)
            
            # Calcular score geral de segurança
            overall_safety_score = self._calculate_overall_safety_score(emergency_metrics, crime_prevention_metrics)
            
            # Avaliação de vulnerabilidade
            vulnerability_assessment = self._assess_vulnerabilities(result, property_data, emergency_metrics, crime_prevention_metrics)
            
            # Recomendações de segurança
            safety_recommendations = self._generate_safety_recommendations(emergency_metrics, crime_prevention_metrics, vulnerability_assessment)
            
            return SafetyMetrics(
                emergency_metrics=emergency_metrics,
                crime_prevention_metrics=crime_prevention_metrics,
                overall_safety_score=overall_safety_score,
                vulnerability_assessment=vulnerability_assessment,
                safety_recommendations=safety_recommendations
            )
            
        except Exception as e:
            logger.error(f"Erro analisando segurança: {str(e)}")
            return self._create_empty_safety_metrics()
    
    def _analyze_emergency_services(self, result, property_data: PropertyData) -> EmergencyMetrics:
        """Analisar serviços de emergência"""
        emergency_services = []
        
        # Processar hospitais e clínicas
        for element in result.nodes + result.ways:
            amenity = element.tags.get('amenity')
            
            if amenity in ['hospital', 'clinic']:
                # Obter coordenadas
                if hasattr(element, 'lat') and hasattr(element, 'lon'):
                    lat, lon = element.lat, element.lon
                elif hasattr(element, 'center_lat') and hasattr(element, 'center_lon'):
                    lat, lon = element.center_lat, element.center_lon
                elif hasattr(element, 'nodes') and len(element.nodes) >= 2:
                    lat = np.mean([node.lat for node in element.nodes])
                    lon = np.mean([node.lon for node in element.nodes])
                else:
                    continue
                
                distance = geodesic((property_data.lat, property_data.lon), (lat, lon)).meters
                
                # Estimar tempo de resposta (baseado na distância)
                if amenity == 'hospital':
                    base_time = 8  # minutos
                    capacity = 'large'
                else:  # clinic
                    base_time = 15
                    capacity = 'small'
                
                response_time = base_time + (distance / 1000) * 2  # +2 min por km
                
                emergency_services.append(EmergencyService(
                    id=str(element.id),
                    name=element.tags.get('name', amenity.title()),
                    service_type=amenity,
                    distance=distance,
                    response_time_estimate=response_time,
                    capacity_estimate=capacity,
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar polícia
        for element in result.nodes + result.ways:
            if element.tags.get('amenity') == 'police':
                # Obter coordenadas
                if hasattr(element, 'lat') and hasattr(element, 'lon'):
                    lat, lon = element.lat, element.lon
                elif hasattr(element, 'center_lat') and hasattr(element, 'center_lon'):
                    lat, lon = element.center_lat, element.center_lon
                elif hasattr(element, 'nodes') and len(element.nodes) >= 2:
                    lat = np.mean([node.lat for node in element.nodes])
                    lon = np.mean([node.lon for node in element.nodes])
                else:
                    continue
                
                distance = geodesic((property_data.lat, property_data.lon), (lat, lon)).meters
                response_time = 5 + (distance / 1000) * 1.5  # Polícia responde mais rápido
                
                emergency_services.append(EmergencyService(
                    id=str(element.id),
                    name=element.tags.get('name', 'Delegacia de Polícia'),
                    service_type='police',
                    distance=distance,
                    response_time_estimate=response_time,
                    capacity_estimate='medium',
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar bombeiros
        for element in result.nodes + result.ways:
            if element.tags.get('amenity') == 'fire_station':
                # Obter coordenadas
                if hasattr(element, 'lat') and hasattr(element, 'lon'):
                    lat, lon = element.lat, element.lon
                elif hasattr(element, 'center_lat') and hasattr(element, 'center_lon'):
                    lat, lon = element.center_lat, element.center_lon
                elif hasattr(element, 'nodes') and len(element.nodes) >= 2:
                    lat = np.mean([node.lat for node in element.nodes])
                    lon = np.mean([node.lon for node in element.nodes])
                else:
                    continue
                
                distance = geodesic((property_data.lat, property_data.lon), (lat, lon)).meters
                response_time = 6 + (distance / 1000) * 1.8  # Bombeiros têm tempo médio
                
                emergency_services.append(EmergencyService(
                    id=str(element.id),
                    name=element.tags.get('name', 'Corpo de Bombeiros'),
                    service_type='fire_station',
                    distance=distance,
                    response_time_estimate=response_time,
                    capacity_estimate='medium',
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar outros serviços de emergência
        for node in result.nodes:
            if 'emergency' in node.tags:
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                emergency_type = node.tags.get('emergency', 'emergency')
                
                emergency_services.append(EmergencyService(
                    id=str(node.id),
                    name=node.tags.get('name', f'Serviço de Emergência ({emergency_type})'),
                    service_type='emergency',
                    distance=distance,
                    response_time_estimate=10 + (distance / 1000) * 2,
                    capacity_estimate='small',
                    accessibility='unknown'
                ))
        
        # Calcular métricas
        response_time_score = self._calculate_response_time_score(emergency_services)
        coverage_completeness = self._calculate_coverage_completeness(emergency_services)
        service_diversity = self._calculate_service_diversity(emergency_services)
        accessibility_score = self._calculate_emergency_accessibility(emergency_services)
        
        overall_emergency_score = (
            response_time_score * 0.35 +
            coverage_completeness * 0.25 +
            service_diversity * 0.25 +
            accessibility_score * 0.15
        )
        
        return EmergencyMetrics(
            emergency_services=emergency_services,
            response_time_score=response_time_score,
            coverage_completeness=coverage_completeness,
            service_diversity=service_diversity,
            accessibility_score=accessibility_score,
            overall_emergency_score=overall_emergency_score
        )
    
    def _analyze_crime_prevention(self, result, property_data: PropertyData) -> CrimePreventionMetrics:
        """Analisar características de prevenção ao crime"""
        safety_features = []
        
        # Iluminação pública
        for node in result.nodes:
            if node.tags.get('highway') == 'street_lamp':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                safety_features.append(SafetyFeature(
                    id=str(node.id),
                    feature_type='street_lamp',
                    distance=distance,
                    coverage_radius=30,  # raio de iluminação típico
                    effectiveness_score=20
                ))
        
        # Sistemas de vigilância
        for node in result.nodes:
            tags = node.tags
            if (tags.get('man_made') == 'surveillance' or 
                'surveillance' in tags):
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                # Tipo de vigilância
                surveillance_type = tags.get('surveillance:type', 'camera')
                if surveillance_type == 'camera':
                    coverage_radius = 50
                    effectiveness = 40
                else:
                    coverage_radius = 30
                    effectiveness = 25
                
                safety_features.append(SafetyFeature(
                    id=str(node.id),
                    feature_type='surveillance',
                    distance=distance,
                    coverage_radius=coverage_radius,
                    effectiveness_score=effectiveness
                ))
        
        # Presença policial (já coletada nos serviços de emergência)
        police_stations = [node for node in result.nodes + result.ways 
                          if node.tags.get('amenity') == 'police']
        
        for station in police_stations:
            if hasattr(station, 'lat') and hasattr(station, 'lon'):
                lat, lon = station.lat, station.lon
            elif hasattr(station, 'center_lat') and hasattr(station, 'center_lon'):
                lat, lon = station.center_lat, station.center_lon
            elif hasattr(station, 'nodes') and len(station.nodes) >= 2:
                lat = np.mean([node.lat for node in station.nodes])
                lon = np.mean([node.lon for node in station.nodes])
            else:
                continue
            
            distance = geodesic((property_data.lat, property_data.lon), (lat, lon)).meters
            
            safety_features.append(SafetyFeature(
                id=str(station.id),
                feature_type='police',
                distance=distance,
                coverage_radius=1000,  # área de influência policial
                effectiveness_score=60
            ))
        
        # Visibilidade das ruas (baseada na largura e tipo de via)
        major_streets = []
        for way in result.ways:
            highway_type = way.tags.get('highway')
            if highway_type in ['primary', 'secondary', 'tertiary']:
                if len(way.nodes) >= 2:
                    center_lat = np.mean([node.lat for node in way.nodes])
                    center_lon = np.mean([node.lon for node in way.nodes])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    if distance <= 200:  # Apenas ruas muito próximas afetam visibilidade
                        safety_features.append(SafetyFeature(
                            id=str(way.id),
                            feature_type='visibility',
                            distance=distance,
                            coverage_radius=100,
                            effectiveness_score=15
                        ))
        
        # Calcular métricas
        lighting_coverage = self._calculate_lighting_coverage(safety_features, property_data)
        surveillance_coverage = self._calculate_surveillance_coverage(safety_features, property_data)
        police_presence = self._calculate_police_presence(safety_features, property_data)
        visibility_score = self._calculate_visibility_score(safety_features, result, property_data)
        
        overall_prevention_score = (
            lighting_coverage * 0.3 +
            surveillance_coverage * 0.25 +
            police_presence * 0.25 +
            visibility_score * 0.2
        )
        
        return CrimePreventionMetrics(
            safety_features=safety_features,
            lighting_coverage=lighting_coverage,
            surveillance_coverage=surveillance_coverage,
            police_presence=police_presence,
            visibility_score=visibility_score,
            overall_prevention_score=overall_prevention_score
        )
    
    def _calculate_response_time_score(self, emergency_services: List[EmergencyService]) -> float:
        """Calcular score de tempo de resposta"""
        if not emergency_services:
            return 0
        
        # Encontrar o serviço mais próximo de cada tipo
        service_types = ['hospital', 'police', 'fire_station']
        best_times = {}
        
        for service_type in service_types:
            relevant_services = [s for s in emergency_services if s.service_type == service_type]
            if relevant_services:
                best_times[service_type] = min(s.response_time_estimate for s in relevant_services)
        
        if not best_times:
            return 0
        
        # Score baseado nos melhores tempos (menor tempo = melhor score)
        total_score = 0
        for service_type, time in best_times.items():
            if time <= 5:
                score = 100
            elif time <= 10:
                score = 80
            elif time <= 15:
                score = 60
            elif time <= 20:
                score = 40
            else:
                score = max(0, 20 - (time - 20))
            
            total_score += score
        
        return total_score / len(best_times)
    
    def _calculate_coverage_completeness(self, emergency_services: List[EmergencyService]) -> float:
        """Calcular completude da cobertura de emergência"""
        service_types = set(s.service_type for s in emergency_services)
        essential_services = {'hospital', 'police', 'fire_station'}
        
        coverage = len(service_types & essential_services) / len(essential_services)
        return coverage * 100
    
    def _calculate_service_diversity(self, emergency_services: List[EmergencyService]) -> float:
        """Calcular diversidade de serviços"""
        service_types = set(s.service_type for s in emergency_services)
        max_diversity = 5  # hospital, clinic, police, fire_station, emergency
        
        return min(len(service_types) / max_diversity * 100, 100)
    
    def _calculate_emergency_accessibility(self, emergency_services: List[EmergencyService]) -> float:
        """Calcular acessibilidade dos serviços de emergência"""
        if not emergency_services:
            return 0
        
        accessible_count = sum(1 for s in emergency_services if s.accessibility == 'yes')
        unknown_count = sum(1 for s in emergency_services if s.accessibility == 'unknown')
        
        # Assumir 50% dos "unknown" como acessíveis
        estimated_accessible = accessible_count + (unknown_count * 0.5)
        
        return (estimated_accessible / len(emergency_services)) * 100
    
    def _calculate_lighting_coverage(self, safety_features: List[SafetyFeature], property_data: PropertyData) -> float:
        """Calcular cobertura de iluminação"""
        street_lamps = [f for f in safety_features if f.feature_type == 'street_lamp']
        
        if not street_lamps:
            return 0
        
        # Calcular área coberta por iluminação
        covered_area = 0
        for lamp in street_lamps:
            if lamp.distance <= 200:  # Apenas lâmpadas próximas
                # Área de cobertura diminui com a distância
                effective_radius = max(0, lamp.coverage_radius - lamp.distance * 0.1)
                covered_area += math.pi * (effective_radius ** 2)
        
        # Área total considerada (200m radius)
        total_area = math.pi * (200 ** 2)
        coverage = min((covered_area / total_area) * 100, 100)
        
        return coverage
    
    def _calculate_surveillance_coverage(self, safety_features: List[SafetyFeature], property_data: PropertyData) -> float:
        """Calcular cobertura de vigilância"""
        surveillance = [f for f in safety_features if f.feature_type == 'surveillance']
        
        if not surveillance:
            return 0
        
        # Score baseado na proximidade e efetividade
        total_score = 0
        for camera in surveillance:
            if camera.distance <= 150:  # Alcance efetivo de câmeras
                proximity_factor = max(0, 1 - camera.distance / 150)
                total_score += camera.effectiveness_score * proximity_factor
        
        return min(total_score, 100)
    
    def _calculate_police_presence(self, safety_features: List[SafetyFeature], property_data: PropertyData) -> float:
        """Calcular presença policial"""
        police_features = [f for f in safety_features if f.feature_type == 'police']
        
        if not police_features:
            return 0
        
        # Score baseado na proximidade da delegacia mais próxima
        closest_distance = min(f.distance for f in police_features)
        
        if closest_distance <= 500:
            return 100
        elif closest_distance <= 1000:
            return 80
        elif closest_distance <= 1500:
            return 60
        elif closest_distance <= 2000:
            return 40
        else:
            return 20
    
    def _calculate_visibility_score(self, safety_features: List[SafetyFeature], result, property_data: PropertyData) -> float:
        """Calcular score de visibilidade"""
        visibility_features = [f for f in safety_features if f.feature_type == 'visibility']
        
        # Score base por proximidade a ruas principais
        base_score = min(len(visibility_features) * 20, 60)
        
        # Bônus por áreas abertas (parques próximos, mas não muito próximos)
        parks = [way for way in result.ways if way.tags.get('leisure') == 'park']
        park_bonus = 0
        
        for park in parks:
            if len(park.nodes) >= 3:
                center_lat = np.mean([node.lat for node in park.nodes])
                center_lon = np.mean([node.lon for node in park.nodes])
                distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                
                if 100 <= distance <= 300:  # Distância ideal - próximo mas não dentro
                    park_bonus += 20
        
        return min(base_score + park_bonus, 100)
    
    def _calculate_overall_safety_score(self, emergency_metrics: EmergencyMetrics, crime_prevention_metrics: CrimePreventionMetrics) -> float:
        """Calcular score geral de segurança"""
        return (emergency_metrics.overall_emergency_score * 0.6 + crime_prevention_metrics.overall_prevention_score * 0.4)
    
    def _assess_vulnerabilities(self, result, property_data: PropertyData, emergency_metrics: EmergencyMetrics, crime_prevention_metrics: CrimePreventionMetrics) -> Dict[str, float]:
        """Avaliar vulnerabilidades de segurança"""
        vulnerabilities = {}
        
        # Vulnerabilidade por tempo de resposta
        if emergency_metrics.response_time_score < 50:
            vulnerabilities['slow_emergency_response'] = 100 - emergency_metrics.response_time_score
        
        # Vulnerabilidade por falta de iluminação
        if crime_prevention_metrics.lighting_coverage < 40:
            vulnerabilities['poor_lighting'] = 100 - crime_prevention_metrics.lighting_coverage
        
        # Vulnerabilidade por falta de vigilância
        if crime_prevention_metrics.surveillance_coverage < 30:
            vulnerabilities['inadequate_surveillance'] = 100 - crime_prevention_metrics.surveillance_coverage
        
        # Vulnerabilidade por isolamento
        if crime_prevention_metrics.visibility_score < 40:
            vulnerabilities['isolated_location'] = 100 - crime_prevention_metrics.visibility_score
        
        # Vulnerabilidade por locais de risco próximos
        bars_clubs = [node for node in result.nodes if node.tags.get('amenity') in ['bar', 'nightclub']]
        nearby_risk_locations = 0
        
        for location in bars_clubs:
            distance = geodesic((property_data.lat, property_data.lon), (location.lat, location.lon)).meters
            if distance <= 200:
                nearby_risk_locations += 1
        
        if nearby_risk_locations > 2:
            vulnerabilities['high_risk_proximity'] = min(nearby_risk_locations * 20, 80)
        
        return vulnerabilities
    
    def _generate_safety_recommendations(self, emergency_metrics: EmergencyMetrics, crime_prevention_metrics: CrimePreventionMetrics, vulnerabilities: Dict[str, float]) -> List[str]:
        """Gerar recomendações de segurança"""
        recommendations = []
        
        # Recomendações baseadas em emergência
        if emergency_metrics.response_time_score < 60:
            recommendations.append("Considere ter um kit de primeiros socorros bem equipado devido aos tempos de resposta mais longos")
        
        if emergency_metrics.coverage_completeness < 80:
            recommendations.append("Verifique a disponibilidade de serviços de emergência privados na região")
        
        # Recomendações baseadas em prevenção
        if crime_prevention_metrics.lighting_coverage < 50:
            recommendations.append("Instale iluminação adicional na propriedade e considere sensores de movimento")
        
        if crime_prevention_metrics.surveillance_coverage < 40:
            recommendations.append("Considere instalar sistema de segurança com câmeras")
        
        if crime_prevention_metrics.police_presence < 50:
            recommendations.append("Considere contratar segurança privada ou serviços de monitoramento")
        
        # Recomendações baseadas em vulnerabilidades
        if 'isolated_location' in vulnerabilities:
            recommendations.append("Evite caminhar sozinho(a) durante a noite e considere aplicativos de segurança")
        
        if 'high_risk_proximity' in vulnerabilities:
            recommendations.append("Esteja atento ao movimento noturno e considere rotas alternativas")
        
        # Recomendações gerais se score geral for baixo
        overall_score = (emergency_metrics.overall_emergency_score + crime_prevention_metrics.overall_prevention_score) / 2
        
        if overall_score < 50:
            recommendations.append("Considere seguro residencial com cobertura ampliada")
            recommendations.append("Mantenha contatos de emergência sempre atualizados e acessíveis")
        
        return recommendations
    
    def _create_empty_safety_metrics(self) -> SafetyMetrics:
        """Criar métricas de segurança vazias em caso de erro"""
        return SafetyMetrics(
            emergency_metrics=EmergencyMetrics([], 30, 40, 30, 50, 35),
            crime_prevention_metrics=CrimePreventionMetrics([], 40, 30, 40, 50, 40),
            overall_safety_score=37,
            vulnerability_assessment={},
            safety_recommendations=["Recomenda-se uma avaliação detalhada de segurança da região"]
        ) 