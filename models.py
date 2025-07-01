from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MatchStatus(str, Enum):
    """Status das partidas"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class PlayerPosition(str, Enum):
    """Posições dos jogadores"""
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"


# === TEAMS ===
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=50)
    league: str = Field(..., min_length=1, max_length=50)
    logo_url: Optional[str] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2024)
    stadium: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class Team(TeamBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === PLAYERS ===
class PlayerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=16, le=50)
    position: PlayerPosition
    nationality: str = Field(..., min_length=2, max_length=50)
    market_value: Optional[float] = Field(None, ge=0)
    jersey_number: Optional[int] = Field(None, ge=1, le=99)
    height: Optional[int] = Field(None, ge=150, le=220)  # cm
    weight: Optional[int] = Field(None, ge=50, le=120)   # kg


class PlayerCreate(PlayerBase):
    team_id: int


class Player(PlayerBase):
    id: int
    team_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === MATCHES ===
class MatchBase(BaseModel):
    home_team_id: int
    away_team_id: int
    competition: str = Field(..., min_length=1, max_length=100)
    match_date: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: Optional[int] = Field(None, ge=0)
    away_score: Optional[int] = Field(None, ge=0)
    minute: Optional[int] = Field(None, ge=0, le=120)
    venue: Optional[str] = None


class MatchCreate(MatchBase):
    pass


class Match(MatchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === LIVE MATCHES ===
class LiveMatchBase(BaseModel):
    match_id: int
    current_score_home: int = Field(..., ge=0)
    current_score_away: int = Field(..., ge=0)
    current_minute: int = Field(..., ge=0, le=120)
    status: MatchStatus
    possession_home: Optional[int] = Field(None, ge=0, le=100)
    possession_away: Optional[int] = Field(None, ge=0, le=100)
    shots_home: Optional[int] = Field(None, ge=0)
    shots_away: Optional[int] = Field(None, ge=0)
    corners_home: Optional[int] = Field(None, ge=0)
    corners_away: Optional[int] = Field(None, ge=0)
    cards_yellow_home: Optional[int] = Field(None, ge=0)
    cards_yellow_away: Optional[int] = Field(None, ge=0)
    cards_red_home: Optional[int] = Field(None, ge=0)
    cards_red_away: Optional[int] = Field(None, ge=0)
    odds_home: Optional[float] = Field(None, gt=0)
    odds_draw: Optional[float] = Field(None, gt=0)
    odds_away: Optional[float] = Field(None, gt=0)


class LiveMatchCreate(LiveMatchBase):
    pass


class LiveMatch(LiveMatchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === MATCH STATS ===
class MatchStatsBase(BaseModel):
    match_id: int
    team_id: int
    possession: Optional[int] = Field(None, ge=0, le=100)
    shots_total: Optional[int] = Field(None, ge=0)
    shots_on_target: Optional[int] = Field(None, ge=0)
    corners: Optional[int] = Field(None, ge=0)
    fouls: Optional[int] = Field(None, ge=0)
    yellow_cards: Optional[int] = Field(None, ge=0)
    red_cards: Optional[int] = Field(None, ge=0)
    offsides: Optional[int] = Field(None, ge=0)
    passes_total: Optional[int] = Field(None, ge=0)
    passes_accurate: Optional[int] = Field(None, ge=0)
    pass_accuracy: Optional[float] = Field(None, ge=0, le=100)


class MatchStatsCreate(MatchStatsBase):
    pass


class MatchStats(MatchStatsBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# === PLAYER STATS ===
class PlayerStatsBase(BaseModel):
    player_id: int
    match_id: Optional[int] = None  # None para stats da temporada
    season: str = Field(..., min_length=4, max_length=10)  # ex: "2023/24"
    goals: Optional[int] = Field(None, ge=0)
    assists: Optional[int] = Field(None, ge=0)
    minutes_played: Optional[int] = Field(None, ge=0)
    yellow_cards: Optional[int] = Field(None, ge=0)
    red_cards: Optional[int] = Field(None, ge=0)
    rating: Optional[float] = Field(None, ge=0, le=10)
    passes_total: Optional[int] = Field(None, ge=0)
    passes_accurate: Optional[int] = Field(None, ge=0)
    shots_total: Optional[int] = Field(None, ge=0)
    shots_on_target: Optional[int] = Field(None, ge=0)


class PlayerStatsCreate(PlayerStatsBase):
    pass


class PlayerStats(PlayerStatsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === GEMINI ANALYSIS ===
class GeminiAnalysisType(str, Enum):
    """Tipos de análise do Gemini"""
    MATCH_PREDICTION = "match_prediction"
    TEAM_FORM = "team_form"
    PLAYER_PERFORMANCE = "player_performance"
    BETTING_TRENDS = "betting_trends"
    INJURY_IMPACT = "injury_impact"


class GeminiAnalysisBase(BaseModel):
    analysis_type: GeminiAnalysisType
    entity_id: int  # ID da entidade analisada (match, team, player)
    entity_type: str = Field(..., min_length=1, max_length=20)  # "match", "team", "player"
    prompt_used: str = Field(..., min_length=10)
    analysis_result: str = Field(..., min_length=10)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    key_insights: Optional[List[str]] = []
    recommendations: Optional[List[str]] = []


class GeminiAnalysisCreate(GeminiAnalysisBase):
    pass


class GeminiAnalysis(GeminiAnalysisBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# === API RESPONSES ===
class APIResponse(BaseModel):
    """Resposta padrão da API"""
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel):
    """Resposta paginada"""
    items: List[Any]
    total: int
    page: int = 1
    per_page: int = 10
    pages: int

    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        per_page = values.get('per_page', 10)
        return (total + per_page - 1) // per_page


# === SCRAPER RESPONSES ===
class ScrapingJobStatus(str, Enum):
    """Status dos jobs de scraping"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapingJob(BaseModel):
    """Job de scraping"""
    id: str
    job_type: str  # "live_matches", "team_stats", "player_stats"
    status: ScrapingJobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    items_processed: int = 0
    items_total: Optional[int] = None

    class Config:
        from_attributes = True


# === ANALYTICS REQUESTS ===
class AnalyticsRequest(BaseModel):
    """Request para análise do Gemini"""
    analysis_type: GeminiAnalysisType
    entity_id: int
    entity_type: str = Field(..., pattern="^(match|team|player)$")
    custom_prompt: Optional[str] = None
    include_recent_data: bool = True


class MatchPredictionRequest(BaseModel):
    """Request específico para previsão de partida"""
    match_id: int
    include_team_form: bool = True
    include_head_to_head: bool = True
    include_player_conditions: bool = True
    analysis_depth: str = Field("standard", pattern="^(basic|standard|detailed)$") 