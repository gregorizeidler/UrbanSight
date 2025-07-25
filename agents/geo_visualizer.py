import folium
from folium import plugins
from folium.plugins import HeatMap
import numpy as np
from typing import List, Dict, Optional
from sklearn.cluster import DBSCAN
import logging
from dataclasses import dataclass

from agents.osm_data_collector import POI, PropertyData
from agents.neighborhood_analyst import NeighborhoodMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MapVisualization:
    """Container for map visualization data"""
    map_html: str
    map_type: str
    title: str
    description: str


class GeoVisualizer:
    """Advanced geographic visualizations using existing OSM data"""

    def __init__(self):
        self.category_colors = {
            'education': '#2E86AB',
            'healthcare': '#A23B72',
            'shopping': '#F18F01',
            'transport': '#C73E1D',
            'leisure': '#4CAF50',
            'services': '#9C27B0',
            'food': '#FF5722',
            'other': '#607D8B'
        }

    def create_category_heatmap(
        self, property_data: PropertyData, pois: List[POI],
        category: str
    ) -> MapVisualization:
        """Create heatmap for specific POI category"""

        # Filter POIs by category
        category_pois = [poi for poi in pois if poi.category == category]

        if not category_pois:
            logger.warning(f"No POIs found for category: {category}")
            return self._create_empty_map(property_data, f"No {category} POIs found")

        # Create base map
        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b>",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Prepare heat data (lat, lon, weight)
        heat_data = []
        for poi in category_pois:
            # Weight based on inverse distance (closer = more weight)
            weight = max(0.1, 1 - (float(poi.distance) / 1000))
            heat_data.append([float(poi.lat), float(poi.lon), weight])

        # Add heatmap
        HeatMap(
            heat_data,
            radius=20,
            blur=15,
            max_zoom=1,
            gradient={
                0.0: 'blue',
                0.3: 'cyan',
                0.6: 'lime',
                0.8: 'yellow',
                1.0: 'red'
            }
        ).add_to(m)

        # Add individual markers
        for poi in category_pois:
            folium.CircleMarker(
                location=[poi.lat, poi.lon],
                radius=5,
                popup=f"""
                <div style="width: 200px;">
                    <h5>{poi.name}</h5>
                    <p><strong>Tipo:</strong> {poi.subcategory.replace('_', ' ').title()}</p>
                    <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                </div>
                """,
                tooltip=f"{poi.name} ({poi.distance:.0f}m)",
                color=self.category_colors.get(category, '#607D8B'),
                fill=True,
                fillOpacity=0.7
            ).add_to(m)

        # Add legend
        legend_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; width: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px;">
        <h4>Densidade: {category.title()}</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        <p><i class="fa fa-circle" style="color:{self.category_colors.get(category, '#607D8B')}"></i> {category.title()}</p>
        <p><strong>Total:</strong> {len(category_pois)} locais</p>
        <p><strong>Mais próximo:</strong> {min(poi.distance for poi in category_pois):.0f}m</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="heatmap",
            title=f"Densidade de {category.title()}",
            description=f"Mapa de calor mostrando densidade de {len(category_pois)} locais de {category}"
        )

    def create_distance_zones_map(self, property_data: PropertyData, pois: List[POI]) -> MapVisualization:
        """Create map with distance zones and POIs colored by distance"""

        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b>",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Distance zones
        zones = [
            (300, '#4CAF50', 'Muito Próximo'),
            (600, '#FFC107', 'Próximo'),
            (1000, '#FF5722', 'Caminhável')
        ]

        # Add distance circles
        for distance, color, label in zones:
            folium.Circle(
                location=[property_data.lat, property_data.lon],
                radius=distance,
                popup=f"<b>{label}</b><br>Raio: {distance}m",
                color=color,
                fill=True,
                fillOpacity=0.1,
                weight=2
            ).add_to(m)

        # Color POIs by distance
        zone_counts = {label: 0 for _, _, label in zones}

        for poi in pois:
            # Determine zone
            if poi.distance <= 300:
                color = '#4CAF50'
                zone = 'Muito Próximo'
            elif poi.distance <= 600:
                color = '#FFC107'
                zone = 'Próximo'
            else:
                color = '#FF5722'
                zone = 'Caminhável'

            zone_counts[zone] += 1

            # Add marker
            folium.CircleMarker(
                location=[poi.lat, poi.lon],
                radius=6,
                popup=f"""
                <div style="width: 200px;">
                    <h5>{poi.name}</h5>
                    <p><strong>Categoria:</strong> {poi.category.title()}</p>
                    <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                    <p><strong>Zona:</strong> {zone}</p>
                </div>
                """,
                tooltip=f"{poi.name} ({poi.distance:.0f}m)",
                color=color,
                fill=True,
                fillOpacity=0.8
            ).add_to(m)

        # Add legend
        legend_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; width: 220px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px;">
        <h4>Zonas de Distância</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        <p><i class="fa fa-circle" style="color:#4CAF50"></i> Muito Próximo (≤300m): {zone_counts['Muito Próximo']}</p>
        <p><i class="fa fa-circle" style="color:#FFC107"></i> Próximo (300-600m): {zone_counts['Próximo']}</p>
        <p><i class="fa fa-circle" style="color:#FF5722"></i> Caminhável (600-1000m): {zone_counts['Caminhável']}</p>
        <p><strong>Total POIs:</strong> {len(pois)}</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="distance_zones",
            title="Zonas de Distância",
            description=f"POIs organizados por proximidade em {len(pois)} locais"
        )

    def create_service_clusters_map(self, property_data: PropertyData, pois: List[POI]) -> MapVisualization:
        """Create map showing service clusters using DBSCAN"""

        if len(pois) < 3:
            return self._create_empty_map(property_data, "Insufficient POIs for clustering")

        # Prepare coordinates for clustering
        coords = np.array([[poi.lat, poi.lon] for poi in pois])

        # Apply DBSCAN clustering
        # eps=0.001 ≈ ~100m, min_samples=3
        clustering = DBSCAN(eps=0.001, min_samples=3).fit(coords)

        # Create base map
        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b>",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Colors for clusters
        cluster_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                          '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']

        # Group POIs by cluster
        clusters = {}
        noise_pois = []

        for i, poi in enumerate(pois):
            cluster_id = clustering.labels_[i]
            if cluster_id == -1:
                noise_pois.append(poi)
            else:
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(poi)

        # Add cluster markers
        for cluster_id, cluster_pois in clusters.items():
            color = cluster_colors[cluster_id % len(cluster_colors)]

            # Calculate cluster center
            center_lat = np.mean([poi.lat for poi in cluster_pois])
            center_lon = np.mean([poi.lon for poi in cluster_pois])

            # Add cluster center marker
            folium.Marker(
                location=[center_lat, center_lon],
                popup=f"""
                <div style="width: 200px;">
                    <h5>Cluster {cluster_id + 1}</h5>
                    <p><strong>Serviços:</strong> {len(cluster_pois)}</p>
                    <p><strong>Categorias:</strong> {len(set(poi.category for poi in cluster_pois))}</p>
                </div>
                """,
                tooltip=f"Cluster {cluster_id + 1} ({len(cluster_pois)} serviços)",
                icon=folium.Icon(color='black', icon='star', prefix='fa')
            ).add_to(m)

            # Add individual POIs in cluster
            for poi in cluster_pois:
                folium.CircleMarker(
                    location=[poi.lat, poi.lon],
                    radius=5,
                    popup=f"""
                    <div style="width: 200px;">
                        <h5>{poi.name}</h5>
                        <p><strong>Cluster:</strong> {cluster_id + 1}</p>
                        <p><strong>Categoria:</strong> {poi.category.title()}</p>
                        <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                    </div>
                    """,
                    tooltip=f"Cluster {cluster_id + 1}: {poi.name}",
                    color=color,
                    fill=True,
                    fillOpacity=0.7
                ).add_to(m)

        # Add noise POIs (not in any cluster)
        for poi in noise_pois:
            folium.CircleMarker(
                location=[poi.lat, poi.lon],
                radius=4,
                popup=f"""
                <div style="width: 200px;">
                    <h5>{poi.name}</h5>
                    <p><strong>Status:</strong> Isolado</p>
                    <p><strong>Categoria:</strong> {poi.category.title()}</p>
                    <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                </div>
                """,
                tooltip=f"Isolado: {poi.name}",
                color='gray',
                fill=True,
                fillOpacity=0.5
            ).add_to(m)

        # Add legend
        legend_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; width: 220px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px;">
        <h4>Clusters de Serviços</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        <p><i class="fa fa-star" style="color:black"></i> Centro do Cluster</p>
        <p><strong>Clusters encontrados:</strong> {len(clusters)}</p>
        <p><strong>Serviços isolados:</strong> {len(noise_pois)}</p>
        <p><strong>Total POIs:</strong> {len(pois)}</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="service_clusters",
            title="Clusters de Serviços",
            description=f"Identificados {len(clusters)} clusters de serviços próximos"
        )

    def create_walkability_directions_map(self, property_data: PropertyData, pois: List[POI]) -> MapVisualization:
        """Create map showing walkability by direction (N, S, E, W)"""

        # Categorize POIs by direction
        directions = {'Norte': [], 'Sul': [], 'Leste': [], 'Oeste': []}

        for poi in pois:
            lat_diff = float(poi.lat) - float(property_data.lat)
            lon_diff = float(poi.lon) - float(property_data.lon)

            if abs(lat_diff) > abs(lon_diff):
                if lat_diff > 0:
                    directions['Norte'].append(poi)
                else:
                    directions['Sul'].append(poi)
            else:
                if lon_diff > 0:
                    directions['Leste'].append(poi)
                else:
                    directions['Oeste'].append(poi)

        # Create base map
        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b>",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Direction colors
        direction_colors = {
            'Norte': '#2196F3',
            'Sul': '#4CAF50',
            'Leste': '#FF9800',
            'Oeste': '#9C27B0'
        }

        # Add directional sectors
        import math

        for direction, color in direction_colors.items():
            # Calculate sector boundaries
            if direction == 'Norte':
                start_angle = 315
                end_angle = 45
            elif direction == 'Leste':
                start_angle = 45
                end_angle = 135
            elif direction == 'Sul':
                start_angle = 135
                end_angle = 225
            else:  # Oeste
                start_angle = 225
                end_angle = 315

            # Add sector visualization (simplified as markers)
            angle_rad = math.radians((start_angle + end_angle) / 2)
            sector_lat = property_data.lat + 0.005 * math.cos(angle_rad)
            sector_lon = property_data.lon + 0.005 * math.sin(angle_rad)

            folium.Marker(
                location=[sector_lat, sector_lon],
                popup=f"""
                <div style="width: 200px;">
                    <h5>Direção: {direction}</h5>
                    <p><strong>POIs:</strong> {len(directions[direction])}</p>
                    <p><strong>Categorias:</strong> {len(set(poi.category for poi in directions[direction]))}</p>
                </div>
                """,
                tooltip=f"{direction} ({len(directions[direction])} POIs)",
                icon=folium.Icon(color='white', icon='arrow-up', prefix='fa')
            ).add_to(m)

        # Add POIs colored by direction
        for direction, direction_pois in directions.items():
            color = direction_colors[direction]

            for poi in direction_pois:
                folium.CircleMarker(
                    location=[poi.lat, poi.lon],
                    radius=5,
                    popup=f"""
                    <div style="width: 200px;">
                        <h5>{poi.name}</h5>
                        <p><strong>Direção:</strong> {direction}</p>
                        <p><strong>Categoria:</strong> {poi.category.title()}</p>
                        <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                    </div>
                    """,
                    tooltip=f"{direction}: {poi.name}",
                    color=color,
                    fill=True,
                    fillOpacity=0.7
                ).add_to(m)

        # Calculate walkability score by direction
        direction_scores = {}
        for direction, direction_pois in directions.items():
            if direction_pois:
                avg_distance = np.mean([float(poi.distance) for poi in direction_pois])
                poi_count = len(direction_pois)
                # Simple score: more POIs and closer = better
                score = min(100, (poi_count * 10) + (1000 - float(avg_distance)) / 10)
                direction_scores[direction] = score
            else:
                direction_scores[direction] = 0

        # Add legend
        legend_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; width: 220px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px;">
        <h4>Caminhabilidade por Direção</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        """

        for direction, color in direction_colors.items():
            count = len(directions[direction])
            score = direction_scores[direction]
            legend_html += f'<p><i class="fa fa-circle" style="color:{color}"></i> {direction}: {count} POIs (Score: {score:.0f})</p>'

        legend_html += f"""
        <p><strong>Melhor direção:</strong> {max(direction_scores, key=direction_scores.get)}</p>
        </div>
        """

        m.get_root().html.add_child(folium.Element(legend_html))

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="walkability_directions",
            title="Caminhabilidade por Direção",
            description=f"Análise direcional de {len(pois)} POIs"
        )

    def create_service_gaps_map(self, property_data: PropertyData, pois: List[POI]) -> MapVisualization:
        """Create map highlighting service gaps"""

        # Analyze service coverage
        categories = ['education', 'healthcare', 'shopping', 'transport', 'leisure', 'food', 'services']

        coverage_analysis = {}
        for category in categories:
            category_pois = [poi for poi in pois if poi.category == category]
            if category_pois:
                closest_distance = min(poi.distance for poi in category_pois)
                coverage_analysis[category] = {
                    'count': len(category_pois),
                    'closest_distance': closest_distance,
                    'status': 'good' if closest_distance <= 500 else 'poor' if closest_distance <= 800 else 'critical'
                }
            else:
                coverage_analysis[category] = {
                    'count': 0,
                    'closest_distance': float('inf'),
                    'status': 'missing'
                }

        # Create base map
        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b>",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Status colors
        status_colors = {
            'good': '#4CAF50',
            'poor': '#FF9800',
            'critical': '#F44336',
            'missing': '#9E9E9E'
        }

        # Add coverage circles for each category
        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False)

        for i, category in enumerate(categories):
            analysis = coverage_analysis[category]
            color = status_colors[analysis['status']]

            # Position around property
            angle = angles[i]
            marker_lat = property_data.lat + 0.003 * np.cos(angle)
            marker_lon = property_data.lon + 0.003 * np.sin(angle)

            # Add category status marker
            folium.Marker(
                location=[marker_lat, marker_lon],
                popup=f"""
                <div style="width: 200px;">
                    <h5>{category.title()}</h5>
                    <p><strong>Status:</strong> {analysis['status'].title()}</p>
                    <p><strong>Quantidade:</strong> {analysis['count']}</p>
                    <p><strong>Mais próximo:</strong> {analysis['closest_distance']:.0f}m</p>
                </div>
                """,
                tooltip=f"{category.title()}: {analysis['status']}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)

            # Add coverage circle if service exists
            if analysis['status'] != 'missing':
                folium.Circle(
                    location=[property_data.lat, property_data.lon],
                    radius=analysis['closest_distance'],
                    popup=f"Cobertura: {category.title()}",
                    color=color,
                    fill=True,
                    fillOpacity=0.1,
                    weight=1
                ).add_to(m)

        # Add all POIs
        for poi in pois:
            analysis = coverage_analysis[poi.category]
            color = status_colors[analysis['status']]

            folium.CircleMarker(
                location=[poi.lat, poi.lon],
                radius=4,
                popup=f"""
                <div style="width: 200px;">
                    <h5>{poi.name}</h5>
                    <p><strong>Categoria:</strong> {poi.category.title()}</p>
                    <p><strong>Status:</strong> {analysis['status'].title()}</p>
                    <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                </div>
                """,
                tooltip=f"{poi.name} ({analysis['status']})",
                color=color,
                fill=True,
                fillOpacity=0.7
            ).add_to(m)

        # Count gaps
        gaps = sum(1 for analysis in coverage_analysis.values() if analysis['status'] in ['missing', 'critical'])

        # Add legend
        legend_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; width: 220px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px;">
        <h4>Análise de Gaps de Serviços</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        <p><i class="fa fa-circle" style="color:#4CAF50"></i> Boa cobertura (≤500m)</p>
        <p><i class="fa fa-circle" style="color:#FF9800"></i> Cobertura ruim (500-800m)</p>
        <p><i class="fa fa-circle" style="color:#F44336"></i> Cobertura crítica (>800m)</p>
        <p><i class="fa fa-circle" style="color:#9E9E9E"></i> Serviço ausente</p>
        <p><strong>Gaps identificados:</strong> {gaps}/{len(categories)}</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="service_gaps",
            title="Análise de Gaps de Serviços",
            description=f"Identificados {gaps} gaps de serviços em {len(categories)} categorias"
        )

    def create_all_advanced_maps(
        self, property_data: PropertyData, pois: List[POI],
        metrics: NeighborhoodMetrics
    ) -> Dict[str, MapVisualization]:
        """Create all advanced map visualizations"""

        logger.info(f"Creating advanced maps for {len(pois)} POIs")

        maps = {}

        try:
            # 1. Distance zones map
            maps['distance_zones'] = self.create_distance_zones_map(property_data, pois)

            # 2. Service clusters map
            maps['service_clusters'] = self.create_service_clusters_map(property_data, pois)

            # 3. Walkability directions map
            maps['walkability_directions'] = self.create_walkability_directions_map(property_data, pois)

            # 4. Service gaps map
            maps['service_gaps'] = self.create_service_gaps_map(property_data, pois)

            # 5. Category heatmaps
            main_categories = ['food', 'transport', 'healthcare', 'education', 'shopping']
            for category in main_categories:
                if any(poi.category == category for poi in pois):
                    maps[f'heatmap_{category}'] = self.create_category_heatmap(property_data, pois, category)

            logger.info(f"Successfully created {len(maps)} advanced maps")

        except Exception as e:
            logger.error(f"Error creating advanced maps: {str(e)}")

        return maps

    def _create_empty_map(self, property_data: PropertyData, message: str) -> MapVisualization:
        """Create empty map with message"""

        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"<b>{property_data.address}</b><br>{message}",
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        return MapVisualization(
            map_html=m._repr_html_(),
            map_type="empty",
            title="Mapa Vazio",
            description=message
        ) 