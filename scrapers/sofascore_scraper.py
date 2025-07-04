"""
🔥 SCRAPER ROBUSTO SOFASCORE - DADOS REAIS AO VIVO
Sistema completo de scraping em tempo real do SofaScore
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class SofascoreScraper:
    """Scraper robusto para dados reais do SofaScore"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://api.sofascore.com/api/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        }
        self.rate_limit_delay = 1.0
        self.max_retries = 3
        self.timeout = 30
    
    async def __aenter__(self):
        """Contexto assíncrono - entrada"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        
        logger.info("🔥 SofaScore scraper iniciado - DADOS REAIS")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto assíncrono - saída"""
        if self.session:
            await self.session.close()
            logger.info("🔒 SofaScore scraper encerrado")
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Faz requisição com retry e rate limiting"""
        if not self.session:
            logger.error("❌ Sessão não inicializada")
            return None
            
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.rate_limit_delay)
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"✅ {endpoint} - Status: {response.status}")
                        return data
                    
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', '60'))
                        logger.warning(f"⚠️ Rate limit - aguardando {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    else:
                        logger.warning(f"⚠️ {endpoint} - Status: {response.status}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout no endpoint {endpoint} - tentativa {attempt + 1}")
                
            except Exception as e:
                logger.error(f"❌ Erro na requisição {endpoint}: {e}")
                
            # Delay exponencial entre tentativas
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"❌ Falha após {self.max_retries} tentativas: {endpoint}")
        return None
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """🔴 PARTIDAS AO VIVO - DADOS REAIS EM TEMPO REAL"""
        try:
            logger.info("🔍 Buscando partidas ao vivo REAIS...")
            
            # Endpoint para partidas ao vivo do SofaScore
            data = await self._make_request("/sport/football/events/live")
            
            if not data or 'events' not in data:
                logger.warning("⚠️ Nenhuma partida ao vivo encontrada")
                return []
            
            live_matches = []
            events = data.get('events', [])
            
            for event in events:
                try:
                    match = await self._parse_live_match(event)
                    if match:
                        live_matches.append(match)
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar partida {event.get('id')}: {e}")
                    continue
            
            logger.info(f"🎉 {len(live_matches)} partidas ao vivo REAIS processadas")
            return live_matches
            
        except Exception as e:
            logger.error(f"❌ Erro crítico no scraping de partidas ao vivo: {e}")
            return []
    
    async def _parse_live_match(self, event: Dict) -> Optional[Dict[str, Any]]:
        """Processa dados de uma partida ao vivo REAL"""
        try:
            # Informações básicas
            match_id = event.get('id')
            if not match_id:
                return None
            
            # Times
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            
            # Placar
            home_score = event.get('homeScore', {}).get('current', 0)
            away_score = event.get('awayScore', {}).get('current', 0)
            
            # Status e tempo
            status = event.get('status', {})
            match_status = status.get('description', 'unknown')
            minute = status.get('minute', 0)
            
            # Torneio
            tournament = event.get('tournament', {})
            competition = tournament.get('name', 'Unknown')
            country = tournament.get('category', {}).get('name', 'Unknown')
            
            # Timestamp
            start_timestamp = event.get('startTimestamp')
            start_time = None
            if start_timestamp:
                start_time = datetime.fromtimestamp(start_timestamp, tz=timezone.utc)
            
            match_data = {
                'match_id': f"sofascore_{match_id}",
                'id': match_id,
                'home_team': home_team.get('name', 'Unknown'),
                'away_team': away_team.get('name', 'Unknown'),
                'home_team_id': home_team.get('id'),
                'away_team_id': away_team.get('id'),
                'home_score': home_score,
                'away_score': away_score,
                'minute': minute,
                'status': match_status,
                'competition': competition,
                'country': country,
                'start_time': start_time.isoformat() if start_time else None,
                'is_live': match_status.lower() in ['live', '1st half', '2nd half', 'halftime', 'inplay'],
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'sofascore_real'
            }
            
            # Buscar dados adicionais se partida está ao vivo
            if match_data['is_live']:
                additional_data = await self._get_live_match_details(match_id)
                if additional_data:
                    match_data.update(additional_data)
            
            return match_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao parsear partida: {e}")
            return None
    
    async def _get_live_match_details(self, match_id: str) -> Optional[Dict]:
        """Busca detalhes adicionais da partida ao vivo"""
        try:
            # Estatísticas da partida
            stats_data = await self._make_request(f"/event/{match_id}/statistics")
            
            details = {}
            
            if stats_data and 'statistics' in stats_data:
                stats = stats_data['statistics']
                
                for period in stats:
                    groups = period.get('groups', [])
                    
                    for group in groups:
                        stats_items = group.get('statisticsItems', [])
                        
                        for item in stats_items:
                            name = item.get('name', '').lower()
                            home_value = item.get('homeValue', 0)
                            away_value = item.get('awayValue', 0)
                            
                            # Mapear estatísticas importantes para apostas
                            if 'possession' in name:
                                details['home_possession'] = self._safe_int(home_value)
                                details['away_possession'] = self._safe_int(away_value)
                            
                            elif 'shots' in name and 'target' in name:
                                details['home_shots_on_target'] = self._safe_int(home_value)
                                details['away_shots_on_target'] = self._safe_int(away_value)
                            
                            elif 'corner' in name:
                                details['home_corners'] = self._safe_int(home_value)
                                details['away_corners'] = self._safe_int(away_value)
                            
                            elif 'yellow card' in name:
                                details['home_yellow_cards'] = self._safe_int(home_value)
                                details['away_yellow_cards'] = self._safe_int(away_value)
                            
                            elif 'red card' in name:
                                details['home_red_cards'] = self._safe_int(home_value)
                                details['away_red_cards'] = self._safe_int(away_value)
            
            # Buscar odds se disponível
            odds_data = await self._make_request(f"/event/{match_id}/odds/1/all")
            if odds_data and 'markets' in odds_data:
                odds_info = self._parse_odds(odds_data['markets'])
                details.update(odds_info)
            
            return details
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes da partida {match_id}: {e}")
            return {}
    
    def _parse_odds(self, markets: List[Dict]) -> Dict:
        """Extrai odds das casas de apostas"""
        odds_info = {}
        
        try:
            for market in markets:
                market_name = market.get('marketName', '').lower()
                
                if '1x2' in market_name or 'match winner' in market_name:
                    choices = market.get('choices', [])
                    
                    for choice in choices:
                        name = choice.get('name', '').lower()
                        fractional_value = choice.get('fractionalValue')
                        
                        if fractional_value:
                            if '1' in name or 'home' in name:
                                odds_info['odds_home'] = round(float(fractional_value), 2)
                            elif 'x' in name or 'draw' in name:
                                odds_info['odds_draw'] = round(float(fractional_value), 2)
                            elif '2' in name or 'away' in name:
                                odds_info['odds_away'] = round(float(fractional_value), 2)
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar odds: {e}")
        
        return odds_info
    
    def _safe_int(self, value) -> int:
        """Converte valor para int de forma segura"""
        try:
            if isinstance(value, str):
                value = value.replace('%', '')
            return int(float(value))
        except (ValueError, TypeError):
            return 0

async def scrape_live_matches():
    """Função principal para scraping do Sofascore"""
    try:
        async with SofascoreScraper() as scraper:
            matches = await scraper.get_live_matches()
            logger.info(f"✅ {len(matches)} partidas ao vivo encontradas")
            return matches
            
    except Exception as e:
        logger.error(f"Erro no scraping do Sofascore: {e}")
        return []

# Para execução direta
if __name__ == "__main__":
    asyncio.run(scrape_live_matches()) 