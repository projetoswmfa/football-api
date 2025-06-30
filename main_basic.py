"""
API Básica de Dados Esportivos - Versão de Teste
"""
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
from config import settings
from supabase import create_client, Client
import google.generativeai as genai
import asyncio
from typing import List
from datetime import datetime

# Importar scrapers
from scrapers.sofascore_scraper import scrape_live_matches
from scrapers.transfermarkt_scraper import scrape_transfermarkt_teams
from scrapers.whoscored_scraper import scrape_whoscored_stats
from scrapers.live_scores_scraper import scrape_live_scores

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar Gemini AI
genai.configure(api_key=settings.gemini_api_key)

# Inicializar FastAPI
app = FastAPI(
    title="Sports Data API - Teste",
    description="API básica para dados esportivos",
    version="1.0.0",
    debug=settings.debug
)

# Inicializar Supabase
try:
    supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
    logger.info("✅ Supabase conectado com sucesso!")
except Exception as e:
    logger.error(f"❌ Erro ao conectar Supabase: {e}")
    supabase = None

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "🚀 Sports Data API - Funcionando!",
        "version": "1.0.0",
        "status": "✅ Ativo",
        "database": "✅ Conectado" if supabase else "❌ Erro"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        # Testar conexão com Supabase
        if supabase:
            response = supabase.table('teams').select('count').execute()
            db_status = "✅ OK"
        else:
            db_status = "❌ Erro"
            
        # Testar Gemini AI
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            ai_status = "✅ OK"
        except:
            ai_status = "❌ Erro"
            
        return {
            "api": "✅ OK",
            "database": db_status,
            "ai": ai_status,
            "timestamp": "2025-06-30"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no health check: {e}")

@app.get("/teams")
async def get_teams():
    """Listar times"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Banco de dados não conectado")
            
        response = supabase.table('teams').select('*').execute()
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar times: {e}")

@app.get("/players")
async def get_players():
    """Listar jogadores"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Banco de dados não conectado")
            
        response = supabase.table('players').select('''
            id, name, age, position, nationality, market_value, jersey_number,
            teams (name, country, league)
        ''').execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar jogadores: {e}")

