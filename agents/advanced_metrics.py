import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import numpy as np
import math
from agents.osm_data_collector import POI, PropertyData
from agents.neighborhood_analyst import NeighborhoodMetrics
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceDensityMetrics:
    """Densidade de serviços por categoria"""
    density_per_km2: Dict[str, float]
    total_services: int
    service_variety_score: float
    completeness_score: float

@dataclass
class UrbanDiversityMetrics:
    """Métricas de diversidade urbana"""
    shannon_diversity_index: float
    service_variety_count: int
    dominant_category: str
    balance_score: float

@dataclass
class MobilityMetrics:
    """Métricas avançadas de mobilidade"""
    transport_density: float
    walkability_by_direction: Dict[str, float]
    average_walking_time: Dict[str, float]
    connectivity_score: float

@dataclass
class LifestyleMetrics:
    """Métricas de estilo de vida"""
    daily_life_score: float
    entertainment_score: float
    family_friendliness: float
    professional_score: float

@dataclass
class AdvancedMetrics:
    """Métricas avançadas completas"""
    service_density: ServiceDensityMetrics
    urban_diversity: UrbanDiversityMetrics
    mobility: MobilityMetrics
    lifestyle: LifestyleMetrics
    green_space_score: float
    urban_intensity_score: float

class AdvancedMetricsCalculator:
    """Calculadora de métricas avançadas usando dados OSM existentes"""
    
    def __init__(self):
        self.config = Config()
        self.area_km2 = math.pi * (self.config.DEFAULT_SEARCH_RADIUS / 1000) ** 2
        
    def calculate_service_density(self, pois: List[POI]) -> ServiceDensityMetrics:
        """Calcula densidade de serviços por categoria"""
        
        # Agrupar POIs por categoria
        category_counts = Counter(poi.category for poi in pois)
        
        # Calcular densidade por km²
        density_per_km2 = {
            category: count / self.area_km2 
            for category, count in category_counts.items()
        }
        
        # Score de variedade de serviços (0-100)
        max_categories = len(self.config.POI_CATEGORIES)
        service_variety_score = (len(category_counts) / max_categories) * 100
        
        # Score de completude (baseado em serviços essenciais)
        essential_services = ['healthcare', 'education', 'shopping', 'transport']
        available_essential = sum(1 for service in essential_services if service in category_counts)
        completeness_score = (available_essential / len(essential_services)) * 100
        
        return ServiceDensityMetrics(
            density_per_km2=density_per_km2,
            total_services=len(pois),
            service_variety_score=service_variety_score,
            completeness_score=completeness_score
        )
    
    def calculate_urban_diversity(self, pois: List[POI]) -> UrbanDiversityMetrics:
        """Calcula índice de diversidade urbana usando Shannon Index"""
        
        if not pois:
            return UrbanDiversityMetrics(0, 0, "none", 0)
        
        # Contar POIs por categoria
        category_counts = Counter(poi.category for poi in pois)
        total_pois = len(pois)
        
        # Calcular Shannon Diversity Index
        shannon_index = 0
        for count in category_counts.values():
            if count > 0:
                proportion = count / total_pois
                shannon_index -= proportion * math.log(proportion)
        
        # Normalizar para 0-100
        max_diversity = math.log(len(self.config.POI_CATEGORIES))
        diversity_score = (shannon_index / max_diversity) * 100 if max_diversity > 0 else 0
        
        # Categoria dominante
        dominant_category = category_counts.most_common(1)[0][0] if category_counts else "none"
        
        # Score de balanceamento (quanto mais equilibrado, melhor)
        if len(category_counts) > 1:
            max_count = max(category_counts.values())
            min_count = min(category_counts.values())
            balance_score = (min_count / max_count) * 100
        else:
            balance_score = 0
        
        return UrbanDiversityMetrics(
            shannon_diversity_index=diversity_score,
            service_variety_count=len(category_counts),
            dominant_category=dominant_category,
            balance_score=balance_score
        )
    
    def calculate_mobility_metrics(self, pois: List[POI]) -> MobilityMetrics:
        """Calcula métricas avançadas de mobilidade"""
        
        # Filtrar POIs de transporte
        transport_pois = [poi for poi in pois if poi.category == 'transport']
        transport_density = len(transport_pois) / self.area_km2
        
        # Calcular walkability por direção (N, S, E, W)
        walkability_by_direction = self._calculate_directional_walkability(pois)
        
        # Tempo médio de caminhada para serviços essenciais
        average_walking_time = self._calculate_walking_times(pois)
        
        # Score de conectividade (baseado em variedade de transporte)
        transport_types = set(poi.subcategory for poi in transport_pois)
        connectivity_score = min(len(transport_types) * 20, 100)  # Max 100
        
        return MobilityMetrics(
            transport_density=transport_density,
            walkability_by_direction=walkability_by_direction,
            average_walking_time=average_walking_time,
            connectivity_score=connectivity_score
        )
    
    def _calculate_directional_walkability(self, pois: List[POI]) -> Dict[str, float]:
        """Calcula walkability por direção"""
        if not pois:
            return {"north": 0, "south": 0, "east": 0, "west": 0}
        
        # Assumir que o centro é (0,0) e calcular direções relativas
        center_lat = np.mean([poi.lat for poi in pois])
        center_lon = np.mean([poi.lon for poi in pois])
        
        directions = {"north": 0, "south": 0, "east": 0, "west": 0}
        
        for poi in pois:
            if poi.lat > center_lat:
                directions["north"] += 1
            else:
                directions["south"] += 1
                
            if poi.lon > center_lon:
                directions["east"] += 1
            else:
                directions["west"] += 1
        
        # Normalizar para 0-100
        total_pois = len(pois)
        return {direction: (count / total_pois) * 100 for direction, count in directions.items()}
    
    def _calculate_walking_times(self, pois: List[POI]) -> Dict[str, float]:
        """Calcula tempo médio de caminhada para cada categoria"""
        walking_times = {}
        
        # Agrupar por categoria
        pois_by_category = defaultdict(list)
        for poi in pois:
            pois_by_category[poi.category].append(poi)
        
        # Calcular tempo médio (assumindo 5 km/h de velocidade)
        for category, category_pois in pois_by_category.items():
            if category_pois:
                avg_distance = np.mean([poi.distance for poi in category_pois])
                # Tempo em minutos (distância em metros, velocidade 5 km/h = 83.33 m/min)
                walking_times[category] = avg_distance / 83.33
        
        return walking_times
    
    def calculate_lifestyle_metrics(self, pois: List[POI]) -> LifestyleMetrics:
        """Calcula métricas de estilo de vida"""
        
        # Score de vida cotidiana (supermercados, farmácias, bancos)
        daily_essentials = ['shopping', 'healthcare', 'services']
        daily_pois = [poi for poi in pois if poi.category in daily_essentials]
        daily_life_score = min(len(daily_pois) * 2, 100)
        
        # Score de entretenimento (restaurantes, bares, cinemas)
        entertainment_categories = ['food', 'leisure']
        entertainment_pois = [poi for poi in pois if poi.category in entertainment_categories]
        entertainment_score = min(len(entertainment_pois) * 1.5, 100)
        
        # Score de família (escolas, parques, playgrounds)
        family_categories = ['education', 'leisure']
        family_pois = [poi for poi in pois if poi.category in family_categories]
        family_friendliness = min(len(family_pois) * 3, 100)
        
        # Score profissional (transporte, serviços, conectividade)
        professional_categories = ['transport', 'services']
        professional_pois = [poi for poi in pois if poi.category in professional_categories]
        professional_score = min(len(professional_pois) * 2.5, 100)
        
        return LifestyleMetrics(
            daily_life_score=daily_life_score,
            entertainment_score=entertainment_score,
            family_friendliness=family_friendliness,
            professional_score=professional_score
        )
    
    def calculate_green_space_score(self, pois: List[POI]) -> float:
        """Calcula score de espaços verdes"""
        green_pois = [poi for poi in pois if poi.category == 'leisure' and 
                     any(keyword in poi.name.lower() for keyword in ['park', 'garden', 'green', 'tree'])]
        
        if not green_pois:
            return 0
        
        # Score baseado em quantidade e proximidade
        base_score = min(len(green_pois) * 10, 70)  # Max 70 por quantidade
        
        # Bonus por proximidade (se há parque muito próximo)
        closest_distance = min(poi.distance for poi in green_pois)
        proximity_bonus = max(30 - (closest_distance / 100), 0)  # Max 30 bonus
        
        return min(base_score + proximity_bonus, 100)
    
    def calculate_urban_intensity(self, pois: List[POI]) -> float:
        """Calcula intensidade urbana (densidade total de atividades)"""
        if not pois:
            return 0
        
        # Densidade total de POIs
        total_density = len(pois) / self.area_km2
        
        # Normalizar para 0-100 (assumindo 500 POIs/km² como máximo urbano)
        intensity_score = min((total_density / 500) * 100, 100)
        
        return intensity_score
    
    def calculate_all_metrics(self, pois: List[POI]) -> AdvancedMetrics:
        """Calcula todas as métricas avançadas"""
        
        logger.info(f"Calculando métricas avançadas para {len(pois)} POIs")
        
        return AdvancedMetrics(
            service_density=self.calculate_service_density(pois),
            urban_diversity=self.calculate_urban_diversity(pois),
            mobility=self.calculate_mobility_metrics(pois),
            lifestyle=self.calculate_lifestyle_metrics(pois),
            green_space_score=self.calculate_green_space_score(pois),
            urban_intensity_score=self.calculate_urban_intensity(pois)
        )
    
    def get_metrics_summary(self, advanced_metrics: AdvancedMetrics) -> Dict[str, float]:
        """Retorna resumo das métricas para display"""
        return {
            "densidade_servicos": advanced_metrics.service_density.service_variety_score,
            "diversidade_urbana": advanced_metrics.urban_diversity.shannon_diversity_index,
            "conectividade": advanced_metrics.mobility.connectivity_score,
            "vida_cotidiana": advanced_metrics.lifestyle.daily_life_score,
            "entretenimento": advanced_metrics.lifestyle.entertainment_score,
            "familia": advanced_metrics.lifestyle.family_friendliness,
            "profissional": advanced_metrics.lifestyle.professional_score,
            "espacos_verdes": advanced_metrics.green_space_score,
            "intensidade_urbana": advanced_metrics.urban_intensity_score
        } 