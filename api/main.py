from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime
import json

from agents.orchestrator import PropertyAnalysisOrchestrator, PropertyAnalysisResult
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UrbanSight API",
    description="API para análise imobiliária usando OpenStreetMap e Multi-Agentes IA",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = PropertyAnalysisOrchestrator()
config = Config()

# In-memory storage for analysis results (in production, use Redis or database)
analysis_cache = {}


# Pydantic models
class AnalysisRequest(BaseModel):
    address: str
    analysis_id: Optional[str] = None


class BatchAnalysisRequest(BaseModel):
    addresses: List[str]


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PropTech Analyzer API",
        "version": "1.0.0",
        "description": "API para análise imobiliária usando OpenStreetMap e Multi-Agentes",
        "endpoints": {
            "analyze": "/analyze",
            "result": "/result/{analysis_id}",
            "batch": "/batch-analyze",
            "map": "/map/{analysis_id}",
            "advanced_map": "/advanced-map/{analysis_id}/{map_type}",
            "analytics": "/analytics"
        }
    }


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Analyze property
@app.post("/analyze")
async def analyze_property(request: AnalysisRequest):
    """Analyze a property location"""

    try:
        logger.info(f"Analyzing property: {request.address}")

        # Run analysis
        result = await orchestrator.analyze_property(request.address, request.analysis_id)

        # Cache result
        analysis_cache[result.analysis_id] = result

        if result.success:
            logger.info(f"Analysis completed successfully: {result.analysis_id}")
            return {
                "success": True,
                "analysis_id": result.analysis_id,
                "message": "Analysis completed successfully",
                "data": {
                    "address": result.property_data.address,
                    "total_score": result.metrics.total_score,
                    "walk_score": result.metrics.walk_score.overall_score,
                    "pois_count": len(result.pois)
                }
            }
        else:
            logger.error(f"Analysis failed: {result.error_message}")
            return {
                "success": False,
                "analysis_id": result.analysis_id,
                "error": result.error_message
            }

    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get analysis result
@app.get("/result/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Get complete analysis result"""

    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = analysis_cache[analysis_id]

    if result.success:
        return orchestrator.export_analysis_report(result)
    else:
        return {
            "success": False,
            "analysis_id": analysis_id,
            "error": result.error_message
        }


# Batch analysis
@app.post("/batch-analyze")
async def batch_analyze(request: BatchAnalysisRequest):
    """Analyze multiple properties"""

    try:
        logger.info(f"Starting batch analysis for {len(request.addresses)} properties")

        results = await orchestrator.batch_analyze_properties(request.addresses)

        # Cache results
        for result in results:
            analysis_cache[result.analysis_id] = result

        return {
            "success": True,
            "total_properties": len(request.addresses),
            "successful_analyses": len(results),
            "analysis_ids": [r.analysis_id for r in results]
        }

    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get analysis map
@app.get("/map/{analysis_id}")
async def get_analysis_map(analysis_id: str):
    """Get interactive map for analysis"""

    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = analysis_cache[analysis_id]

    if result.success and result.map_html:
        return HTMLResponse(content=result.map_html)
    else:
        raise HTTPException(status_code=400, detail="Map not available for this analysis")


# Get advanced map visualization
@app.get("/advanced-map/{analysis_id}/{map_type}")
async def get_advanced_map(analysis_id: str, map_type: str):
    """Get specific advanced map visualization"""

    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = analysis_cache[analysis_id]

    if not result.success:
        raise HTTPException(status_code=400, detail="Analysis was not successful")

    if not result.advanced_maps or map_type not in result.advanced_maps:
        raise HTTPException(status_code=404, detail=f"Advanced map '{map_type}' not found")

    map_viz = result.advanced_maps[map_type]

    if map_viz.map_html:
        return HTMLResponse(content=map_viz.map_html)
    else:
        raise HTTPException(status_code=400, detail="Map visualization not available")


# List available advanced maps
@app.get("/advanced-maps/{analysis_id}")
async def list_advanced_maps(analysis_id: str):
    """List available advanced map visualizations for an analysis"""

    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = analysis_cache[analysis_id]

    if not result.success:
        raise HTTPException(status_code=400, detail="Analysis was not successful")

    if not result.advanced_maps:
        return {"available_maps": []}

    available_maps = {}
    for map_type, map_viz in result.advanced_maps.items():
        available_maps[map_type] = {
            "title": map_viz.title,
            "description": map_viz.description,
            "type": map_viz.map_type,
            "url": f"/advanced-map/{analysis_id}/{map_type}"
        }

    return {"available_maps": available_maps}


# Get analytics
@app.get("/analytics")
async def get_analytics():
    """Get system analytics"""

    total_analyses = len(analysis_cache)
    successful_analyses = sum(1 for r in analysis_cache.values() if r.success)
    failed_analyses = total_analyses - successful_analyses

    # Calculate average scores
    successful_results = [r for r in analysis_cache.values() if r.success]

    if successful_results:
        avg_walk_score = sum(r.metrics.walk_score.overall_score for r in successful_results) / len(successful_results)
        avg_total_score = sum(r.metrics.total_score for r in successful_results) / len(successful_results)

        # Most common categories
        all_categories = []
        for result in successful_results:
            all_categories.extend(result.metrics.category_counts.keys())

        from collections import Counter
        category_frequency = Counter(all_categories)

        # Advanced maps statistics
        advanced_maps_stats = {}
        for result in successful_results:
            if result.advanced_maps:
                for map_type in result.advanced_maps.keys():
                    advanced_maps_stats[map_type] = advanced_maps_stats.get(map_type, 0) + 1

        analytics_data = {
            "total_analyses": total_analyses,
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "success_rate": (successful_analyses / total_analyses * 100) if total_analyses > 0 else 0,
            "average_walk_score": avg_walk_score,
            "average_total_score": avg_total_score,
            "most_common_categories": dict(category_frequency.most_common(10)),
            "advanced_maps_generated": advanced_maps_stats
        }
    else:
        analytics_data = {
            "total_analyses": total_analyses,
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "success_rate": 0,
            "message": "No successful analyses yet"
        }

    return JSONResponse(content=analytics_data)


# Clear cache (for development)
@app.delete("/cache")
async def clear_cache():
    """Clear analysis cache"""
    global analysis_cache
    cache_size = len(analysis_cache)
    analysis_cache.clear()
    return {"message": f"Cache cleared. Removed {cache_size} analyses."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT) 