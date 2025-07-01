"""
⚽ FOOTBALL-DATA.ORG SCRAPER - DADOS 100% REAIS GRATUITOS
Sistema usando Football-Data.org API - completamente gratuito com dados oficiais
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class FootballDataScraper:
    """Scraper usando Football-Data.org - DADOS 100% REAIS GRATUITOS"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {
            "X-Auth-Token": "YOUR_TOKEN_HERE",  # Gratuito em football-data.org
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.rate_limit_delay = 6  # API gratuita: 10 req/min = 6s entre requests
        self.max_retries = 3
        self.timeout = 30
        
        # Para tier gratuito, usar sem token (dados limitados mas funcionais)
        self.use_free_tier = True
    
    async def __aenter__(self):
        """Contexto assíncrono - entrada"""
        connector = aiohttp.TCPConnector(
            limit=5,  # Limite baixo para tier gratuito
            limit_per_host=3,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        # Headers para tier gratuito (sem token)
        headers = {"User-Agent": self.headers["User-Agent"]}
        if not self.use_free_tier and "YOUR_TOKEN_HERE" not in self.headers["X-Auth-Token"]:
            headers["X-Auth-Token"] = self.headers["X-Auth-Token"]
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        )
        
        logger.info("⚽ Football-Data.org scraper iniciado - DADOS 100% REAIS GRATUITOS")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto assíncrono - saída"""
        if self.session:
            await self.session.close()
            logger.info("🔒 Football-Data.org scraper encerrado")
    
    async def get_live_matches_real(self) -> List[Dict[str, Any]]:
        """🔴 PARTIDAS AO VIVO - 100% REAIS via Football-Data.org"""
        try:
            logger.info("🔍 Buscando partidas ao vivo REAIS via Football-Data.org...")
            
            # Buscar partidas de hoje que podem estar ao vivo
            today = datetime.now().strftime('%Y-%m-%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Endpoints disponíveis no tier gratuito
            competitions = ['PL', 'BL1', 'SA', 'PD', 'FL1']  # Premier League, Bundesliga, Serie A, La Liga, Ligue 1
            
            all_matches = []
            
            for comp in competitions:
                try:
                    endpoint = f"/competitions/{comp}/matches"
                    params = {
                        "dateFrom": today,
                        "dateTo": tomorrow,
                        "status": "IN_PLAY"  # Apenas partidas em andamento
                    }
                    
                    data = await self._make_request(endpoint, params)
                    
                    if data and data.get('matches'):
                        matches = data['matches']
                        
                        for match in matches:
                            parsed = await self._parse_live_match(match, comp)
                            if parsed:
                                all_matches.append(parsed)
                        
                        logger.info(f"✅ {len(matches)} partidas REAIS de {comp}")
                    
                    # Rate limiting para tier gratuito
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro em competição {comp}: {e}")
                    continue
            
            logger.info(f"🎉 Total: {len(all_matches)} partidas ao vivo 100% REAIS")
            return all_matches
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na busca de partidas: {e}")
            return []
    
    async def get_today_matches_real(self) -> List[Dict[str, Any]]:
        """📅 PARTIDAS DE HOJE - 100% REAIS"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"📅 Buscando partidas de hoje ({today}) - DADOS REAIS")
            
            competitions = ['PL', 'BL1', 'SA', 'PD', 'FL1', 'CL', 'WC']
            all_matches = []
            
            for comp in competitions:
                try:
                    endpoint = f"/competitions/{comp}/matches"
                    params = {
                        "dateFrom": today,
                        "dateTo": today
                    }
                    
                    data = await self._make_request(endpoint, params)
                    
                    if data and data.get('matches'):
                        for match in data['matches']:
                            parsed = await self._parse_match(match, comp)
                            if parsed:
                                all_matches.append(parsed)
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro em {comp}: {e}")
                    continue
            
            logger.info(f"📅 {len(all_matches)} partidas de hoje REAIS processadas")
            return all_matches
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar partidas de hoje: {e}")
            return []
    
    async def get_competition_standings_real(self, competition: str = "PL") -> List[Dict[str, Any]]:
        """🏆 CLASSIFICAÇÃO REAL de uma competição"""
        try:
            logger.info(f"🏆 Buscando classificação REAL de {competition}")
            
            endpoint = f"/competitions/{competition}/standings"
            data = await self._make_request(endpoint)
            
            if not data or not data.get('standings'):
                return []
            
            standings = []
            for standing_group in data['standings']:
                if standing_group.get('type') == 'TOTAL':
                    for team in standing_group.get('table', []):
                        standings.append({
                            'position': team.get('position'),
                            'team': team.get('team', {}).get('name'),
                            'team_id': team.get('team', {}).get('id'),
                            'points': team.get('points'),
                            'played': team.get('playedGames'),
                            'won': team.get('won'),
                            'drawn': team.get('draw'),
                            'lost': team.get('lost'),
                            'goals_for': team.get('goalsFor'),
                            'goals_against': team.get('goalsAgainst'),
                            'goal_difference': team.get('goalDifference'),
                            'competition': competition,
                            'source': 'football_data_real',
                            'data_quality': '100_percent_real'
                        })
            
            logger.info(f"🏆 {len(standings)} posições REAIS processadas")
            return standings
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar classificação: {e}")
            return []
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Faz requisição para Football-Data.org"""
        if not self.session:
            logger.error("❌ Sessão não inicializada")
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.rate_limit_delay if attempt > 0 else 0)
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"✅ Football-Data {endpoint} - Status: 200")
                        return data
                    
                    elif response.status == 429:  # Rate limit
                        logger.warning(f"⚠️ Rate limit - aguardando...")
                        await asyncio.sleep(60)  # Aguardar 1 minuto
                        continue
                    
                    elif response.status == 403:
                        logger.warning(f"⚠️ Token inválido ou limite excedido")
                        # Tentar sem token
                        if 'X-Auth-Token' in self.session.headers:
                            del self.session.headers['X-Auth-Token']
                            continue
                        return None
                    
                    elif response.status == 404:
                        logger.warning(f"⚠️ Endpoint não encontrado: {endpoint}")
                        return None
                    
                    else:
                        logger.warning(f"⚠️ Status {response.status} para {endpoint}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout - tentativa {attempt + 1}")
                
            except Exception as e:
                logger.error(f"❌ Erro na requisição: {e}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"❌ Falha após {self.max_retries} tentativas: {endpoint}")
        return None
    
    async def _parse_live_match(self, match: Dict, competition: str) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida ao vivo REAL"""
        try:
            # Verificar se está realmente ao vivo
            status = match.get('status')
            if status != 'IN_PLAY':
                return None
            
            home_team = match.get('homeTeam', {})
            away_team = match.get('awayTeam', {})
            score = match.get('score', {})
            
            match_data = {
                'match_id': f"footballdata_{match.get('id')}",
                'id': match.get('id'),
                'home_team': home_team.get('name', 'Unknown'),
                'away_team': away_team.get('name', 'Unknown'),
                'home_team_id': home_team.get('id'),
                'away_team_id': away_team.get('id'),
                'home_score': score.get('fullTime', {}).get('home', 0),
                'away_score': score.get('fullTime', {}).get('away', 0),
                'status': status,
                'competition': competition,
                'start_time': match.get('utcDate'),
                'is_live': True,
                'minute': self._extract_minute(match),
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'football_data_real',
                'data_quality': '100_percent_real'
            }
            
            # Adicionar odds se disponível
            if match.get('odds'):
                odds = match['odds']
                match_data['home_odds'] = odds.get('homeWin')
                match_data['draw_odds'] = odds.get('draw')
                match_data['away_odds'] = odds.get('awayWin')
            
            return match_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar partida ao vivo: {e}")
            return None
    
    async def _parse_match(self, match: Dict, competition: str) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida REAL"""
        try:
            home_team = match.get('homeTeam', {})
            away_team = match.get('awayTeam', {})
            score = match.get('score', {})
            
            return {
                'match_id': f"footballdata_{match.get('id')}",
                'id': match.get('id'),
                'home_team': home_team.get('name', 'Unknown'),
                'away_team': away_team.get('name', 'Unknown'),
                'home_team_id': home_team.get('id'),
                'away_team_id': away_team.get('id'),
                'home_score': score.get('fullTime', {}).get('home'),
                'away_score': score.get('fullTime', {}).get('away'),
                'status': match.get('status'),
                'competition': competition,
                'start_time': match.get('utcDate'),
                'is_live': match.get('status') == 'IN_PLAY',
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'football_data_real',
                'data_quality': '100_percent_real'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar partida: {e}")
            return None
    
    def _extract_minute(self, match: Dict) -> int:
        """Extrai minuto da partida se disponível"""
        try:
            # Football-Data.org não fornece minuto em tempo real no tier gratuito
            # Calcular baseado no tempo de início
            start_time = match.get('utcDate')
            if start_time:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                now = datetime.now(tz=timezone.utc)
                elapsed = (now - start_dt).total_seconds() / 60
                return max(0, min(int(elapsed), 120))  # Máximo 120 minutos
            return 0
        except:
            return 0


# 🚀 FUNÇÕES PRINCIPAIS PARA USO NA API
async def get_live_matches_football_data_real() -> List[Dict[str, Any]]:
    """Função principal para obter partidas ao vivo 100% REAIS via Football-Data.org"""
    try:
        async with FootballDataScraper() as scraper:
            matches = await scraper.get_live_matches_real()
            
            logger.info(f"⚽ FOOTBALL-DATA: {len(matches)} partidas ao vivo 100% REAIS")
            
            if matches:
                for match in matches[:3]:
                    logger.info(f"✅ REAL: {match['home_team']} vs {match['away_team']} - Status: {match['status']}")
            
            return matches
            
    except Exception as e:
        logger.error(f"❌ ERRO na busca Football-Data: {e}")
        return []

async def get_today_matches_football_data_real() -> List[Dict[str, Any]]:
    """Função para obter partidas de hoje 100% REAIS via Football-Data.org"""
    try:
        async with FootballDataScraper() as scraper:
            matches = await scraper.get_today_matches_real()
            
            logger.info(f"📅 FOOTBALL-DATA: {len(matches)} partidas de hoje 100% REAIS")
            return matches
            
    except Exception as e:
        logger.error(f"❌ ERRO nas partidas de hoje Football-Data: {e}")
        return []

async def get_premier_league_standings_real() -> List[Dict[str, Any]]:
    """Função para obter classificação REAL da Premier League"""
    try:
        async with FootballDataScraper() as scraper:
            standings = await scraper.get_competition_standings_real("PL")
            
            logger.info(f"🏆 FOOTBALL-DATA: Classificação Premier League 100% REAL")
            return standings
            
    except Exception as e:
        logger.error(f"❌ ERRO na classificação: {e}")
        return []

# Para execução direta
if __name__ == "__main__":
    async def test_football_data_real():
        print("⚽ TESTANDO FOOTBALL-DATA.ORG - DADOS 100% REAIS GRATUITOS")
        print("=" * 70)
        
        # Teste partidas ao vivo
        live = await get_live_matches_football_data_real()
        print(f"🔴 Partidas ao vivo REAIS: {len(live)}")
        
        if live:
            print("\n📊 PRIMEIRA PARTIDA REAL:")
            print(json.dumps(live[0], indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 70)
        
        # Teste partidas de hoje
        today = await get_today_matches_football_data_real()
        print(f"📅 Partidas de hoje REAIS: {len(today)}")
        
        if today:
            print(f"\n📋 EXEMPLO: {today[0]['home_team']} vs {today[0]['away_team']}")
        
        print("\n" + "=" * 70)
        
        # Teste classificação
        standings = await get_premier_league_standings_real()
        print(f"🏆 Classificação Premier League: {len(standings)} times")
        
        if standings:
            print(f"\n🥇 LÍDER: {standings[0]['team']} - {standings[0]['points']} pontos")
    
    asyncio.run(test_football_data_real()) 