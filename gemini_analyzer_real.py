"""
🤖 GEMINI AI ANALYZER ROBUSTO - ANÁLISES REAIS DE APOSTAS
Sistema avançado de análise de partidas usando IA para sinais de apostas
"""
import asyncio
import google.generativeai as genai
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging
import json
from config import settings

logger = logging.getLogger(__name__)

class GeminiRealAnalyzer:
    """Analisador robusto usando Gemini AI para dados reais"""
    
    def __init__(self):
        self.model = None
        self.prompts_cache = {}
        self.analysis_cache = {}
        self.setup_ai()
    
    def setup_ai(self):
        """Configura o modelo Gemini AI"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            
            # Configuração do modelo para análises de apostas
            generation_config = {
                "temperature": 0.3,  # Mais conservador para análises
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            logger.info("🤖 Gemini AI configurado com sucesso para análises REAIS")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar Gemini AI: {e}")
            raise
    
    async def analyze_match_for_betting(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 ANÁLISE COMPLETA DE PARTIDA PARA APOSTAS"""
        try:
            if not match_data or not match_data.get('is_live'):
                logger.warning("⚠️ Partida não está ao vivo ou dados insuficientes")
                return self._empty_analysis()
            
            logger.info(f"🔍 Analisando partida: {match_data.get('home_team')} vs {match_data.get('away_team')}")
            
            # Análises paralelas para diferentes tipos de apostas
            results = await asyncio.gather(
                self._analyze_corners(match_data),
                self._analyze_cards(match_data),
                self._analyze_both_teams_score(match_data),
                return_exceptions=True
            )
            
            corners_analysis = results[0] if not isinstance(results[0], Exception) else self._empty_signal()
            cards_analysis = results[1] if not isinstance(results[1], Exception) else self._empty_signal()
            btts_analysis = results[2] if not isinstance(results[2], Exception) else self._empty_signal()
            
            # Análise consolidada
            consolidated = {
                'match_id': match_data.get('match_id', 'unknown'),
                'home_team': match_data.get('home_team', 'Unknown'),
                'away_team': match_data.get('away_team', 'Unknown'),
                'minute': match_data.get('minute', 0),
                'competition': match_data.get('competition', 'Unknown'),
                'current_score': f"{match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}",
                'analysis_timestamp': datetime.now(tz=timezone.utc).isoformat(),
                'corners_signal': corners_analysis,
                'cards_signal': cards_analysis,
                'both_teams_score_signal': btts_analysis,
                'source': 'gemini_real_ai'
            }
            
            # Calcular confiança geral
            confidences = [
                corners_analysis.get('confidence', 0),
                cards_analysis.get('confidence', 0),
                btts_analysis.get('confidence', 0)
            ]
            
            consolidated['overall_confidence'] = round(sum(confidences) / len(confidences), 1)
            consolidated['signals_count'] = sum(1 for c in confidences if c >= 7)
            
            logger.info(f"✅ Análise concluída - Confiança geral: {consolidated['overall_confidence']}/10")
            
            return consolidated
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na análise da partida: {e}")
            return self._empty_analysis()
    
    async def _analyze_corners(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🚩 ANÁLISE DE ESCANTEIOS - Dados reais"""
        try:
            prompt = self._build_corners_prompt(match_data)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if not response:
                return self._empty_signal()
            
            analysis = self._parse_corners_response(response, match_data)
            logger.info(f"🚩 Escanteios analisados - Confiança: {analysis.get('confidence', 0)}/10")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de escanteios: {e}")
            return self._empty_signal()
    
    async def _analyze_cards(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """🟨 ANÁLISE DE CARTÕES - Dados reais"""
        try:
            prompt = self._build_cards_prompt(match_data)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if not response:
                return self._empty_signal()
            
            analysis = self._parse_cards_response(response, match_data)
            logger.info(f"🟨 Cartões analisados - Confiança: {analysis.get('confidence', 0)}/10")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de cartões: {e}")
            return self._empty_signal()
    
    async def _analyze_both_teams_score(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """⚽ ANÁLISE AMBAS MARCAM - Dados reais"""
        try:
            prompt = self._build_btts_prompt(match_data)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_ai_response, prompt
            )
            
            if not response:
                return self._empty_signal()
            
            analysis = self._parse_btts_response(response, match_data)
            logger.info(f"⚽ Ambas marcam analisado - Confiança: {analysis.get('confidence', 0)}/10")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de ambas marcam: {e}")
            return self._empty_signal()
    
    def _build_corners_prompt(self, match_data: Dict[str, Any]) -> str:
        """Constrói prompt especializado para análise de escanteios"""
        return f\"\"\"
🚩 ANÁLISE ESPECIALIZADA: ESCANTEIOS - DADOS REAIS

CONTEXTO DA PARTIDA:
• {match_data.get('home_team')} vs {match_data.get('away_team')}
• Placar atual: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}
• Minuto: {match_data.get('minute', 0)}'
• Competição: {match_data.get('competition', 'N/A')}
• País: {match_data.get('country', 'N/A')}

ESTATÍSTICAS ATUAIS (DADOS REAIS):
• Escanteios: Casa {match_data.get('home_corners', 0)} - {match_data.get('away_corners', 0)} Fora
• Finalizações: Casa {match_data.get('home_shots', 0)} - {match_data.get('away_shots', 0)} Fora
• Finalizações no alvo: Casa {match_data.get('home_shots_on_target', 0)} - {match_data.get('away_shots_on_target', 0)} Fora
• Posse de bola: Casa {match_data.get('home_possession', 0)}% - {match_data.get('away_possession', 0)}% Fora

MISSÃO: Como especialista em apostas esportivas, analise os DADOS REAIS e determine se há uma oportunidade de aposta em ESCANTEIOS.

FOQUE EM:
1. Tendência atual de escanteios (ritmo por minuto)
2. Pressão ofensiva de cada time
3. Padrão de finalizações vs escanteios
4. Tempo restante e contexto do jogo

RESPONDA EM JSON:
{{
    \"tipo\": \"escanteios\",
    \"recomendacao\": \"over_8.5\" ou \"over_9.5\" ou \"under_7.5\" ou \"nenhuma\",
    \"confidence\": [1-10],
    \"reasoning\": \"Explicação detalhada baseada nos dados reais\",
    \"key_factors\": [\"fator1\", \"fator2\", \"fator3\"],
    \"market_value\": \"Valor estimado da odd\",
    \"risk_level\": \"baixo\", \"medio\" ou \"alto\"
}}

IMPORTANTE: Só recomende apostas com confiança >= 7. Base sua análise EXCLUSIVAMENTE nos dados reais fornecidos.
\"\"\"
    
    def _build_cards_prompt(self, match_data: Dict[str, Any]) -> str:
        """Constrói prompt especializado para análise de cartões"""
        return f\"\"\"
🟨 ANÁLISE ESPECIALIZADA: CARTÕES - DADOS REAIS

CONTEXTO DA PARTIDA:
• {match_data.get('home_team')} vs {match_data.get('away_team')}
• Placar atual: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}
• Minuto: {match_data.get('minute', 0)}'
• Competição: {match_data.get('competition', 'N/A')}

ESTATÍSTICAS ATUAIS (DADOS REAIS):
• Cartões amarelos: Casa {match_data.get('home_yellow_cards', 0)} - {match_data.get('away_yellow_cards', 0)} Fora
• Cartões vermelhos: Casa {match_data.get('home_red_cards', 0)} - {match_data.get('away_red_cards', 0)} Fora
• Total de cartões: {match_data.get('home_yellow_cards', 0) + match_data.get('away_yellow_cards', 0) + match_data.get('home_red_cards', 0) + match_data.get('away_red_cards', 0)}

CONTEXTO ADICIONAL:
• Posse de bola: Casa {match_data.get('home_possession', 0)}% - {match_data.get('away_possession', 0)}% Fora
• Pressão no jogo (baseada em finalizações): {match_data.get('home_shots', 0) + match_data.get('away_shots', 0)} total

MISSÃO: Analise a tendência de CARTÕES baseada nos dados reais da partida.

CONSIDERE:
1. Ritmo atual de cartões por minuto
2. Contexto do jogo (resultado, importância)
3. Tempo restante e possível intensificação
4. Padrão histórico da competição

RESPONDA EM JSON:
{{
    \"tipo\": \"cartoes\",
    \"recomendacao\": \"over_3.5\" ou \"over_4.5\" ou \"under_2.5\" ou \"nenhuma\",
    \"confidence\": [1-10],
    \"reasoning\": \"Análise baseada nos dados reais\",
    \"key_factors\": [\"fator1\", \"fator2\"],
    \"current_cards\": {match_data.get('home_yellow_cards', 0) + match_data.get('away_yellow_cards', 0) + match_data.get('home_red_cards', 0) + match_data.get('away_red_cards', 0)},
    \"risk_level\": \"baixo\", \"medio\" ou \"alto\"
}}

IMPORTANTE: Só recomende com confiança >= 7. Use APENAS os dados reais fornecidos.
\"\"\"
    
    def _build_btts_prompt(self, match_data: Dict[str, Any]) -> str:
        """Constrói prompt especializado para análise de ambas marcam"""
        return f\"\"\"
⚽ ANÁLISE ESPECIALIZADA: AMBAS AS EQUIPES MARCAM (BTTS) - DADOS REAIS

CONTEXTO DA PARTIDA:
• {match_data.get('home_team')} vs {match_data.get('away_team')}
• Placar atual: {match_data.get('home_score', 0)} - {match_data.get('away_score', 0)}
• Minuto: {match_data.get('minute', 0)}'
• Competição: {match_data.get('competition', 'N/A')}

ESTATÍSTICAS OFENSIVAS (DADOS REAIS):
• Finalizações: Casa {match_data.get('home_shots', 0)} - {match_data.get('away_shots', 0)} Fora
• No alvo: Casa {match_data.get('home_shots_on_target', 0)} - {match_data.get('away_shots_on_target', 0)} Fora
• Escanteios: Casa {match_data.get('home_corners', 0)} - {match_data.get('away_corners', 0)} Fora
• Posse: Casa {match_data.get('home_possession', 0)}% - {match_data.get('away_possession', 0)}% Fora

SITUAÇÃO ATUAL:
• Tempo restante: ~{90 - match_data.get('minute', 0)} minutos
• Ambos já marcaram: {\"SIM\" if match_data.get('home_score', 0) > 0 and match_data.get('away_score', 0) > 0 else \"NÃO\"}
• Pressão ofensiva total: {match_data.get('home_shots_on_target', 0) + match_data.get('away_shots_on_target', 0)} finalizações no alvo

MISSÃO: Determine se AMBAS AS EQUIPES VÃO MARCAR baseado nos dados reais.

ANALISE:
1. Capacidade ofensiva de cada time (dados reais)
2. Tempo restante vs necessidade de gols
3. Padrão de criação de chances
4. Contexto do resultado atual

RESPONDA EM JSON:
{{
    \"tipo\": \"ambas_marcam\",
    \"recomendacao\": \"sim\" ou \"nao\" ou \"nenhuma\",
    \"confidence\": [1-10],
    \"reasoning\": \"Análise detalhada baseada nos dados reais\",
    \"home_goal_probability\": [0-100],
    \"away_goal_probability\": [0-100],
    \"key_factors\": [\"fator1\", \"fator2\"],
    \"risk_level\": \"baixo\", \"medio\" ou \"alto\"
}}

IMPORTANTE: Confiança >= 7 para recomendação. Use EXCLUSIVAMENTE dados reais fornecidos.
\"\"\"
    
    def _generate_ai_response(self, prompt: str) -> Optional[str]:
        """Gera resposta da IA de forma síncrona"""
        try:
            if not self.model:
                logger.error("❌ Modelo Gemini não configurado")
                return None
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("⚠️ Resposta vazia da IA")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resposta da IA: {e}")
            return None
    
    def _parse_corners_response(self, response: str, match_data: Dict) -> Dict[str, Any]:
        """Parseia resposta da IA para escanteios"""
        try:
            # Tentar extrair JSON da resposta
            json_match = self._extract_json_from_response(response)
            if json_match:
                analysis = json.loads(json_match)
                
                # Validar e sanitizar
                return {
                    'tipo': 'escanteios',
                    'recomendacao': analysis.get('recomendacao', 'nenhuma'),
                    'confidence': min(10, max(1, int(analysis.get('confidence', 1)))),
                    'reasoning': analysis.get('reasoning', 'Análise não disponível'),
                    'key_factors': analysis.get('key_factors', []),
                    'market_value': analysis.get('market_value', 'N/A'),
                    'risk_level': analysis.get('risk_level', 'alto'),
                    'current_corners': match_data.get('home_corners', 0) + match_data.get('away_corners', 0),
                    'minute': match_data.get('minute', 0)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao parsear resposta de escanteios: {e}")
        
        return self._empty_signal()
    
    def _parse_cards_response(self, response: str, match_data: Dict) -> Dict[str, Any]:
        """Parseia resposta da IA para cartões"""
        try:
            json_match = self._extract_json_from_response(response)
            if json_match:
                analysis = json.loads(json_match)
                
                return {
                    'tipo': 'cartoes',
                    'recomendacao': analysis.get('recomendacao', 'nenhuma'),
                    'confidence': min(10, max(1, int(analysis.get('confidence', 1)))),
                    'reasoning': analysis.get('reasoning', 'Análise não disponível'),
                    'key_factors': analysis.get('key_factors', []),
                    'current_cards': analysis.get('current_cards', 0),
                    'risk_level': analysis.get('risk_level', 'alto'),
                    'minute': match_data.get('minute', 0)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao parsear resposta de cartões: {e}")
        
        return self._empty_signal()
    
    def _parse_btts_response(self, response: str, match_data: Dict) -> Dict[str, Any]:
        """Parseia resposta da IA para ambas marcam"""
        try:
            json_match = self._extract_json_from_response(response)
            if json_match:
                analysis = json.loads(json_match)
                
                return {
                    'tipo': 'ambas_marcam',
                    'recomendacao': analysis.get('recomendacao', 'nenhuma'),
                    'confidence': min(10, max(1, int(analysis.get('confidence', 1)))),
                    'reasoning': analysis.get('reasoning', 'Análise não disponível'),
                    'home_goal_probability': analysis.get('home_goal_probability', 0),
                    'away_goal_probability': analysis.get('away_goal_probability', 0),
                    'key_factors': analysis.get('key_factors', []),
                    'risk_level': analysis.get('risk_level', 'alto'),
                    'current_score': f\"{match_data.get('home_score', 0)}-{match_data.get('away_score', 0)}\",
                    'minute': match_data.get('minute', 0)
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao parsear resposta de ambas marcam: {e}")
        
        return self._empty_signal()
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extrai JSON da resposta da IA"""
        try:
            # Procurar por blocos JSON
            import re
            
            # Padrões para encontrar JSON
            patterns = [
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{[^{}]*\"confidence\"[^{}]*\})',
                r'(\{.*?\})'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    # Tentar validar JSON
                    try:
                        json.loads(match)
                        return match
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair JSON: {e}")
            return None
    
    def _empty_signal(self) -> Dict[str, Any]:
        """Retorna sinal vazio"""
        return {
            'tipo': 'unknown',
            'recomendacao': 'nenhuma',
            'confidence': 1,
            'reasoning': 'Dados insuficientes para análise',
            'key_factors': [],
            'risk_level': 'alto'
        }
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Retorna análise vazia"""
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

# 🚀 INSTÂNCIA GLOBAL DO ANALISADOR
gemini_analyzer = GeminiRealAnalyzer()

# 🎯 FUNÇÃO PRINCIPAL PARA ANÁLISE
async def analyze_match_real(match_data: Dict[str, Any]) -> Dict[str, Any]:
    """Função principal para análise de partida com dados reais"""
    try:
        return await gemini_analyzer.analyze_match_for_betting(match_data)
    except Exception as e:
        logger.error(f"❌ Erro na análise da partida: {e}")
        return gemini_analyzer._empty_analysis()

# Para execução direta
if __name__ == "__main__":
    async def test_analyzer():
        print("🤖 TESTANDO ANALISADOR GEMINI REAL")
        print("=" * 50)
        
        # Dados de teste realistas
        test_match = {
            'match_id': 'test_123',
            'home_team': 'Manchester City',
            'away_team': 'Liverpool',
            'home_score': 1,
            'away_score': 0,
            'minute': 65,
            'is_live': True,
            'competition': 'Premier League',
            'home_corners': 6,
            'away_corners': 3,
            'home_shots': 12,
            'away_shots': 8,
            'home_shots_on_target': 4,
            'away_shots_on_target': 2,
            'home_possession': 58,
            'away_possession': 42,
            'home_yellow_cards': 2,
            'away_yellow_cards': 1,
            'home_red_cards': 0,
            'away_red_cards': 0
        }
        
        analysis = await analyze_match_real(test_match)
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    asyncio.run(test_analyzer()) 