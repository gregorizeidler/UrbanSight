import streamlit as st
import requests
from datetime import datetime

def health_check():
    """Simple health check for deployment monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "UrbanSight",
        "version": "2.0"
    }

# Add to streamlit_app.py if needed
if __name__ == "__main__":
    # This can be used for health checks
    print("UrbanSight Health Check:", health_check())
