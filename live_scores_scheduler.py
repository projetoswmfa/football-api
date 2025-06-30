"""
Scheduler para Atualização Automática de Placares em Tempo Real
"""
import asyncio
import logging
from datetime import datetime
from scrapers.live_scores_scraper import scrape_live_scores
from config import settings
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveScoresScheduler:
    """Scheduler para atualização automática de placares"""
    
    def __init__(self):
        self.running = False
        self.update_interval = 30  # segundos
        self.supabase: Client = None
        
        try:
            self.supabase = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("✅ Supabase conectado para scheduler")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar Supabase: {e}")
    
    async def update_live_scores(self):
        """Atualizar placares uma vez"""
        try:
            logger.info("🔄 Atualizando placares...")
            
            live_matches = await scrape_live_scores()
            
            if not live_matches:
                logger.info("ℹ️ Nenhuma partida ao vivo")
                return 0
            
            updated_count = 0
            if self.supabase:
                for match in live_matches:
                    try:
                        existing = self.supabase.table('live_matches').select('*').eq('external_id', match['match_id']).execute()
                        
                        match_data = {
                            'external_id': match['match_id'],
                            'current_score_home': match['home_score'],
                            'current_score_away': match['away_score'],
                            'current_minute': match.get('minute', 0),
                            'status': match['status'],
                            'competition': match['competition'],
                            'home_team_name': match['home_team'],
                            'away_team_name': match['away_team'],
                            'venue': match.get('venue', ''),
                            'source': match['source'],
                            'last_updated': match['timestamp']
                        }
                        
                        if existing.data:
                            self.supabase.table('live_matches').update(match_data).eq('external_id', match['match_id']).execute()
                        else:
                            self.supabase.table('live_matches').insert(match_data).execute()
                        
                        updated_count += 1
                        
                    except Exception as db_error:
                        logger.error(f"❌ Erro DB: {db_error}")
                        continue
            
            logger.info(f"✅ {updated_count} placares atualizados")
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Erro na atualização: {e}")
            return 0
    
    async def run_scheduler(self):
        """Executar scheduler em loop"""
        logger.info(f"🚀 Scheduler iniciado (cada {self.update_interval}s)")
        self.running = True
        
        while self.running:
            try:
                await self.update_live_scores()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ Erro no loop: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Parar o scheduler"""
        self.running = False

async def main():
    """Função principal"""
    scheduler = LiveScoresScheduler()
    
    try:
        await scheduler.run_scheduler()
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler interrompido")
        scheduler.stop()

if __name__ == "__main__":
    logger.info("🏈 Iniciando Live Scores Scheduler...")
    asyncio.run(main()) 