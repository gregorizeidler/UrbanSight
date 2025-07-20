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
class DigitalInfrastructure:
    """Infraestrutura digital"""
    id: str
    name: str
    infrastructure_type: str  # internet_cafe, wifi_hotspot, tech_service
    distance: float
    access_type: str  # public, paid, private
    technology_level: str  # basic, advanced, modern

@dataclass
class AccessibilityFeature:
    """Característica de acessibilidade"""
    id: str
    name: str
    feature_type: str  # ramp, elevator, tactile_paving, accessible_entrance
    distance: float
    accessibility_category: str  # mobility, visual, hearing, general
    compliance_level: str  # basic, good, excellent

@dataclass
class NightLifeVenue:
    """Local de vida noturna"""
    id: str
    name: str
    venue_type: str  # bar, nightclub, late_night_service, 24h_service
    distance: float
    operating_hours: str
    venue_category: str  # entertainment, food, service, convenience
    safety_rating: str

@dataclass
class DigitalInfrastructureMetrics:
    """Métricas de infraestrutura digital"""
    digital_infrastructure: List[DigitalInfrastructure]
    internet_accessibility: float
    digital_services_score: float
    connectivity_coverage: float
    digital_divide_risk: float
    overall_digital_score: float

@dataclass
class UniversalAccessibilityMetrics:
    """Métricas de acessibilidade universal"""
    accessibility_features: List[AccessibilityFeature]
    mobility_accessibility: float
    visual_accessibility: float
    infrastructure_compliance: float
    inclusivity_score: float
    overall_accessibility_score: float

@dataclass
class NightLifeMetrics:
    """Métricas de vida noturna"""
    nightlife_venues: List[NightLifeVenue]
    entertainment_variety: float
    late_night_services: float
    night_safety_score: float
    convenience_24h: float
    overall_nightlife_score: float

@dataclass
class SpecialFeaturesMetrics:
    """Métricas de características especiais completas"""
    digital_infrastructure_metrics: DigitalInfrastructureMetrics
    universal_accessibility_metrics: UniversalAccessibilityMetrics
    nightlife_metrics: NightLifeMetrics
    innovation_index: float
    social_inclusion_score: float
    overall_special_features_score: float

