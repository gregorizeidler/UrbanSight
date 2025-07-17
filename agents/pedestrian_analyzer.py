import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import overpy
import numpy as np
from shapely.geometry import Point, LineString
from geopy.distance import geodesic

from agents.osm_data_collector import PropertyData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PedestrianInfrastructure:
    """Pedestrian infrastructure data structure"""
    sidewalks: List[Dict]
    crossings: List[Dict]
    pedestrian_areas: List[Dict]
    traffic_signals: List[Dict]
    speed_limits: List[Dict]
    street_lighting: List[Dict]
    
@dataclass
class PedestrianScore:
    """Pedestrian infrastructure walkability score"""
    overall_score: float
    sidewalk_score: float
    crossing_score: float
    safety_score: float
    accessibility_score: float
    comfort_score: float
    grade: str
    description: str

class PedestrianAnalyzer:
    """Agent specialized in pedestrian infrastructure analysis"""
    
    def __init__(self):
        self.overpass_api = overpy.Overpass()
        
    def _build_pedestrian_query(self, lat: float, lon: float, radius: int = 500) -> str:
        """Build query for pedestrian infrastructure data"""
        query = f"""
        [out:json][timeout:25];
        (
          // Sidewalks
          way["footway"="sidewalk"](around:{radius},{lat},{lon});
          way["sidewalk"](around:{radius},{lat},{lon});
          
          // Pedestrian areas and walkways
          way["highway"="pedestrian"](around:{radius},{lat},{lon});
          way["highway"="footway"](around:{radius},{lat},{lon});
          
          // Crossings
          node["highway"="crossing"](around:{radius},{lat},{lon});
          node["crossing"](around:{radius},{lat},{lon});
          
          // Traffic signals
          node["highway"="traffic_signals"](around:{radius},{lat},{lon});
          
          // Roads with speed limits
          way["highway"]["maxspeed"](around:{radius},{lat},{lon});
          way["highway"~"^(residential|living_street|service)$"](around:{radius},{lat},{lon});
          
          // Street lighting
          node["highway"="street_lamp"](around:{radius},{lat},{lon});
          
          // Accessibility features
          node["kerb"="lowered"](around:{radius},{lat},{lon});
          node["tactile_paving"="yes"](around:{radius},{lat},{lon});
        );
        out geom meta;
        """
        return query
    
    async def collect_pedestrian_data(self, property_data: PropertyData, radius: int = 500) -> PedestrianInfrastructure:
        """Collect pedestrian infrastructure data"""
        try:
            logger.info(f"Collecting pedestrian data for {property_data.address} (radius: {radius}m)")
            query = self._build_pedestrian_query(property_data.lat, property_data.lon, radius)
            logger.info("Executing Overpass query for pedestrian infrastructure...")
            result = self.overpass_api.query(query)
            logger.info(f"Query returned {len(result.ways)} ways and {len(result.nodes)} nodes")
            
            # Process different types of infrastructure
            sidewalks = self._process_sidewalks(result, property_data)
            crossings = self._process_crossings(result, property_data)
            pedestrian_areas = self._process_pedestrian_areas(result, property_data)
            traffic_signals = self._process_traffic_signals(result, property_data)
            speed_limits = self._process_speed_limits(result, property_data)
            street_lighting = self._process_street_lighting(result, property_data)
            
            return PedestrianInfrastructure(
                sidewalks=sidewalks,
                crossings=crossings,
                pedestrian_areas=pedestrian_areas,
                traffic_signals=traffic_signals,
                speed_limits=speed_limits,
                street_lighting=street_lighting
            )
            
        except Exception as e:
            logger.error(f"Error collecting pedestrian data: {str(e)}")
            return PedestrianInfrastructure([], [], [], [], [], [])
    
    def _process_sidewalks(self, result, property_data: PropertyData) -> List[Dict]:
        """Process sidewalk data"""
        sidewalks = []
        
        for way in result.ways:
            if any(tag in way.tags for tag in ['footway', 'sidewalk']):
                if way.tags.get('footway') == 'sidewalk' or 'sidewalk' in way.tags:
                    # Calculate average sidewalk distance
                    if len(way.nodes) >= 2:
                        coords = [(node.lat, node.lon) for node in way.nodes]
                        center_lat = np.mean([coord[0] for coord in coords])
                        center_lon = np.mean([coord[1] for coord in coords])
                        
                        distance = geodesic(
                            (property_data.lat, property_data.lon),
                            (center_lat, center_lon)
                        ).meters
                        
                        # Calculate sidewalk length
                        length = 0
                        for i in range(len(coords) - 1):
                            length += geodesic(coords[i], coords[i+1]).meters
                        
                        sidewalks.append({
                            'id': way.id,
                            'distance': distance,
                            'length': length,
                            'surface': way.tags.get('surface', 'unknown'),
                            'width': way.tags.get('width', 'unknown'),
                            'lit': way.tags.get('lit', 'unknown'),
                            'wheelchair': way.tags.get('wheelchair', 'unknown')
                        })
        
        return sidewalks
    
    def _process_crossings(self, result, property_data: PropertyData) -> List[Dict]:
        """Process crossing data"""
        crossings = []
        
        for node in result.nodes:
            if 'crossing' in node.tags or node.tags.get('highway') == 'crossing':
                distance = geodesic(
                    (property_data.lat, property_data.lon),
                    (node.lat, node.lon)
                ).meters
                
                crossings.append({
                    'id': node.id,
                    'distance': distance,
                    'type': node.tags.get('crossing', 'unknown'),
                    'signals': node.tags.get('crossing:signals', 'no'),
                    'tactile_paving': node.tags.get('tactile_paving', 'unknown'),
                    'wheelchair': node.tags.get('wheelchair', 'unknown')
                })
        
        return crossings
    
    def _process_pedestrian_areas(self, result, property_data: PropertyData) -> List[Dict]:
        """Process pedestrian areas (pedestrian zones)"""
        pedestrian_areas = []
        
        for way in result.ways:
            if way.tags.get('highway') in ['pedestrian', 'footway']:
                if len(way.nodes) >= 2:
                    coords = [(node.lat, node.lon) for node in way.nodes]
                    center_lat = np.mean([coord[0] for coord in coords])
                    center_lon = np.mean([coord[1] for coord in coords])
                    
                    distance = geodesic(
                        (property_data.lat, property_data.lon),
                        (center_lat, center_lon)
                    ).meters
                    
                    # Calculate approximate area
                    length = 0
                    for i in range(len(coords) - 1):
                        length += geodesic(coords[i], coords[i+1]).meters
                    
                    pedestrian_areas.append({
                        'id': way.id,
                        'distance': distance,
                        'length': length,
                        'type': way.tags.get('highway'),
                        'surface': way.tags.get('surface', 'unknown'),
                        'lit': way.tags.get('lit', 'unknown')
                    })
        
        return pedestrian_areas
    
    def _process_traffic_signals(self, result, property_data: PropertyData) -> List[Dict]:
        """Process traffic signals"""
        signals = []
        
        for node in result.nodes:
            if node.tags.get('highway') == 'traffic_signals':
                distance = geodesic(
                    (property_data.lat, property_data.lon),
                    (node.lat, node.lon)
                ).meters
                
                signals.append({
                    'id': node.id,
                    'distance': distance,
                    'type': 'traffic_signals',
                    'button': node.tags.get('button_operated', 'unknown'),
                    'sound': node.tags.get('traffic_signals:sound', 'unknown')
                })
        
        return signals
    
    def _process_speed_limits(self, result, property_data: PropertyData) -> List[Dict]:
        """Process road speed limits"""
        speed_limits = []
        
        for way in result.ways:
            if 'highway' in way.tags:
                maxspeed = way.tags.get('maxspeed', 'unknown')
                highway_type = way.tags.get('highway')
                
                # Estimate speed based on highway type
                estimated_speed = self._estimate_speed_by_highway_type(highway_type)
                
                if len(way.nodes) >= 2:
                    coords = [(node.lat, node.lon) for node in way.nodes]
                    center_lat = np.mean([coord[0] for coord in coords])
                    center_lon = np.mean([coord[1] for coord in coords])
                    
                    distance = geodesic(
                        (property_data.lat, property_data.lon),
                        (center_lat, center_lon)
                    ).meters
                    
                    speed_limits.append({
                        'id': way.id,
                        'distance': distance,
                        'maxspeed': maxspeed,
                        'estimated_speed': estimated_speed,
                        'highway_type': highway_type,
                        'pedestrian_friendly': estimated_speed <= 30
                    })
        
        return speed_limits
    
    def _process_street_lighting(self, result, property_data: PropertyData) -> List[Dict]:
        """Process street lighting"""
        lighting = []
        
        for node in result.nodes:
            if node.tags.get('highway') == 'street_lamp':
                distance = geodesic(
                    (property_data.lat, property_data.lon),
                    (node.lat, node.lon)
                ).meters
                
                lighting.append({
                    'id': node.id,
                    'distance': distance,
                    'type': 'street_lamp',
                    'lamp_type': node.tags.get('lamp_type', 'unknown'),
                    'support': node.tags.get('support', 'unknown')
                })
        
        return lighting
    
    def _estimate_speed_by_highway_type(self, highway_type: str) -> int:
        """Estimate speed based on highway type"""
        speed_map = {
            'living_street': 20,
            'residential': 30,
            'service': 20,
            'tertiary': 40,
            'secondary': 50,
            'primary': 60,
            'trunk': 80,
            'motorway': 100,
            'pedestrian': 0,
            'footway': 0
        }
        return speed_map.get(highway_type, 50)
    
    def calculate_pedestrian_score(self, infrastructure: PedestrianInfrastructure) -> PedestrianScore:
        """Calculate pedestrian infrastructure walkability score"""
        
        logger.info(f"Calculating pedestrian score from infrastructure data:")
        logger.info(f"  - Sidewalks: {len(infrastructure.sidewalks)}")
        logger.info(f"  - Crossings: {len(infrastructure.crossings)}")
        logger.info(f"  - Traffic signals: {len(infrastructure.traffic_signals)}")
        logger.info(f"  - Speed limits: {len(infrastructure.speed_limits)}")
        logger.info(f"  - Street lighting: {len(infrastructure.street_lighting)}")
        
        # 1. Sidewalk score (0-100)
        sidewalk_score = self._calculate_sidewalk_score(infrastructure.sidewalks)
        
        # 2. Crossing score (0-100)
        crossing_score = self._calculate_crossing_score(infrastructure.crossings, infrastructure.traffic_signals)
        
        # 3. Safety score (0-100)
        safety_score = self._calculate_safety_score(infrastructure.speed_limits, infrastructure.street_lighting)
        
        # 4. Accessibility score (0-100)
        accessibility_score = self._calculate_accessibility_score(infrastructure.crossings, infrastructure.sidewalks)
        
        # 5. Comfort score (0-100)
        comfort_score = self._calculate_comfort_score(infrastructure.pedestrian_areas, infrastructure.sidewalks)
        
        # Overall score (weighted)
        overall_score = (
            sidewalk_score * 0.30 +      # 30% - Sidewalks
            crossing_score * 0.25 +      # 25% - Crossings
            safety_score * 0.20 +        # 20% - Safety
            accessibility_score * 0.15 + # 15% - Accessibility
            comfort_score * 0.10         # 10% - Comfort
        )
        
        grade, description = self._get_pedestrian_grade(overall_score)
        
        logger.info(f"Pedestrian scores calculated:")
        logger.info(f"  - Overall: {overall_score:.1f} ({grade})")
        logger.info(f"  - Sidewalks: {sidewalk_score:.1f}")
        logger.info(f"  - Crossings: {crossing_score:.1f}")
        logger.info(f"  - Safety: {safety_score:.1f}")
        logger.info(f"  - Accessibility: {accessibility_score:.1f}")
        logger.info(f"  - Comfort: {comfort_score:.1f}")
        
        return PedestrianScore(
            overall_score=overall_score,
            sidewalk_score=sidewalk_score,
            crossing_score=crossing_score,
            safety_score=safety_score,
            accessibility_score=accessibility_score,
            comfort_score=comfort_score,
            grade=grade,
            description=description
        )
    
    def _calculate_sidewalk_score(self, sidewalks: List[Dict]) -> float:
        """Calculate score based on sidewalks"""
        if not sidewalks:
            return 0.0
        
        # Nearby sidewalks (within 100m)
        nearby_sidewalks = [s for s in sidewalks if s['distance'] <= 100]
        
        if not nearby_sidewalks:
            return 20.0  # Penalty for no nearby sidewalks
        
        # Total sidewalk length
        total_length = sum(s['length'] for s in nearby_sidewalks)
        
        # Sidewalk quality
        quality_bonus = 0
        for sidewalk in nearby_sidewalks:
            if sidewalk['surface'] in ['paved', 'asphalt', 'concrete']:
                quality_bonus += 10
            if sidewalk['lit'] == 'yes':
                quality_bonus += 5
            if sidewalk['wheelchair'] == 'yes':
                quality_bonus += 5
        
        # Score based on length + quality
        length_score = min(total_length / 10, 70)  # Max 70 points for length
        quality_score = min(quality_bonus, 30)     # Max 30 points for quality
        
        return min(length_score + quality_score, 100)
    
    def _calculate_crossing_score(self, crossings: List[Dict], signals: List[Dict]) -> float:
        """Calculate score based on crossings"""
        if not crossings and not signals:
            return 30.0  # Minimum score if no data
        
        # Nearby crossings (within 200m)
        nearby_crossings = [c for c in crossings if c['distance'] <= 200]
        nearby_signals = [s for s in signals if s['distance'] <= 200]
        
        base_score = 40.0
        
        # Bonus for crossings
        crossing_bonus = min(len(nearby_crossings) * 15, 30)
        
        # Bonus for traffic signals
        signal_bonus = min(len(nearby_signals) * 20, 30)
        
        # Quality bonus
        quality_bonus = 0
        for crossing in nearby_crossings:
            if crossing['signals'] == 'yes':
                quality_bonus += 5
            if crossing['tactile_paving'] == 'yes':
                quality_bonus += 3
        
        return min(base_score + crossing_bonus + signal_bonus + quality_bonus, 100)
    
    def _calculate_safety_score(self, speed_limits: List[Dict], lighting: List[Dict]) -> float:
        """Calculate score based on safety"""
        if not speed_limits:
            return 50.0
        
        # Nearby streets (within 150m)
        nearby_streets = [s for s in speed_limits if s['distance'] <= 150]
        
        if not nearby_streets:
            return 60.0
        
        # Score based on low speeds
        pedestrian_friendly_streets = [s for s in nearby_streets if s['pedestrian_friendly']]
        safety_ratio = len(pedestrian_friendly_streets) / len(nearby_streets)
        
        base_score = safety_ratio * 70
        
        # Bonus for lighting
        nearby_lighting = [l for l in lighting if l['distance'] <= 100]
        lighting_bonus = min(len(nearby_lighting) * 5, 30)
        
        return min(base_score + lighting_bonus, 100)
    
    def _calculate_accessibility_score(self, crossings: List[Dict], sidewalks: List[Dict]) -> float:
        """Calculate score based on accessibility"""
        base_score = 40.0
        
        # Bonus for accessibility features
        accessibility_features = 0
        
        for crossing in crossings:
            if crossing['tactile_paving'] == 'yes':
                accessibility_features += 1
            if crossing['wheelchair'] == 'yes':
                accessibility_features += 1
        
        for sidewalk in sidewalks:
            if sidewalk['wheelchair'] == 'yes':
                accessibility_features += 1
        
        accessibility_bonus = min(accessibility_features * 20, 60)
        
        return min(base_score + accessibility_bonus, 100)
    
    def _calculate_comfort_score(self, pedestrian_areas: List[Dict], sidewalks: List[Dict]) -> float:
        """Calculate score based on comfort"""
        base_score = 30.0
        
        # Bonus for pedestrian areas
        nearby_pedestrian_areas = [p for p in pedestrian_areas if p['distance'] <= 200]
        pedestrian_bonus = min(len(nearby_pedestrian_areas) * 25, 40)
        
        # Bonus for sidewalk quality
        comfort_bonus = 0
        for sidewalk in sidewalks:
            if sidewalk['surface'] in ['paved', 'asphalt', 'concrete']:
                comfort_bonus += 5
            if sidewalk['width'] and sidewalk['width'] != 'unknown':
                comfort_bonus += 3
        
        comfort_bonus = min(comfort_bonus, 30)
        
        return min(base_score + pedestrian_bonus + comfort_bonus, 100)
    
    def _get_pedestrian_grade(self, score: float) -> Tuple[str, str]:
        """Convert score to grade and description"""
        if score >= 90:
            return "A+", "Excellent Pedestrian Infrastructure"
        elif score >= 80:
            return "A", "Very Pedestrian-Friendly"
        elif score >= 70:
            return "B", "Good Pedestrian Infrastructure"
        elif score >= 60:
            return "C", "Fair Pedestrian Infrastructure"
        elif score >= 50:
            return "D", "Poor Pedestrian Infrastructure"
        else:
            return "F", "Very Poor Pedestrian Infrastructure" 