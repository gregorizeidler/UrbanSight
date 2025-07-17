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
    
    # UrbanSight Branding
    APP_NAME = "UrbanSight"
    APP_VERSION = "2.0"
    APP_DESCRIPTION = "Inteligência Imobiliária com Tecnologia de Ponta" 