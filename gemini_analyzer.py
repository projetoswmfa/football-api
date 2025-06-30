import google.generativeai as genai
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from loguru import logger
from config import settings
from database import analysis_repo, match_repo, team_repo, player_repo, live_match_repo
from models import GeminiAnalysisType


class GeminiAnalyzer:
    """Analisador de dados esportivos usando Gemini AI"""
    
    def __init__(self):
        # Configurar Gemini
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Configurações do modelo
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 2048,
        }
        
        self.safety_settings = [
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
    
    async def analyze_match_prediction(self, match_id: int, 
                                     include_detailed_stats: bool = True) -> Dict[str, Any]:
        """Análise de previsão de partida"""
        try:
            # Buscar dados da partida
            match_data = await self._get_match_context(match_id, include_detailed_stats)
            if not match_data:
                raise ValueError(f"Partida {match_id} não encontrada")
            
            # Gerar prompt contextual
            prompt = self._build_match_prediction_prompt(match_data)
            
            # Gerar análise
            response = await self._generate_analysis(prompt)
            
            # Processar e estruturar resposta
            analysis_result = self._parse_match_analysis(response)
            
            # Salvar no banco
            analysis_data = {
                'analysis_type': GeminiAnalysisType.MATCH_PREDICTION,
                'entity_id': match_id,
                'entity_type': 'match',
                'prompt_used': prompt[:500] + "..." if len(prompt) > 500 else prompt,
                'analysis_result': analysis_result['full_analysis'],
                'confidence_score': analysis_result.get('confidence_score'),
                'key_insights': analysis_result.get('key_insights', []),
                'recommendations': analysis_result.get('recommendations', [])
            }
            
            saved_analysis = await analysis_repo.create_analysis(analysis_data)
            
            return {
                'analysis_id': saved_analysis['id'],
                'match_id': match_id,
                'prediction': analysis_result,
                'created_at': saved_analysis['created_at']
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de previsão da partida {match_id}: {e}")
            raise
    
    async def analyze_team_form(self, team_id: int, matches_count: int = 10) -> Dict[str, Any]:
        """Análise da forma atual do time"""
        try:
            # Buscar últimas partidas do time
            team_data = await self._get_team_form_context(team_id, matches_count)
            if not team_data:
                raise ValueError(f"Time {team_id} não encontrado")
            
            # Gerar prompt
            prompt = self._build_team_form_prompt(team_data)
            
            # Gerar análise
            response = await self._generate_analysis(prompt)
            
            # Processar resposta
            analysis_result = self._parse_team_analysis(response)
            
            # Salvar no banco
            analysis_data = {
                'analysis_type': GeminiAnalysisType.TEAM_FORM,
                'entity_id': team_id,
                'entity_type': 'team',
                'prompt_used': prompt[:500] + "..." if len(prompt) > 500 else prompt,
                'analysis_result': analysis_result['full_analysis'],
                'confidence_score': analysis_result.get('confidence_score'),
                'key_insights': analysis_result.get('key_insights', []),
                'recommendations': analysis_result.get('recommendations', [])
            }
            
            saved_analysis = await analysis_repo.create_analysis(analysis_data)
            
            return {
                'analysis_id': saved_analysis['id'],
                'team_id': team_id,
                'form_analysis': analysis_result,
                'created_at': saved_analysis['created_at']
            }
            
        except Exception as e:
            logger.error(f"Erro na análise da forma do time {team_id}: {e}")
            raise
    
    async def analyze_betting_trends(self, match_id: int) -> Dict[str, Any]:
        """Análise de tendências para apostas"""
        try:
            # Buscar contexto completo da partida
            match_context = await self._get_betting_context(match_id)
            if not match_context:
                raise ValueError(f"Contexto da partida {match_id} não encontrado")
            
            # Gerar prompt específico para apostas
            prompt = self._build_betting_trends_prompt(match_context)
            
            # Gerar análise
            response = await self._generate_analysis(prompt)
            
            # Processar resposta
            analysis_result = self._parse_betting_analysis(response)
            
            # Salvar no banco
            analysis_data = {
                'analysis_type': GeminiAnalysisType.BETTING_TRENDS,
                'entity_id': match_id,
                'entity_type': 'match',
                'prompt_used': prompt[:500] + "..." if len(prompt) > 500 else prompt,
                'analysis_result': analysis_result['full_analysis'],
                'confidence_score': analysis_result.get('confidence_score'),
                'key_insights': analysis_result.get('key_insights', []),
                'recommendations': analysis_result.get('recommendations', [])
            }
            
            saved_analysis = await analysis_repo.create_analysis(analysis_data)
            
            return {
                'analysis_id': saved_analysis['id'],
                'match_id': match_id,
                'betting_analysis': analysis_result,
                'created_at': saved_analysis['created_at']
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de apostas da partida {match_id}: {e}")
            raise
    
    async def analyze_player_performance(self, player_id: int, season: str = "2023/24") -> Dict[str, Any]:
        """Análise de performance de jogador"""
        try:
            # Buscar dados do jogador
            player_context = await self._get_player_context(player_id, season)
            if not player_context:
                raise ValueError(f"Jogador {player_id} não encontrado")
            
            # Gerar prompt
            prompt = self._build_player_performance_prompt(player_context)
            
            # Gerar análise
            response = await self._generate_analysis(prompt)
            
            # Processar resposta
            analysis_result = self._parse_player_analysis(response)
            
            # Salvar no banco
            analysis_data = {
                'analysis_type': GeminiAnalysisType.PLAYER_PERFORMANCE,
                'entity_id': player_id,
                'entity_type': 'player',
                'prompt_used': prompt[:500] + "..." if len(prompt) > 500 else prompt,
                'analysis_result': analysis_result['full_analysis'],
                'confidence_score': analysis_result.get('confidence_score'),
                'key_insights': analysis_result.get('key_insights', []),
                'recommendations': analysis_result.get('recommendations', [])
            }
            
            saved_analysis = await analysis_repo.create_analysis(analysis_data)
            
            return {
                'analysis_id': saved_analysis['id'],
                'player_id': player_id,
                'performance_analysis': analysis_result,
                'created_at': saved_analysis['created_at']
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de performance do jogador {player_id}: {e}")
            raise
    
    async def _generate_analysis(self, prompt: str) -> str:
        """Gera análise usando Gemini"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.candidates and len(response.candidates) > 0:
                return response.candidates[0].content.parts[0].text
            else:
                raise Exception("Nenhuma resposta válida gerada pelo Gemini")
                
        except Exception as e:
            logger.error(f"Erro ao gerar análise com Gemini: {e}")
            raise
    
    async def _get_match_context(self, match_id: int, include_stats: bool = True) -> Optional[Dict[str, Any]]:
        """Busca contexto completo da partida"""
        try:
            # Dados básicos da partida
            match = await match_repo.execute_one(
                """
                SELECT m.*, 
                       ht.name as home_team_name, ht.country as home_country,
                       at.name as away_team_name, at.country as away_country
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE m.id = $1
                """,
                match_id
            )
            
            if not match:
                return None
            
            context = {
                'match': match,
                'recent_form': {},
                'head_to_head': [],
                'live_data': None
            }
            
            # Dados ao vivo se disponível
            live_data = await live_match_repo.execute_one(
                "SELECT * FROM live_matches WHERE match_id = $1",
                match_id
            )
            if live_data:
                context['live_data'] = live_data
            
            if include_stats:
                # Forma recente dos times
                context['recent_form']['home'] = await self._get_recent_matches(
                    match['home_team_id'], 5
                )
                context['recent_form']['away'] = await self._get_recent_matches(
                    match['away_team_id'], 5
                )
                
                # Histórico de confrontos
                context['head_to_head'] = await self._get_head_to_head(
                    match['home_team_id'], match['away_team_id'], 5
                )
            
            return context
            
        except Exception as e:
            logger.error(f"Erro ao buscar contexto da partida: {e}")
            return None
    
    async def _get_recent_matches(self, team_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca partidas recentes de um time"""
        try:
            return await match_repo.execute_query(
                """
                SELECT m.*, 
                       CASE 
                           WHEN m.home_team_id = $1 THEN 'home'
                           ELSE 'away'
                       END as team_position,
                       CASE 
                           WHEN m.home_team_id = $1 THEN ot.name
                           ELSE ht.name
                       END as opponent_name
                FROM matches m
                LEFT JOIN teams ht ON m.home_team_id = ht.id
                LEFT JOIN teams ot ON m.away_team_id = ot.id
                WHERE (m.home_team_id = $1 OR m.away_team_id = $1)
                  AND m.status = 'finished'
                ORDER BY m.match_date DESC
                LIMIT $2
                """,
                team_id, limit
            )
        except Exception as e:
            logger.error(f"Erro ao buscar partidas recentes: {e}")
            return []
    
    async def _get_head_to_head(self, team1_id: int, team2_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca histórico de confrontos diretos"""
        try:
            return await match_repo.execute_query(
                """
                SELECT m.*, ht.name as home_team_name, at.name as away_team_name
                FROM matches m
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE ((m.home_team_id = $1 AND m.away_team_id = $2) 
                    OR (m.home_team_id = $2 AND m.away_team_id = $1))
                  AND m.status = 'finished'
                ORDER BY m.match_date DESC
                LIMIT $3
                """,
                team1_id, team2_id, limit
            )
        except Exception as e:
            logger.error(f"Erro ao buscar confrontos diretos: {e}")
            return []
    
    def _build_match_prediction_prompt(self, match_data: Dict[str, Any]) -> str:
        """Constrói prompt para previsão de partida"""
        match = match_data['match']
        
        prompt = f"""
Você é um analista esportivo especializado em futebol. Analise os dados abaixo e forneça uma previsão detalhada para a partida:

PARTIDA: {match['home_team_name']} vs {match['away_team_name']}
COMPETIÇÃO: {match['competition']}
DATA: {match['match_date']}

"""
        
        # Adicionar forma recente
        if match_data.get('recent_form'):
            prompt += "\nFORMA RECENTE:\n"
            
            home_form = match_data['recent_form'].get('home', [])
            if home_form:
                prompt += f"{match['home_team_name']} (últimas 5 partidas):\n"
                for i, game in enumerate(home_form):
                    result = self._get_match_result(game, match['home_team_id'])
                    prompt += f"  {i+1}. vs {game['opponent_name']} ({game['team_position']}) - {result}\n"
            
            away_form = match_data['recent_form'].get('away', [])
            if away_form:
                prompt += f"\n{match['away_team_name']} (últimas 5 partidas):\n"
                for i, game in enumerate(away_form):
                    result = self._get_match_result(game, match['away_team_id'])
                    prompt += f"  {i+1}. vs {game['opponent_name']} ({game['team_position']}) - {result}\n"
        
        # Adicionar confrontos diretos
        if match_data.get('head_to_head'):
            prompt += "\nCONFRONTOS DIRETOS (últimos 5):\n"
            for i, h2h in enumerate(match_data['head_to_head']):
                prompt += f"  {i+1}. {h2h['home_team_name']} {h2h['home_score']} x {h2h['away_score']} {h2h['away_team_name']}\n"
        
        # Dados ao vivo se disponível
        if match_data.get('live_data'):
            live = match_data['live_data']
            prompt += f"\nDADOS AO VIVO:\n"
            prompt += f"  Placar atual: {live['current_score_home']} x {live['current_score_away']}\n"
            prompt += f"  Minuto: {live['current_minute']}\n"
            if live.get('possession_home'):
                prompt += f"  Posse de bola: {live['possession_home']}% x {live['possession_away']}%\n"
            if live.get('shots_home'):
                prompt += f"  Finalizações: {live['shots_home']} x {live['shots_away']}\n"
        
        prompt += """

Com base nesses dados, forneça uma análise estruturada no seguinte formato JSON:

{
  "prediction": {
    "winner": "home/away/draw",
    "confidence": 0.0-1.0,
    "predicted_score": "X-Y"
  },
  "key_factors": [
    "Fator 1",
    "Fator 2", 
    "Fator 3"
  ],
  "betting_recommendations": [
    {
      "market": "Resultado Final",
      "recommendation": "Casa/Empate/Fora",
      "confidence": 0.0-1.0
    }
  ],
  "analysis": "Análise detalhada em português explicando o raciocínio da previsão"
}

Seja objetivo e baseie suas previsões nos dados estatísticos apresentados.
"""
        
        return prompt
    
    def _build_betting_trends_prompt(self, match_context: Dict[str, Any]) -> str:
        """Constrói prompt para análise de apostas"""
        match = match_context['match']
        
        prompt = f"""
Você é um especialista em análise de apostas esportivas. Analise os dados da partida e identifique as melhores oportunidades de apostas:

PARTIDA: {match['home_team_name']} vs {match['away_team_name']}
COMPETIÇÃO: {match['competition']}

"""
        
        # Adicionar odds se disponível
        if match_context.get('live_data') and match_context['live_data'].get('odds_home'):
            live = match_context['live_data']
            prompt += f"ODDS ATUAIS:\n"
            prompt += f"  Casa: {live['odds_home']}\n"
            prompt += f"  Empate: {live['odds_draw']}\n" 
            prompt += f"  Fora: {live['odds_away']}\n\n"
        
        # Adicionar contexto da partida
        prompt += self._add_match_context_to_prompt(match_context)
        
        prompt += """

Forneça uma análise de apostas no formato JSON:

{
  "value_bets": [
    {
      "market": "Nome do mercado",
      "recommendation": "Aposta recomendada",
      "odds_needed": 0.00,
      "probability": 0.00,
      "value_rating": 1-5
    }
  ],
  "safe_bets": [
    {
      "market": "Mercado seguro",
      "recommendation": "Aposta",
      "confidence": 0.0-1.0
    }
  ],
  "avoid": [
    "Mercados a evitar"
  ],
  "analysis": "Análise detalhada das tendências de apostas em português"
}

Foque em identificar apostas com valor real baseado em estatísticas.
"""
        
        return prompt
    
    def _get_match_result(self, match: Dict[str, Any], team_id: int) -> str:
        """Determina resultado da partida para um time específico"""
        if match['status'] != 'finished':
            return "Não finalizado"
        
        is_home = match.get('team_position') == 'home'
        
        if is_home:
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
        else:
            home_score = match.get('away_score', 0)
            away_score = match.get('home_score', 0)
        
        if home_score > away_score:
            return f"V {home_score}-{away_score}"
        elif home_score < away_score:
            return f"D {home_score}-{away_score}"
        else:
            return f"E {home_score}-{away_score}"
    
    def _parse_match_analysis(self, response: str) -> Dict[str, Any]:
        """Parse da resposta de análise de partida"""
        try:
            # Tentar extrair JSON da resposta
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                return {
                    'full_analysis': response,
                    'prediction': parsed.get('prediction', {}),
                    'key_insights': parsed.get('key_factors', []),
                    'recommendations': [
                        f"{bet['market']}: {bet['recommendation']}" 
                        for bet in parsed.get('betting_recommendations', [])
                    ],
                    'confidence_score': parsed.get('prediction', {}).get('confidence', 0.5)
                }
            else:
                # Fallback se não conseguir fazer parse do JSON
                return {
                    'full_analysis': response,
                    'prediction': {'analysis': response},
                    'key_insights': [],
                    'recommendations': [],
                    'confidence_score': 0.5
                }
                
        except Exception as e:
            logger.error(f"Erro ao fazer parse da análise: {e}")
            return {
                'full_analysis': response,
                'prediction': {'analysis': response},
                'key_insights': [],
                'recommendations': [],
                'confidence_score': 0.5
            }
    
    def _parse_betting_analysis(self, response: str) -> Dict[str, Any]:
        """Parse da resposta de análise de apostas"""
        # Similar ao _parse_match_analysis mas focado em apostas
        return self._parse_match_analysis(response)
    
    def _parse_team_analysis(self, response: str) -> Dict[str, Any]:
        """Parse da resposta de análise de time"""
        return self._parse_match_analysis(response)
    
    def _parse_player_analysis(self, response: str) -> Dict[str, Any]:
        """Parse da resposta de análise de jogador"""
        return self._parse_match_analysis(response)
    
    def _add_match_context_to_prompt(self, match_context: Dict[str, Any]) -> str:
        """Adiciona contexto da partida ao prompt"""
        context_text = ""
        
        # Adicionar forma recente resumida
        if match_context.get('recent_form'):
            home_form = match_context['recent_form'].get('home', [])
            away_form = match_context['recent_form'].get('away', [])
            
            if home_form:
                wins = sum(1 for m in home_form if self._get_match_result(m, match_context['match']['home_team_id']).startswith('V'))
                context_text += f"Casa: {wins} vitórias em 5 jogos\n"
            
            if away_form:
                wins = sum(1 for m in away_form if self._get_match_result(m, match_context['match']['away_team_id']).startswith('V'))
                context_text += f"Fora: {wins} vitórias em 5 jogos\n"
        
        return context_text


# Instância global do analisador
analyzer = GeminiAnalyzer() 