import asyncpg
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from supabase import create_client, Client
from config import settings
from loguru import logger
import json


class DatabaseManager:
    """Gerenciador de conexões com o banco de dados"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.supabase: Optional[Client] = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Inicializa cliente Supabase"""
        try:
            self.supabase = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Cliente Supabase inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar Supabase: {e}")
            raise
    
    async def initialize_pool(self):
        """Inicializa pool de conexões AsyncPG"""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Melhora performance para queries simples
                }
            )
            logger.info("Pool de conexões inicializado com sucesso")
            
            # Testa conexão
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                logger.info("Conexão com banco testada com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar pool de conexões: {e}")
            raise
    
    async def close_pool(self):
        """Fecha pool de conexões"""
        if self.pool:
            await self.pool.close()
            logger.info("Pool de conexões fechado")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager para obter conexão do pool"""
        if not self.pool:
            raise RuntimeError("Pool de conexões não inicializado")
        
        async with self.pool.acquire() as connection:
            yield connection


# Instância global do gerenciador de banco
db_manager = DatabaseManager()


class BaseRepository:
    """Classe base para repositórios de dados"""
    
    def __init__(self):
        self.db = db_manager
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Executa query e retorna resultados como dicionários"""
        async with self.db.get_connection() as conn:
            try:
                result = await conn.fetch(query, *args)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Erro ao executar query: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Args: {args}")
                raise
    
    async def execute_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Executa query e retorna um resultado"""
        async with self.db.get_connection() as conn:
            try:
                result = await conn.fetchrow(query, *args)
                return dict(result) if result else None
            except Exception as e:
                logger.error(f"Erro ao executar query: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Args: {args}")
                raise
    
    async def execute_command(self, query: str, *args) -> str:
        """Executa comando (INSERT, UPDATE, DELETE)"""
        async with self.db.get_connection() as conn:
            try:
                result = await conn.execute(query, *args)
                logger.debug(f"Comando executado: {result}")
                return result
            except Exception as e:
                logger.error(f"Erro ao executar comando: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Args: {args}")
                raise


class TeamRepository(BaseRepository):
    """Repositório para times"""
    
    async def create_team(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria novo time"""
        query = """
        INSERT INTO teams (name, country, league, logo_url, founded_year, stadium)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """
        return await self.execute_one(
            query,
            team_data['name'],
            team_data['country'], 
            team_data['league'],
            team_data.get('logo_url'),
            team_data.get('founded_year'),
            team_data.get('stadium')
        )
    
    async def get_team_by_id(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Busca time por ID"""
        query = "SELECT * FROM teams WHERE id = $1"
        return await self.execute_one(query, team_id)
    
    async def get_teams_by_league(self, league: str) -> List[Dict[str, Any]]:
        """Busca times por liga"""
        query = "SELECT * FROM teams WHERE league = $1 ORDER BY name"
        return await self.execute_query(query, league)
    
    async def update_team(self, team_id: int, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza time"""
        query = """
        UPDATE teams 
        SET name = $2, country = $3, league = $4, logo_url = $5, 
            founded_year = $6, stadium = $7, updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """
        return await self.execute_one(
            query, team_id,
            team_data['name'], team_data['country'], team_data['league'],
            team_data.get('logo_url'), team_data.get('founded_year'),
            team_data.get('stadium')
        )


class PlayerRepository(BaseRepository):
    """Repositório para jogadores"""
    
    async def create_player(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria novo jogador"""
        query = """
        INSERT INTO players (name, team_id, age, position, nationality, 
                           market_value, jersey_number, height, weight)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """
        return await self.execute_one(
            query,
            player_data['name'], player_data['team_id'], player_data.get('age'),
            player_data['position'], player_data['nationality'],
            player_data.get('market_value'), player_data.get('jersey_number'),
            player_data.get('height'), player_data.get('weight')
        )
    
    async def get_players_by_team(self, team_id: int) -> List[Dict[str, Any]]:
        """Busca jogadores por time"""
        query = """
        SELECT p.*, t.name as team_name 
        FROM players p 
        JOIN teams t ON p.team_id = t.id 
        WHERE p.team_id = $1 
        ORDER BY p.jersey_number
        """
        return await self.execute_query(query, team_id)
    
    async def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Busca jogador por ID"""
        query = """
        SELECT p.*, t.name as team_name 
        FROM players p 
        JOIN teams t ON p.team_id = t.id 
        WHERE p.id = $1
        """
        return await self.execute_one(query, player_id)


class MatchRepository(BaseRepository):
    """Repositório para partidas"""
    
    async def create_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria nova partida"""
        query = """
        INSERT INTO matches (home_team_id, away_team_id, competition, match_date,
                           status, home_score, away_score, minute, venue)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
        """
        return await self.execute_one(
            query,
            match_data['home_team_id'], match_data['away_team_id'],
            match_data['competition'], match_data['match_date'],
            match_data.get('status', 'scheduled'),
            match_data.get('home_score'), match_data.get('away_score'),
            match_data.get('minute'), match_data.get('venue')
        )
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Busca partidas ao vivo"""
        query = """
        SELECT m.*, 
               ht.name as home_team_name, ht.logo_url as home_team_logo,
               at.name as away_team_name, at.logo_url as away_team_logo
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status IN ('live', 'halftime')
        ORDER BY m.match_date
        """
        return await self.execute_query(query)
    
    async def get_matches_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Busca partidas por data"""
        query = """
        SELECT m.*, 
               ht.name as home_team_name, ht.logo_url as home_team_logo,
               at.name as away_team_name, at.logo_url as away_team_logo
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE DATE(m.match_date) = $1
        ORDER BY m.match_date
        """
        return await self.execute_query(query, date)
    
    async def update_match_score(self, match_id: int, home_score: int, 
                                away_score: int, minute: int, status: str) -> Dict[str, Any]:
        """Atualiza placar da partida"""
        query = """
        UPDATE matches 
        SET home_score = $2, away_score = $3, minute = $4, status = $5, updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """
        return await self.execute_one(query, match_id, home_score, away_score, minute, status)


class LiveMatchRepository(BaseRepository):
    """Repositório para dados ao vivo das partidas"""
    
    async def upsert_live_match(self, live_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insere ou atualiza dados ao vivo"""
        query = """
        INSERT INTO live_matches (
            match_id, current_score_home, current_score_away, current_minute,
            status, possession_home, possession_away, shots_home, shots_away,
            corners_home, corners_away, cards_yellow_home, cards_yellow_away,
            cards_red_home, cards_red_away, odds_home, odds_draw, odds_away
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        ON CONFLICT (match_id) DO UPDATE SET
            current_score_home = EXCLUDED.current_score_home,
            current_score_away = EXCLUDED.current_score_away,
            current_minute = EXCLUDED.current_minute,
            status = EXCLUDED.status,
            possession_home = EXCLUDED.possession_home,
            possession_away = EXCLUDED.possession_away,
            shots_home = EXCLUDED.shots_home,
            shots_away = EXCLUDED.shots_away,
            corners_home = EXCLUDED.corners_home,
            corners_away = EXCLUDED.corners_away,
            cards_yellow_home = EXCLUDED.cards_yellow_home,
            cards_yellow_away = EXCLUDED.cards_yellow_away,
            cards_red_home = EXCLUDED.cards_red_home,
            cards_red_away = EXCLUDED.cards_red_away,
            odds_home = EXCLUDED.odds_home,
            odds_draw = EXCLUDED.odds_draw,
            odds_away = EXCLUDED.odds_away,
            updated_at = NOW()
        RETURNING *
        """
        return await self.execute_one(
            query,
            live_data['match_id'], live_data['current_score_home'],
            live_data['current_score_away'], live_data['current_minute'],
            live_data['status'], live_data.get('possession_home'),
            live_data.get('possession_away'), live_data.get('shots_home'),
            live_data.get('shots_away'), live_data.get('corners_home'),
            live_data.get('corners_away'), live_data.get('cards_yellow_home'),
            live_data.get('cards_yellow_away'), live_data.get('cards_red_home'),
            live_data.get('cards_red_away'), live_data.get('odds_home'),
            live_data.get('odds_draw'), live_data.get('odds_away')
        )


class GeminiAnalysisRepository(BaseRepository):
    """Repositório para análises do Gemini"""
    
    async def create_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria nova análise"""
        query = """
        INSERT INTO gemini_analyses (analysis_type, entity_id, entity_type,
                                   prompt_used, analysis_result, confidence_score,
                                   key_insights, recommendations)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """
        return await self.execute_one(
            query,
            analysis_data['analysis_type'], analysis_data['entity_id'],
            analysis_data['entity_type'], analysis_data['prompt_used'],
            analysis_data['analysis_result'], analysis_data.get('confidence_score'),
            json.dumps(analysis_data.get('key_insights', [])),
            json.dumps(analysis_data.get('recommendations', []))
        )
    
    async def get_recent_analyses(self, entity_type: str, entity_id: int, 
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Busca análises recentes por entidade"""
        query = """
        SELECT * FROM gemini_analyses 
        WHERE entity_type = $1 AND entity_id = $2
        ORDER BY created_at DESC
        LIMIT $3
        """
        return await self.execute_query(query, entity_type, entity_id, limit)


# Instâncias dos repositórios
team_repo = TeamRepository()
player_repo = PlayerRepository()
match_repo = MatchRepository()
live_match_repo = LiveMatchRepository()
analysis_repo = GeminiAnalysisRepository() 