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
class BikeInfrastructure:
    """Infraestrutura ciclística"""
    id: str
    infrastructure_type: str  # cycleway, bike_lane, shared_lane
    distance: float
    length: float
    surface: str
    segregation: str  # segregated, shared, unknown
    bidirectional: bool

@dataclass
class BikeStation:
    """Estação de bike-sharing"""
    id: str
    name: str
    distance: float
    capacity: int
    station_type: str

@dataclass
class ParkingFacility:
    """Facilidade de estacionamento"""
    id: str
    name: str
    distance: float
    parking_type: str  # surface, underground, multi-storey
    access: str  # public, private, customers
    fee: str  # yes, no, unknown
    capacity: int
    wheelchair_accessible: bool

@dataclass
class TransportStop:
    """Ponto de transporte público"""
    id: str
    name: str
    distance: float
    transport_type: str  # bus, metro, train, tram
    lines_count: int
    accessibility: str
    shelter: bool

@dataclass
class BikeMetrics:
    """Métricas de infraestrutura ciclística"""
    bike_infrastructure: List[BikeInfrastructure]
    bike_stations: List[BikeStation]
    cycleway_density: float
    bike_connectivity_score: float
    bike_safety_score: float
    overall_bike_score: float

@dataclass
class ParkingMetrics:
    """Métricas de estacionamento"""
    parking_facilities: List[ParkingFacility]
    parking_availability_score: float
    parking_cost_score: float
    parking_convenience_score: float
    overall_parking_score: float

@dataclass
class PublicTransportMetrics:
    """Métricas de transporte público"""
    transport_stops: List[TransportStop]
    modal_diversity_score: float
    frequency_estimate_score: float
    accessibility_score: float
    coverage_score: float
    overall_transport_score: float

@dataclass
class MobilityMetrics:
    """Métricas de mobilidade completas"""
    bike_metrics: BikeMetrics
    parking_metrics: ParkingMetrics
    public_transport_metrics: PublicTransportMetrics
    overall_mobility_score: float
    car_dependency_score: float
    sustainable_mobility_score: float

