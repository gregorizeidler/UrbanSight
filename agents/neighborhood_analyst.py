import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import numpy as np
from agents.osm_data_collector import POI, PropertyData
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WalkScore:
    """Walk Score calculation result"""
    overall_score: float
    category_scores: Dict[str, float]
    grade: str
    description: str


@dataclass
class NeighborhoodMetrics:
    """Comprehensive neighborhood analysis metrics"""
    walk_score: WalkScore
    poi_density: Dict[str, float]
    closest_pois: Dict[str, POI]
    category_counts: Dict[str, int]
    accessibility_score: float
    convenience_score: float
    safety_score: float
    quality_of_life_score: float
    total_score: float


class NeighborhoodAnalyst:
    """Agent specialized in neighborhood analysis and metrics calculation"""

    def __init__(self):
        self.config = Config()
        self.weights = self.config.WALK_SCORE_WEIGHTS

    def calculate_walk_score(self, pois: List[POI]) -> WalkScore:
        """Calculate Walk Score based on POI proximity and density"""
        category_scores = {}

        # Group POIs by category
        pois_by_category = defaultdict(list)
        for poi in pois:
            pois_by_category[poi.category].append(poi)

        # Calculate score for each category
        for category, weight in self.weights.items():
            category_pois = pois_by_category.get(category, [])

            if not category_pois:
                category_scores[category] = 0.0
                continue

            # Find closest POIs in this category
            closest_pois = sorted(category_pois, key=lambda p: p.distance)[:5]

            # Calculate distance-based score
            distance_score = 0.0
            for i, poi in enumerate(closest_pois):
                # Distance penalty: closer = higher score
                distance_factor = max(0, 1 - (poi.distance / 800))  # 800m max useful distance

                # Diminishing returns for additional POIs
                poi_weight = 1.0 / (i + 1)

                distance_score += distance_factor * poi_weight

            # Normalize to 0-100 scale
            category_scores[category] = min(100, distance_score * 100)

        # Calculate overall score
        overall_score = sum(
            category_scores.get(category, 0) * weight
            for category, weight in self.weights.items()
        )

        # Determine grade and description
        grade, description = self._get_walk_score_grade(overall_score)

        return WalkScore(
            overall_score=overall_score,
            category_scores=category_scores,
            grade=grade,
            description=description
        )

    def _get_walk_score_grade(self, score: float) -> Tuple[str, str]:
        """Convert numeric score to grade and description"""
        if score >= 90:
            return "A+", "Paraíso dos Pedestres - Não precisa de carro"
        elif score >= 80:
            return "A", "Muito Caminhável - Maioria das tarefas a pé"
        elif score >= 70:
            return "B", "Caminhável - Algumas tarefas a pé"
        elif score >= 60:
            return "C", "Pouco Caminhável - Algumas tarefas a pé"
        elif score >= 50:
            return "D", "Dependente de Carro - Maioria das tarefas de carro"
        else:
            return "F", "Dependente de Carro - Quase todas as tarefas de carro"

    def calculate_poi_density(self, pois: List[POI], radius: int = 1000) -> Dict[str, float]:
        """Calculate POI density per category (POIs per km²)"""
        area_km2 = (np.pi * (radius / 1000) ** 2)  # Area in km²

        category_counts = Counter(poi.category for poi in pois)

        density = {}
        for category, count in category_counts.items():
            density[category] = count / area_km2

        return density

    def find_closest_pois(self, pois: List[POI]) -> Dict[str, POI]:
        """Find the closest POI for each category"""
        closest_pois = {}

        # Group by category and find closest
        for poi in pois:
            category = poi.category
            if category not in closest_pois or poi.distance < closest_pois[category].distance:
                closest_pois[category] = poi

        return closest_pois

    def calculate_accessibility_score(self, pois: List[POI]) -> float:
        """Calculate accessibility score based on transport options"""
        transport_pois = [poi for poi in pois if poi.category == 'transport']

        if not transport_pois:
            return 0.0

        # Find closest transport options
        closest_transport = min(transport_pois, key=lambda p: p.distance)

        # Score based on distance to closest transport
        if closest_transport.distance <= 200:
            return 100.0
        elif closest_transport.distance <= 500:
            return 80.0
        elif closest_transport.distance <= 800:
            return 60.0
        elif closest_transport.distance <= 1200:
            return 40.0
        else:
            return 20.0

    def calculate_convenience_score(self, pois: List[POI]) -> float:
        """Calculate convenience score based on essential services"""
        essential_categories = ['shopping', 'healthcare', 'services']

        scores = []
        for category in essential_categories:
            category_pois = [poi for poi in pois if poi.category == category]

            if not category_pois:
                scores.append(0.0)
                continue

            closest = min(category_pois, key=lambda p: p.distance)

            # Score based on distance
            if closest.distance <= 300:
                scores.append(100.0)
            elif closest.distance <= 600:
                scores.append(80.0)
            elif closest.distance <= 1000:
                scores.append(60.0)
            else:
                scores.append(30.0)

        return np.mean(scores) if scores else 0.0

    def calculate_safety_score(self, pois: List[POI]) -> float:
        """Calculate safety score based on security services proximity"""
        safety_pois = [poi for poi in pois if poi.subcategory in ['police', 'fire_station']]

        if not safety_pois:
            return 50.0  # Neutral score if no data

        closest_safety = min(safety_pois, key=lambda p: p.distance)

        # Score based on distance to safety services
        if closest_safety.distance <= 500:
            return 100.0
        elif closest_safety.distance <= 1000:
            return 80.0
        elif closest_safety.distance <= 1500:
            return 60.0
        else:
            return 40.0

    def calculate_quality_of_life_score(self, pois: List[POI]) -> float:
        """Calculate quality of life score based on leisure and cultural amenities"""
        leisure_pois = [poi for poi in pois if poi.category in ['leisure', 'food']]

        if not leisure_pois:
            return 0.0

        # Consider variety and proximity
        leisure_types = set(poi.subcategory for poi in leisure_pois)
        variety_score = min(len(leisure_types) * 10, 50)  # Max 50 points for variety

        # Proximity score
        closest_leisure = min(leisure_pois, key=lambda p: p.distance)
        if closest_leisure.distance <= 300:
            proximity_score = 50.0
        elif closest_leisure.distance <= 600:
            proximity_score = 40.0
        elif closest_leisure.distance <= 1000:
            proximity_score = 30.0
        else:
            proximity_score = 20.0

        return variety_score + proximity_score

    def analyze_neighborhood(self, property_data: PropertyData, pois: List[POI]) -> NeighborhoodMetrics:
        """Comprehensive neighborhood analysis"""
        logger.info(f"Analyzing neighborhood for {property_data.address}")

        # Calculate all metrics
        walk_score = self.calculate_walk_score(pois)
        poi_density = self.calculate_poi_density(pois)
        closest_pois = self.find_closest_pois(pois)
        category_counts = Counter(poi.category for poi in pois)

        accessibility_score = self.calculate_accessibility_score(pois)
        convenience_score = self.calculate_convenience_score(pois)
        safety_score = self.calculate_safety_score(pois)
        quality_of_life_score = self.calculate_quality_of_life_score(pois)

        # Calculate total score (weighted average)
        total_score = (
            walk_score.overall_score * 0.3 +
            accessibility_score * 0.25 +
            convenience_score * 0.25 +
            safety_score * 0.1 +
            quality_of_life_score * 0.1
        )

        return NeighborhoodMetrics(
            walk_score=walk_score,
            poi_density=poi_density,
            closest_pois=closest_pois,
            category_counts=dict(category_counts),
            accessibility_score=accessibility_score,
            convenience_score=convenience_score,
            safety_score=safety_score,
            quality_of_life_score=quality_of_life_score,
            total_score=total_score
        )

    def get_neighborhood_highlights(self, metrics: NeighborhoodMetrics) -> Dict[str, List[str]]:
        """Extract key highlights and concerns from metrics"""
        highlights = {
            'strengths': [],
            'concerns': [],
            'recommendations': []
        }

        # Analyze strengths
        if metrics.walk_score.overall_score >= 80:
            highlights['strengths'].append(f"Excelente caminhabilidade ({metrics.walk_score.grade})")

        if metrics.accessibility_score >= 80:
            highlights['strengths'].append("Ótimo acesso ao transporte público")

        if metrics.convenience_score >= 80:
            highlights['strengths'].append("Serviços essenciais muito próximos")

        if metrics.quality_of_life_score >= 60:
            highlights['strengths'].append("Boa variedade de opções de lazer")

        # Analyze concerns
        if metrics.walk_score.overall_score < 50:
            highlights['concerns'].append("Baixa caminhabilidade - dependente de carro")

        if metrics.accessibility_score < 40:
            highlights['concerns'].append("Acesso limitado ao transporte público")

        if metrics.convenience_score < 50:
            highlights['concerns'].append("Serviços essenciais distantes")

        # Generate recommendations
        if metrics.accessibility_score < 60:
            highlights['recommendations'].append("Considere a necessidade de veículo próprio")

        if metrics.quality_of_life_score < 40:
            highlights['recommendations'].append("Área com poucas opções de lazer e entretenimento")

        return highlights

    def get_ideal_resident_profile(self, metrics: NeighborhoodMetrics) -> str:
        """Generate ideal resident profile based on metrics"""
        profiles = []

        # Based on walk score and transport
        if metrics.walk_score.overall_score >= 80:
            profiles.append("pessoas que preferem se locomover a pé")

        if metrics.accessibility_score >= 80:
            profiles.append("usuários de transporte público")

        # Based on convenience
        if metrics.convenience_score >= 80:
            profiles.append("pessoas que valorizam conveniência")

        # Based on quality of life
        if metrics.quality_of_life_score >= 60:
            profiles.append("pessoas que apreciam vida cultural e social")

        # Based on category presence
        if metrics.category_counts.get('education', 0) >= 3:
            profiles.append("famílias com crianças")

        if metrics.category_counts.get('food', 0) >= 10:
            profiles.append("jovens profissionais")

        if not profiles:
            profiles.append("pessoas que preferem áreas mais tranquilas")

        return ", ".join(profiles) 