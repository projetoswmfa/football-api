import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from datetime import datetime, timedelta
import pytz
from loguru import logger
from typing import Dict, Any

from config import settings
from scrapers.sofascore_scraper import scrape_live_matches
from scrapers.transfermarkt_scraper import scrape_transfermarkt_teams
from database import db_manager


class SchedulerManager:
    """Gerenciador de tarefas agendadas"""
    
    def __init__(self):
        # Configurar jobstores e executors
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,  # Combinar jobs atrasados
            'max_instances': 1,  # Máximo uma instância por job
            'misfire_grace_time': 300  # 5 minutos de tolerância
        }
        
        # Criar scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('America/Sao_Paulo')
        )
        
        self.is_running = False
        self.jobs_status = {}
    
    async def start(self):
        """Inicia o scheduler e agenda jobs"""
        if self.is_running:
            logger.warning("Scheduler já está rodando")
            return
        
        try:
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler iniciado com sucesso")
            
            # Agendar jobs se habilitados
            if settings.enable_live_scraping:
                await self._schedule_live_scraping()
            
            if settings.enable_team_scraping:
                await self._schedule_team_scraping()
            
            if settings.enable_player_scraping:
                await self._schedule_player_scraping()
            
            # Job de limpeza
            await self._schedule_cleanup_jobs()
            
            logger.info("Todos os jobs foram agendados")
            
        except Exception as e:
            logger.error(f"Erro ao iniciar scheduler: {e}")
            raise
    
    async def stop(self):
        """Para o scheduler"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Scheduler parado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao parar scheduler: {e}")
    
    async def _schedule_live_scraping(self):
        """Agenda scraping de partidas ao vivo"""
        try:
            # Executar a cada minuto durante horários de jogos
            self.scheduler.add_job(
                self._safe_live_scraping,
                'interval',
                seconds=settings.live_matches_interval,
                id='live_matches_scraping',
                name='Scraping de Partidas Ao Vivo',
                replace_existing=True
            )
            
            logger.info(f"Scraping ao vivo agendado a cada {settings.live_matches_interval} segundos")
            
        except Exception as e:
            logger.error(f"Erro ao agendar scraping ao vivo: {e}")
    
    async def _schedule_team_scraping(self):
        """Agenda scraping de times"""
        try:
            # Executar diariamente às 3:00 AM
            self.scheduler.add_job(
                self._safe_team_scraping,
                'cron',
                hour=3,
                minute=0,
                id='team_scraping',
                name='Scraping de Times',
                replace_existing=True
            )
            
            logger.info("Scraping de times agendado para 03:00 diariamente")
            
        except Exception as e:
            logger.error(f"Erro ao agendar scraping de times: {e}")
    
    async def _schedule_player_scraping(self):
        """Agenda scraping de jogadores"""
        try:
            # Executar a cada 12 horas
            self.scheduler.add_job(
                self._safe_player_scraping,
                'interval',
                seconds=settings.player_stats_interval,
                id='player_scraping',
                name='Scraping de Jogadores',
                replace_existing=True
            )
            
            logger.info(f"Scraping de jogadores agendado a cada {settings.player_stats_interval/3600:.1f} horas")
            
        except Exception as e:
            logger.error(f"Erro ao agendar scraping de jogadores: {e}")
    
    async def _schedule_cleanup_jobs(self):
        """Agenda jobs de limpeza"""
        try:
            # Limpeza diária às 2:00 AM
            self.scheduler.add_job(
                self._cleanup_old_data,
                'cron',
                hour=2,
                minute=0,
                id='cleanup_job',
                name='Limpeza de Dados Antigos',
                replace_existing=True
            )
            
            logger.info("Job de limpeza agendado para 02:00 diariamente")
            
        except Exception as e:
            logger.error(f"Erro ao agendar job de limpeza: {e}")
    
    async def _safe_live_scraping(self):
        """Wrapper seguro para scraping ao vivo"""
        job_id = 'live_matches_scraping'
        
        try:
            self.jobs_status[job_id] = {
                'status': 'running',
                'started_at': datetime.now(),
                'last_error': None
            }
            
            logger.debug("Iniciando scraping de partidas ao vivo")
            
            # Verificar se há partidas ao vivo primeiro
            live_count = await self._check_live_matches_count()
            
            if live_count > 0:
                matches_scraped = await scrape_live_matches()
                
                self.jobs_status[job_id].update({
                    'status': 'completed',
                    'completed_at': datetime.now(),
                    'matches_scraped': matches_scraped
                })
                
                logger.info(f"Scraping ao vivo concluído: {matches_scraped} partidas processadas")
            else:
                self.jobs_status[job_id].update({
                    'status': 'skipped',
                    'completed_at': datetime.now(),
                    'reason': 'Nenhuma partida ao vivo encontrada'
                })
                
                logger.debug("Scraping ao vivo pulado - nenhuma partida ao vivo")
            
        except Exception as e:
            self.jobs_status[job_id].update({
                'status': 'failed',
                'completed_at': datetime.now(),
                'last_error': str(e)
            })
            
            logger.error(f"Erro no scraping ao vivo: {e}")
    
    async def _safe_team_scraping(self):
        """Wrapper seguro para scraping de times"""
        job_id = 'team_scraping'
        
        try:
            self.jobs_status[job_id] = {
                'status': 'running',
                'started_at': datetime.now(),
                'last_error': None
            }
            
            logger.info("Iniciando scraping de times")
            
            total_teams = 0
            
            # Scraping para cada liga configurada
            for league in settings.leagues:
                try:
                    logger.info(f"Fazendo scraping da liga: {league}")
                    players_count = await scrape_transfermarkt_teams([league])
                    
                    total_teams += 1 if players_count > 0 else 0  # Contar como 1 time se encontrou jogadores
                    
                    logger.info(f"Liga {league}: {players_count} jogadores processados")
                    
                    # Delay entre ligas para evitar rate limiting
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Erro no scraping da liga {league}: {e}")
                    continue
            
            self.jobs_status[job_id].update({
                'status': 'completed',
                'completed_at': datetime.now(),
                'teams_scraped': total_teams
            })
            
            logger.info(f"Scraping de times concluído: {total_teams} times processados")
            
        except Exception as e:
            self.jobs_status[job_id].update({
                'status': 'failed',
                'completed_at': datetime.now(),
                'last_error': str(e)
            })
            
            logger.error(f"Erro no scraping de times: {e}")
    
    async def _safe_player_scraping(self):
        """Wrapper seguro para scraping de jogadores"""
        job_id = 'player_scraping'
        
        try:
            self.jobs_status[job_id] = {
                'status': 'running',
                'started_at': datetime.now(),
                'last_error': None
            }
            
            logger.info("Iniciando atualização de dados de jogadores")
            
            # Por enquanto, apenas log - implementação futura pode incluir
            # atualizações de valor de mercado, estatísticas, etc.
            
            self.jobs_status[job_id].update({
                'status': 'completed',
                'completed_at': datetime.now(),
                'note': 'Funcionalidade em desenvolvimento'
            })
            
            logger.info("Atualização de jogadores concluída")
            
        except Exception as e:
            self.jobs_status[job_id].update({
                'status': 'failed',
                'completed_at': datetime.now(),
                'last_error': str(e)
            })
            
            logger.error(f"Erro na atualização de jogadores: {e}")
    
    async def _cleanup_old_data(self):
        """Limpeza de dados antigos"""
        job_id = 'cleanup_job'
        
        try:
            self.jobs_status[job_id] = {
                'status': 'running',
                'started_at': datetime.now(),
                'last_error': None
            }
            
            logger.info("Iniciando limpeza de dados antigos")
            
            cleanup_stats = {}
            
            # Limpar dados ao vivo antigos (mais de 24 horas)
            cutoff_date = datetime.now() - timedelta(days=1)
            
            async with db_manager.get_connection() as conn:
                # Limpar live_matches antigos
                result = await conn.execute(
                    "DELETE FROM live_matches WHERE updated_at < $1",
                    cutoff_date
                )
                cleanup_stats['live_matches_deleted'] = int(result.split()[-1])
                
                # Limpar análises antigas (mais de 30 dias)
                analysis_cutoff = datetime.now() - timedelta(days=30)
                result = await conn.execute(
                    "DELETE FROM gemini_analyses WHERE created_at < $1",
                    analysis_cutoff
                )
                cleanup_stats['analyses_deleted'] = int(result.split()[-1])
                
                # Atualizar estatísticas de vacuum
                await conn.execute("VACUUM ANALYZE live_matches")
                await conn.execute("VACUUM ANALYZE gemini_analyses")
            
            self.jobs_status[job_id].update({
                'status': 'completed',
                'completed_at': datetime.now(),
                'cleanup_stats': cleanup_stats
            })
            
            logger.info(f"Limpeza concluída: {cleanup_stats}")
            
        except Exception as e:
            self.jobs_status[job_id].update({
                'status': 'failed',
                'completed_at': datetime.now(),
                'last_error': str(e)
            })
            
            logger.error(f"Erro na limpeza: {e}")
    
    async def _check_live_matches_count(self) -> int:
        """Verifica quantas partidas ao vivo existem"""
        try:
            async with db_manager.get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM matches WHERE status IN ('live', 'halftime')"
                )
                return result or 0
        except Exception as e:
            logger.error(f"Erro ao verificar partidas ao vivo: {e}")
            return 0
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Retorna status de um job específico"""
        return self.jobs_status.get(job_id, {'status': 'not_found'})
    
    def get_all_jobs_status(self) -> Dict[str, Any]:
        """Retorna status de todos os jobs"""
        return {
            'scheduler_running': self.is_running,
            'jobs': self.jobs_status,
            'scheduled_jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                for job in self.scheduler.get_jobs()
            ]
        }
    
    async def trigger_job_manually(self, job_id: str) -> bool:
        """Dispara um job manualmente"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"Job {job_id} disparado manualmente")
                return True
            else:
                logger.warning(f"Job {job_id} não encontrado")
                return False
        except Exception as e:
            logger.error(f"Erro ao disparar job {job_id}: {e}")
            return False
    
    async def pause_job(self, job_id: str) -> bool:
        """Pausa um job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} pausado")
            return True
        except Exception as e:
            logger.error(f"Erro ao pausar job {job_id}: {e}")
            return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume um job pausado"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumido")
            return True
        except Exception as e:
            logger.error(f"Erro ao resumir job {job_id}: {e}")
            return False


# Instância global do gerenciador
scheduler_manager = SchedulerManager()


# Funções auxiliares para uso em endpoints
async def get_scheduler_status():
    """Retorna status completo do scheduler"""
    return scheduler_manager.get_all_jobs_status()


async def trigger_scraping_job(job_type: str) -> bool:
    """Dispara job de scraping específico"""
    job_mapping = {
        'live': 'live_matches_scraping',
        'teams': 'team_scraping',
        'players': 'player_scraping',
        'cleanup': 'cleanup_job'
    }
    
    job_id = job_mapping.get(job_type)
    if not job_id:
        return False
    
    return await scheduler_manager.trigger_job_manually(job_id)


async def control_scraping_job(job_type: str, action: str) -> bool:
    """Controla job de scraping (pause/resume)"""
    job_mapping = {
        'live': 'live_matches_scraping',
        'teams': 'team_scraping', 
        'players': 'player_scraping'
    }
    
    job_id = job_mapping.get(job_type)
    if not job_id:
        return False
    
    if action == 'pause':
        return await scheduler_manager.pause_job(job_id)
    elif action == 'resume':
        return await scheduler_manager.resume_job(job_id)
    
    return False 