import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import overpy
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class POI:
    """Point of Interest data structure"""
    id: str
    name: str
    category: str
    subcategory: str
    lat: float
    lon: float
    distance: float
    tags: Dict[str, str]


@dataclass
class PropertyData:
    """Property location data structure"""
    address: str
    lat: float
    lon: float
    city: str
    state: str
    country: str
    postal_code: Optional[str] = None


class OSMDataCollector:
    """Agent specialized in collecting data from OpenStreetMap"""

    def __init__(self):
        self.geolocator = Nominatim(user_agent=Config.OSM_USER_AGENT)
        self.overpass_api = overpy.Overpass()
        self.config = Config()

    async def geocode_address(self, address: str) -> Optional[PropertyData]:
        """Convert address to coordinates and extract location data"""
        try:
            location = self.geolocator.geocode(address, timeout=10)
            if not location:
                logger.error(f"Could not geocode address: {address}")
                return None

            # Extract address components
            address_components = location.raw.get('address', {})

            return PropertyData(
                address=address,
                lat=location.latitude,
                lon=location.longitude,
                city=address_components.get('city', address_components.get('town', '')),
                state=address_components.get('state', ''),
                country=address_components.get('country', ''),
                postal_code=address_components.get('postcode')
            )

        except GeocoderTimedOut:
            logger.error(f"Geocoding timeout for address: {address}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding address {address}: {str(e)}")
            return None

    def _build_overpass_query(self, lat: float, lon: float, radius: int) -> str:
        """Build Overpass API query for POIs around location"""
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"](around:{radius},{lat},{lon});
          node["shop"](around:{radius},{lat},{lon});
          node["leisure"](around:{radius},{lat},{lon});
          node["tourism"](around:{radius},{lat},{lon});
          node["public_transport"](around:{radius},{lat},{lon});
          way["amenity"](around:{radius},{lat},{lon});
          way["shop"](around:{radius},{lat},{lon});
          way["leisure"](around:{radius},{lat},{lon});
          way["tourism"](around:{radius},{lat},{lon});
          way["public_transport"](around:{radius},{lat},{lon});
        );
        out center meta;
        """
        return query

    def _categorize_poi(self, tags: Dict[str, str]) -> Tuple[str, str]:
        """Categorize POI based on OSM tags"""
        # Check main category tags
        for tag_key in ['amenity', 'shop', 'leisure', 'tourism', 'public_transport']:
            if tag_key in tags:
                tag_value = tags[tag_key]

                # Map to our categories
                if tag_key == 'amenity':
                    if tag_value in ['school', 'university', 'college', 'kindergarten']:
                        return 'education', tag_value
                    elif tag_value in ['hospital', 'clinic', 'pharmacy', 'dentist']:
                        return 'healthcare', tag_value
                    elif tag_value in ['restaurant', 'cafe', 'fast_food', 'bar', 'pub']:
                        return 'food', tag_value
                    elif tag_value in ['bank', 'post_office', 'police', 'fire_station']:
                        return 'services', tag_value
                    elif tag_value in ['bus_station', 'subway_entrance', 'train_station']:
                        return 'transport', tag_value
                    else:
                        return 'services', tag_value

                elif tag_key == 'shop':
                    if tag_value in ['supermarket', 'mall', 'marketplace']:
                        return 'shopping', tag_value
                    else:
                        return 'shopping', tag_value

                elif tag_key == 'leisure':
                    if tag_value in ['park', 'playground', 'sports_centre']:
                        return 'leisure', tag_value
                    else:
                        return 'leisure', tag_value

                elif tag_key == 'public_transport':
                    return 'transport', tag_value

                elif tag_key == 'tourism':
                    return 'leisure', tag_value

        return 'other', 'unknown'

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))

        # Radius of earth in kilometers
        r = 6371
        return c * r * 1000  # Return in meters

    async def collect_pois(self, property_data: PropertyData, radius: int = None) -> List[POI]:
        """Collect Points of Interest around the property"""
        if radius is None:
            radius = self.config.DEFAULT_SEARCH_RADIUS

        try:
            query = self._build_overpass_query(property_data.lat, property_data.lon, radius)
            result = self.overpass_api.query(query)

            pois = []
            processed_ids = set()

            # Process nodes and ways
            for element in result.nodes + result.ways:
                # Avoid duplicates
                if element.id in processed_ids:
                    continue
                processed_ids.add(element.id)

                # Get coordinates
                if hasattr(element, 'lat') and hasattr(element, 'lon'):
                    lat, lon = element.lat, element.lon
                elif hasattr(element, 'center_lat') and hasattr(element, 'center_lon'):
                    lat, lon = element.center_lat, element.center_lon
                else:
                    continue

                # Calculate distance
                distance = self._calculate_distance(
                    property_data.lat, property_data.lon, lat, lon
                )

                # Skip if too far (safety check)
                if distance > radius:
                    continue

                # Categorize POI
                category, subcategory = self._categorize_poi(element.tags)

                # Get name
                name = element.tags.get('name', f"{subcategory.replace('_', ' ').title()}")

                poi = POI(
                    id=str(element.id),
                    name=name,
                    category=category,
                    subcategory=subcategory,
                    lat=lat,
                    lon=lon,
                    distance=distance,
                    tags=element.tags
                )

                pois.append(poi)

            logger.info(f"Collected {len(pois)} POIs around {property_data.address}")
            return pois

        except Exception as e:
            logger.error(f"Error collecting POIs: {str(e)}")
            return []

    async def get_property_details(self, lat: float, lon: float) -> Dict:
        """Get detailed property information from OSM"""
        try:
            # Query for building and landuse information
            query = f"""
            [out:json][timeout:25];
            (
              way["building"](around:50,{lat},{lon});
              way["landuse"](around:100,{lat},{lon});
              relation["landuse"](around:100,{lat},{lon});
            );
            out geom;
            """

            result = self.overpass_api.query(query)

            property_details = {
                'building_type': None,
                'building_levels': None,
                'landuse': None,
                'area': None
            }

            # Process buildings
            for way in result.ways:
                if 'building' in way.tags:
                    property_details['building_type'] = way.tags.get('building')
                    property_details['building_levels'] = way.tags.get('building:levels')
                    break

            # Process landuse
            for element in result.ways + result.relations:
                if 'landuse' in element.tags:
                    property_details['landuse'] = element.tags.get('landuse')
                    break

            return property_details

        except Exception as e:
            logger.error(f"Error getting property details: {str(e)}")
            return {}

    async def analyze_location(self, address: str) -> Optional[Dict]:
        """Complete location analysis - main method"""
        logger.info(f"Starting analysis for address: {address}")

        # Step 1: Geocode address
        property_data = await self.geocode_address(address)
        if not property_data:
            return None

        # Step 2: Collect POIs
        pois = await self.collect_pois(property_data)

        # Step 3: Get property details
        property_details = await self.get_property_details(
            property_data.lat, property_data.lon
        )

        return {
            'property': property_data,
            'pois': pois,
            'property_details': property_details,
            'total_pois': len(pois),
            'analysis_timestamp': asyncio.get_event_loop().time()
        } 