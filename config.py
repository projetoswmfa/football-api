from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database - Supabase
    supabase_url: str = "https://lxcmoiqgmjfvrzteaonl.supabase.co"
    supabase_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx4Y21vaXFnbWpmdnJ6dGVhb25sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEyODkxMTMsImV4cCI6MjA2Njg2NTExM30.8ookpO3JQBwJSpW1Jhx0UkVBg-m8CoVSVU1b_VYPJes"
    database_url: str = "postgresql://postgres.lxcmoiqgmjfvrzteaonl:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    
    # Google Gemini AI
    gemini_api_key: str = "AIzaSyBpFb-rdZIVGIs-oZQ7VJlEnbPJGeTNnzI"
    
    # Redis para Celery
    redis_url: str = "redis://localhost:6379/0"
    
    # Configurações da API
    api_title: str = "Sports Data API"
    api_version: str = "1.0.0"
    debug: bool = True
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Rate Limiting
    requests_per_minute: int = 60
    max_concurrent_requests: int = 10
    
    # Scrapers Configuration
    enable_live_scraping: bool = True
    enable_team_scraping: bool = True
    enable_player_scraping: bool = True
    
    # Leagues to scrape
    leagues: List[str] = ["brasileirao", "champions-league", "premier-league", "la-liga"]
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # Scraping intervals (em segundos)
    live_matches_interval: int = 60  # 1 minuto
    team_stats_interval: int = 86400  # 1 dia
    player_stats_interval: int = 43200  # 12 horas
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instância global das configurações
settings = Settings()

# Criar diretório de logs se não existir
os.makedirs("logs", exist_ok=True) 