"""
⚽ ESPN SPORTS API - DADOS 100% REAIS
Sistema usando ESPN Sports APIs públicas para dados reais ao vivo
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class ESPNScraper:
    """Scraper usando ESPN Sports APIs - DADOS 100% REAIS"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://www.espn.com.br/",
            "Origin": "https://www.espn.com.br"
        }
        self.rate_limit_delay = 1.0  # ESPN é mais permissivo
        self.max_retries = 3
        self.timeout = 30
    
    async def __aenter__(self):
        """Contexto assíncrono - entrada"""
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        
        logger.info("⚽ ESPN scraper iniciado - DADOS 100% REAIS")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto assíncrono - saída"""
        if self.session:
            await self.session.close()
            logger.info("🔒 ESPN scraper encerrado")
    
    async def get_live_soccer_matches_real(self) -> List[Dict[str, Any]]:
        """🔴 PARTIDAS DE FUTEBOL AO VIVO - 100% REAIS via ESPN"""
        try:
            logger.info("🔍 Buscando partidas de futebol ao vivo REAIS via ESPN...")
            
            # Ligas disponíveis na ESPN
            leagues = [
                'bra.1',  # Brasileirão
                'eng.1',  # Premier League
                'esp.1',  # La Liga
                'ita.1',  # Serie A
                'ger.1',  # Bundesliga
                'fra.1',  # Ligue 1
                'uefa.champions',  # Champions League
                'conmebol.libertadores'  # Libertadores
            ]
            
            all_matches = []
            
            for league in leagues:
                try:
                    endpoint = f"/soccer/{league}/scoreboard"
                    data = await self._make_request(endpoint)
                    
                    if data and data.get('events'):
                        events = data['events']
                        
                        for event in events:
                            # Verificar se está ao vivo
                            status = event.get('status', {})
                            status_type = status.get('type', {}).get('name', '')
                            
                            if status_type in ['STATUS_IN_PROGRESS', 'STATUS_HALFTIME']:
                                match = await self._parse_live_soccer_match(event, league)
                                if match:
                                    all_matches.append(match)
                        
                        logger.info(f"✅ ESPN {league}: {len([e for e in events if e.get('status', {}).get('type', {}).get('name') in ['STATUS_IN_PROGRESS', 'STATUS_HALFTIME']])} ao vivo")
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro na liga {league}: {e}")
                    continue
            
            logger.info(f"🎉 ESPN: {len(all_matches)} partidas de futebol ao vivo 100% REAIS")
            return all_matches
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na busca ESPN: {e}")
            return []
    
    async def get_today_soccer_matches_real(self) -> List[Dict[str, Any]]:
        """📅 PARTIDAS DE FUTEBOL DE HOJE - 100% REAIS"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            logger.info(f"📅 Buscando partidas de futebol de hoje ({today}) - DADOS REAIS ESPN")
            
            leagues = ['bra.1', 'eng.1', 'esp.1', 'ita.1', 'ger.1', 'fra.1', 'uefa.champions']
            all_matches = []
            
            for league in leagues:
                try:
                    endpoint = f"/soccer/{league}/scoreboard"
                    params = {"dates": today}
                    
                    data = await self._make_request(endpoint, params)
                    
                    if data and data.get('events'):
                        for event in data['events']:
                            match = await self._parse_soccer_match(event, league)
                            if match:
                                all_matches.append(match)
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro em {league}: {e}")
                    continue
            
            logger.info(f"📅 ESPN: {len(all_matches)} partidas de hoje REAIS")
            return all_matches
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar partidas de hoje ESPN: {e}")
            return []
    
    async def get_basketball_live_real(self) -> List[Dict[str, Any]]:
        """🏀 PARTIDAS DE BASQUETE AO VIVO - 100% REAIS"""
        try:
            logger.info("🏀 Buscando partidas de basquete ao vivo REAIS via ESPN...")
            
            leagues = ['nba', 'mens-college-basketball']
            all_matches = []
            
            for league in leagues:
                try:
                    endpoint = f"/basketball/{league}/scoreboard"
                    data = await self._make_request(endpoint)
                    
                    if data and data.get('events'):
                        for event in data['events']:
                            status_type = event.get('status', {}).get('type', {}).get('name', '')
                            
                            if status_type == 'STATUS_IN_PROGRESS':
                                match = await self._parse_basketball_match(event, league)
                                if match:
                                    all_matches.append(match)
                    
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Erro no basquete {league}: {e}")
                    continue
            
            logger.info(f"🏀 ESPN: {len(all_matches)} partidas de basquete ao vivo REAIS")
            return all_matches
            
        except Exception as e:
            logger.error(f"❌ Erro no basquete ESPN: {e}")
            return []
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Faz requisição para ESPN API"""
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
                        logger.debug(f"✅ ESPN {endpoint} - Status: 200")
                        return data
                    
                    elif response.status == 429:
                        logger.warning(f"⚠️ Rate limit ESPN - aguardando...")
                        await asyncio.sleep(10)
                        continue
                    
                    elif response.status == 403:
                        logger.warning(f"⚠️ Acesso negado ESPN")
                        return None
                    
                    else:
                        logger.warning(f"⚠️ ESPN Status {response.status} para {endpoint}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout ESPN - tentativa {attempt + 1}")
                
            except Exception as e:
                logger.error(f"❌ Erro na requisição ESPN: {e}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"❌ ESPN falha após {self.max_retries} tentativas: {endpoint}")
        return None
    
    async def _parse_live_soccer_match(self, event: Dict, league: str) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida de futebol ao vivo REAL"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                return None
            
            # Identificar casa e fora
            home_team = None
            away_team = None
            
            for competitor in competitors:
                if competitor.get('homeAway') == 'home':
                    home_team = competitor
                else:
                    away_team = competitor
            
            if not home_team or not away_team:
                return None
            
            status = event.get('status', {})
            
            match_data = {
                'match_id': f"espn_{event.get('id')}",
                'id': event.get('id'),
                'home_team': home_team.get('team', {}).get('displayName', 'Unknown'),
                'away_team': away_team.get('team', {}).get('displayName', 'Unknown'),
                'home_team_id': home_team.get('team', {}).get('id'),
                'away_team_id': away_team.get('team', {}).get('id'),
                'home_score': int(home_team.get('score', 0)),
                'away_score': int(away_team.get('score', 0)),
                'minute': self._extract_soccer_minute(status),
                'status': status.get('type', {}).get('description', 'Unknown'),
                'competition': league,
                'start_time': event.get('date'),
                'is_live': True,
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'espn_real',
                'data_quality': '100_percent_real'
            }
            
            # Adicionar estatísticas se disponível
            self._add_soccer_statistics(match_data, competition)
            
            return match_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar partida ao vivo ESPN: {e}")
            return None
    
    async def _parse_soccer_match(self, event: Dict, league: str) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida de futebol REAL"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                return None
            
            home_team = None
            away_team = None
            
            for competitor in competitors:
                if competitor.get('homeAway') == 'home':
                    home_team = competitor
                else:
                    away_team = competitor
            
            if not home_team or not away_team:
                return None
            
            status = event.get('status', {})
            status_type = status.get('type', {}).get('name', '')
            
            return {
                'match_id': f"espn_{event.get('id')}",
                'id': event.get('id'),
                'home_team': home_team.get('team', {}).get('displayName', 'Unknown'),
                'away_team': away_team.get('team', {}).get('displayName', 'Unknown'),
                'home_team_id': home_team.get('team', {}).get('id'),
                'away_team_id': away_team.get('team', {}).get('id'),
                'home_score': int(home_team.get('score', 0)) if home_team.get('score') else None,
                'away_score': int(away_team.get('score', 0)) if away_team.get('score') else None,
                'status': status.get('type', {}).get('description', 'Unknown'),
                'competition': league,
                'start_time': event.get('date'),
                'is_live': status_type in ['STATUS_IN_PROGRESS', 'STATUS_HALFTIME'],
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'espn_real',
                'data_quality': '100_percent_real'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar partida ESPN: {e}")
            return None
    
    async def _parse_basketball_match(self, event: Dict, league: str) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida de basquete REAL"""
        try:
            competitions = event.get('competitions', [])
            if not competitions:
                return None
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) != 2:
                return None
            
            home_team = None
            away_team = None
            
            for competitor in competitors:
                if competitor.get('homeAway') == 'home':
                    home_team = competitor
                else:
                    away_team = competitor
            
            if not home_team or not away_team:
                return None
            
            status = event.get('status', {})
            
            return {
                'match_id': f"espn_bball_{event.get('id')}",
                'id': event.get('id'),
                'sport': 'basketball',
                'home_team': home_team.get('team', {}).get('displayName', 'Unknown'),
                'away_team': away_team.get('team', {}).get('displayName', 'Unknown'),
                'home_score': int(home_team.get('score', 0)),
                'away_score': int(away_team.get('score', 0)),
                'period': self._extract_basketball_period(status),
                'time_remaining': status.get('displayClock', ''),
                'status': status.get('type', {}).get('description', 'Unknown'),
                'competition': league,
                'start_time': event.get('date'),
                'is_live': True,
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'espn_real',
                'data_quality': '100_percent_real'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar basquete ESPN: {e}")
            return None
    
    def _extract_soccer_minute(self, status: Dict) -> int:
        """Extrai minuto da partida de futebol"""
        try:
            display_clock = status.get('displayClock', '')
            if display_clock and "'" in display_clock:
                minute_str = display_clock.replace("'", "").replace("+", "")
                return int(minute_str.split()[0])
            return 0
        except:
            return 0
    
    def _extract_basketball_period(self, status: Dict) -> str:
        """Extrai período do basquete"""
        try:
            period = status.get('period', 0)
            if period <= 4:
                return f"{period}º Quarto"
            else:
                return f"Prorrogação {period - 4}"
        except:
            return "1º Quarto"
    
    def _add_soccer_statistics(self, match_data: Dict, competition: Dict):
        """Adiciona estatísticas de futebol se disponível"""
        try:
            # ESPN às vezes fornece estatísticas básicas
            if 'details' in competition:
                details = competition['details']
                # Aqui poderia extrair mais detalhes se disponível
                pass
        except:
            pass


# 🚀 FUNÇÕES PRINCIPAIS PARA USO NA API
async def get_live_soccer_espn_real() -> List[Dict[str, Any]]:
    """Função principal para obter partidas de futebol ao vivo 100% REAIS via ESPN"""
    try:
        async with ESPNScraper() as scraper:
            matches = await scraper.get_live_soccer_matches_real()
            
            logger.info(f"⚽ ESPN: {len(matches)} partidas de futebol ao vivo 100% REAIS")
            
            if matches:
                for match in matches[:3]:
                    logger.info(f"✅ REAL: {match['home_team']} vs {match['away_team']} - {match['minute']}'")
            
            return matches
            
    except Exception as e:
        logger.error(f"❌ ERRO ESPN futebol: {e}")
        return []

async def get_live_basketball_espn_real() -> List[Dict[str, Any]]:
    """Função para obter partidas de basquete ao vivo 100% REAIS via ESPN"""
    try:
        async with ESPNScraper() as scraper:
            matches = await scraper.get_basketball_live_real()
            
            logger.info(f"🏀 ESPN: {len(matches)} partidas de basquete ao vivo 100% REAIS")
            return matches
            
    except Exception as e:
        logger.error(f"❌ ERRO ESPN basquete: {e}")
        return []

async def get_today_soccer_espn_real() -> List[Dict[str, Any]]:
    """Função para obter partidas de futebol de hoje 100% REAIS via ESPN"""
    try:
        async with ESPNScraper() as scraper:
            matches = await scraper.get_today_soccer_matches_real()
            
            logger.info(f"📅 ESPN: {len(matches)} partidas de hoje 100% REAIS")
            return matches
            
    except Exception as e:
        logger.error(f"❌ ERRO ESPN hoje: {e}")
        return []

# Para execução direta
if __name__ == "__main__":
    async def test_espn_real():
        print("⚽ TESTANDO ESPN SPORTS API - DADOS 100% REAIS")
        print("=" * 60)
        
        # Teste futebol ao vivo
        soccer_live = await get_live_soccer_espn_real()
        print(f"⚽ Futebol ao vivo REAIS: {len(soccer_live)}")
        
        if soccer_live:
            print("\n📊 PRIMEIRA PARTIDA REAL:")
            print(json.dumps(soccer_live[0], indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 60)
        
        # Teste basquete ao vivo
        basketball_live = await get_live_basketball_espn_real()
        print(f"🏀 Basquete ao vivo REAIS: {len(basketball_live)}")
        
        print("\n" + "=" * 60)
        
        # Teste futebol de hoje
        soccer_today = await get_today_soccer_espn_real()
        print(f"📅 Futebol hoje REAIS: {len(soccer_today)}")
        
        if soccer_today:
            print(f"\n📋 EXEMPLO: {soccer_today[0]['home_team']} vs {soccer_today[0]['away_team']}")
    
    asyncio.run(test_espn_real()) 