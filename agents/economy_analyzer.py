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
class EconomicEstablishment:
    """Estabelecimento econômico"""
    id: str
    name: str
    business_type: str  # shop, craft, office, service
    distance: float
    business_category: str
    opening_hours: str
    business_size: str  # small, medium, large
    accessibility: str

@dataclass
class CulturalVenue:
    """Local cultural"""
    id: str
    name: str
    venue_type: str  # museum, gallery, theatre, arts_centre
    distance: float
    cultural_category: str
    accessibility: str
    tourist_attraction: bool

@dataclass
class RetailFacility:
    """Facilidade de varejo"""
    id: str
    name: str
    retail_type: str  # shop, market, mall, service
    distance: float
    product_category: str
    opening_hours: str
    accessibility: str
    service_quality: str

@dataclass
class EconomyVitalityMetrics:
    """Métricas de vitalidade econômica"""
    economic_establishments: List[EconomicEstablishment]
    business_diversity: float
    small_business_density: float
    economic_activity_score: float
    employment_potential: float
    overall_economy_score: float

@dataclass
class CulturalRichnessMetrics:
    """Métricas de riqueza cultural"""
    cultural_venues: List[CulturalVenue]
    cultural_diversity: float
    artistic_variety: float
    cultural_accessibility: float
    tourism_appeal: float
    overall_cultural_score: float

@dataclass
class RetailAccessibilityMetrics:
    """Métricas de acessibilidade comercial"""
    retail_facilities: List[RetailFacility]
    shopping_convenience: float
    service_variety: float
    accessibility_score: float
    operating_hours_score: float
    overall_retail_score: float

@dataclass
class LocalEconomyMetrics:
    """Métricas de economia local completas"""
    economy_vitality_metrics: EconomyVitalityMetrics
    cultural_richness_metrics: CulturalRichnessMetrics
    retail_accessibility_metrics: RetailAccessibilityMetrics
    local_character_score: float
    economic_resilience_score: float
    overall_local_economy_score: float

