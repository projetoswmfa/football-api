"""
🤖 GEMINI AI ANALYZER ROBUSTO - ANÁLISES REAIS DE APOSTAS
Sistema avançado de análise de partidas usando IA para sinais de apostas
"""
import asyncio
import google.generativeai as genai
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import json
import re
from config import settings

logger = logging.getLogger(__name__)

class GeminiRealAnalyzer:
    """Analisador robusto usando Gemini AI para dados reais"""
    
    def __init__(self):
        self.model = None
        self.setup_ai()
    
    def setup_ai(self):
        """Configura o modelo Gemini AI"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                generation_config=generation_config
            )
            
            logger.info("🤖 Gemini AI configurado para análises REAIS")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar Gemini AI: {e}")
            raise
    
    async def analyze_match_for_betting(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 ANÁLISE COMPLETA DE PARTIDA PARA APOSTAS"""
        try:
            if not match_data or not match_data.get('is_live'):
                return self._empty_analysis()
            
            logger.info(f"🔍 Analisando: {match_data.get('home_team')} vs {match_data.get('away_team')}")
            
            # Análises paralelas
            results = await asyncio.gather(
                self._analyze_corners(match_data),
                self._analyze_cards(match_data),
                self._analyze_both_teams_score(match_data),
                return_exceptions=True
            )
            
            corners = results[0] if not isinstance(results[0], Exception) else self._empty_signal()
            cards = results[1] if not isinstance(results[1], Exception) else self._empty_signal()
            btts = results[2] if not isinstance(results[2], Exception) else self._empty_signal()
            
            # Análise consolidada
            consolidated = {
                'match_id': match_data.get('match_id', 'unknown'),
                'home_team': match_data.get('home_team', 'Unknown'),
                'away_team': match_data.get('away_team', 'Unknown'),
                'minute': match_data.get('minute', 0),
                'current_score': f"{match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}",
                'analysis_timestamp': datetime.now(tz=timezone.utc).isoformat(),
                'corners_signal': corners,
                'cards_signal': cards,
                'both_teams_score_signal': btts,
                'source': 'gemini_real_ai'
            }
            
            # Calcular confiança geral
            confidences = [
                corners.get('confidence', 0),
                cards.get('confidence', 0),
                btts.get('confidence', 0)
            ]
            
            consolidated['overall_confidence'] = round(sum(confidences) / len(confidences), 1)
            consolidated['signals_count'] = sum(1 for c in confidences if c >= 7)
            
            logger.info(f"✅ Análise concluída - Confiança: {consolidated['overall_confidence']}/10")
            return consolidated
            
        except Exception as e:
            logger.error(f"❌ Erro na análise: {e}")
            return self._empty_analysis()
    
    async def _analyze_corners(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🚩 ANÁLISE DE ESCANTEIOS"""
        try:
            prompt = f'''
🚩 ANÁLISE DE ESCANTEIOS - DADOS REAIS

PARTIDA: {match_data.get('home_team')} vs {match_data.get('away_team')}
PLACAR: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}
MINUTO: {match_data.get('minute', 0)}'

ESTATÍSTICAS REAIS:
- Escanteios: {match_data.get('home_corners', 0)} - {match_data.get('away_corners', 0)}
- Finalizações: {match_data.get('home_shots', 0)} - {match_data.get('away_shots', 0)}
- No alvo: {match_data.get('home_shots_on_target', 0)} - {match_data.get('away_shots_on_target', 0)}
- Posse: {match_data.get('home_possession', 0)}% - {match_data.get('away_possession', 0)}%

Analise a tendência de escanteios e responda em JSON:
{{
    "recomendacao": "over_8.5" ou "over_9.5" ou "nenhuma",
    "confidence": [1-10],
    "reasoning": "Explicação baseada nos dados"
}}

Só recomende com confiança >= 7.
'''
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if response:
                return self._parse_response(response, 'escanteios')
            
            return self._empty_signal()
            
        except Exception as e:
            logger.error(f"❌ Erro escanteios: {e}")
            return self._empty_signal()
    
    async def _analyze_cards(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🟨 ANÁLISE DE CARTÕES"""
        try:
            total_cards = (match_data.get('home_yellow_cards', 0) + 
                          match_data.get('away_yellow_cards', 0) + 
                          match_data.get('home_red_cards', 0) + 
                          match_data.get('away_red_cards', 0))
            
            prompt = f'''
🟨 ANÁLISE DE CARTÕES - DADOS REAIS

PARTIDA: {match_data.get('home_team')} vs {match_data.get('away_team')}
MINUTO: {match_data.get('minute', 0)}'

CARTÕES ATUAIS:
- Amarelos: {match_data.get('home_yellow_cards', 0)} - {match_data.get('away_yellow_cards', 0)}
- Vermelhos: {match_data.get('home_red_cards', 0)} - {match_data.get('away_red_cards', 0)}
- Total: {total_cards}

Analise a tendência e responda em JSON:
{{
    "recomendacao": "over_3.5" ou "over_4.5" ou "nenhuma",
    "confidence": [1-10],
    "reasoning": "Análise dos cartões"
}}

Só recomende com confiança >= 7.
'''
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if response:
                return self._parse_response(response, 'cartoes')
            
            return self._empty_signal()
            
        except Exception as e:
            logger.error(f"❌ Erro cartões: {e}")
            return self._empty_signal()
    
    async def _analyze_both_teams_score(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """⚽ ANÁLISE AMBAS MARCAM"""
        try:
            prompt = f'''
⚽ ANÁLISE AMBAS MARCAM - DADOS REAIS

PARTIDA: {match_data.get('home_team')} vs {match_data.get('away_team')}
PLACAR: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}
MINUTO: {match_data.get('minute', 0)}'

OFENSIVO:
- Finalizações: {match_data.get('home_shots', 0)} - {match_data.get('away_shots', 0)}
- No alvo: {match_data.get('home_shots_on_target', 0)} - {match_data.get('away_shots_on_target', 0)}
- Tempo restante: ~{90 - match_data.get('minute', 0)} min

Analise se ambas vão marcar e responda em JSON:
{{
    "recomendacao": "sim" ou "nao" ou "nenhuma",
    "confidence": [1-10],
    "reasoning": "Análise das chances"
}}

Só recomende com confiança >= 7.
'''
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if response:
                return self._parse_response(response, 'ambas_marcam')
            
            return self._empty_signal()
            
        except Exception as e:
            logger.error(f"❌ Erro ambas marcam: {e}")
            return self._empty_signal()
    
    def _generate_ai_response(self, prompt: str) -> Optional[str]:
        """Gera resposta da IA"""
        try:
            if not self.model:
                return None
            
            response = self.model.generate_content(prompt)
            return response.text.strip() if response and response.text else None
                
        except Exception as e:
            logger.error(f"❌ Erro IA: {e}")
            return None
    
    def _parse_response(self, response: str, signal_type: str) -> Dict[str, Any]:
        """Parseia resposta da IA"""
        try:
            # Extrair JSON
            json_match = re.search(r'\{[^{}]*"confidence"[^{}]*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                
                return {
                    'tipo': signal_type,
                    'recomendacao': analysis.get('recomendacao', 'nenhuma'),
                    'confidence': min(10, max(1, int(analysis.get('confidence', 1)))),
                    'reasoning': analysis.get('reasoning', 'Análise não disponível')
                }
                
        except Exception as e:
            logger.error(f"❌ Erro parse: {e}")
        
        return self._empty_signal()
    
    def _empty_signal(self) -> Dict[str, Any]:
        """Sinal vazio"""
        return {
            'tipo': 'unknown',
            'recomendacao': 'nenhuma',
            'confidence': 1,
            'reasoning': 'Dados insuficientes'
        }
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Análise vazia"""
        return {
            'match_id': 'unknown',
            'home_team': 'Unknown',
            'away_team': 'Unknown',
            'minute': 0,
            'analysis_timestamp': datetime.now(tz=timezone.utc).isoformat(),
            'corners_signal': self._empty_signal(),
            'cards_signal': self._empty_signal(),
            'both_teams_score_signal': self._empty_signal(),
            'overall_confidence': 1,
            'signals_count': 0,
            'source': 'gemini_real_ai'
        }

# Instância global
gemini_analyzer = GeminiRealAnalyzer()

# Função principal
async def analyze_match_real(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """Análise principal de partida"""
    return await gemini_analyzer.analyze_match_for_betting(match_data) 