class SpecialFeaturesAnalyzer:
    """Agente especializado em análise de características especiais"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_special_features_query(self, lat: float, lon: float, radius: int = 1500) -> str:
        """Construir query para características especiais"""
        query = f"""
        [out:json][timeout:30];
        (
          // Infraestrutura digital
          node["amenity"="internet_cafe"](around:{radius},{lat},{lon});
          node["internet_access"](around:{radius},{lat},{lon});
          node["shop"~"^(computer|electronics|mobile_phone)$"](around:{radius},{lat},{lon});
          
          // Acessibilidade
          node["wheelchair"="yes"](around:{radius},{lat},{lon});
          way["wheelchair"="yes"](around:{radius},{lat},{lon});
          node["tactile_paving"="yes"](around:{radius},{lat},{lon});
          way["tactile_paving"="yes"](around:{radius},{lat},{lon});
          node["kerb"="lowered"](around:{radius},{lat},{lon});
          
          // Infraestrutura de acessibilidade
          node["highway"="elevator"](around:{radius},{lat},{lon});
          node["man_made"="ramp"](around:{radius},{lat},{lon});
          way["ramp"="yes"](around:{radius},{lat},{lon});
          
          // Vida noturna e serviços 24h
          node["amenity"~"^(bar|nightclub|pub)$"](around:{radius},{lat},{lon});
          node["shop"="convenience"]["opening_hours"~"24/7|Mo-Su"](around:{radius},{lat},{lon});
          node["amenity"~"^(fuel|pharmacy|hospital|police)$"]["opening_hours"~"24/7|Mo-Su"](around:{radius},{lat},{lon});
          
          // Estabelecimentos com horários estendidos
          node["opening_hours"~"2[0-3]:|0[0-5]:"](around:{radius},{lat},{lon});
          node["amenity"~"^(restaurant|fast_food|cafe)$"]["opening_hours"~"2[0-3]:|0[0-5]:"](around:{radius},{lat},{lon});
          
          // Transporte noturno
          node["public_transport"]["service"~"night"](around:{radius},{lat},{lon});
          
          // Serviços especializados
          node["amenity"~"^(coworking_space|hackerspace)$"](around:{radius},{lat},{lon});
          node["office"="coworking"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def analyze_special_features(self, property_data: PropertyData, radius: int = 1500) -> SpecialFeaturesMetrics:
        """Analisar características especiais"""
        try:
            logger.info(f"Analisando características especiais para {property_data.address} (raio: {radius}m)")
            query = self._build_special_features_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar infraestrutura digital
            digital_metrics = self._analyze_digital_infrastructure(result, property_data)
            
            # Analisar acessibilidade universal
            accessibility_metrics = self._analyze_universal_accessibility(result, property_data)
            
            # Analisar vida noturna
            nightlife_metrics = self._analyze_nightlife(result, property_data)
            
            # Calcular scores gerais
            innovation_index = self._calculate_innovation_index(digital_metrics, accessibility_metrics)
            social_inclusion_score = self._calculate_social_inclusion(accessibility_metrics, nightlife_metrics)
            overall_special_features_score = self._calculate_overall_special_features_score(digital_metrics, accessibility_metrics, nightlife_metrics)
            
            return SpecialFeaturesMetrics(
                digital_infrastructure_metrics=digital_metrics,
                universal_accessibility_metrics=accessibility_metrics,
                nightlife_metrics=nightlife_metrics,
                innovation_index=innovation_index,
                social_inclusion_score=social_inclusion_score,
                overall_special_features_score=overall_special_features_score
            )
            
        except Exception as e:
            logger.error(f"Erro analisando características especiais: {str(e)}")
            return self._create_empty_special_features_metrics()
    
    def _analyze_digital_infrastructure(self, result, property_data: PropertyData) -> DigitalInfrastructureMetrics:
        """Analisar infraestrutura digital"""
        digital_infrastructure = []
        
        # Processar internet cafés
        for node in result.nodes:
            if node.tags.get('amenity') == 'internet_cafe':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                digital_infrastructure.append(DigitalInfrastructure(
                    id=str(node.id),
                    name=node.tags.get('name', 'Internet Café'),
                    infrastructure_type='internet_cafe',
                    distance=distance,
                    access_type='paid',
                    technology_level='basic'
                ))
        
        # Processar pontos de WiFi
        for element in result.nodes + result.ways:
            if element.tags.get('internet_access'):
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
                
                # Determinar tipo de acesso
                access_type = element.tags.get('internet_access:fee', 'unknown')
                if access_type == 'no':
                    access_type = 'public'
                elif access_type == 'yes':
                    access_type = 'paid'
                else:
                    access_type = 'unknown'
                
                digital_infrastructure.append(DigitalInfrastructure(
                    id=str(element.id),
                    name=element.tags.get('name', 'Ponto WiFi'),
                    infrastructure_type='wifi_hotspot',
                    distance=distance,
                    access_type=access_type,
                    technology_level='modern'
                ))
        
        # Processar lojas de tecnologia
        for node in result.nodes:
            shop = node.tags.get('shop')
            if shop in ['computer', 'electronics', 'mobile_phone']:
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                digital_infrastructure.append(DigitalInfrastructure(
                    id=str(node.id),
                    name=node.tags.get('name', f'Loja de {shop.title()}'),
                    infrastructure_type='tech_service',
                    distance=distance,
                    access_type='paid',
                    technology_level='advanced'
                ))
        
        # Processar coworkings e hackerspaces
        for element in result.nodes + result.ways:
            amenity = element.tags.get('amenity')
            office = element.tags.get('office')
            
            if amenity in ['coworking_space', 'hackerspace'] or office == 'coworking':
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
                
                space_type = amenity if amenity else office
                
                digital_infrastructure.append(DigitalInfrastructure(
                    id=str(element.id),
                    name=element.tags.get('name', space_type.replace('_', ' ').title()),
                    infrastructure_type='innovation_space',
                    distance=distance,
                    access_type='paid',
                    technology_level='advanced'
                ))
        
        # Calcular métricas
        internet_accessibility = self._calculate_internet_accessibility(digital_infrastructure)
        digital_services_score = self._calculate_digital_services_score(digital_infrastructure)
        connectivity_coverage = self._calculate_connectivity_coverage(digital_infrastructure)
        digital_divide_risk = self._calculate_digital_divide_risk(digital_infrastructure)
        
        overall_digital_score = (
            internet_accessibility * 0.3 +
            digital_services_score * 0.25 +
            connectivity_coverage * 0.25 +
            (100 - digital_divide_risk) * 0.2
        )
        
        return DigitalInfrastructureMetrics(
            digital_infrastructure=digital_infrastructure,
            internet_accessibility=internet_accessibility,
            digital_services_score=digital_services_score,
            connectivity_coverage=connectivity_coverage,
            digital_divide_risk=digital_divide_risk,
            overall_digital_score=overall_digital_score
        )
    
    def _analyze_universal_accessibility(self, result, property_data: PropertyData) -> UniversalAccessibilityMetrics:
        """Analisar acessibilidade universal"""
        accessibility_features = []
        
        # Processar características de acessibilidade para cadeirantes
        for element in result.nodes + result.ways:
            if element.tags.get('wheelchair') == 'yes':
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
                
                accessibility_features.append(AccessibilityFeature(
                    id=str(element.id),
                    name=element.tags.get('name', 'Local Acessível'),
                    feature_type='accessible_entrance',
                    distance=distance,
                    accessibility_category='mobility',
                    compliance_level='good'
                ))
        
        # Processar piso tátil
        for element in result.nodes + result.ways:
            if element.tags.get('tactile_paving') == 'yes':
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
                
                accessibility_features.append(AccessibilityFeature(
                    id=str(element.id),
                    name='Piso Tátil',
                    feature_type='tactile_paving',
                    distance=distance,
                    accessibility_category='visual',
                    compliance_level='excellent'
                ))
        
        # Processar meio-fio rebaixado
        for node in result.nodes:
            if node.tags.get('kerb') == 'lowered':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                accessibility_features.append(AccessibilityFeature(
                    id=str(node.id),
                    name='Meio-fio Rebaixado',
                    feature_type='lowered_kerb',
                    distance=distance,
                    accessibility_category='mobility',
                    compliance_level='good'
                ))
        
        # Processar elevadores
        for node in result.nodes:
            if node.tags.get('highway') == 'elevator':
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                accessibility_features.append(AccessibilityFeature(
                    id=str(node.id),
                    name='Elevador',
                    feature_type='elevator',
                    distance=distance,
                    accessibility_category='mobility',
                    compliance_level='excellent'
                ))
        
        # Processar rampas
        for element in result.nodes + result.ways:
            if (element.tags.get('man_made') == 'ramp' or 
                element.tags.get('ramp') == 'yes'):
                
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
                
                accessibility_features.append(AccessibilityFeature(
                    id=str(element.id),
                    name='Rampa de Acessibilidade',
                    feature_type='ramp',
                    distance=distance,
                    accessibility_category='mobility',
                    compliance_level='excellent'
                ))
        
        # Calcular métricas
        mobility_accessibility = self._calculate_mobility_accessibility(accessibility_features)
        visual_accessibility = self._calculate_visual_accessibility(accessibility_features)
        infrastructure_compliance = self._calculate_infrastructure_compliance(accessibility_features)
        inclusivity_score = self._calculate_inclusivity_score(accessibility_features)
        
        overall_accessibility_score = (
            mobility_accessibility * 0.4 +
            visual_accessibility * 0.3 +
            infrastructure_compliance * 0.2 +
            inclusivity_score * 0.1
        )
        
        return UniversalAccessibilityMetrics(
            accessibility_features=accessibility_features,
            mobility_accessibility=mobility_accessibility,
            visual_accessibility=visual_accessibility,
            infrastructure_compliance=infrastructure_compliance,
            inclusivity_score=inclusivity_score,
            overall_accessibility_score=overall_accessibility_score
        )
    
    def _analyze_nightlife(self, result, property_data: PropertyData) -> NightLifeMetrics:
        """Analisar vida noturna"""
        nightlife_venues = []
        
        # Processar bares e casas noturnas
        for node in result.nodes:
            amenity = node.tags.get('amenity')
            
            if amenity in ['bar', 'nightclub', 'pub']:
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                # Avaliar segurança baseado em localização e tipo
                safety_rating = self._assess_venue_safety(node.tags, amenity)
                
                nightlife_venues.append(NightLifeVenue(
                    id=str(node.id),
                    name=node.tags.get('name', amenity.title()),
                    venue_type=amenity,
                    distance=distance,
                    operating_hours=node.tags.get('opening_hours', 'night_hours'),
                    venue_category='entertainment',
                    safety_rating=safety_rating
                ))
        
        # Processar serviços 24h
        for element in result.nodes + result.ways:
            amenity = element.tags.get('amenity')
            shop = element.tags.get('shop')
            hours = element.tags.get('opening_hours', '')
            
            if ('24/7' in hours or 'Mo-Su' in hours) and (amenity or shop):
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
                
                # Categorizar serviço
                if shop == 'convenience':
                    venue_category = 'convenience'
                    venue_type = '24h_convenience'
                elif amenity in ['fuel', 'pharmacy']:
                    venue_category = 'service'
                    venue_type = f'24h_{amenity}'
                elif amenity in ['hospital', 'police']:
                    venue_category = 'emergency'
                    venue_type = f'24h_{amenity}'
                else:
                    venue_category = 'service'
                    venue_type = '24h_service'
                
                nightlife_venues.append(NightLifeVenue(
                    id=str(element.id),
                    name=element.tags.get('name', venue_type.replace('_', ' ').title()),
                    venue_type=venue_type,
                    distance=distance,
                    operating_hours='24/7',
                    venue_category=venue_category,
                    safety_rating='medium'
                ))
        
        # Processar estabelecimentos com horários estendidos
        for element in result.nodes + result.ways:
            hours = element.tags.get('opening_hours', '')
            amenity = element.tags.get('amenity')
            
            if any(hour in hours for hour in ['20:', '21:', '22:', '23:']) and amenity in ['restaurant', 'fast_food', 'cafe']:
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
                
                nightlife_venues.append(NightLifeVenue(
                    id=str(element.id),
                    name=element.tags.get('name', f'{amenity.title()} Noturno'),
                    venue_type='late_night_food',
                    distance=distance,
                    operating_hours=hours,
                    venue_category='food',
                    safety_rating='medium'
                ))
        
        # Calcular métricas
        entertainment_variety = self._calculate_entertainment_variety(nightlife_venues)
        late_night_services = self._calculate_late_night_services(nightlife_venues)
        night_safety_score = self._calculate_night_safety_score(nightlife_venues)
        convenience_24h = self._calculate_24h_convenience(nightlife_venues)
        
        overall_nightlife_score = (
            entertainment_variety * 0.3 +
            late_night_services * 0.25 +
            convenience_24h * 0.25 +
            night_safety_score * 0.2
        )
        
        return NightLifeMetrics(
            nightlife_venues=nightlife_venues,
            entertainment_variety=entertainment_variety,
            late_night_services=late_night_services,
            night_safety_score=night_safety_score,
            convenience_24h=convenience_24h,
            overall_nightlife_score=overall_nightlife_score
        )
    
    def _calculate_internet_accessibility(self, infrastructure: List[DigitalInfrastructure]) -> float:
        """Calcular acessibilidade à internet"""
        if not infrastructure:
            return 0
        
        # Pontos de acesso próximos
        nearby_access = [inf for inf in infrastructure if inf.distance <= 800]
        
        if not nearby_access:
            return 0
        
        # Score baseado na proximidade e tipo de acesso
        access_score = 0
        for inf in nearby_access:
            if inf.access_type == 'public':
                access_score += 30
            elif inf.access_type == 'paid':
                access_score += 20
            else:
                access_score += 10
        
        return min(access_score, 100)
    
    def _calculate_digital_services_score(self, infrastructure: List[DigitalInfrastructure]) -> float:
        """Calcular score de serviços digitais"""
        if not infrastructure:
            return 0
        
        # Contar tipos únicos de infraestrutura
        types = set(inf.infrastructure_type for inf in infrastructure if inf.distance <= 1500)
        
        # Score baseado na variedade
        diversity_score = len(types) * 25
        
        return min(diversity_score, 100)
    
    def _calculate_connectivity_coverage(self, infrastructure: List[DigitalInfrastructure]) -> float:
        """Calcular cobertura de conectividade"""
        wifi_hotspots = [inf for inf in infrastructure if inf.infrastructure_type == 'wifi_hotspot' and inf.distance <= 1000]
        
        if not wifi_hotspots:
            return 0
        
        # Score baseado na densidade de hotspots WiFi
        coverage_score = min(len(wifi_hotspots) * 20, 100)
        
        return coverage_score
    
    def _calculate_digital_divide_risk(self, infrastructure: List[DigitalInfrastructure]) -> float:
        """Calcular risco de exclusão digital"""
        # Maior risco quando há poucos serviços digitais acessíveis
        public_access = [inf for inf in infrastructure if inf.access_type == 'public' and inf.distance <= 1200]
        tech_services = [inf for inf in infrastructure if inf.infrastructure_type == 'tech_service' and inf.distance <= 1500]
        
        if len(public_access) >= 3 and len(tech_services) >= 2:
            return 20  # Baixo risco
        elif len(public_access) >= 1 or len(tech_services) >= 1:
            return 50  # Risco médio
        else:
            return 80  # Alto risco
    
    def _calculate_mobility_accessibility(self, features: List[AccessibilityFeature]) -> float:
        """Calcular acessibilidade de mobilidade"""
        mobility_features = [f for f in features if f.accessibility_category == 'mobility' and f.distance <= 800]
        
        if not mobility_features:
            return 0
        
        # Score baseado na quantidade e qualidade
        mobility_score = 0
        for feature in mobility_features:
            if feature.compliance_level == 'excellent':
                mobility_score += 25
            elif feature.compliance_level == 'good':
                mobility_score += 15
            else:
                mobility_score += 10
        
        return min(mobility_score, 100)
    
    def _calculate_visual_accessibility(self, features: List[AccessibilityFeature]) -> float:
        """Calcular acessibilidade visual"""
        visual_features = [f for f in features if f.accessibility_category == 'visual' and f.distance <= 600]
        
        if not visual_features:
            return 0
        
        # Score baseado na presença de piso tátil
        visual_score = min(len(visual_features) * 30, 100)
        
        return visual_score
    
    def _calculate_infrastructure_compliance(self, features: List[AccessibilityFeature]) -> float:
        """Calcular conformidade da infraestrutura"""
        if not features:
            return 0
        
        nearby_features = [f for f in features if f.distance <= 1000]
        
        if not nearby_features:
            return 0
        
        # Score baseado no nível de conformidade
        excellent_count = sum(1 for f in nearby_features if f.compliance_level == 'excellent')
        good_count = sum(1 for f in nearby_features if f.compliance_level == 'good')
        
        compliance_score = (excellent_count * 20) + (good_count * 10)
        
        return min(compliance_score, 100)
    
    def _calculate_inclusivity_score(self, features: List[AccessibilityFeature]) -> float:
        """Calcular score de inclusividade"""
        # Variedade de categorias de acessibilidade
        categories = set(f.accessibility_category for f in features if f.distance <= 1000)
        
        # Score baseado na variedade
        inclusivity_score = len(categories) * 35  # mobility, visual, hearing
        
        return min(inclusivity_score, 100)
    
    def _assess_venue_safety(self, tags: Dict[str, str], venue_type: str) -> str:
        """Avaliar segurança do local"""
        safety_indicators = 0
        
        # Indicadores positivos
        if tags.get('surveillance') == 'yes':
            safety_indicators += 1
        if tags.get('security') == 'yes':
            safety_indicators += 1
        if venue_type in ['pub', 'bar'] and 'restaurant' in tags.get('amenity', ''):
            safety_indicators += 1  # Estabelecimentos mistos são mais seguros
        
        if safety_indicators >= 2:
            return 'high'
        elif safety_indicators == 1:
            return 'medium'
        else:
            return 'basic'
    
    def _calculate_entertainment_variety(self, venues: List[NightLifeVenue]) -> float:
        """Calcular variedade de entretenimento"""
        entertainment_venues = [v for v in venues if v.venue_category == 'entertainment' and v.distance <= 2000]
        
        if not entertainment_venues:
            return 0
        
        # Score baseado na variedade de tipos
        venue_types = set(v.venue_type for v in entertainment_venues)
        variety_score = min(len(venue_types) * 35, 100)
        
        return variety_score
    
    def _calculate_late_night_services(self, venues: List[NightLifeVenue]) -> float:
        """Calcular serviços noturnos"""
        late_night_venues = [v for v in venues if 'late_night' in v.venue_type and v.distance <= 1500]
        
        if not late_night_venues:
            return 0
        
        # Score baseado na quantidade
        services_score = min(len(late_night_venues) * 25, 100)
        
        return services_score
    
    def _calculate_night_safety_score(self, venues: List[NightLifeVenue]) -> float:
        """Calcular score de segurança noturna"""
        nearby_venues = [v for v in venues if v.distance <= 1000]
        
        if not nearby_venues:
            return 70  # Score neutro
        
        # Avaliar segurança baseada nos locais
        high_safety_count = sum(1 for v in nearby_venues if v.safety_rating == 'high')
        medium_safety_count = sum(1 for v in nearby_venues if v.safety_rating == 'medium')
        
        safety_score = (high_safety_count * 30) + (medium_safety_count * 20) + 40
        
        return min(safety_score, 100)
    
    def _calculate_24h_convenience(self, venues: List[NightLifeVenue]) -> float:
        """Calcular conveniência 24h"""
        convenience_venues = [v for v in venues if v.venue_category in ['convenience', 'service'] and v.distance <= 1200]
        
        if not convenience_venues:
            return 0
        
        # Score baseado na quantidade e proximidade
        convenience_score = min(len(convenience_venues) * 20, 100)
        
        return convenience_score
    
    def _calculate_innovation_index(self, digital_metrics: DigitalInfrastructureMetrics, accessibility_metrics: UniversalAccessibilityMetrics) -> float:
        """Calcular índice de inovação"""
        # Combinar infraestrutura digital e acessibilidade
        digital_innovation = digital_metrics.overall_digital_score
        accessibility_innovation = accessibility_metrics.overall_accessibility_score
        
        innovation_index = (digital_innovation * 0.7 + accessibility_innovation * 0.3)
        
        return innovation_index
    
    def _calculate_social_inclusion(self, accessibility_metrics: UniversalAccessibilityMetrics, nightlife_metrics: NightLifeMetrics) -> float:
        """Calcular inclusão social"""
        # Combinar acessibilidade e opções noturnas
        accessibility_inclusion = accessibility_metrics.overall_accessibility_score
        nightlife_inclusion = nightlife_metrics.overall_nightlife_score
        
        social_inclusion_score = (accessibility_inclusion * 0.6 + nightlife_inclusion * 0.4)
        
        return social_inclusion_score
    
    def _calculate_overall_special_features_score(self, digital_metrics: DigitalInfrastructureMetrics, accessibility_metrics: UniversalAccessibilityMetrics, nightlife_metrics: NightLifeMetrics) -> float:
        """Calcular score geral de características especiais"""
        return (
            digital_metrics.overall_digital_score * 0.4 +
            accessibility_metrics.overall_accessibility_score * 0.35 +
            nightlife_metrics.overall_nightlife_score * 0.25
        )
    
    def _create_empty_special_features_metrics(self) -> SpecialFeaturesMetrics:
        """Criar métricas de características especiais vazias em caso de erro"""
        return SpecialFeaturesMetrics(
            digital_infrastructure_metrics=DigitalInfrastructureMetrics([], 0, 0, 0, 50, 5),
            universal_accessibility_metrics=UniversalAccessibilityMetrics([], 0, 0, 0, 0, 0),
            nightlife_metrics=NightLifeMetrics([], 0, 0, 70, 0, 17),
            innovation_index=3,
            social_inclusion_score=10,
            overall_special_features_score=8
        ) 