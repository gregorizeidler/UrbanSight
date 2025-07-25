#!/bin/bash
# Render deployment startup script for UrbanSight

echo "🚀 Starting UrbanSight deployment..."

# Install system dependencies if needed
echo "📦 Installing system packages..."

# Start the Streamlit application
echo "🏙️ Launching UrbanSight Streamlit app..."
streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false
