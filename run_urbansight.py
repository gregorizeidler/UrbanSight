#!/usr/bin/env python3
"""
🏙️ UrbanSight - Inteligência Imobiliária
Script de inicialização da aplicação

Execute este arquivo para iniciar o UrbanSight:
python run_urbansight.py
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Verifica se todas as dependências estão instaladas"""
    try:
        import streamlit
        import plotly
        import folium
        import pandas
        import requests
        print("✅ Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência não encontrada: {e}")
        print("💡 Execute: pip install -r requirements.txt")
        return False

def print_banner():
    """Exibe o banner do UrbanSight"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║    🏙️  U R B A N S I G H T                                   ║
    ║                                                               ║
    ║         Inteligência Imobiliária com Tecnologia de Ponta     ║
    ║                                                               ║
    ║    🚀 Versão 2.0 Professional                                ║
    ║    🗺️  Análise com OpenStreetMap + Multi-Agentes IA         ║
    ║    📊 Métricas Avançadas + Visualizações Interativas        ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Função principal"""
    print_banner()
    
    print("🔍 Verificando dependências...")
    if not check_requirements():
        print("\n❌ Por favor, instale as dependências antes de continuar.")
        print("💻 Execute: pip install -r requirements.txt")
        sys.exit(1)
    
    print("\n🚀 Iniciando UrbanSight...")
    print("🌐 A aplicação será aberta em: http://localhost:8501")
    print("⏰ Aguarde alguns segundos para o carregamento completo...")
    print("\n" + "="*60)
    print("🏙️  BEM-VINDO AO URBANSIGHT!")
    print("📍 Digite um endereço e descubra insights incríveis!")
    print("="*60 + "\n")
    
    try:
        # Executa o Streamlit
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "streamlit_app.py",
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao iniciar UrbanSight: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 UrbanSight encerrado pelo usuário.")
        print("💫 Obrigado por usar o UrbanSight - Inteligência Imobiliária!")
        sys.exit(0)

if __name__ == "__main__":
    main() 