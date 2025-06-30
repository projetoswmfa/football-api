from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Optional
import asyncio
from datetime import datetime, timedelta
import uvicorn

from config import settings
from models import (
    APIResponse, PaginatedResponse, Team, TeamCreate, Player, PlayerCreate,
    Match, MatchCreate, LiveMatch, MatchPredictionRequest, AnalyticsRequest,
    ScrapingJob, ScrapingJobStatus
)
from database import (
    db_manager, team_repo, player_repo, match_repo, live_match_repo, analysis_repo
)
from scrapers.sofascore_scraper import scrape_live_matches
from scrapers.transfermarkt_scraper import scrape_teams_by_league
from gemini_analyzer import analyzer
from scheduler import scheduler_manager
from loguru import logger

# Configurar logging
logger.add(
    settings.log_file,
    rotation="100 MB",
    retention="7 days",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de ciclo de vida da aplicação"""
    # Startup
    logger.info("Iniciando Sports Data API...")
    
    try:
        # Inicializar banco de dados
        await db_manager.initialize_pool()
        logger.info("Banco de dados inicializado")
        
        # Inicializar scheduler
        await scheduler_manager.start()
        logger.info("Scheduler inicializado")
        
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Encerrando Sports Data API...")
    try:
        await scheduler_manager.stop()
        await db_manager.close_pool()
        logger.info("Recursos liberados com sucesso")
    except Exception as e:
        logger.error(f"Erro no encerramento: {e}")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="API completa para scraping e análise de dados esportivos",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================================
# UTILS & DEPENDENCIES
# ===============================================

def get_pagination_params(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página")
) -> dict:
    """Parâmetros de paginação"""
    return {"page": page, "per_page": per_page, "offset": (page - 1) * per_page}


# ===============================================
# HEALTH CHECK
# ===============================================

@app.get("/", response_model=APIResponse)
async def root():
    """Endpoint raiz - health check"""
    return APIResponse(
        message="Sports Data API está funcionando!",
        data={
            "version": settings.api_version,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get("/health", response_model=APIResponse)
async def health_check():
    """Health check detalhado"""
    try:
        # Testar conexão com banco
        async with db_manager.get_connection() as conn:
            await conn.fetchval("SELECT 1")
        
        db_status = "OK"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
    
    return APIResponse(
        message="Health check completo",
        data={
            "status": "OK" if db_status == "OK" else "DEGRADED",
            "database": db_status,
            "timestamp": datetime.now().isoformat(),
            "version": settings.api_version
        }
    )


# ===============================================
# TEAMS ENDPOINTS
# ===============================================

@app.get("/teams", response_model=PaginatedResponse)
async def get_teams(
    league: Optional[str] = Query(None, description="Filtrar por liga"),
    pagination: dict = Depends(get_pagination_params)
):
    """Lista times com paginação e filtros"""
    try:
        if league:
            teams_data = await team_repo.get_teams_by_league(league)
        else:
            teams_data = await team_repo.execute_query(
                "SELECT * FROM teams ORDER BY name LIMIT $1 OFFSET $2",
                pagination["per_page"], pagination["offset"]
            )
        
        # Contar total
        total_query = "SELECT COUNT(*) FROM teams"
        total_params = []
        if league:
            total_query += " WHERE league = $1"
            total_params.append(league)
        
        total_result = await team_repo.execute_one(total_query, *total_params)
        total = total_result['count'] if total_result else 0
        
        return PaginatedResponse(
            items=teams_data,
            total=total,
            page=pagination["page"],
            per_page=pagination["per_page"]
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar times: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/teams/{team_id}", response_model=APIResponse)
async def get_team(team_id: int):
    """Busca time por ID"""
    try:
        team = await team_repo.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Time não encontrado")
        
        return APIResponse(data=team)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar time {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.post("/teams", response_model=APIResponse)
async def create_team(team: TeamCreate):
    """Cria novo time"""
    try:
        new_team = await team_repo.create_team(team.dict())
        return APIResponse(
            message="Time criado com sucesso",
            data=new_team
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar time: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar time")


@app.get("/teams/{team_id}/players", response_model=APIResponse)
async def get_team_players(team_id: int):
    """Busca jogadores de um time"""
    try:
        players = await player_repo.get_players_by_team(team_id)
        return APIResponse(data=players)
        
    except Exception as e:
        logger.error(f"Erro ao buscar jogadores do time {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# ===============================================
# PLAYERS ENDPOINTS
# ===============================================

@app.get("/players/{player_id}", response_model=APIResponse)
async def get_player(player_id: int):
    """Busca jogador por ID"""
    try:
        player = await player_repo.get_player_by_id(player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Jogador não encontrado")
        
        return APIResponse(data=player)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar jogador {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.post("/players", response_model=APIResponse)
async def create_player(player: PlayerCreate):
    """Cria novo jogador"""
    try:
        new_player = await player_repo.create_player(player.dict())
        return APIResponse(
            message="Jogador criado com sucesso",
            data=new_player
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar jogador: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar jogador")


# ===============================================
# MATCHES ENDPOINTS
# ===============================================

@app.get("/matches", response_model=PaginatedResponse)
async def get_matches(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    competition: Optional[str] = Query(None, description="Filtrar por competição"),
    date: Optional[str] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    pagination: dict = Depends(get_pagination_params)
):
    """Lista partidas com filtros"""
    try:
        query = """
        SELECT m.*, 
               ht.name as home_team_name, ht.logo_url as home_team_logo,
               at.name as away_team_name, at.logo_url as away_team_logo
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE 1=1
        """
        
        params = []
        param_count = 0
        
        if status:
            param_count += 1
            query += f" AND m.status = ${param_count}"
            params.append(status)
        
        if competition:
            param_count += 1
            query += f" AND m.competition ILIKE ${param_count}"
            params.append(f"%{competition}%")
        
        if date:
            param_count += 1
            query += f" AND DATE(m.match_date) = ${param_count}"
            params.append(date)
        
        query += " ORDER BY m.match_date DESC"
        
        # Adicionar paginação
        param_count += 1
        query += f" LIMIT ${param_count}"
        params.append(pagination["per_page"])
        
        param_count += 1
        query += f" OFFSET ${param_count}"
        params.append(pagination["offset"])
        
        matches = await match_repo.execute_query(query, *params)
        
        # Contar total
        count_query = "SELECT COUNT(*) FROM matches m WHERE 1=1"
        count_params = []
        if status:
            count_query += " AND m.status = $1"
            count_params.append(status)
        if competition:
            count_query += f" AND m.competition ILIKE ${len(count_params) + 1}"
            count_params.append(f"%{competition}%")
        if date:
            count_query += f" AND DATE(m.match_date) = ${len(count_params) + 1}"
            count_params.append(date)
        
        total_result = await match_repo.execute_one(count_query, *count_params)
        total = total_result['count'] if total_result else 0
        
        return PaginatedResponse(
            items=matches,
            total=total,
            page=pagination["page"],
            per_page=pagination["per_page"]
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar partidas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/matches/live", response_model=APIResponse)
async def get_live_matches():
    """Busca partidas ao vivo"""
    try:
        live_matches = await match_repo.get_live_matches()
        
        # Buscar dados ao vivo detalhados
        for match in live_matches:
            live_data = await live_match_repo.execute_one(
                "SELECT * FROM live_matches WHERE match_id = $1",
                match['id']
            )
            if live_data:
                match['live_data'] = live_data
        
        return APIResponse(data=live_matches)
        
    except Exception as e:
        logger.error(f"Erro ao buscar partidas ao vivo: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/matches/{match_id}", response_model=APIResponse)
async def get_match(match_id: int):
    """Busca partida por ID"""
    try:
        match = await match_repo.execute_one(
            """
            SELECT m.*, 
                   ht.name as home_team_name, ht.logo_url as home_team_logo,
                   at.name as away_team_name, at.logo_url as away_team_logo
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            WHERE m.id = $1
            """,
            match_id
        )
        
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        
        # Buscar dados ao vivo se disponível
        live_data = await live_match_repo.execute_one(
            "SELECT * FROM live_matches WHERE match_id = $1",
            match_id
        )
        if live_data:
            match['live_data'] = live_data
        
        return APIResponse(data=match)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar partida {match_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.post("/matches", response_model=APIResponse)
async def create_match(match: MatchCreate):
    """Cria nova partida"""
    try:
        new_match = await match_repo.create_match(match.dict())
        return APIResponse(
            message="Partida criada com sucesso",
            data=new_match
        )
        
    except Exception as e:
        logger.error(f"Erro ao criar partida: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar partida")


# ===============================================
# SCRAPING ENDPOINTS
# ===============================================

@app.post("/scraping/live-matches", response_model=APIResponse)
async def trigger_live_scraping(background_tasks: BackgroundTasks):
    """Dispara scraping de partidas ao vivo"""
    try:
        # Executar em background
        background_tasks.add_task(scrape_live_matches)
        
        return APIResponse(
            message="Scraping de partidas ao vivo iniciado",
            data={"status": "started"}
        )
        
    except Exception as e:
        logger.error(f"Erro ao iniciar scraping ao vivo: {e}")
        raise HTTPException(status_code=500, detail="Erro ao iniciar scraping")


@app.post("/scraping/teams/{league}", response_model=APIResponse)
async def trigger_team_scraping(
    league: str,
    background_tasks: BackgroundTasks,
    max_teams: int = Query(5, ge=1, le=20, description="Máximo de times para fazer scraping")
):
    """Dispara scraping de times por liga"""
    try:
        # Executar em background
        background_tasks.add_task(scrape_teams_by_league, league, max_teams)
        
        return APIResponse(
            message=f"Scraping de times da liga {league} iniciado",
            data={"league": league, "max_teams": max_teams, "status": "started"}
        )
        
    except Exception as e:
        logger.error(f"Erro ao iniciar scraping de times: {e}")
        raise HTTPException(status_code=500, detail="Erro ao iniciar scraping")


# ===============================================
# GEMINI ANALYSIS ENDPOINTS
# ===============================================

@app.post("/analysis/match-prediction", response_model=APIResponse)
async def analyze_match_prediction(request: MatchPredictionRequest):
    """Gera análise de previsão de partida usando Gemini"""
    try:
        analysis = await analyzer.analyze_match_prediction(
            request.match_id,
            include_detailed_stats=True
        )
        
        return APIResponse(
            message="Análise de previsão gerada com sucesso",
            data=analysis
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro na análise de previsão: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar análise")


@app.post("/analysis/betting-trends", response_model=APIResponse)
async def analyze_betting_trends(match_id: int):
    """Gera análise de tendências de apostas"""
    try:
        analysis = await analyzer.analyze_betting_trends(match_id)
        
        return APIResponse(
            message="Análise de apostas gerada com sucesso",
            data=analysis
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro na análise de apostas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar análise")


@app.post("/analysis/team-form", response_model=APIResponse)
async def analyze_team_form(
    team_id: int,
    matches_count: int = Query(10, ge=5, le=20, description="Número de partidas a analisar")
):
    """Gera análise da forma atual do time"""
    try:
        analysis = await analyzer.analyze_team_form(team_id, matches_count)
        
        return APIResponse(
            message="Análise da forma do time gerada com sucesso",
            data=analysis
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro na análise da forma do time: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar análise")


@app.get("/analysis/{analysis_id}", response_model=APIResponse)
async def get_analysis(analysis_id: int):
    """Busca análise por ID"""
    try:
        analysis = await analysis_repo.execute_one(
            "SELECT * FROM gemini_analyses WHERE id = $1",
            analysis_id
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        
        return APIResponse(data=analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar análise {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/analysis/entity/{entity_type}/{entity_id}", response_model=APIResponse)
async def get_entity_analyses(
    entity_type: str,
    entity_id: int,
    limit: int = Query(10, ge=1, le=50, description="Número de análises a retornar")
):
    """Busca análises recentes de uma entidade"""
    try:
        analyses = await analysis_repo.get_recent_analyses(entity_type, entity_id, limit)
        
        return APIResponse(data=analyses)
        
    except Exception as e:
        logger.error(f"Erro ao buscar análises da entidade: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# ===============================================
# STATISTICS ENDPOINTS
# ===============================================

@app.get("/stats/summary", response_model=APIResponse)
async def get_stats_summary():
    """Estatísticas gerais da API"""
    try:
        stats = {}
        
        # Contar times
        teams_count = await team_repo.execute_one("SELECT COUNT(*) FROM teams")
        stats['teams'] = teams_count['count']
        
        # Contar jogadores
        players_count = await player_repo.execute_one("SELECT COUNT(*) FROM players")
        stats['players'] = players_count['count']
        
        # Contar partidas
        matches_count = await match_repo.execute_one("SELECT COUNT(*) FROM matches")
        stats['matches'] = matches_count['count']
        
        # Contar partidas ao vivo
        live_count = await match_repo.execute_one(
            "SELECT COUNT(*) FROM matches WHERE status IN ('live', 'halftime')"
        )
        stats['live_matches'] = live_count['count']
        
        # Contar análises
        analyses_count = await analysis_repo.execute_one("SELECT COUNT(*) FROM gemini_analyses")
        stats['analyses'] = analyses_count['count']
        
        # Ligas disponíveis
        leagues = await team_repo.execute_query("SELECT DISTINCT league FROM teams ORDER BY league")
        stats['leagues'] = [league['league'] for league in leagues]
        
        return APIResponse(data=stats)
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# ===============================================
# ERROR HANDLERS
# ===============================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handler para 404"""
    return JSONResponse(
        status_code=404,
        content=APIResponse(
            success=False,
            message="Recurso não encontrado",
            errors=["O recurso solicitado não foi encontrado"]
        ).dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handler para 500"""
    logger.error(f"Erro interno: {exc}")
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Erro interno do servidor",
            errors=["Ocorreu um erro interno. Tente novamente mais tarde."]
        ).dict()
    )


# ===============================================
# MAIN
# ===============================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 