@app.get("/matches")
async def get_matches():
    """Listar partidas"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Banco de dados não conectado")
            
        response = supabase.table('matches').select('''
            id, competition, match_date, status, home_score, away_score, venue,
            home_team:teams!matches_home_team_id_fkey (name, country),
            away_team:teams!matches_away_team_id_fkey (name, country)
        ''').execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar partidas: {e}")

@app.get("/matches/live")
async def get_live_matches():
    """Listar partidas ao vivo"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Banco de dados não conectado")
            
        response = supabase.table('live_matches').select('''
            id, current_score_home, current_score_away, current_minute, status,
            possession_home, possession_away, odds_home, odds_draw, odds_away,
            matches (
                competition, match_date, venue,
                home_team:teams!matches_home_team_id_fkey (name),
                away_team:teams!matches_away_team_id_fkey (name)
            )
        ''').eq('status', 'live').execute()
        
        return {
            "success": True,
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar partidas ao vivo: {e}")

# ========== ENDPOINTS DOS SCRAPERS ==========

@app.post("/scraper/sofascore/live")
async def scrape_sofascore_live(background_tasks: BackgroundTasks):
    """Executar scraper do Sofascore para partidas ao vivo"""
    try:
        logger.info("🔄 Iniciando scraping do Sofascore...")
        
        # Executar scraper
        result = await scrape_live_matches()
        
        return {
            "success": True,
            "message": "✅ Scraping do Sofascore executado",
            "matches_found": len(result) if result else 0,
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ Erro no scraping do Sofascore: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no scraping do Sofascore: {e}")

@app.post("/live-scores/update")
async def update_live_scores():
    """🔥 ENDPOINT PRINCIPAL - Atualizar placares em tempo real"""
    try:
        logger.info("🔄 Iniciando atualização de placares em tempo real...")
        
        # Buscar dados de múltiplas fontes
        live_matches = await scrape_live_scores()
        
        if not live_matches:
            return {
                "success": False,
                "message": "❌ Nenhuma partida ao vivo encontrada",
                "matches_found": 0,
                "data": []
            }
        
        # Atualizar banco de dados
        updated_count = 0
        if supabase:
            for match in live_matches:
                try:
                    # Verificar se a partida já existe
                    existing = supabase.table('live_matches').select('*').eq('external_id', match['match_id']).execute()
                    
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
                        # Atualizar partida existente
                        supabase.table('live_matches').update(match_data).eq('external_id', match['match_id']).execute()
                        updated_count += 1
                    else:
                        # Inserir nova partida
                        supabase.table('live_matches').insert(match_data).execute()
                        updated_count += 1
                        
                except Exception as db_error:
                    logger.error(f"Erro ao atualizar partida {match['match_id']}: {db_error}")
                    continue
        
        return {
            "success": True,
            "message": f"✅ Placares atualizados com sucesso",
            "matches_found": len(live_matches),
            "matches_updated": updated_count,
            "data": live_matches,
            "sources": list(set([match['source'] for match in live_matches])),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na atualização de placares: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na atualização de placares: {e}")

@app.get("/live-scores/current")
async def get_current_live_scores():
    """📊 Buscar placares atuais do banco de dados"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Banco de dados não conectado")
            
        # Buscar partidas ao vivo do banco
        response = supabase.table('live_matches').select('*').in_('status', ['live', 'halftime']).order('last_updated', desc=True).execute()
        
        return {
            "success": True,
            "message": "✅ Placares atuais obtidos",
            "matches_found": len(response.data),
            "data": response.data,
            "last_update": max([match.get('last_updated', '') for match in response.data]) if response.data else None
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar placares atuais: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar placares atuais: {e}")

@app.post("/scraper/transfermarkt/teams")
async def scrape_transfermarkt_players(team_names: List[str]):
    """Executar scraper do Transfermarkt para jogadores de times específicos"""
    try:
        if not team_names:
            raise HTTPException(status_code=400, detail="Lista de times não pode estar vazia")
        
        logger.info(f"🔄 Iniciando scraping do Transfermarkt para {len(team_names)} times...")
        
        # Executar scraper
        total_players = await scrape_transfermarkt_teams(team_names)
        
        return {
            "success": True,
            "message": "✅ Scraping do Transfermarkt executado",
            "teams_searched": team_names,
            "total_players": total_players
        }
    except Exception as e:
        logger.error(f"❌ Erro no scraping do Transfermarkt: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no scraping do Transfermarkt: {e}")

@app.post("/scraper/whoscored/stats")
async def scrape_whoscored_match_stats(match_names: List[str]):
    """Executar scraper do WhoScored para estatísticas de partidas"""
    try:
        if not match_names:
            raise HTTPException(status_code=400, detail="Lista de partidas não pode estar vazia")
        
        logger.info(f"🔄 Iniciando scraping do WhoScored para {len(match_names)} partidas...")
        
        # Executar scraper
        stats = await scrape_whoscored_stats(match_names)
        
        return {
            "success": True,
            "message": "✅ Scraping do WhoScored executado",
            "matches_searched": match_names,
            "stats_collected": len(stats),
            "data": stats
        }
    except Exception as e:
        logger.error(f"❌ Erro no scraping do WhoScored: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no scraping do WhoScored: {e}")

@app.post("/scraper/run-all")
async def run_all_scrapers():
    """Executar todos os scrapers de uma vez"""
    try:
        logger.info("🚀 Executando todos os scrapers...")
        
        results = {}
        
        # 1. Sofascore (partidas ao vivo)
        try:
            logger.info("📊 Executando Sofascore...")
            sofascore_result = await scrape_live_matches()
            results["sofascore"] = {
                "success": True,
                "matches": len(sofascore_result) if sofascore_result else 0
            }
        except Exception as e:
            results["sofascore"] = {"success": False, "error": str(e)}
        
        # 2. Transfermarkt (times principais)
        try:
            logger.info("📊 Executando Transfermarkt...")
            main_teams = ["Flamengo", "Palmeiras", "Real Madrid", "Barcelona"]
            transfermarkt_result = await scrape_transfermarkt_teams(main_teams)
            results["transfermarkt"] = {
                "success": True,
                "total_players": transfermarkt_result
            }
        except Exception as e:
            results["transfermarkt"] = {"success": False, "error": str(e)}
        
        # 3. WhoScored (partidas principais)
        try:
            logger.info("📊 Executando WhoScored...")
            main_matches = ["Flamengo vs Palmeiras", "Real Madrid vs Barcelona"]
            whoscored_result = await scrape_whoscored_stats(main_matches)
            results["whoscored"] = {
                "success": True,
                "stats_collected": len(whoscored_result)
            }
        except Exception as e:
            results["whoscored"] = {"success": False, "error": str(e)}
        
        return {
            "success": True,
            "message": "🎉 Todos os scrapers executados!",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar todos os scrapers: {e}")
        raise HTTPException(status_code=500, detail=f"Erro geral: {e}")

@app.post("/ai/analyze")
async def analyze_with_ai(prompt: str):
    """Análise básica com Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prompt personalizado para dados esportivos
        sports_prompt = f"""
        Você é um analista esportivo especializado. Analise a seguinte questão sobre futebol:
        
        {prompt}
        
        Forneça uma análise técnica e insights baseados em dados.
        """
        
        response = model.generate_content(sports_prompt)
        
        return {
            "success": True,
            "prompt": prompt,
            "analysis": response.text,
            "model": "gemini-1.5-flash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise AI: {e}")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint não encontrado", "status": "error"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Erro interno do servidor", "status": "error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_basic:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 