class LocalEconomyAnalyzer:
    """Agente especializado em análise de economia local"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_economy_query(self, lat: float, lon: float, radius: int = 1500) -> str:
        """Construir query para dados de economia local"""
        query = f"""
        [out:json][timeout:30];
        (
          // Estabelecimentos comerciais
          node["shop"](around:{radius},{lat},{lon});
          way["shop"](around:{radius},{lat},{lon});
          
          // Artesanato e pequenos negócios
          node["craft"](around:{radius},{lat},{lon});
          way["craft"](around:{radius},{lat},{lon});
          
          // Escritórios e coworking
          node["office"](around:{radius},{lat},{lon});
          way["office"](around:{radius},{lat},{lon});
          
          // Mercados e feiras
          node["amenity"="marketplace"](around:{radius},{lat},{lon});
          way["amenity"="marketplace"](around:{radius},{lat},{lon});
          
          // Locais culturais
          node["tourism"~"^(museum|gallery|artwork)$"](around:{radius},{lat},{lon});
          way["tourism"~"^(museum|gallery)$"](around:{radius},{lat},{lon});
          node["amenity"~"^(theatre|arts_centre|community_centre)$"](around:{radius},{lat},{lon});
          way["amenity"~"^(theatre|arts_centre|community_centre)$"](around:{radius},{lat},{lon});
          
          // Patrimônio histórico
          node["historic"](around:{radius},{lat},{lon});
          way["historic"](around:{radius},{lat},{lon});
          
          // Serviços essenciais
          node["amenity"~"^(bank|post_office|pharmacy|clinic)$"](around:{radius},{lat},{lon});
          
          // Entretenimento
          node["amenity"~"^(cinema|nightclub|bar|restaurant)$"](around:{radius},{lat},{lon});
          
          // Supermercados e shopping
          node["shop"~"^(supermarket|mall|department_store)$"](around:{radius},{lat},{lon});
          way["shop"~"^(supermarket|mall|department_store)$"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def analyze_local_economy(self, property_data: PropertyData, radius: int = 1500) -> LocalEconomyMetrics:
        """Analisar economia local"""
        try:
            logger.info(f"Analisando economia local para {property_data.address} (raio: {radius}m)")
            query = self._build_economy_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar vitalidade econômica
            economy_metrics = self._analyze_economy_vitality(result, property_data)
            
            # Analisar riqueza cultural
            cultural_metrics = self._analyze_cultural_richness(result, property_data)
            
            # Analisar acessibilidade comercial
            retail_metrics = self._analyze_retail_accessibility(result, property_data)
            
            # Calcular scores gerais
            local_character_score = self._calculate_local_character(economy_metrics, cultural_metrics)
            economic_resilience_score = self._calculate_economic_resilience(economy_metrics, retail_metrics)
            overall_local_economy_score = self._calculate_overall_economy_score(economy_metrics, cultural_metrics, retail_metrics)
            
            return LocalEconomyMetrics(
                economy_vitality_metrics=economy_metrics,
                cultural_richness_metrics=cultural_metrics,
                retail_accessibility_metrics=retail_metrics,
                local_character_score=local_character_score,
                economic_resilience_score=economic_resilience_score,
                overall_local_economy_score=overall_local_economy_score
            )
            
        except Exception as e:
            logger.error(f"Erro analisando economia local: {str(e)}")
            return self._create_empty_economy_metrics()
    
    def _analyze_economy_vitality(self, result, property_data: PropertyData) -> EconomyVitalityMetrics:
        """Analisar vitalidade econômica"""
        economic_establishments = []
        
        # Processar lojas e comércios
        for element in result.nodes + result.ways:
            shop = element.tags.get('shop')
            
            if shop:
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
                
                # Categorizar tipo de negócio
                business_category = self._categorize_shop(shop)
                
                # Estimar tamanho do negócio
                if shop in ['supermarket', 'mall', 'department_store']:
                    business_size = 'large'
                elif shop in ['convenience', 'kiosk', 'newsagent']:
                    business_size = 'small'
                else:
                    business_size = 'medium'
                
                economic_establishments.append(EconomicEstablishment(
                    id=str(element.id),
                    name=element.tags.get('name', shop.title()),
                    business_type='shop',
                    distance=distance,
                    business_category=business_category,
                    opening_hours=element.tags.get('opening_hours', 'unknown'),
                    business_size=business_size,
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar artesanato e pequenos negócios
        for element in result.nodes + result.ways:
            craft = element.tags.get('craft')
            
            if craft:
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
                
                economic_establishments.append(EconomicEstablishment(
                    id=str(element.id),
                    name=element.tags.get('name', f'Artesanato - {craft.title()}'),
                    business_type='craft',
                    distance=distance,
                    business_category='artisanal',
                    opening_hours=element.tags.get('opening_hours', 'unknown'),
                    business_size='small',
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar escritórios
        for element in result.nodes + result.ways:
            office = element.tags.get('office')
            
            if office:
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
                
                # Estimar tamanho baseado no tipo
                if office in ['company', 'corporation']:
                    business_size = 'large'
                elif office in ['coworking', 'freelancer']:
                    business_size = 'small'
                else:
                    business_size = 'medium'
                
                economic_establishments.append(EconomicEstablishment(
                    id=str(element.id),
                    name=element.tags.get('name', f'Escritório - {office.title()}'),
                    business_type='office',
                    distance=distance,
                    business_category='professional',
                    opening_hours=element.tags.get('opening_hours', 'business_hours'),
                    business_size=business_size,
                    accessibility=element.tags.get('wheelchair', 'unknown')
                ))
        
        # Processar mercados
        for element in result.nodes + result.ways:
            if element.tags.get('amenity') == 'marketplace':
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
                
                economic_establishments.append(EconomicEstablishment(
                    id=str(element.id),
                    name=element.tags.get('name', 'Mercado/Feira'),
                    business_type='marketplace',
                    distance=distance,
                    business_category='food_market',
                    opening_hours=element.tags.get('opening_hours', 'market_hours'),
                    business_size='medium',
                    accessibility='partial'
                ))
        
        # Calcular métricas
        business_diversity = self._calculate_business_diversity(economic_establishments)
        small_business_density = self._calculate_small_business_density(economic_establishments)
        economic_activity_score = self._calculate_economic_activity(economic_establishments)
        employment_potential = self._calculate_employment_potential(economic_establishments)
        
        overall_economy_score = (
            business_diversity * 0.3 +
            small_business_density * 0.25 +
            economic_activity_score * 0.25 +
            employment_potential * 0.2
        )
        
        return EconomyVitalityMetrics(
            economic_establishments=economic_establishments,
            business_diversity=business_diversity,
            small_business_density=small_business_density,
            economic_activity_score=economic_activity_score,
            employment_potential=employment_potential,
            overall_economy_score=overall_economy_score
        )
    
    def _analyze_cultural_richness(self, result, property_data: PropertyData) -> CulturalRichnessMetrics:
        """Analisar riqueza cultural"""
        cultural_venues = []
        
        # Processar museus e galerias
        for element in result.nodes + result.ways:
            tourism = element.tags.get('tourism')
            
            if tourism in ['museum', 'gallery', 'artwork']:
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
                
                cultural_category = self._categorize_cultural_venue(tourism, element.tags)
                
                cultural_venues.append(CulturalVenue(
                    id=str(element.id),
                    name=element.tags.get('name', tourism.title()),
                    venue_type=tourism,
                    distance=distance,
                    cultural_category=cultural_category,
                    accessibility=element.tags.get('wheelchair', 'unknown'),
                    tourist_attraction=True
                ))
        
        # Processar teatros e centros artísticos
        for element in result.nodes + result.ways:
            amenity = element.tags.get('amenity')
            
            if amenity in ['theatre', 'arts_centre', 'community_centre']:
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
                
                if amenity == 'theatre':
                    cultural_category = 'performing_arts'
                elif amenity == 'arts_centre':
                    cultural_category = 'visual_arts'
                else:
                    cultural_category = 'community'
                
                cultural_venues.append(CulturalVenue(
                    id=str(element.id),
                    name=element.tags.get('name', amenity.replace('_', ' ').title()),
                    venue_type=amenity,
                    distance=distance,
                    cultural_category=cultural_category,
                    accessibility=element.tags.get('wheelchair', 'unknown'),
                    tourist_attraction=(amenity == 'theatre')
                ))
        
        # Processar patrimônio histórico
        for element in result.nodes + result.ways:
            historic = element.tags.get('historic')
            
            if historic:
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
                
                cultural_venues.append(CulturalVenue(
                    id=str(element.id),
                    name=element.tags.get('name', f'Patrimônio Histórico - {historic.title()}'),
                    venue_type='historic',
                    distance=distance,
                    cultural_category='heritage',
                    accessibility='unknown',
                    tourist_attraction=True
                ))
        
        # Calcular métricas
        cultural_diversity = self._calculate_cultural_diversity(cultural_venues)
        artistic_variety = self._calculate_artistic_variety(cultural_venues)
        cultural_accessibility = self._calculate_cultural_accessibility(cultural_venues)
        tourism_appeal = self._calculate_tourism_appeal(cultural_venues)
        
        overall_cultural_score = (
            cultural_diversity * 0.3 +
            artistic_variety * 0.25 +
            cultural_accessibility * 0.25 +
            tourism_appeal * 0.2
        )
        
        return CulturalRichnessMetrics(
            cultural_venues=cultural_venues,
            cultural_diversity=cultural_diversity,
            artistic_variety=artistic_variety,
            cultural_accessibility=cultural_accessibility,
            tourism_appeal=tourism_appeal,
            overall_cultural_score=overall_cultural_score
        )
    
    def _analyze_retail_accessibility(self, result, property_data: PropertyData) -> RetailAccessibilityMetrics:
        """Analisar acessibilidade comercial"""
        retail_facilities = []
        
        # Coletar facilidades de varejo já processadas
        for element in result.nodes + result.ways:
            shop = element.tags.get('shop')
            amenity = element.tags.get('amenity')
            
            if shop or amenity in ['bank', 'post_office', 'pharmacy']:
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
                
                if shop:
                    retail_type = 'shop'
                    product_category = self._categorize_shop(shop)
                    name = element.tags.get('name', shop.title())
                else:
                    retail_type = 'service'
                    product_category = 'essential_service'
                    name = element.tags.get('name', amenity.title())
                
                # Avaliar qualidade do serviço baseado em tags
                service_quality = self._assess_service_quality(element.tags)
                
                retail_facilities.append(RetailFacility(
                    id=str(element.id),
                    name=name,
                    retail_type=retail_type,
                    distance=distance,
                    product_category=product_category,
                    opening_hours=element.tags.get('opening_hours', 'unknown'),
                    accessibility=element.tags.get('wheelchair', 'unknown'),
                    service_quality=service_quality
                ))
        
        # Calcular métricas
        shopping_convenience = self._calculate_shopping_convenience(retail_facilities)
        service_variety = self._calculate_service_variety(retail_facilities)
        accessibility_score = self._calculate_retail_accessibility_score(retail_facilities)
        operating_hours_score = self._calculate_operating_hours_score(retail_facilities)
        
        overall_retail_score = (
            shopping_convenience * 0.3 +
            service_variety * 0.25 +
            accessibility_score * 0.25 +
            operating_hours_score * 0.2
        )
        
        return RetailAccessibilityMetrics(
            retail_facilities=retail_facilities,
            shopping_convenience=shopping_convenience,
            service_variety=service_variety,
            accessibility_score=accessibility_score,
            operating_hours_score=operating_hours_score,
            overall_retail_score=overall_retail_score
        )
    
    def _categorize_shop(self, shop: str) -> str:
        """Categorizar tipo de loja"""
        categories = {
            'food': ['supermarket', 'convenience', 'bakery', 'butcher', 'greengrocer'],
            'fashion': ['clothes', 'shoes', 'jewelry', 'beauty'],
            'home': ['furniture', 'hardware', 'electronics', 'appliance'],
            'health': ['pharmacy', 'optician', 'medical_supply'],
            'services': ['hairdresser', 'laundry', 'repair'],
            'specialty': ['books', 'music', 'art', 'sports']
        }
        
        for category, shops in categories.items():
            if shop in shops:
                return category
        
        return 'other'
    
    def _categorize_cultural_venue(self, venue_type: str, tags: Dict[str, str]) -> str:
        """Categorizar local cultural"""
        if venue_type == 'museum':
            museum_type = tags.get('museum', 'general')
            if 'art' in museum_type:
                return 'art_museum'
            elif 'history' in museum_type:
                return 'history_museum'
            else:
                return 'general_museum'
        elif venue_type == 'gallery':
            return 'art_gallery'
        elif venue_type == 'artwork':
            return 'public_art'
        else:
            return venue_type
    
    def _assess_service_quality(self, tags: Dict[str, str]) -> str:
        """Avaliar qualidade do serviço baseado em tags"""
        quality_indicators = 0
        
        # Indicadores positivos
        if tags.get('wheelchair') == 'yes':
            quality_indicators += 1
        if tags.get('internet_access') == 'yes':
            quality_indicators += 1
        if 'payment:' in str(tags):  # Aceita diferentes formas de pagamento
            quality_indicators += 1
        if tags.get('opening_hours') and 'Mo-Su' in tags.get('opening_hours'):
            quality_indicators += 1
        
        if quality_indicators >= 3:
            return 'high'
        elif quality_indicators >= 2:
            return 'medium'
        else:
            return 'basic'
    
    def _calculate_business_diversity(self, establishments: List[EconomicEstablishment]) -> float:
        """Calcular diversidade de negócios"""
        if not establishments:
            return 0
        
        # Contar categorias únicas
        categories = set(est.business_category for est in establishments if est.distance <= 1000)
        
        # Score baseado na diversidade
        max_categories = 8  # food, fashion, home, health, services, specialty, artisanal, professional
        diversity_score = (len(categories) / max_categories) * 100
        
        return min(diversity_score, 100)
    
    def _calculate_small_business_density(self, establishments: List[EconomicEstablishment]) -> float:
        """Calcular densidade de pequenos negócios"""
        small_businesses = [est for est in establishments if est.business_size == 'small' and est.distance <= 800]
        
        if not small_businesses:
            return 0
        
        # Score baseado na quantidade de pequenos negócios
        density_score = min(len(small_businesses) * 10, 100)
        
        return density_score
    
    def _calculate_economic_activity(self, establishments: List[EconomicEstablishment]) -> float:
        """Calcular atividade econômica"""
        nearby_establishments = [est for est in establishments if est.distance <= 1200]
        
        if not nearby_establishments:
            return 0
        
        # Score baseado na quantidade total e variedade de tipos
        quantity_score = min(len(nearby_establishments) * 3, 70)
        
        # Bônus por variedade de tipos de negócio
        business_types = set(est.business_type for est in nearby_establishments)
        variety_bonus = len(business_types) * 7
        
        return min(quantity_score + variety_bonus, 100)
    
    def _calculate_employment_potential(self, establishments: List[EconomicEstablishment]) -> float:
        """Calcular potencial de emprego"""
        # Estimar geração de empregos baseado no tipo e tamanho dos negócios
        employment_score = 0
        
        for est in establishments:
            if est.distance <= 1500:
                if est.business_size == 'large':
                    employment_score += 15
                elif est.business_size == 'medium':
                    employment_score += 8
                else:  # small
                    employment_score += 3
                
                # Bônus para tipos que geram mais empregos
                if est.business_type in ['office', 'marketplace']:
                    employment_score += 5
        
        return min(employment_score, 100)
    
    def _calculate_cultural_diversity(self, venues: List[CulturalVenue]) -> float:
        """Calcular diversidade cultural"""
        if not venues:
            return 0
        
        # Contar tipos únicos de locais culturais
        venue_types = set(venue.venue_type for venue in venues if venue.distance <= 2000)
        
        # Score baseado na diversidade
        max_types = 6  # museum, gallery, theatre, arts_centre, community_centre, historic
        diversity_score = (len(venue_types) / max_types) * 100
        
        return min(diversity_score, 100)
    
    def _calculate_artistic_variety(self, venues: List[CulturalVenue]) -> float:
        """Calcular variedade artística"""
        if not venues:
            return 0
        
        # Contar categorias culturais únicas
        categories = set(venue.cultural_category for venue in venues if venue.distance <= 2000)
        
        # Score baseado na variedade
        variety_score = min(len(categories) * 15, 100)
        
        return variety_score
    
    def _calculate_cultural_accessibility(self, venues: List[CulturalVenue]) -> float:
        """Calcular acessibilidade cultural"""
        if not venues:
            return 0
        
        nearby_venues = [venue for venue in venues if venue.distance <= 1500]
        
        if not nearby_venues:
            return 0
        
        accessible_count = sum(1 for venue in nearby_venues if venue.accessibility == 'yes')
        unknown_count = sum(1 for venue in nearby_venues if venue.accessibility == 'unknown')
        
        # Assumir 30% dos "unknown" como acessíveis
        estimated_accessible = accessible_count + (unknown_count * 0.3)
        
        accessibility_score = (estimated_accessible / len(nearby_venues)) * 100
        
        return accessibility_score
    
    def _calculate_tourism_appeal(self, venues: List[CulturalVenue]) -> float:
        """Calcular apelo turístico"""
        tourist_venues = [venue for venue in venues if venue.tourist_attraction and venue.distance <= 2500]
        
        if not tourist_venues:
            return 0
        
        # Score baseado na quantidade e proximidade de atrações turísticas
        appeal_score = min(len(tourist_venues) * 20, 100)
        
        return appeal_score
    
    def _calculate_shopping_convenience(self, facilities: List[RetailFacility]) -> float:
        """Calcular conveniência de compras"""
        essential_categories = ['food', 'health', 'essential_service']
        convenience_score = 0
        
        for category in essential_categories:
            category_facilities = [f for f in facilities if f.product_category == category and f.distance <= 800]
            
            if category_facilities:
                closest_distance = min(f.distance for f in category_facilities)
                if closest_distance <= 200:
                    convenience_score += 35
                elif closest_distance <= 400:
                    convenience_score += 25
                elif closest_distance <= 800:
                    convenience_score += 15
        
        return min(convenience_score, 100)
    
    def _calculate_service_variety(self, facilities: List[RetailFacility]) -> float:
        """Calcular variedade de serviços"""
        nearby_facilities = [f for f in facilities if f.distance <= 1200]
        
        if not nearby_facilities:
            return 0
        
        # Contar categorias únicas
        categories = set(f.product_category for f in nearby_facilities)
        
        # Score baseado na variedade
        max_categories = 7  # food, fashion, home, health, services, specialty, essential_service
        variety_score = (len(categories) / max_categories) * 100
        
        return min(variety_score, 100)
    
    def _calculate_retail_accessibility_score(self, facilities: List[RetailFacility]) -> float:
        """Calcular score de acessibilidade do varejo"""
        if not facilities:
            return 0
        
        nearby_facilities = [f for f in facilities if f.distance <= 1000]
        
        if not nearby_facilities:
            return 0
        
        accessible_count = sum(1 for f in nearby_facilities if f.accessibility == 'yes')
        unknown_count = sum(1 for f in nearby_facilities if f.accessibility == 'unknown')
        
        # Assumir 40% dos "unknown" como acessíveis
        estimated_accessible = accessible_count + (unknown_count * 0.4)
        
        accessibility_score = (estimated_accessible / len(nearby_facilities)) * 100
        
        return accessibility_score
    
    def _calculate_operating_hours_score(self, facilities: List[RetailFacility]) -> float:
        """Calcular score de horários de funcionamento"""
        nearby_facilities = [f for f in facilities if f.distance <= 1000]
        
        if not nearby_facilities:
            return 0
        
        extended_hours_count = 0
        known_hours_count = 0
        
        for facility in nearby_facilities:
            hours = facility.opening_hours
            if hours != 'unknown':
                known_hours_count += 1
                
                # Verificar se tem horários estendidos
                if any(indicator in hours.lower() for indicator in ['mo-su', '24/7', '08:', '09:', '20:', '21:', '22:']):
                    extended_hours_count += 1
        
        if known_hours_count == 0:
            return 50  # Score médio quando não há informações
        
        hours_score = (extended_hours_count / known_hours_count) * 100
        
        return hours_score
    
    def _calculate_local_character(self, economy_metrics: EconomyVitalityMetrics, cultural_metrics: CulturalRichnessMetrics) -> float:
        """Calcular caráter local"""
        # Combinar diversidade econômica e cultural
        economic_character = economy_metrics.small_business_density
        cultural_character = cultural_metrics.cultural_diversity
        
        local_character_score = (economic_character * 0.6 + cultural_character * 0.4)
        
        return local_character_score
    
    def _calculate_economic_resilience(self, economy_metrics: EconomyVitalityMetrics, retail_metrics: RetailAccessibilityMetrics) -> float:
        """Calcular resiliência econômica"""
        # Baseado na diversidade e densidade de negócios
        diversity_factor = economy_metrics.business_diversity
        accessibility_factor = retail_metrics.shopping_convenience
        activity_factor = economy_metrics.economic_activity_score
        
        resilience_score = (
            diversity_factor * 0.4 +
            accessibility_factor * 0.3 +
            activity_factor * 0.3
        )
        
        return resilience_score
    
    def _calculate_overall_economy_score(self, economy_metrics: EconomyVitalityMetrics, cultural_metrics: CulturalRichnessMetrics, retail_metrics: RetailAccessibilityMetrics) -> float:
        """Calcular score geral da economia local"""
        return (
            economy_metrics.overall_economy_score * 0.4 +
            retail_metrics.overall_retail_score * 0.35 +
            cultural_metrics.overall_cultural_score * 0.25
        )
    
    def _create_empty_economy_metrics(self) -> LocalEconomyMetrics:
        """Criar métricas de economia vazias em caso de erro"""
        return LocalEconomyMetrics(
            economy_vitality_metrics=EconomyVitalityMetrics([], 0, 0, 0, 0, 0),
            cultural_richness_metrics=CulturalRichnessMetrics([], 0, 0, 0, 0, 0),
            retail_accessibility_metrics=RetailAccessibilityMetrics([], 0, 0, 0, 50, 12),
            local_character_score=0,
            economic_resilience_score=0,
            overall_local_economy_score=5
        ) 