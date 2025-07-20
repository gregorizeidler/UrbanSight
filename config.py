import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # OpenStreetMap Configuration
    OSM_USER_AGENT = os.getenv("OSM_USER_AGENT", "UrbanSight/2.0")
    DEFAULT_SEARCH_RADIUS = int(os.getenv("DEFAULT_SEARCH_RADIUS", "1000"))
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # UrbanSight Scoring Weights
    WALK_SCORE_WEIGHTS = {
        "grocery": 0.15,        # Supermercados e alimentação básica
        "restaurant": 0.10,     # Restaurantes e alimentação
        "shopping": 0.05,       # Compras e varejo
        "school": 0.15,         # Educação e ensino
        "park": 0.10,           # Parques e áreas verdes
        "entertainment": 0.05,  # Entretenimento e cultura
        "healthcare": 0.10,     # Saúde e bem-estar
        "transport": 0.20,      # Transporte público
        "services": 0.10        # Serviços essenciais
    }
    
    # POI Categories for UrbanSight Analysis
    POI_CATEGORIES = {
        "education": ["school", "university", "college", "kindergarten", "library"],
        "healthcare": ["hospital", "clinic", "pharmacy", "dentist", "veterinary"],
        "shopping": ["supermarket", "mall", "shop", "marketplace", "convenience"],
        "transport": ["bus_station", "subway_entrance", "train_station", "taxi"],
        "leisure": ["park", "playground", "sports_centre", "cinema", "theatre"],
        "services": ["bank", "post_office", "police", "fire_station", "government"],
        "food": ["restaurant", "cafe", "fast_food", "bar", "pub"]
    }
    
    # Novos Pesos para Análises Especializadas
    ENVIRONMENTAL_WEIGHTS = {
        "microclimate": 0.3,
        "water_features": 0.25,
        "green_space": 0.25,
        "air_quality": 0.2
    }
    
    MOBILITY_WEIGHTS = {
        "public_transport": 0.4,
        "bike_infrastructure": 0.3,
        "parking": 0.2,
        "walkability": 0.1
    }
    
    URBAN_WEIGHTS = {
        "building_density": 0.25,
        "noise_pollution": 0.3,
        "infrastructure_quality": 0.25,
        "development_potential": 0.2
    }
    
    SAFETY_WEIGHTS = {
        "emergency_services": 0.4,
        "crime_prevention": 0.35,
        "lighting": 0.15,
        "visibility": 0.1
    }
    

    
    ECONOMY_WEIGHTS = {
        "business_diversity": 0.35,
        "cultural_richness": 0.3,
        "retail_accessibility": 0.35
    }
    
    SPECIAL_FEATURES_WEIGHTS = {
        "digital_infrastructure": 0.4,
        "accessibility": 0.35,
        "nightlife": 0.25
    }
    
    # Novas Categorias OSM para Análises Especializadas
    SPECIALIZED_OSM_CATEGORIES = {
        "environmental": {
            "natural": ["tree", "water", "forest", "park", "garden"],
            "waterway": ["river", "stream", "canal"],
            "landuse": ["forest", "grass", "meadow", "park"]
        },
        "mobility": {
            "highway": ["cycleway", "bus_stop"],
            "amenity": ["bicycle_rental", "parking", "fuel"],
            "public_transport": ["platform", "stop_position"],
            "railway": ["station", "halt"]
        },
        "urban_infrastructure": {
            "building": ["yes", "residential", "commercial", "industrial"],
            "power": ["line", "pole", "tower"],
            "man_made": ["mast", "tower", "antenna", "surveillance"]
        },
        "safety": {
            "amenity": ["hospital", "police", "fire_station"],
            "emergency": ["yes", "fire_hydrant", "defibrillator"],
            "highway": ["street_lamp"],
            "man_made": ["surveillance"]
        },

        "economy": {
            "shop": ["*"],
            "craft": ["*"],
            "office": ["*"],
            "tourism": ["museum", "gallery", "artwork"],
            "amenity": ["marketplace", "arts_centre"]
        },
        "special_features": {
            "amenity": ["internet_cafe", "coworking_space"],
            "accessibility": ["wheelchair", "tactile_paving"],
            "nightlife": ["bar", "nightclub", "pub"],
            "internet_access": ["yes", "wifi"]
        }
    }
    
    # UrbanSight Branding
    APP_NAME = "UrbanSight"
    APP_VERSION = "3.0"
    APP_DESCRIPTION = "Inteligência Imobiliária com Análise Completa OpenStreetMap"
    
    # Compatibility properties for lowercase access
    @property
    def openai_api_key(self):
        return self.OPENAI_API_KEY
    
    @property
    def gemini_api_key(self):
        return self.GEMINI_API_KEY 