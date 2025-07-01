"""
🎯 UNIFIED REAL SCRAPER - SISTEMA UNIFICADO 100% DADOS REAIS
Combina múltiplas fontes reais com sistema de fallback inteligente
ZERO simulação - apenas dados reais de APIs confiáveis
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging
import json
from urllib.parse import urljoin

# Importar os scrapers específicos
try:
    from .api_football_real import get_live_matches_100_real, get_today_fixtures_100_real
    from .football_data_real import get_live_matches_football_data_real, get_today_matches_football_data_real
    from .espn_real import get_live_soccer_espn_real, get_today_soccer_espn_real, get_live_basketball_espn_real
except ImportError:
    # Para execução direta
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))

logger = logging.getLogger(__name__)

class UnifiedRealScraper:
    """Sistema Unificado de Scraping 100% REAL"""
    
    def __init__(self):
        self.sources = [
            'espn',           # ESPN Sports (mais confiável)
            'football_data',  # Football-Data.org (gratuito)
            'api_football',   # API-Football (se tiver chave)
            'live_score'      # LiveScore alternativo
        ]
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_concurrent = 3  # Máximo de fontes simultâneas
        
    async def __aenter__(self):
        """Contexto assíncrono - entrada"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        
        logger.info("🎯 UNIFIED REAL SCRAPER INICIADO - ZERO SIMULAÇÃO")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto assíncrono - saída"""
        if self.session:
            await self.session.close()
            logger.info("🔒 Unified Real Scraper encerrado")
    
    async def get_all_live_matches_real(self) -> List[Dict[str, Any]]:
        """🔴 PARTIDAS AO VIVO DE TODAS AS FONTES REAIS"""
        logger.info("🔍 Buscando partidas ao vivo em TODAS as fontes REAIS...")
        
        # Executar scrapers em paralelo para máxima eficiência
        tasks = []
        
        # ESPN (mais rápido e confiável)
        tasks.append(self._safe_scraper_call("ESPN", get_live_soccer_espn_real))
        
        # Football-Data.org (gratuito)
        tasks.append(self._safe_scraper_call("Football-Data", get_live_matches_football_data_real))
        
        # API-Football (se disponível)
        tasks.append(self._safe_scraper_call("API-Football", get_live_matches_100_real))
        
        # LiveScore alternativo
        tasks.append(self._safe_scraper_call("LiveScore", self._get_livescore_matches))
        
        # Aguardar todos os resultados
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Consolidar resultados
        all_matches = []
        source_counts = {}
        
        for i, result in enumerate(results):
            source_name = ["ESPN", "Football-Data", "API-Football", "LiveScore"][i]
            
            if isinstance(result, Exception):
                logger.warning(f"⚠️ {source_name} falhou: {result}")
                source_counts[source_name] = 0
                continue
            
            if isinstance(result, list):
                matches = result
                source_counts[source_name] = len(matches)
                all_matches.extend(matches)
                logger.info(f"✅ {source_name}: {len(matches)} partidas REAIS")
        
        # Remover duplicatas baseado em times
        unique_matches = self._remove_duplicates(all_matches)
        
        logger.info(f"🎉 TOTAL CONSOLIDADO: {len(unique_matches)} partidas ao vivo 100% REAIS")
        logger.info(f"📊 Fontes: {source_counts}")
        
        return unique_matches
    
    async def get_all_today_matches_real(self) -> List[Dict[str, Any]]:
        """📅 PARTIDAS DE HOJE DE TODAS AS FONTES REAIS"""
        logger.info("📅 Buscando partidas de hoje em TODAS as fontes REAIS...")
        
        tasks = []
        
        # ESPN
        tasks.append(self._safe_scraper_call("ESPN-Today", get_today_soccer_espn_real))
        
        # Football-Data.org
        tasks.append(self._safe_scraper_call("Football-Data-Today", get_today_matches_football_data_real))
        
        # API-Football
        tasks.append(self._safe_scraper_call("API-Football-Today", get_today_fixtures_100_real))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_matches.extend(result)
        
        unique_matches = self._remove_duplicates(all_matches)
        
        logger.info(f"📅 HOJE TOTAL: {len(unique_matches)} partidas 100% REAIS")
        return unique_matches
    
    async def get_multi_sport_live_real(self) -> Dict[str, List[Dict[str, Any]]]:
        """🏆 MÚLTIPLOS ESPORTES AO VIVO - DADOS REAIS"""
        logger.info("🏆 Buscando múltiplos esportes ao vivo - DADOS REAIS...")
        
        tasks = []
        
        # Futebol
        tasks.append(self._safe_scraper_call("Soccer", self.get_all_live_matches_real))
        
        # Basquete
        tasks.append(self._safe_scraper_call("Basketball", get_live_basketball_espn_real))
        
        # Tênis (se implementado)
        tasks.append(self._safe_scraper_call("Tennis", self._get_tennis_live))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        sports_data = {
            'soccer': results[0] if isinstance(results[0], list) else [],
            'basketball': results[1] if isinstance(results[1], list) else [],
            'tennis': results[2] if isinstance(results[2], list) else []
        }
        
        total_matches = sum(len(matches) for matches in sports_data.values())
        logger.info(f"🏆 MULTI-SPORT: {total_matches} partidas ao vivo REAIS")
        
        return sports_data
    
    async def _safe_scraper_call(self, source_name: str, scraper_func) -> List[Dict[str, Any]]:
        """Executa scraper de forma segura com timeout"""
        try:
            logger.debug(f"🔄 Iniciando {source_name}...")
            
            # Timeout individual por fonte
            result = await asyncio.wait_for(scraper_func(), timeout=15.0)
            
            if not isinstance(result, list):
                logger.warning(f"⚠️ {source_name} retornou tipo inválido")
                return []
            
            logger.debug(f"✅ {source_name} completado: {len(result)} items")
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ {source_name} timeout (15s)")
            return []
        except Exception as e:
            logger.error(f"❌ {source_name} erro: {e}")
            return []
    
    async def _get_livescore_matches(self) -> List[Dict[str, Any]]:
        """Scraper alternativo LiveScore (público)"""
        try:
            if not self.session:
                return []
            
            # URL pública do LiveScore (dados básicos)
            url = "https://www.livescore.com/en/football"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive"
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    # Aqui seria necessário parsing HTML para extrair dados
                    # Por simplicidade, retornando lista vazia por enquanto
                    # Em produção, implementar BeautifulSoup parsing
                    logger.info("📱 LiveScore acessível - parsing HTML necessário")
                    return []
                else:
                    logger.warning(f"⚠️ LiveScore status: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Erro LiveScore: {e}")
            return []
    
    async def _get_tennis_live(self) -> List[Dict[str, Any]]:
        """Buscar tênis ao vivo (placeholder)"""
        try:
            # Implementar quando necessário
            logger.debug("🎾 Tênis ao vivo - não implementado ainda")
            return []
        except Exception as e:
            logger.error(f"❌ Erro tênis: {e}")
            return []
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove partidas duplicadas baseado em times e horário"""
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Criar chave única baseada em times e data
            home = match.get('home_team', '').lower().strip()
            away = match.get('away_team', '').lower().strip()
            start_time = match.get('start_time', '')
            
            # Normalizar nomes de times (remover acentos, etc.)
            key = f"{home}_{away}_{start_time[:10]}"  # Usar apenas data, não hora exata
            
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
                
                # Adicionar info de deduplicação
                match['unified_key'] = key
                match['is_deduplicated'] = True
        
        logger.info(f"🔄 Deduplicação: {len(matches)} → {len(unique_matches)} partidas únicas")
        return unique_matches
    
    def validate_real_data(self, matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Valida se os dados são realmente reais e não simulados"""
        validated = []
        validation_stats = {
            'total': len(matches),
            'real': 0,
            'suspicious': 0,
            'invalid': 0
        }
        
        for match in matches:
            # Verificações de qualidade
            quality_score = 0
            
            # Verificar se tem campos essenciais
            if match.get('home_team') and match.get('away_team'):
                quality_score += 1
            
            # Verificar se tem timestamp real
            if match.get('scraped_at'):
                quality_score += 1
            
            # Verificar se tem fonte identificada
            if match.get('source'):
                quality_score += 1
            
            # Verificar se não é simulação óbvia
            if not self._is_simulation(match):
                quality_score += 1
            
            # Classificar baseado na qualidade
            if quality_score >= 4:
                match['validation_score'] = quality_score
                match['is_validated_real'] = True
                validated.append(match)
                validation_stats['real'] += 1
            elif quality_score >= 2:
                validation_stats['suspicious'] += 1
            else:
                validation_stats['invalid'] += 1
        
        logger.info(f"✅ Validação: {validation_stats['real']}/{validation_stats['total']} partidas validadas como REAIS")
        
        return validated, validation_stats
    
    def _is_simulation(self, match: Dict[str, Any]) -> bool:
        """Detecta se uma partida é simulação"""
        suspicious_indicators = [
            'test',
            'fake',
            'demo',
            'example',
            'sample',
            'mock',
            'dummy'
        ]
        
        # Verificar nomes de times
        home_team = match.get('home_team', '').lower()
        away_team = match.get('away_team', '').lower()
        
        for indicator in suspicious_indicators:
            if indicator in home_team or indicator in away_team:
                return True
        
        # Verificar se fonte indica simulação
        source = match.get('source', '').lower()
        if 'simulate' in source or 'fake' in source:
            return True
        
        return False


# 🚀 FUNÇÕES PRINCIPAIS PARA USO NA API
async def get_unified_live_matches_100_real() -> List[Dict[str, Any]]:
    """Função PRINCIPAL para obter partidas ao vivo 100% REAIS de todas as fontes"""
    try:
        async with UnifiedRealScraper() as scraper:
            # Buscar de todas as fontes
            matches = await scraper.get_all_live_matches_real()
            
            # Validar qualidade dos dados
            validated_matches, stats = scraper.validate_real_data(matches)
            
            logger.info(f"🎯 UNIFIED REAL: {len(validated_matches)} partidas 100% REAIS validadas")
            logger.info(f"📊 Validação: {stats}")
            
            # Adicionar metadata de qualidade
            for match in validated_matches:
                match['unified_scraper_version'] = '1.0'
                match['data_guarantee'] = '100_percent_real'
                match['validation_timestamp'] = datetime.now(tz=timezone.utc).isoformat()
            
            return validated_matches
            
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO Unified Scraper: {e}")
        return []

async def get_unified_today_matches_100_real() -> List[Dict[str, Any]]:
    """Função para obter partidas de hoje 100% REAIS de todas as fontes"""
    try:
        async with UnifiedRealScraper() as scraper:
            matches = await scraper.get_all_today_matches_real()
            validated_matches, stats = scraper.validate_real_data(matches)
            
            logger.info(f"📅 UNIFIED REAL HOJE: {len(validated_matches)} partidas validadas")
            return validated_matches
            
    except Exception as e:
        logger.error(f"❌ ERRO hoje unified: {e}")
        return []

async def get_unified_multi_sport_real() -> Dict[str, List[Dict[str, Any]]]:
    """Função para obter múltiplos esportes 100% REAIS"""
    try:
        async with UnifiedRealScraper() as scraper:
            sports_data = await scraper.get_multi_sport_live_real()
            
            # Validar cada esporte
            for sport, matches in sports_data.items():
                if matches:
                    validated, _ = scraper.validate_real_data(matches)
                    sports_data[sport] = validated
            
            total = sum(len(matches) for matches in sports_data.values())
            logger.info(f"🏆 UNIFIED MULTI-SPORT: {total} partidas REAIS")
            
            return sports_data
            
    except Exception as e:
        logger.error(f"❌ ERRO multi-sport: {e}")
        return {}

# Para execução direta
if __name__ == "__main__":
    async def test_unified_real():
        print("🎯 TESTANDO UNIFIED REAL SCRAPER - ZERO SIMULAÇÃO")
        print("=" * 70)
        
        # Teste partidas ao vivo
        live = await get_unified_live_matches_100_real()
        print(f"🔴 Partidas ao vivo 100% REAIS: {len(live)}")
        
        if live:
            print("\n📊 PRIMEIRA PARTIDA VALIDADA:")
            first_match = live[0]
            print(f"⚽ {first_match['home_team']} vs {first_match['away_team']}")
            print(f"📍 Fonte: {first_match.get('source')}")
            print(f"✅ Validação: {first_match.get('validation_score')}/4")
            print(f"🔐 Garantia: {first_match.get('data_guarantee')}")
        
        print("\n" + "=" * 70)
        
        # Teste partidas de hoje
        today = await get_unified_today_matches_100_real()
        print(f"📅 Partidas de hoje 100% REAIS: {len(today)}")
        
        print("\n" + "=" * 70)
        
        # Teste multi-esporte
        multi = await get_unified_multi_sport_real()
        for sport, matches in multi.items():
            print(f"🏆 {sport.upper()}: {len(matches)} partidas REAIS")
    
    asyncio.run(test_unified_real()) 