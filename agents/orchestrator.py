import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass, asdict
import folium
from folium import plugins
from datetime import datetime

from agents.osm_data_collector import OSMDataCollector, PropertyData, POI
from agents.neighborhood_analyst import NeighborhoodAnalyst, NeighborhoodMetrics
from agents.insight_generator import InsightGenerator, PropertyInsight
from agents.advanced_metrics import AdvancedMetricsCalculator, AdvancedMetrics
from agents.geo_visualizer import GeoVisualizer, MapVisualization
from agents.pedestrian_analyzer import PedestrianAnalyzer, PedestrianScore
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PropertyAnalysisResult:
    """Complete property analysis result"""
    property_data: PropertyData
    metrics: NeighborhoodMetrics
    insights: PropertyInsight
    pois: list
    map_html: str
    analysis_id: str
    timestamp: datetime
    success: bool
    advanced_metrics: Optional[AdvancedMetrics] = None
    advanced_maps: Optional[Dict[str, MapVisualization]] = None
    pedestrian_score: Optional[PedestrianScore] = None
    error_message: Optional[str] = None


class PropertyAnalysisOrchestrator:
    """Main orchestrator that coordinates all agents"""

    def __init__(self):
        self.config = Config()
        self.osm_collector = OSMDataCollector()
        self.neighborhood_analyst = NeighborhoodAnalyst()
        self.insight_generator = InsightGenerator()
        self.advanced_metrics_calculator = AdvancedMetricsCalculator()
        self.geo_visualizer = GeoVisualizer()
        self.pedestrian_analyzer = PedestrianAnalyzer()

    async def analyze_property(self, address: str, analysis_id: str = None) -> PropertyAnalysisResult:
        """Complete property analysis orchestration"""

        if analysis_id is None:
            analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting property analysis for: {address} (ID: {analysis_id})")

        try:
            # Step 1: Collect OSM data
            logger.info("Step 1: Collecting OSM data...")
            osm_data = await self.osm_collector.analyze_location(address)

            if not osm_data:
                return PropertyAnalysisResult(
                    property_data=None,
                    metrics=None,
                    insights=None,
                    pois=[],
                    map_html="",
                    analysis_id=analysis_id,
                    timestamp=datetime.now(),
                    success=False,
                    error_message="Could not geocode address or collect OSM data"
                )

            property_data = osm_data['property']
            pois = osm_data['pois']

            # Step 2: Analyze neighborhood
            logger.info("Step 2: Analyzing neighborhood metrics...")
            metrics = self.neighborhood_analyst.analyze_neighborhood(property_data, pois)

            # Step 3: Calculate advanced metrics
            logger.info("Step 3: Calculating advanced metrics...")
            advanced_metrics = self.advanced_metrics_calculator.calculate_all_metrics(pois)

            # Step 4: Analyze pedestrian infrastructure
            logger.info("Step 4: Analyzing pedestrian infrastructure...")
            pedestrian_infrastructure = await self.pedestrian_analyzer.collect_pedestrian_data(property_data)
            pedestrian_score = self.pedestrian_analyzer.calculate_pedestrian_score(pedestrian_infrastructure)

            # Step 5: Generate insights
            logger.info("Step 5: Generating insights with LLM...")
            insights = await self.insight_generator.generate_insights(property_data, metrics, pois)

            # Step 6: Create interactive map
            logger.info("Step 6: Creating interactive map...")
            map_html = self._create_interactive_map(property_data, pois, metrics, pedestrian_score)

            # Step 7: Create advanced maps
            logger.info("Step 7: Creating advanced map visualizations...")
            advanced_maps = self.geo_visualizer.create_all_advanced_maps(property_data, pois, metrics)

            logger.info(f"Analysis completed successfully for {address}")

            return PropertyAnalysisResult(
                property_data=property_data,
                metrics=metrics,
                insights=insights,
                pois=[asdict(poi) for poi in pois],  # Convert to dict for JSON serialization
                map_html=map_html,
                analysis_id=analysis_id,
                timestamp=datetime.now(),
                success=True,
                advanced_metrics=advanced_metrics,
                advanced_maps=advanced_maps,
                pedestrian_score=pedestrian_score
            )

        except Exception as e:
            logger.error(f"Error in property analysis: {str(e)}")
            return PropertyAnalysisResult(
                property_data=None,
                metrics=None,
                insights=None,
                pois=[],
                map_html="",
                analysis_id=analysis_id,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e)
            )

    def _create_interactive_map(
        self, property_data: PropertyData, pois: list,
        metrics: NeighborhoodMetrics, pedestrian_score: PedestrianScore = None
    ) -> str:
        """Create interactive Folium map with property and POIs"""

        # Create base map centered on property
        m = folium.Map(
            location=[property_data.lat, property_data.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )

        # Add property marker
        folium.Marker(
            location=[property_data.lat, property_data.lon],
            popup=f"""
            <div style="width: 300px;">
                <h4>{property_data.address}</h4>
                <p><strong>Walk Score:</strong> {metrics.walk_score.overall_score:.1f}/100 ({metrics.walk_score.grade})</p>
                <p><strong>Score Total:</strong> {metrics.total_score:.1f}/100</p>
                <p><strong>Acessibilidade:</strong> {metrics.accessibility_score:.1f}/100</p>
                <p><strong>Conveniência:</strong> {metrics.convenience_score:.1f}/100</p>
                {f'<p><strong>Pedestrian Score:</strong> {pedestrian_score.overall_score:.1f}/100 ({pedestrian_score.grade})</p>' if pedestrian_score else ''}
            </div>
            """,
            tooltip="Propriedade Analisada",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Define category colors and icons
        category_config = {
            'education': {'color': 'blue', 'icon': 'graduation-cap'},
            'healthcare': {'color': 'green', 'icon': 'plus'},
            'shopping': {'color': 'orange', 'icon': 'shopping-cart'},
            'transport': {'color': 'purple', 'icon': 'bus'},
            'leisure': {'color': 'darkgreen', 'icon': 'tree'},
            'services': {'color': 'gray', 'icon': 'cog'},
            'food': {'color': 'darkred', 'icon': 'cutlery'},
            'other': {'color': 'lightgray', 'icon': 'question'}
        }

        # Add POI markers
        for poi in pois:
            config = category_config.get(poi.category, category_config['other'])

            folium.Marker(
                location=[poi.lat, poi.lon],
                popup=f"""
                <div style="width: 250px;">
                    <h5>{poi.name}</h5>
                    <p><strong>Categoria:</strong> {poi.category.title()}</p>
                    <p><strong>Tipo:</strong> {poi.subcategory.replace('_', ' ').title()}</p>
                    <p><strong>Distância:</strong> {poi.distance:.0f}m</p>
                </div>
                """,
                tooltip=f"{poi.name} ({poi.distance:.0f}m)",
                icon=folium.Icon(
                    color=config['color'],
                    icon=config['icon'],
                    prefix='fa'
                )
            ).add_to(m)

        # Add search radius circle
        folium.Circle(
            location=[property_data.lat, property_data.lon],
            radius=1000,
            popup="Raio de análise (1km)",
            color='blue',
            fill=True,
            fillOpacity=0.1
        ).add_to(m)

        # Add marker clusters for better visualization
        plugins.MarkerCluster().add_to(m)

        # Add legend
        legend_html = """
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>Legenda</h4>
        <p><i class="fa fa-home" style="color:red"></i> Propriedade</p>
        <p><i class="fa fa-graduation-cap" style="color:blue"></i> Educação</p>
        <p><i class="fa fa-plus" style="color:green"></i> Saúde</p>
        <p><i class="fa fa-shopping-cart" style="color:orange"></i> Compras</p>
        <p><i class="fa fa-bus" style="color:purple"></i> Transporte</p>
        <p><i class="fa fa-tree" style="color:darkgreen"></i> Lazer</p>
        <p><i class="fa fa-cutlery" style="color:darkred"></i> Alimentação</p>
        <p><i class="fa fa-cog" style="color:gray"></i> Serviços</p>
        </div>
        """

        m.get_root().html.add_child(folium.Element(legend_html))

        # Add fullscreen button
        plugins.Fullscreen().add_to(m)

        # Return HTML string
        return m._repr_html_()

    def get_advanced_map(self, analysis_id: str, map_type: str) -> Optional[MapVisualization]:
        """Get specific advanced map from analysis result"""
        # This would typically retrieve from cache/database
        # For now, return None - implementation depends on storage strategy
        return None

    def export_analysis_report(self, result: PropertyAnalysisResult) -> Dict:
        """Export complete analysis report as structured data"""

        if not result.success:
            return {
                'success': False,
                'error': result.error_message,
                'analysis_id': result.analysis_id,
                'timestamp': result.timestamp.isoformat()
            }

        # Base report
        report = {
            'success': True,
            'analysis_id': result.analysis_id,
            'timestamp': result.timestamp.isoformat(),
            'property': {
                'address': result.property_data.address,
                'city': result.property_data.city,
                'state': result.property_data.state,
                'coordinates': {
                    'lat': result.property_data.lat,
                    'lon': result.property_data.lon
                }
            },
            'scores': {
                'walk_score': result.metrics.walk_score.overall_score,
                'walk_score_grade': result.metrics.walk_score.grade,
                'accessibility_score': result.metrics.accessibility_score,
                'convenience_score': result.metrics.convenience_score,
                'safety_score': result.metrics.safety_score,
                'quality_of_life_score': result.metrics.quality_of_life_score,
                'total_score': result.metrics.total_score
            },
            'pois': {
                'total_count': len(result.pois),
                'by_category': result.metrics.category_counts,
                'density_per_km2': result.metrics.poi_density
            },
            'insights': {
                'executive_summary': result.insights.executive_summary,
                'strengths': result.insights.strengths,
                'concerns': result.insights.concerns,
                'recommendations': result.insights.recommendations,
                'ideal_resident_profile': result.insights.ideal_resident_profile
            }
        }

        # Add advanced metrics if available
        if result.advanced_metrics:
            report['advanced_metrics'] = {
                'service_density': {
                    'variety_score': result.advanced_metrics.service_density.service_variety_score,
                    'completeness_score': result.advanced_metrics.service_density.completeness_score,
                    'total_services': result.advanced_metrics.service_density.total_services
                },
                'urban_diversity': {
                    'shannon_index': result.advanced_metrics.urban_diversity.shannon_diversity_index,
                    'variety_count': result.advanced_metrics.urban_diversity.service_variety_count,
                    'dominant_category': result.advanced_metrics.urban_diversity.dominant_category
                },
                'lifestyle_scores': {
                    'daily_life': result.advanced_metrics.lifestyle.daily_life_score,
                    'entertainment': result.advanced_metrics.lifestyle.entertainment_score,
                    'family_friendliness': result.advanced_metrics.lifestyle.family_friendliness,
                    'professional': result.advanced_metrics.lifestyle.professional_score
                },
                'green_space_score': result.advanced_metrics.green_space_score,
                'urban_intensity_score': result.advanced_metrics.urban_intensity_score
            }

        # Add advanced maps info if available
        if result.advanced_maps:
            report['advanced_maps'] = {
                map_type: {
                    'title': map_viz.title,
                    'description': map_viz.description,
                    'type': map_viz.map_type
                }
                for map_type, map_viz in result.advanced_maps.items()
            }

        return report

    async def batch_analyze_properties(self, addresses: list) -> list:
        """Analyze multiple properties in batch"""

        logger.info(f"Starting batch analysis for {len(addresses)} properties")

        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.config.MAX_CONCURRENT_REQUESTS)

        async def limited_analyze(address):
            async with semaphore:
                return await self.analyze_property(address)

        # Execute analyses concurrently
        tasks = [limited_analyze(address) for address in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error analyzing {addresses[i]}: {str(result)}")
            else:
                valid_results.append(result)

        logger.info(f"Batch analysis completed: {len(valid_results)}/{len(addresses)} successful")

        return valid_results 