class AdvancedMobilityAnalyzer:
    """Agente especializado em análise de mobilidade urbana"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_mobility_query(self, lat: float, lon: float, radius: int = 1500) -> str:
        """Construir query para dados de mobilidade"""
        query = f"""
        [out:json][timeout:30];
        (
          // Infraestrutura ciclística
          way["highway"="cycleway"](around:{radius},{lat},{lon});
          way["cycleway"](around:{radius},{lat},{lon});
          way["bicycle"="yes"](around:{radius},{lat},{lon});
          way["bicycle"="designated"](around:{radius},{lat},{lon});
          
          // Estações de bike-sharing
          node["amenity"="bicycle_rental"](around:{radius},{lat},{lon});
          node["amenity"="bicycle_parking"](around:{radius},{lat},{lon});
          
          // Estacionamentos
          node["amenity"="parking"](around:{radius},{lat},{lon});
          way["amenity"="parking"](around:{radius},{lat},{lon});
          relation["amenity"="parking"](around:{radius},{lat},{lon});
          
          // Transporte público
          node["public_transport"="stop_position"](around:{radius},{lat},{lon});
          node["highway"="bus_stop"](around:{radius},{lat},{lon});
          node["railway"="station"](around:{radius},{lat},{lon});
          node["railway"="halt"](around:{radius},{lat},{lon});
          node["public_transport"="platform"](around:{radius},{lat},{lon});
          
          // Linhas de transporte
          relation["route"="bus"](around:{radius},{lat},{lon});
          relation["route"="metro"](around:{radius},{lat},{lon});
          relation["route"="train"](around:{radius},{lat},{lon});
          relation["route"="tram"](around:{radius},{lat},{lon});
          
          // Vias para análise de tráfego
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential)$"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def analyze_mobility(self, property_data: PropertyData, radius: int = 1500) -> MobilityMetrics:
        """Analisar mobilidade urbana"""
        try:
            logger.info(f"Analisando mobilidade para {property_data.address} (raio: {radius}m)")
            query = self._build_mobility_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)
            
            # Analisar infraestrutura ciclística
            bike_metrics = self._analyze_bike_infrastructure(result, property_data)
            
            # Analisar estacionamento
            parking_metrics = self._analyze_parking(result, property_data)
            
            # Analisar transporte público
            transport_metrics = self._analyze_public_transport(result, property_data)
            
            # Calcular scores gerais
            overall_mobility_score = self._calculate_overall_mobility_score(bike_metrics, parking_metrics, transport_metrics)
            car_dependency_score = self._calculate_car_dependency(parking_metrics, transport_metrics)
            sustainable_mobility_score = self._calculate_sustainable_mobility(bike_metrics, transport_metrics)
            
            return MobilityMetrics(
                bike_metrics=bike_metrics,
                parking_metrics=parking_metrics,
                public_transport_metrics=transport_metrics,
                overall_mobility_score=overall_mobility_score,
                car_dependency_score=car_dependency_score,
                sustainable_mobility_score=sustainable_mobility_score
            )
            
        except Exception as e:
            logger.error(f"Erro analisando mobilidade: {str(e)}")
            return self._create_empty_mobility_metrics()
    
    def _analyze_bike_infrastructure(self, result, property_data: PropertyData) -> BikeMetrics:
        """Analisar infraestrutura ciclística"""
        bike_infrastructure = []
        bike_stations = []
        
        # Processar ciclovias e infraestrutura ciclística
        for way in result.ways:
            tags = way.tags
            
            # Identificar tipo de infraestrutura ciclística
            if (tags.get('highway') == 'cycleway' or 
                'cycleway' in tags or 
                tags.get('bicycle') in ['yes', 'designated']):
                
                if len(way.nodes) >= 2:
                    coords = [(node.lat, node.lon) for node in way.nodes]
                    center_lat = np.mean([coord[0] for coord in coords])
                    center_lon = np.mean([coord[1] for coord in coords])
                    distance = geodesic((property_data.lat, property_data.lon), (center_lat, center_lon)).meters
                    
                    # Calcular comprimento
                    length = 0
                    for i in range(len(coords) - 1):
                        length += geodesic(coords[i], coords[i+1]).meters
                    
                    # Determinar tipo
                    if tags.get('highway') == 'cycleway':
                        infrastructure_type = 'cycleway'
                        segregation = 'segregated'
                    elif tags.get('cycleway') in ['lane', 'track']:
                        infrastructure_type = 'bike_lane'
                        segregation = tags.get('cycleway:segregation', 'unknown')
                    else:
                        infrastructure_type = 'shared_lane'
                        segregation = 'shared'
                    
                    bike_infrastructure.append(BikeInfrastructure(
                        id=str(way.id),
                        infrastructure_type=infrastructure_type,
                        distance=distance,
                        length=length,
                        surface=tags.get('surface', 'unknown'),
                        segregation=segregation,
                        bidirectional=tags.get('oneway', 'no') == 'no'
                    ))
        
        # Processar estações de bike-sharing
        for node in result.nodes:
            if node.tags.get('amenity') in ['bicycle_rental', 'bicycle_parking']:
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                capacity = 0
                if node.tags.get('capacity'):
                    try:
                        capacity = int(node.tags['capacity'])
                    except:
                        capacity = 10  # Estimativa padrão
                
                bike_stations.append(BikeStation(
                    id=str(node.id),
                    name=node.tags.get('name', 'Estação de Bikes'),
                    distance=distance,
                    capacity=capacity,
                    station_type=node.tags.get('amenity')
                ))
        
        # Calcular métricas
        cycleway_density = self._calculate_cycleway_density(bike_infrastructure)
        bike_connectivity_score = self._calculate_bike_connectivity(bike_infrastructure)
        bike_safety_score = self._calculate_bike_safety(bike_infrastructure)
        overall_bike_score = self._calculate_overall_bike_score(bike_infrastructure, bike_stations)
        
        return BikeMetrics(
            bike_infrastructure=bike_infrastructure,
            bike_stations=bike_stations,
            cycleway_density=cycleway_density,
            bike_connectivity_score=bike_connectivity_score,
            bike_safety_score=bike_safety_score,
            overall_bike_score=overall_bike_score
        )
    
    def _analyze_parking(self, result, property_data: PropertyData) -> ParkingMetrics:
        """Analisar estacionamento"""
        parking_facilities = []
        
        # Processar estacionamentos (nodes e ways)
        for element in result.nodes + result.ways:
            if element.tags.get('amenity') == 'parking':
                
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
                
                # Extrair informações
                tags = element.tags
                capacity = 0
                if tags.get('capacity'):
                    try:
                        capacity = int(tags['capacity'])
                    except:
                        capacity = 20  # Estimativa padrão
                
                parking_facilities.append(ParkingFacility(
                    id=str(element.id),
                    name=tags.get('name', 'Estacionamento'),
                    distance=distance,
                    parking_type=tags.get('parking', 'surface'),
                    access=tags.get('access', 'unknown'),
                    fee=tags.get('fee', 'unknown'),
                    capacity=capacity,
                    wheelchair_accessible=tags.get('wheelchair') == 'yes'
                ))
        
        # Calcular métricas
        availability_score = self._calculate_parking_availability(parking_facilities)
        cost_score = self._calculate_parking_cost_score(parking_facilities)
        convenience_score = self._calculate_parking_convenience(parking_facilities)
        overall_parking_score = (availability_score * 0.4 + cost_score * 0.3 + convenience_score * 0.3)
        
        return ParkingMetrics(
            parking_facilities=parking_facilities,
            parking_availability_score=availability_score,
            parking_cost_score=cost_score,
            parking_convenience_score=convenience_score,
            overall_parking_score=overall_parking_score
        )
    
    def _analyze_public_transport(self, result, property_data: PropertyData) -> PublicTransportMetrics:
        """Analisar transporte público"""
        transport_stops = []
        
        # Processar paradas de transporte público
        for node in result.nodes:
            tags = node.tags
            
            if (tags.get('public_transport') in ['stop_position', 'platform'] or
                tags.get('highway') == 'bus_stop' or
                tags.get('railway') in ['station', 'halt']):
                
                distance = geodesic((property_data.lat, property_data.lon), (node.lat, node.lon)).meters
                
                # Determinar tipo de transporte
                if tags.get('railway') in ['station', 'halt']:
                    transport_type = 'train'
                elif tags.get('highway') == 'bus_stop':
                    transport_type = 'bus'
                elif 'metro' in tags.get('name', '').lower():
                    transport_type = 'metro'
                else:
                    transport_type = 'bus'  # Padrão
                
                # Estimar número de linhas (baseado em tags)
                lines_count = 1
                if tags.get('ref'):
                    # Conta o número de linhas separadas por ;
                    lines_count = len(tags['ref'].split(';'))
                
                transport_stops.append(TransportStop(
                    id=str(node.id),
                    name=tags.get('name', f'Parada {transport_type.title()}'),
                    distance=distance,
                    transport_type=transport_type,
                    lines_count=lines_count,
                    accessibility=tags.get('wheelchair', 'unknown'),
                    shelter=tags.get('shelter') == 'yes'
                ))
        
        # Calcular métricas
        modal_diversity_score = self._calculate_modal_diversity(transport_stops)
        frequency_estimate_score = self._calculate_frequency_estimate(transport_stops)
        accessibility_score = self._calculate_transport_accessibility(transport_stops)
        coverage_score = self._calculate_transport_coverage(transport_stops)
        
        overall_transport_score = (
            modal_diversity_score * 0.25 +
            frequency_estimate_score * 0.25 +
            accessibility_score * 0.25 +
            coverage_score * 0.25
        )
        
        return PublicTransportMetrics(
            transport_stops=transport_stops,
            modal_diversity_score=modal_diversity_score,
            frequency_estimate_score=frequency_estimate_score,
            accessibility_score=accessibility_score,
            coverage_score=coverage_score,
            overall_transport_score=overall_transport_score
        )
    
    def _calculate_cycleway_density(self, bike_infrastructure: List[BikeInfrastructure]) -> float:
        """Calcular densidade de ciclovias"""
        if not bike_infrastructure:
            return 0
        
        total_length = sum(infra.length for infra in bike_infrastructure if infra.distance <= 1000)
        # Densidade em metros por km²
        area_km2 = math.pi * (1) ** 2  # 1km radius
        density = total_length / area_km2
        
        # Normalizar para 0-100 (10km/km² = 100)
        return min(density / 100, 100)
    
    def _calculate_bike_connectivity(self, bike_infrastructure: List[BikeInfrastructure]) -> float:
        """Calcular conectividade da rede ciclística"""
        if not bike_infrastructure:
            return 0
        
        # Score baseado em quantidade e proximidade
        nearby_infrastructure = [infra for infra in bike_infrastructure if infra.distance <= 500]
        
        if not nearby_infrastructure:
            return 0
        
        # Pontuação por quantidade
        quantity_score = min(len(nearby_infrastructure) * 15, 60)
        
        # Bônus por diversidade de tipos
        types = set(infra.infrastructure_type for infra in nearby_infrastructure)
        diversity_bonus = len(types) * 10
        
        # Bônus por infraestrutura segregada
        segregated_count = sum(1 for infra in nearby_infrastructure if infra.segregation == 'segregated')
        safety_bonus = min(segregated_count * 5, 20)
        
        return min(quantity_score + diversity_bonus + safety_bonus, 100)
    
    def _calculate_bike_safety(self, bike_infrastructure: List[BikeInfrastructure]) -> float:
        """Calcular segurança ciclística"""
        if not bike_infrastructure:
            return 0
        
        safety_score = 0
        for infra in bike_infrastructure:
            if infra.distance <= 1000:
                if infra.segregation == 'segregated':
                    safety_score += 30
                elif infra.infrastructure_type == 'bike_lane':
                    safety_score += 20
                else:
                    safety_score += 10
        
        return min(safety_score, 100)
    
    def _calculate_overall_bike_score(self, bike_infrastructure: List[BikeInfrastructure], bike_stations: List[BikeStation]) -> float:
        """Calcular score geral de ciclabilidade"""
        if not bike_infrastructure and not bike_stations:
            return 0
        
        # Score de infraestrutura
        infra_score = 0
        if bike_infrastructure:
            nearby_infra = [infra for infra in bike_infrastructure if infra.distance <= 800]
            infra_score = min(len(nearby_infra) * 20, 80)
        
        # Score de estações
        station_score = 0
        if bike_stations:
            nearby_stations = [station for station in bike_stations if station.distance <= 500]
            station_score = min(len(nearby_stations) * 25, 50)
        
        return min(infra_score + station_score, 100)
    
    def _calculate_parking_availability(self, parking_facilities: List[ParkingFacility]) -> float:
        """Calcular disponibilidade de estacionamento"""
        if not parking_facilities:
            return 0
        
        # Score baseado em proximidade e capacidade
        total_capacity = 0
        proximity_score = 0
        
        for facility in parking_facilities:
            if facility.distance <= 800:
                # Pontuação por proximidade (mais próximo = melhor)
                prox_points = max(0, 50 - (facility.distance / 16))
                proximity_score += prox_points
                
                # Capacidade adiciona pontos
                total_capacity += facility.capacity
        
        capacity_score = min(total_capacity / 10, 50)  # Normalizar capacidade
        
        return min(proximity_score + capacity_score, 100)
    
    def _calculate_parking_cost_score(self, parking_facilities: List[ParkingFacility]) -> float:
        """Calcular score de custo de estacionamento"""
        if not parking_facilities:
            return 0
        
        nearby_facilities = [f for f in parking_facilities if f.distance <= 1000]
        if not nearby_facilities:
            return 0
        
        free_count = sum(1 for f in nearby_facilities if f.fee == 'no')
        paid_count = sum(1 for f in nearby_facilities if f.fee == 'yes')
        unknown_count = len(nearby_facilities) - free_count - paid_count
        
        # Score favorece estacionamento gratuito
        score = (free_count * 40) + (unknown_count * 20) + (paid_count * 10)
        
        return min(score, 100)
    
    def _calculate_parking_convenience(self, parking_facilities: List[ParkingFacility]) -> float:
        """Calcular conveniência de estacionamento"""
        if not parking_facilities:
            return 0
        
        convenience_score = 0
        for facility in parking_facilities:
            if facility.distance <= 500:
                # Pontos por proximidade
                convenience_score += 20
                
                # Bônus por acessibilidade
                if facility.wheelchair_accessible:
                    convenience_score += 5
                
                # Bônus por tipo (subsolo/edifício vs. superfície)
                if facility.parking_type in ['underground', 'multi-storey']:
                    convenience_score += 5
        
        return min(convenience_score, 100)
    
    def _calculate_modal_diversity(self, transport_stops: List[TransportStop]) -> float:
        """Calcular diversidade modal"""
        if not transport_stops:
            return 0
        
        # Contar tipos únicos de transporte
        transport_types = set(stop.transport_type for stop in transport_stops if stop.distance <= 1000)
        
        # Score baseado na diversidade
        diversity_score = len(transport_types) * 25  # 25 pontos por tipo
        
        return min(diversity_score, 100)
    
    def _calculate_frequency_estimate(self, transport_stops: List[TransportStop]) -> float:
        """Estimar frequência baseada no número de linhas"""
        if not transport_stops:
            return 0
        
        total_lines = sum(stop.lines_count for stop in transport_stops if stop.distance <= 800)
        
        # Assumir que mais linhas = maior frequência
        frequency_score = min(total_lines * 10, 100)
        
        return frequency_score
    
    def _calculate_transport_accessibility(self, transport_stops: List[TransportStop]) -> float:
        """Calcular acessibilidade do transporte público"""
        if not transport_stops:
            return 0
        
        nearby_stops = [stop for stop in transport_stops if stop.distance <= 800]
        if not nearby_stops:
            return 0
        
        accessible_count = sum(1 for stop in nearby_stops if stop.accessibility == 'yes')
        unknown_count = sum(1 for stop in nearby_stops if stop.accessibility == 'unknown')
        
        # Score favorece paradas acessíveis
        score = (accessible_count * 30) + (unknown_count * 15)
        
        return min(score, 100)
    
    def _calculate_transport_coverage(self, transport_stops: List[TransportStop]) -> float:
        """Calcular cobertura de transporte público"""
        if not transport_stops:
            return 0
        
        # Score baseado na proximidade das paradas mais próximas
        closest_distances = sorted([stop.distance for stop in transport_stops])[:3]
        
        coverage_score = 0
        for i, distance in enumerate(closest_distances):
            # Primeira parada vale mais
            weight = 1.0 / (i + 1)
            distance_score = max(0, 100 - (distance / 10))  # 1km = 0 pontos
            coverage_score += distance_score * weight
        
        return min(coverage_score, 100)
    
    def _calculate_overall_mobility_score(self, bike_metrics: BikeMetrics, parking_metrics: ParkingMetrics, transport_metrics: PublicTransportMetrics) -> float:
        """Calcular score geral de mobilidade"""
        return (
            transport_metrics.overall_transport_score * 0.5 +
            bike_metrics.overall_bike_score * 0.3 +
            parking_metrics.overall_parking_score * 0.2
        )
    
    def _calculate_car_dependency(self, parking_metrics: ParkingMetrics, transport_metrics: PublicTransportMetrics) -> float:
        """Calcular dependência do carro"""
        # Score alto de transporte público = baixa dependência do carro
        transport_factor = 100 - transport_metrics.overall_transport_score
        
        # Score alto de estacionamento = alta dependência do carro
        parking_factor = parking_metrics.overall_parking_score
        
        return (transport_factor * 0.7 + parking_factor * 0.3)
    
    def _calculate_sustainable_mobility(self, bike_metrics: BikeMetrics, transport_metrics: PublicTransportMetrics) -> float:
        """Calcular mobilidade sustentável"""
        return (bike_metrics.overall_bike_score * 0.4 + transport_metrics.overall_transport_score * 0.6)
    
    def _create_empty_mobility_metrics(self) -> MobilityMetrics:
        """Criar métricas de mobilidade vazias em caso de erro"""
        return MobilityMetrics(
            bike_metrics=BikeMetrics([], [], 0, 0, 0, 0),
            parking_metrics=ParkingMetrics([], 0, 0, 0, 0),
            public_transport_metrics=PublicTransportMetrics([], 0, 0, 0, 0, 0),
            overall_mobility_score=0,
            car_dependency_score=50,
            sustainable_mobility_score=0
        ) 