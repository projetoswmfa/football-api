"""
Scraper básico para dados do WhoScored
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WhoScoredScraper:
    """Scraper básico para dados do WhoScored"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://www.whoscored.com"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_match_stats(self, match_name: str) -> Dict[str, Any]:
        """Busca estatísticas de uma partida (dados simulados por enquanto)"""
        try:
            # Simular estatísticas por enquanto
            stats = {
                'match_name': match_name,
                'possession_home': 55,
                'possession_away': 45,
                'shots_home': 8,
                'shots_away': 12,
                'shots_on_target_home': 3,
                'shots_on_target_away': 5,
                'corners_home': 4,
                'corners_away': 7,
                'fouls_home': 11,
                'fouls_away': 9,
                'yellow_cards_home': 2,
                'yellow_cards_away': 1,
                'red_cards_home': 0,
                'red_cards_away': 0,
                'expected_goals_home': 1.2,
                'expected_goals_away': 2.1,
                'pass_accuracy_home': 87.5,
                'pass_accuracy_away': 82.3
            }
            
            logger.info(f"Estatísticas simuladas criadas para {match_name}")
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {}

async def scrape_whoscored_stats(matches: List[str]):
    """Função principal para scraping do WhoScored"""
    try:
        async with WhoScoredScraper() as scraper:
            all_stats = []
            
            for match in matches:
                logger.info(f"Buscando estatísticas para {match}...")
                stats = await scraper.get_match_stats(match)
                if stats:
                    all_stats.append(stats)
                
                await asyncio.sleep(1)  # Rate limiting
            
            logger.info(f"✅ Estatísticas obtidas para {len(all_stats)} partidas")
            return all_stats
            
    except Exception as e:
        logger.error(f"Erro no scraping do WhoScored: {e}")
        return [] 