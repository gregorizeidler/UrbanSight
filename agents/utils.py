"""
Utility functions for agents
"""

def get_poi_category(poi):
    """Get category from POI object or dict"""
    return poi.category if hasattr(poi, 'category') else poi.get('category', 'other')

def get_poi_name(poi):
    """Get name from POI object or dict"""
    return poi.name if hasattr(poi, 'name') else poi.get('name', 'Unknown')

def get_poi_distance(poi):
    """Get distance from POI object or dict"""
    return poi.distance if hasattr(poi, 'distance') else poi.get('distance', 0)

def get_poi_subcategory(poi):
    """Get subcategory from POI object or dict"""
    return poi.subcategory if hasattr(poi, 'subcategory') else poi.get('subcategory', '') 