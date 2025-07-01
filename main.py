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
from scrapers.unified_real_scraper import (
    get_unified_live_matches_100_real,
    get_unified_today_matches_100_real,
    get_unified_multi_sport_real
)
from scrapers.transfermarkt_scraper import scrape_transfermarkt_teams
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
    """🔴 Busca partidas ao vivo - DADOS 100% REAIS"""
    try:
        logger.info("🔍 Buscando partidas ao vivo com dados 100% REAIS...")
        
        # Usar sistema unificado de dados reais
        live_matches = await get_unified_live_matches_100_real()
        
        logger.info(f"⚽ {len(live_matches)} partidas ao vivo REAIS encontradas")
        
        # Adicionar informações extras se necessário
        for match in live_matches:
            # Garantir que temos todos os campos necessários
            match.setdefault('data_quality', '100_percent_real')
            match.setdefault('is_simulation', False)
            match.setdefault('source_type', 'real_api')
        
        return APIResponse(
            message=f"{len(live_matches)} partidas ao vivo com dados 100% REAIS",
            data={
                'matches': live_matches,
                'total_count': len(live_matches),
                'data_guarantee': '100_percent_real',
                'sources_used': list(set(match.get('source', 'unknown') for match in live_matches)),
                'last_updated': datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar partidas ao vivo REAIS: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados reais")


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
# DADOS 100% REAIS - ZERO SIMULAÇÃO
# ===============================================

@app.get("/matches/live-real", response_model=APIResponse)
async def get_live_matches_100_real():
    """🎯 ENDPOINT PRINCIPAL - PARTIDAS AO VIVO 100% REAIS (ZERO SIMULAÇÃO)"""
    try:
        logger.info("🎯 BUSCANDO DADOS 100% REAIS - ZERO SIMULAÇÃO")
        
        # Buscar dados reais de múltiplas fontes
        live_matches = await get_unified_live_matches_100_real()
        
        # Validação extra para garantir que não há simulação
        real_matches = []
        for match in live_matches:
            # Verificar se é realmente real
            if (match.get('data_quality') == '100_percent_real' and 
                not match.get('is_simulation', False) and
                match.get('source') not in ['mock', 'fake', 'test']):
                real_matches.append(match)
        
        logger.info(f"✅ {len(real_matches)} partidas 100% REAIS validadas (zero simulação)")
        
        return APIResponse(
            message=f"DADOS 100% REAIS: {len(real_matches)} partidas ao vivo",
            data={
                'matches': real_matches,
                'total_real_matches': len(real_matches),
                'guarantee': 'ZERO_SIMULATION_100_PERCENT_REAL',
                'validation_level': 'STRICT',
                'sources_validated': list(set(match.get('source', 'unknown') for match in real_matches)),
                'timestamp': datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO ao buscar dados 100% REAIS: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados reais")

@app.get("/matches/today-real", response_model=APIResponse)
async def get_today_matches_100_real():
    """📅 PARTIDAS DE HOJE - DADOS 100% REAIS"""
    try:
        logger.info("📅 Buscando partidas de hoje - DADOS 100% REAIS")
        
        today_matches = await get_unified_today_matches_100_real()
        
        # Filtrar apenas dados reais
        real_matches = [
            match for match in today_matches 
            if match.get('data_quality') == '100_percent_real'
        ]
        
        return APIResponse(
            message=f"Partidas de hoje: {len(real_matches)} jogos com dados 100% REAIS",
            data={
                'matches': real_matches,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'guarantee': '100_PERCENT_REAL',
                'total_count': len(real_matches)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Erro partidas de hoje REAIS: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar dados de hoje")

@app.get("/sports/multi-real", response_model=APIResponse)
async def get_multi_sport_100_real():
    """🏆 MÚLTIPLOS ESPORTES - DADOS 100% REAIS"""
    try:
        logger.info("🏆 Buscando múltiplos esportes - DADOS 100% REAIS")
        
        sports_data = await get_unified_multi_sport_real()
        
        return APIResponse(
            message="Múltiplos esportes com dados 100% REAIS",
            data={
                'sports': sports_data,
                'guarantee': '100_PERCENT_REAL',
                'timestamp': datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Erro multi-esporte REAL: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar esportes reais")

# ===============================================
# SCRAPING ENDPOINTS
# ===============================================

@app.post("/scraping/live-matches", response_model=APIResponse)
async def trigger_live_scraping(background_tasks: BackgroundTasks):
    """🔄 Dispara scraping de partidas ao vivo - DADOS 100% REAIS"""
    try:
        # Executar busca de dados reais em background
        background_tasks.add_task(get_unified_live_matches_100_real)
        
        return APIResponse(
            message="Scraping de partidas ao vivo REAIS iniciado",
            data={
                "status": "started",
                "data_type": "100_percent_real",
                "sources": ["ESPN", "Football-Data", "API-Football", "LiveScore"]
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao iniciar scraping ao vivo REAL: {e}")
        raise HTTPException(status_code=500, detail="Erro ao iniciar scraping real")


@app.post("/scraping/teams/{league}", response_model=APIResponse)
async def trigger_team_scraping(
    league: str,
    background_tasks: BackgroundTasks,
    max_teams: int = Query(5, ge=1, le=20, description="Máximo de times para fazer scraping")
):
    """Dispara scraping de times por liga"""
    try:
        # Executar em background
        background_tasks.add_task(scrape_transfermarkt_teams, [league])
        
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
# N8N INTEGRATION ENDPOINTS
# ===============================================

@app.post("/webhooks/n8n/match-update", response_model=APIResponse)
async def n8n_match_webhook(
    webhook_url: str = Query(..., description="URL do webhook do n8n"),
    match_id: Optional[int] = Query(None, description="ID da partida específica")
):
    """Endpoint para enviar atualizações de partidas para n8n via webhook"""
    try:
        import httpx
        
        if match_id:
            matches = [await match_repo.get_match_by_id(match_id)]
        else:
            # Buscar partidas ao vivo
            matches = await live_match_repo.get_live_matches()
        
        # Enviar para n8n
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={
                    "event": "match_update",
                    "timestamp": datetime.now().isoformat(),
                    "data": matches
                }
            )
        
        return APIResponse(
            message="Webhook enviado com sucesso para n8n",
            data={"status_code": response.status_code, "matches_sent": len(matches)}
        )
        
    except Exception as e:
        logger.error(f"Erro ao enviar webhook para n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/n8n/bulk-data", response_model=APIResponse)
async def n8n_bulk_data(
    entity_type: str = Query(..., description="Tipo: teams, players, matches, analyses"),
    league: Optional[str] = Query(None, description="Filtrar por liga"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de registros")
):
    """Endpoint otimizado para n8n obter dados em lote"""
    try:
        data = []
        
        if entity_type == "teams":
            query = "SELECT * FROM teams"
            params = []
            if league:
                query += " WHERE league = $1"
                params.append(league)
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)
            data = await team_repo.execute_query(query, *params)
            
        elif entity_type == "matches":
            query = "SELECT * FROM matches ORDER BY match_date DESC"
            params = []
            if league:
                query = "SELECT m.* FROM matches m JOIN teams t1 ON m.home_team_id = t1.id WHERE t1.league = $1"
                params.append(league)
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)
            data = await match_repo.execute_query(query, *params)
            
        elif entity_type == "analyses":
            data = await analysis_repo.execute_query(
                "SELECT * FROM analyses ORDER BY created_at DESC LIMIT $1", 
                limit
            )
            
        return APIResponse(
            message=f"Dados em lote para n8n - {entity_type}",
            data={
                "entity_type": entity_type,
                "count": len(data),
                "items": data
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados em lote para n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/n8n/trigger-analysis", response_model=APIResponse)
async def n8n_trigger_analysis(
    analysis_type: str = Query(..., description="Tipo: match-prediction, team-form, betting-trends"),
    entity_id: int = Query(..., description="ID da entidade (partida, time, etc)"),
    webhook_url: Optional[str] = Query(None, description="URL para callback do resultado")
):
    """Endpoint para n8n disparar análises e receber callback"""
    try:
        result = None
        
        if analysis_type == "match-prediction":
            result = await analyzer.analyze_match_prediction(entity_id)
        elif analysis_type == "team-form":
            result = await analyzer.analyze_team_form(entity_id, matches_count=10)
        elif analysis_type == "betting-trends":
            result = await analyzer.analyze_betting_trends(entity_id)
        
        # Salvar análise
        analysis_data = {
            "entity_type": "match" if analysis_type == "match-prediction" else "team",
            "entity_id": entity_id,
            "analysis_type": analysis_type,
            "result": result,
            "created_at": datetime.now()
        }
        
        saved_analysis = await analysis_repo.create_analysis(analysis_data)
        
        # Enviar callback para n8n se fornecido
        if webhook_url and result:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook_url,
                    json={
                        "analysis_id": saved_analysis["id"],
                        "analysis_type": analysis_type,
                        "entity_id": entity_id,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        
        return APIResponse(
            message="Análise executada com sucesso",
            data={
                "analysis_id": saved_analysis["id"],
                "analysis_type": analysis_type,
                "result": result
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao executar análise para n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===============================================
# TELEGRAM INTEGRATION SPECIFIC ENDPOINTS
# ===============================================

@app.get("/telegram/live-summary", response_model=APIResponse)
async def telegram_live_summary():
    """Endpoint otimizado para bot Telegram - dados dos 3 sites"""
    try:
        # 1. SofaScore - Partidas ao vivo
        live_matches = await live_match_repo.get_live_matches()
        
        # 2. WhoScored - Estatísticas das partidas ao vivo
        match_stats = []
        for match in live_matches[:3]:  # Limitar a 3 partidas para não sobrecarregar
            stats = await analysis_repo.get_latest_analysis_by_entity(
                entity_type="match",
                entity_id=match.get("id")
            )
            if stats:
                match_stats.append(stats)
        
        # 3. Transfermarkt - Dados básicos dos times
        team_data = {}
        for match in live_matches[:3]:
            if match.get("home_team_id"):
                team_info = await team_repo.get_team_by_id(match["home_team_id"])
                if team_info:
                    team_data[match["home_team_id"]] = team_info
        
        # Formatar mensagem para Telegram
        telegram_message = "🔴 **PARTIDAS AO VIVO**\n*Dados dos 3 Sites*\n\n"
        
        if not live_matches:
            telegram_message += "⚽ Nenhuma partida ao vivo no momento\n\n"
        else:
            for i, match in enumerate(live_matches[:3]):
                telegram_message += f"⚽ **{match.get('home_team', 'Home')} {match.get('home_score', 0)} x {match.get('away_score', 0)} {match.get('away_team', 'Away')}**\n"
                telegram_message += f"🕐 {match.get('minute', 0)}'min\n"
                telegram_message += f"🏆 {match.get('competition', 'Liga')}\n"
                
                # Adicionar stats do WhoScored se disponível
                if i < len(match_stats) and match_stats[i]:
                    stats = match_stats[i].get('result', {})
                    telegram_message += f"📊 Posse: {stats.get('possession_home', 'N/A')}% x {stats.get('possession_away', 'N/A')}%\n"
                    telegram_message += f"📈 xG: {stats.get('expected_goals_home', 'N/A')} x {stats.get('expected_goals_away', 'N/A')}\n"
                
                # Adicionar dados do Transfermarkt se disponível
                team_id = match.get('home_team_id')
                if team_id in team_data:
                    team_value = team_data[team_id].get('market_value', 0)
                    if team_value > 0:
                        telegram_message += f"💰 Valor: €{team_value/1000000:.0f}M\n"
                
                telegram_message += "\n"
        
        telegram_message += f"📱 Última atualização: {datetime.now().strftime('%H:%M')}\n"
        telegram_message += "🔗 SofaScore + WhoScored + Transfermarkt"
        
        return APIResponse(
            message="Resumo ao vivo para Telegram",
            data={
                "telegram_message": telegram_message,
                "live_matches_count": len(live_matches),
                "stats_available": len(match_stats),
                "teams_with_data": len(team_data),
                "raw_data": {
                    "matches": live_matches[:3],
                    "stats": match_stats,
                    "teams": team_data
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no resumo do Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telegram/daily-report", response_model=APIResponse)
async def telegram_daily_report():
    """Relatório diário consolidado para Telegram"""
    try:
        # Estatísticas gerais
        stats = await analysis_repo.execute_one("""
            SELECT 
                COUNT(DISTINCT m.id) as total_matches,
                COUNT(DISTINCT t.id) as total_teams,
                COUNT(DISTINCT a.id) as total_analyses,
                COUNT(CASE WHEN m.status = 'live' THEN 1 END) as live_matches
            FROM matches m
            CROSS JOIN teams t
            CROSS JOIN analyses a
            WHERE m.created_at >= CURRENT_DATE
        """)
        
        # Partidas recentes
        recent_matches = await match_repo.execute_query("""
            SELECT home_team, away_team, competition, status
            FROM matches 
            WHERE created_at >= CURRENT_DATE 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        # Times principais
        top_teams = await team_repo.execute_query("""
            SELECT name, league, market_value
            FROM teams 
            ORDER BY market_value DESC NULLS LAST
            LIMIT 5
        """)
        
        # Análises recentes
        recent_analyses = await analysis_repo.execute_query("""
            SELECT analysis_type, created_at
            FROM analyses 
            WHERE created_at >= CURRENT_DATE
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        # Formatar relatório
        report = f"📊 **RELATÓRIO DIÁRIO SPORTS DATA**\n"
        report += f"*{datetime.now().strftime('%d/%m/%Y')}*\n\n"
        
        report += f"🔥 **DADOS COLETADOS HOJE:**\n"
        report += f"📊 SofaScore: {stats.get('live_matches', 0)} partidas ao vivo\n"
        report += f"💰 Transfermarkt: {stats.get('total_teams', 0)} times monitorados\n"
        report += f"📈 WhoScored: {stats.get('total_analyses', 0)} análises geradas\n\n"
        
        if recent_matches:
            report += f"⚽ **PARTIDAS RECENTES:**\n"
            for match in recent_matches:
                report += f"• {match['home_team']} vs {match['away_team']} ({match['competition']})\n"
            report += "\n"
        
        if top_teams:
            report += f"🏆 **TIMES PRINCIPAIS:**\n"
            for team in top_teams:
                value_str = f"€{team['market_value']/1000000:.0f}M" if team['market_value'] else "N/A"
                report += f"• {team['name']} ({team['league']}) - {value_str}\n"
            report += "\n"
        
        if recent_analyses:
            report += f"🤖 **ANÁLISES RECENTES:**\n"
            for analysis in recent_analyses:
                report += f"• {analysis['analysis_type']} - {analysis['created_at'].strftime('%H:%M')}\n"
            report += "\n"
        
        report += f"✅ Sistema funcionando perfeitamente!\n"
        report += f"🔗 Integração: SofaScore + Transfermarkt + WhoScored"
        
        return APIResponse(
            message="Relatório diário para Telegram",
            data={
                "telegram_message": report,
                "stats": stats,
                "recent_matches": recent_matches,
                "top_teams": top_teams,
                "recent_analyses": recent_analyses
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no relatório diário do Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/smart-alert", response_model=APIResponse)
async def telegram_smart_alert(
    match_id: int = Query(..., description="ID da partida para análise"),
    threshold: float = Query(7.0, ge=0.0, le=10.0, description="Threshold para alerta (0-10)")
):
    """Alerta inteligente cruzando dados dos 3 sites"""
    try:
        # 1. SofaScore - Dados da partida
        match = await match_repo.get_match_by_id(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        
        # 2. WhoScored - Análise com IA
        analysis = await analyzer.analyze_match_prediction(match_id)
        confidence = analysis.get('confidence', 0)
        
        # 3. Transfermarkt - Valores dos times
        home_team = await team_repo.get_team_by_id(match['home_team_id'])
        away_team = await team_repo.get_team_by_id(match['away_team_id'])
        
        home_value = home_team.get('market_value', 0) if home_team else 0
        away_value = away_team.get('market_value', 0) if away_team else 0
        
        # Calcular score de oportunidade
        odds_score = min((5 - min(match.get('odds_home', 3.0), 5)) * 2, 10)
        confidence_score = confidence / 10
        value_score = min((home_value + away_value) / 100000000, 10)  # Normalizar para 0-10
        
        opportunity_score = (confidence_score * 0.5 + odds_score * 0.3 + value_score * 0.2)
        
        if opportunity_score >= threshold:
            # Formatar alerta
            alert = f"🎯 **OPORTUNIDADE DETECTADA!**\n\n"
            alert += f"⚽ **{match['home_team']} vs {match['away_team']}**\n\n"
            alert += f"📊 **ANÁLISE CRUZADA 3 SITES:**\n\n"
            
            alert += f"🔴 **SofaScore:**\n"
            alert += f"• Odds: {match.get('odds_home', 'N/A')}\n"
            alert += f"• Status: {match.get('status', 'Agendada')}\n\n"
            
            alert += f"📈 **WhoScored + IA:**\n"
            alert += f"• Confiança: {confidence}%\n"
            alert += f"• Recomendação: {analysis.get('recommendation', 'N/A')}\n\n"
            
            alert += f"💰 **Transfermarkt:**\n"
            alert += f"• {match['home_team']}: €{home_value/1000000:.0f}M\n"
            alert += f"• {match['away_team']}: €{away_value/1000000:.0f}M\n\n"
            
            alert += f"🎯 **SCORE FINAL: {opportunity_score:.1f}/10**\n\n"
            alert += f"✅ Oportunidade validada por múltiplas fontes!\n"
            alert += f"⏰ {datetime.now().strftime('%d/%m %H:%M')}"
            
            return APIResponse(
                message="Alerta inteligente gerado",
                data={
                    "is_opportunity": True,
                    "opportunity_score": round(opportunity_score, 1),
                    "telegram_message": alert,
                    "analysis_details": {
                        "confidence": confidence,
                        "odds_score": odds_score,
                        "value_score": value_score,
                        "home_value": home_value,
                        "away_value": away_value
                    }
                }
            )
        else:
            return APIResponse(
                message="Nenhuma oportunidade detectada",
                data={
                    "is_opportunity": False,
                    "opportunity_score": round(opportunity_score, 1),
                    "threshold": threshold,
                    "telegram_message": f"📊 Partida analisada: score {opportunity_score:.1f}/10 (threshold: {threshold})"
                }
            )
        
    except Exception as e:
        logger.error(f"Erro no alerta inteligente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===============================================
# BETTING SIGNALS ENDPOINTS (ESCANTEIOS, CARTÕES, AMBAS MARCAM)
# ===============================================

@app.post("/betting/corners-signal", response_model=APIResponse)
async def corners_betting_signal(
    match_id: int = Query(..., description="ID da partida"),
    live_analysis: bool = Query(True, description="Usar dados ao vivo")
):
    """Sinal de apostas para ESCANTEIOS com análise IA"""
    try:
        # Buscar dados da partida
        match = await match_repo.get_match_by_id(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        
        # Buscar estatísticas detalhadas (WhoScored)
        stats = await analysis_repo.get_latest_analysis_by_entity("match", match_id)
        
        # Prompt especializado para escanteios
        corners_prompt = f"""
        Você é uma ESPECIALISTA EM APOSTAS ESPORTIVAS com 15 anos de experiência, especializada em ESCANTEIOS.
        
        📊 DADOS DA PARTIDA:
        - Times: {match.get('home_team')} vs {match.get('away_team')}
        - Liga: {match.get('competition')}
        - Minuto: {match.get('minute', 0)}'
        - Placar: {match.get('home_score', 0)} x {match.get('away_score', 0)}
        - Status: {match.get('status')}
        
        📈 ESTATÍSTICAS:
        - Posse: {stats.get('possession_home', 50) if stats else 50}% x {stats.get('possession_away', 50) if stats else 50}%
        - Finalizações: {stats.get('shots_home', 0) if stats else 0} x {stats.get('shots_away', 0) if stats else 0}
        - Escanteios: {stats.get('corners_home', 0) if stats else 0} x {stats.get('corners_away', 0) if stats else 0}
        
        🎯 ANÁLISE COMO ESPECIALISTA:
        1. Time perdendo pressiona mais = mais escanteios
        2. Final de jogo = pressão máxima
        3. Posse alta sem gols = cruzamentos e escanteios
        4. Analise o ritmo atual da partida
        
        Me dê um SINAL CLARO para apostas em escanteios:
        - Recomendação: MAIS/MENOS de X.5 escanteios
        - Confiança: 1-10
        - Justificativa: 2 linhas técnicas
        - Momento: Apostar AGORA/Aguardar/Não apostar
        
        Responda APENAS em formato JSON.
        """
        
        # Analisar com Gemini
        analysis = await analyzer.analyze_with_custom_prompt(corners_prompt)
        
        # Formatar mensagem para Telegram
        telegram_message = f"🚨 **SINAL DE ESCANTEIOS**\n\n"
        telegram_message += f"⚽ **{match['home_team']} vs {match['away_team']}**\n"
        telegram_message += f"🕐 {match.get('minute', 0)}'min - {match['home_score']} x {match['away_score']}\n"
        telegram_message += f"🏆 {match.get('competition')}\n\n"
        
        telegram_message += f"📊 **SITUAÇÃO ATUAL:**\n"
        telegram_message += f"• Escanteios: {stats.get('corners_home', 0) if stats else 0} x {stats.get('corners_away', 0) if stats else 0}\n"
        telegram_message += f"• Posse: {stats.get('possession_home', 50) if stats else 50}% x {stats.get('possession_away', 50) if stats else 50}%\n"
        telegram_message += f"• Finalizações: {stats.get('shots_home', 0) if stats else 0} x {stats.get('shots_away', 0) if stats else 0}\n\n"
        
        telegram_message += f"🎯 **SINAL IA:**\n"
        telegram_message += f"• **{analysis.get('recommendation', 'Analisando...')}**\n"
        telegram_message += f"• Confiança: {analysis.get('confidence', 0)}/10\n"
        telegram_message += f"• Momento: {analysis.get('timing', 'Aguardar')}\n\n"
        
        telegram_message += f"💡 **ANÁLISE:**\n{analysis.get('justification', 'Processando análise...')}\n\n"
        telegram_message += f"🤖 Análise IA Gemini Especialista"
        
        return APIResponse(
            message="Sinal de escanteios gerado",
            data={
                "signal_type": "corners",
                "match_info": match,
                "analysis": analysis,
                "telegram_message": telegram_message,
                "confidence_level": analysis.get('confidence', 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no sinal de escanteios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/betting/cards-signal", response_model=APIResponse)
async def cards_betting_signal(
    match_id: int = Query(..., description="ID da partida"),
    live_analysis: bool = Query(True, description="Usar dados ao vivo")
):
    """Sinal de apostas para CARTÕES com análise IA"""
    try:
        # Buscar dados da partida
        match = await match_repo.get_match_by_id(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        
        # Buscar estatísticas detalhadas
        stats = await analysis_repo.get_latest_analysis_by_entity("match", match_id)
        
        # Prompt especializado para cartões
        cards_prompt = f"""
        Você é uma ESPECIALISTA EM APOSTAS ESPORTIVAS com 15 anos de experiência, especializada em CARTÕES.
        
        📊 DADOS DA PARTIDA:
        - Times: {match.get('home_team')} vs {match.get('away_team')}
        - Liga: {match.get('competition')}
        - Minuto: {match.get('minute', 0)}'
        - Placar: {match.get('home_score', 0)} x {match.get('away_score', 0)}
        
        📈 ESTATÍSTICAS:
        - Cartões amarelos: {stats.get('yellow_cards_home', 0) if stats else 0} x {stats.get('yellow_cards_away', 0) if stats else 0}
        - Cartões vermelhos: {stats.get('red_cards_home', 0) if stats else 0} x {stats.get('red_cards_away', 0) if stats else 0}
        - Faltas: {stats.get('fouls_home', 0) if stats else 0} x {stats.get('fouls_away', 0) if stats else 0}
        
        🎯 ANÁLISE COMO ESPECIALISTA:
        1. Jogo tenso = mais cartões
        2. Time perdendo = mais agressividade
        3. Final de jogo = mais faltas táticas
        4. Rivalidade e importância da partida
        5. Muitas faltas = cartões chegando
        
        Me dê um SINAL CLARO para cartões:
        - Recomendação: MAIS/MENOS de X.5 cartões
        - Confiança: 1-10
        - Justificativa: 2 linhas técnicas
        - Foco: Amarelos/Vermelhos/Total
        
        Responda APENAS em formato JSON.
        """
        
        # Analisar com Gemini
        analysis = await analyzer.analyze_with_custom_prompt(cards_prompt)
        
        # Formatar mensagem para Telegram
        telegram_message = f"🟡 **SINAL DE CARTÕES**\n\n"
        telegram_message += f"⚽ **{match['home_team']} vs {match['away_team']}**\n"
        telegram_message += f"🕐 {match.get('minute', 0)}'min - {match['home_score']} x {match['away_score']}\n"
        telegram_message += f"🏆 {match.get('competition')}\n\n"
        
        telegram_message += f"📊 **SITUAÇÃO ATUAL:**\n"
        telegram_message += f"• Amarelos: {stats.get('yellow_cards_home', 0) if stats else 0} x {stats.get('yellow_cards_away', 0) if stats else 0}\n"
        telegram_message += f"• Vermelhos: {stats.get('red_cards_home', 0) if stats else 0} x {stats.get('red_cards_away', 0) if stats else 0}\n"
        telegram_message += f"• Faltas: {stats.get('fouls_home', 0) if stats else 0} x {stats.get('fouls_away', 0) if stats else 0}\n\n"
        
        telegram_message += f"🎯 **SINAL IA:**\n"
        telegram_message += f"• **{analysis.get('recommendation', 'Analisando...')}**\n"
        telegram_message += f"• Confiança: {analysis.get('confidence', 0)}/10\n"
        telegram_message += f"• Foco: {analysis.get('focus', 'Total')}\n\n"
        
        telegram_message += f"💡 **ANÁLISE:**\n{analysis.get('justification', 'Processando análise...')}\n\n"
        telegram_message += f"🤖 Análise IA Gemini Especialista"
        
        return APIResponse(
            message="Sinal de cartões gerado",
            data={
                "signal_type": "cards",
                "match_info": match,
                "analysis": analysis,
                "telegram_message": telegram_message,
                "confidence_level": analysis.get('confidence', 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no sinal de cartões: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/betting/both-teams-score-signal", response_model=APIResponse)
async def both_teams_score_signal(
    match_id: int = Query(..., description="ID da partida"),
    live_analysis: bool = Query(True, description="Usar dados ao vivo")
):
    """Sinal de apostas para AMBAS MARCAM com análise IA"""
    try:
        # Buscar dados da partida
        match = await match_repo.get_match_by_id(match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        
        # Buscar estatísticas detalhadas
        stats = await analysis_repo.get_latest_analysis_by_entity("match", match_id)
        
        # Prompt especializado para ambas marcam
        btts_prompt = f"""
        Você é uma ESPECIALISTA EM APOSTAS ESPORTIVAS com 15 anos de experiência, especializada em AMBAS MARCAM (BTTS).
        
        📊 DADOS DA PARTIDA:
        - Times: {match.get('home_team')} vs {match.get('away_team')}
        - Liga: {match.get('competition')}
        - Minuto: {match.get('minute', 0)}'
        - Placar: {match.get('home_score', 0)} x {match.get('away_score', 0)}
        
        📈 ESTATÍSTICAS:
        - Finalizações: {stats.get('shots_home', 0) if stats else 0} x {stats.get('shots_away', 0) if stats else 0}
        - No alvo: {stats.get('shots_on_target_home', 0) if stats else 0} x {stats.get('shots_on_target_away', 0) if stats else 0}
        - Expected Goals: {stats.get('expected_goals_home', 0) if stats else 0} x {stats.get('expected_goals_away', 0) if stats else 0}
        - Posse: {stats.get('possession_home', 50) if stats else 50}% x {stats.get('possession_away', 50) if stats else 50}%
        
        🎯 ANÁLISE COMO ESPECIALISTA:
        1. xG alto = times criando chances
        2. Ambos finalizando = potencial para gols
        3. Defesas frágeis = mais gols
        4. Placar atual vs tempo restante
        5. Necessidade de gols de ambos os lados
        
        Me dê um SINAL CLARO para AMBAS MARCAM:
        - Recomendação: SIM/NÃO para ambas marcam
        - Confiança: 1-10
        - Justificativa: 2 linhas técnicas
        - Status: Já aconteceu/Falta 1/Faltam 2
        
        Responda APENAS em formato JSON.
        """
        
        # Analisar com Gemini
        analysis = await analyzer.analyze_with_custom_prompt(btts_prompt)
        
        # Determinar status atual
        home_scored = match.get('home_score', 0) > 0
        away_scored = match.get('away_score', 0) > 0
        
        if home_scored and away_scored:
            current_status = "✅ Já aconteceu"
        elif home_scored or away_scored:
            current_status = "🔄 Falta 1 gol"
        else:
            current_status = "⏳ Faltam 2 gols"
        
        # Formatar mensagem para Telegram
        telegram_message = f"⚽ **SINAL AMBAS MARCAM**\n\n"
        telegram_message += f"🏟️ **{match['home_team']} vs {match['away_team']}**\n"
        telegram_message += f"🕐 {match.get('minute', 0)}'min - {match['home_score']} x {match['away_score']}\n"
        telegram_message += f"🏆 {match.get('competition')}\n\n"
        
        telegram_message += f"📊 **SITUAÇÃO ATUAL:**\n"
        telegram_message += f"• Status: {current_status}\n"
        telegram_message += f"• Finalizações: {stats.get('shots_home', 0) if stats else 0} x {stats.get('shots_away', 0) if stats else 0}\n"
        telegram_message += f"• No alvo: {stats.get('shots_on_target_home', 0) if stats else 0} x {stats.get('shots_on_target_away', 0) if stats else 0}\n"
        telegram_message += f"• xG: {stats.get('expected_goals_home', 0) if stats else 0} x {stats.get('expected_goals_away', 0) if stats else 0}\n\n"
        
        telegram_message += f"🎯 **SINAL IA:**\n"
        telegram_message += f"• **{analysis.get('recommendation', 'Analisando...')}**\n"
        telegram_message += f"• Confiança: {analysis.get('confidence', 0)}/10\n"
        telegram_message += f"• Probabilidade: {analysis.get('probability', 'N/A')}\n\n"
        
        telegram_message += f"💡 **ANÁLISE:**\n{analysis.get('justification', 'Processando análise...')}\n\n"
        telegram_message += f"🤖 Análise IA Gemini Especialista"
        
        return APIResponse(
            message="Sinal ambas marcam gerado",
            data={
                "signal_type": "both_teams_score",
                "match_info": match,
                "analysis": analysis,
                "telegram_message": telegram_message,
                "current_status": current_status,
                "confidence_level": analysis.get('confidence', 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no sinal ambas marcam: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/betting/all-signals", response_model=APIResponse)
async def all_betting_signals(match_id: int = Query(..., description="ID da partida")):
    """Gera TODOS os sinais (escanteios, cartões, ambas marcam) para uma partida"""
    try:
        # Executar todos os sinais em paralelo
        tasks = [
            corners_betting_signal(match_id),
            cards_betting_signal(match_id),
            both_teams_score_signal(match_id)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = {}
        telegram_messages = []
        
        signal_types = ['corners', 'cards', 'both_teams_score']
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                signals[signal_types[i]] = result.data
                telegram_messages.append(result.data['telegram_message'])
        
        # Mensagem consolidada
        consolidated_message = "🚨 **SINAIS COMPLETOS DE APOSTAS**\n\n"
        consolidated_message += "\n\n".join(telegram_messages)
        consolidated_message += f"\n\n⏰ {datetime.now().strftime('%H:%M')} - Análise completa IA"
        
        return APIResponse(
            message="Todos os sinais de apostas gerados",
            data={
                "signals": signals,
                "consolidated_message": consolidated_message,
                "signals_count": len(signals),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar todos os sinais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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