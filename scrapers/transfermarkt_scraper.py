"""
🏆 SCRAPER ROBUSTO TRANSFERMARKT - DADOS REAIS
Sistema completo de scraping de times e jogadores do Transfermarkt
"""
import asyncio
import aiohttp
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup  # type: ignore

logger = logging.getLogger(__name__)

class TransfermarktScraper:
    """Scraper robusto para dados reais do Transfermarkt"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://www.transfermarkt.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.rate_limit_delay = 2.0  # Mais conservativo para evitar bloqueio
        self.max_retries = 3
        self.timeout = 45
    
    async def __aenter__(self):
        """Contexto assíncrono - entrada"""
        connector = aiohttp.TCPConnector(
            limit=5,
            limit_per_host=2,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        
        logger.info("🏆 Transfermarkt scraper iniciado - DADOS REAIS")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto assíncrono - saída"""
        if self.session:
            await self.session.close()
            logger.info("🔒 Transfermarkt scraper encerrado")
    
    async def _make_request(self, url: str) -> Optional[str]:
        """Faz requisição com retry e rate limiting"""
        if not self.session:
            logger.error("❌ Sessão não inicializada")
            return None
            
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.rate_limit_delay)
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        logger.debug(f"✅ Requisição bem-sucedida: {url}")
                        return html
                    
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', '120'))
                        logger.warning(f"⚠️ Rate limit - aguardando {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    elif response.status == 403:
                        logger.warning(f"⚠️ Acesso negado (403) para: {url}")
                        await asyncio.sleep(10)
                        
                    else:
                        logger.warning(f"⚠️ Status {response.status} para: {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout na requisição - tentativa {attempt + 1}")
                
            except Exception as e:
                logger.error(f"❌ Erro na requisição: {e}")
                
            # Delay exponencial entre tentativas
            if attempt < self.max_retries - 1:
                await asyncio.sleep(5 * (attempt + 1))
        
        logger.error(f"❌ Falha após {self.max_retries} tentativas: {url}")
        return None
    
    async def search_team_by_name(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Busca time pelo nome e retorna informações básicas"""
        try:
            # URL de busca do Transfermarkt
            search_query = quote(team_name)
            search_url = f"{self.base_url}/schnellsuche/ergebnis/schnellsuche?query={search_query}&Verein_page=1"
            
            logger.info(f"🔍 Buscando time: {team_name}")
            
            html = await self._make_request(search_url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar na seção de clubes
            club_section = soup.find('div', {'id': 'yw1'})  # Seção de clubes
            if not club_section:
                logger.warning(f"⚠️ Seção de clubes não encontrada para: {team_name}")
                return None
            
            # Primeiro resultado de clube
            club_row = club_section.find('tr', class_='odd')
            if not club_row:
                club_row = club_section.find('tr', class_='even')
            
            if not club_row:
                logger.warning(f"⚠️ Nenhum clube encontrado para: {team_name}")
                return None
            
            # Extrair dados do time
            team_link = club_row.find('a', title=True)
            if not team_link:
                return None
            
            team_url = urljoin(self.base_url, team_link['href'])
            team_name_real = team_link.get('title', team_name)
            
            # Extrair país e liga se disponível
            cells = club_row.find_all('td')
            country = 'Unknown'
            league = 'Unknown'
            
            if len(cells) >= 3:
                country_cell = cells[1]
                if country_cell:
                    country_img = country_cell.find('img')
                    if country_img and 'alt' in country_img.attrs:
                        country = country_img['alt']
                
                league_cell = cells[2]
                if league_cell:
                    league_link = league_cell.find('a')
                    if league_link:
                        league = league_link.get_text(strip=True)
            
            team_info = {
                'name': team_name_real,
                'url': team_url,
                'country': country,
                'league': league,
                'original_search': team_name,
                'found_at': datetime.now(tz=timezone.utc).isoformat()
            }
            
            logger.info(f"✅ Time encontrado: {team_name_real} ({country} - {league})")
            return team_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar time {team_name}: {e}")
            return None
    
    async def scrape_team_players(self, team_name: str) -> List[Dict[str, Any]]:
        """🎽 Busca jogadores REAIS de um time"""
        try:
            # Primeiro, encontrar o time
            team_info = await self.search_team_by_name(team_name)
            if not team_info:
                logger.warning(f"⚠️ Time não encontrado: {team_name}")
                return []
            
            # Construir URL do elenco
            team_url = team_info['url']
            if '/verein/' in team_url:
                # Modificar URL para página de jogadores
                squad_url = team_url.replace('/startseite/verein/', '/kader/verein/')
                squad_url = squad_url.replace('/profil/verein/', '/kader/verein/')
                
                # Adicionar parâmetro de saison atual
                if '?' not in squad_url:
                    squad_url += '?saison_id=2024'
            else:
                logger.warning(f"⚠️ URL do time inválida: {team_url}")
                return []
            
            logger.info(f"🎽 Buscando elenco de: {team_info['name']}")
            
            html = await self._make_request(squad_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar tabela de jogadores
            squad_table = soup.find('table', class_='items')
            if not squad_table:
                logger.warning(f"⚠️ Tabela de elenco não encontrada para: {team_name}")
                return []
            
            players = []
            player_rows = squad_table.find('tbody').find_all('tr') if squad_table.find('tbody') else []
            
            for row in player_rows:
                try:
                    player_data = self._parse_player_row(row, team_info)
                    if player_data:
                        players.append(player_data)
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar jogador: {e}")
                    continue
            
            logger.info(f"🎉 {len(players)} jogadores REAIS processados para {team_info['name']}")
            return players
            
        except Exception as e:
            logger.error(f"❌ Erro crítico ao buscar jogadores do time {team_name}: {e}")
            return []
    
    def _parse_player_row(self, row, team_info: Dict) -> Optional[Dict[str, Any]]:
        """Processa dados de um jogador da tabela"""
        try:
            cells = row.find_all('td')
            if len(cells) < 8:  # Verificar se tem colunas suficientes
                return None
            
            # Nome do jogador
            name_cell = cells[1]  # Segunda coluna geralmente tem o nome
            name_link = name_cell.find('a')
            if not name_link:
                return None
            
            player_name = name_link.get_text(strip=True)
            player_url = urljoin(self.base_url, name_link['href'])
            
            # Posição
            position_cell = cells[2]
            position = position_cell.get_text(strip=True) if position_cell else 'Unknown'
            
            # Idade
            age_cell = cells[3]
            age_text = age_cell.get_text(strip=True) if age_cell else '0'
            age = self._extract_number(age_text)
            
            # Nacionalidade
            nationality_cell = cells[4]
            nationality = 'Unknown'
            if nationality_cell:
                nationality_img = nationality_cell.find('img')
                if nationality_img and 'alt' in nationality_img.attrs:
                    nationality = nationality_img['alt']
            
            # Valor de mercado
            market_value_cell = cells[5] if len(cells) > 5 else None
            market_value = self._parse_market_value(market_value_cell.get_text(strip=True) if market_value_cell else '0')
            
            # Número da camisa (se disponível)
            number_cell = cells[0]  # Primeira coluna geralmente tem o número
            jersey_number = self._extract_number(number_cell.get_text(strip=True) if number_cell else '0')
            
            player_data = {
                'name': player_name,
                'url': player_url,
                'position': position,
                'age': age,
                'nationality': nationality,
                'market_value': market_value,
                'jersey_number': jersey_number,
                'team_name': team_info['name'],
                'team_country': team_info['country'],
                'team_league': team_info['league'],
                'scraped_at': datetime.now(tz=timezone.utc).isoformat(),
                'source': 'transfermarkt_real'
            }
            
            return player_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar linha do jogador: {e}")
            return None
    
    def _extract_number(self, text: str) -> int:
        """Extrai número de texto"""
        try:
            # Remover caracteres não numéricos e pegar primeiro número
            numbers = re.findall(r'\d+', text.replace('.', '').replace(',', ''))
            return int(numbers[0]) if numbers else 0
        except (ValueError, IndexError):
            return 0
    
    def _parse_market_value(self, value_text: str) -> int:
        """Converte valor de mercado para número"""
        try:
            if not value_text or value_text == '-':
                return 0
            
            # Remover espaços e converter para minúsculo
            value = value_text.lower().strip()
            
            # Extrair número
            number_match = re.search(r'([0-9,\.]+)', value)
            if not number_match:
                return 0
            
            number_str = number_match.group(1).replace(',', '.')
            number = float(number_str)
            
            # Multiplicadores
            if 'mil' in value or 'k' in value:
                return int(number * 1000)
            elif 'mi' in value or 'm' in value:
                return int(number * 1000000)
            elif 'bi' in value or 'b' in value:
                return int(number * 1000000000)
            else:
                return int(number)
                
        except (ValueError, AttributeError):
            return 0

async def scrape_transfermarkt_teams(team_names: List[str]):
    """Função principal para scraping do Transfermarkt"""
    try:
        async with TransfermarktScraper() as scraper:
            total_players = 0
            
            for team_name in team_names:
                logger.info(f"Buscando jogadores do {team_name}...")
                
                players = await scraper.scrape_team_players(team_name)
                total_players += len(players)
                logger.info(f"✅ {len(players)} jogadores encontrados para {team_name}")
                
                await asyncio.sleep(1)  # Rate limiting
            
            logger.info(f"🎉 Scraping concluído! Total: {total_players} jogadores")
            return total_players
            
    except Exception as e:
        logger.error(f"Erro no scraping do Transfermarkt: {e}")
        return 0 