-- ===============================================
-- SPORTS DATA API - SCHEMA SQL
-- ===============================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ===============================================
-- TEAMS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL,
    league VARCHAR(50) NOT NULL,
    logo_url TEXT,
    founded_year INTEGER CHECK (founded_year >= 1800 AND founded_year <= 2024),
    stadium VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_team_name_league UNIQUE (name, league)
);

-- Index for faster searches
CREATE INDEX IF NOT EXISTS idx_teams_league ON teams(league);
CREATE INDEX IF NOT EXISTS idx_teams_country ON teams(country);
CREATE INDEX IF NOT EXISTS idx_teams_name_gin ON teams USING gin(name gin_trgm_ops);

-- ===============================================
-- PLAYERS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    age INTEGER CHECK (age >= 16 AND age <= 50),
    position VARCHAR(20) NOT NULL CHECK (position IN ('goalkeeper', 'defender', 'midfielder', 'forward')),
    nationality VARCHAR(50) NOT NULL,
    market_value DECIMAL(12,2) CHECK (market_value >= 0),
    jersey_number INTEGER CHECK (jersey_number >= 1 AND jersey_number <= 99),
    height INTEGER CHECK (height >= 150 AND height <= 220), -- em cm
    weight INTEGER CHECK (weight >= 50 AND weight <= 120),  -- em kg
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_jersey_per_team UNIQUE (team_id, jersey_number)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);
CREATE INDEX IF NOT EXISTS idx_players_nationality ON players(nationality);
CREATE INDEX IF NOT EXISTS idx_players_name_gin ON players USING gin(name gin_trgm_ops);

-- ===============================================
-- MATCHES TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    competition VARCHAR(100) NOT NULL,
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'halftime', 'finished', 'postponed', 'cancelled')),
    home_score INTEGER DEFAULT 0 CHECK (home_score >= 0),
    away_score INTEGER DEFAULT 0 CHECK (away_score >= 0),
    minute INTEGER CHECK (minute >= 0 AND minute <= 120),
    venue VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT different_teams CHECK (home_team_id != away_team_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_live ON matches(status) WHERE status IN ('live', 'halftime');

-- ===============================================
-- LIVE MATCHES TABLE (TEMPO REAL)
-- ===============================================
CREATE TABLE IF NOT EXISTS live_matches (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE, -- Opcional para partidas externas
    external_id VARCHAR(100) UNIQUE NOT NULL, -- ID da fonte externa (sofascore, espn, etc.)
    current_score_home INTEGER NOT NULL DEFAULT 0 CHECK (current_score_home >= 0),
    current_score_away INTEGER NOT NULL DEFAULT 0 CHECK (current_score_away >= 0),
    current_minute INTEGER NOT NULL DEFAULT 0 CHECK (current_minute >= 0 AND current_minute <= 120),
    status VARCHAR(20) NOT NULL CHECK (status IN ('scheduled', 'live', 'halftime', 'finished', 'postponed', 'cancelled')),
    
    -- Informações dos times (para partidas externas)
    home_team_name VARCHAR(100) NOT NULL,
    away_team_name VARCHAR(100) NOT NULL,
    competition VARCHAR(100) NOT NULL,
    venue VARCHAR(200),
    
    -- Fonte dos dados
    source VARCHAR(50) NOT NULL, -- 'sofascore', 'espn', 'football_api', etc.
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Possession stats
    possession_home INTEGER CHECK (possession_home >= 0 AND possession_home <= 100),
    possession_away INTEGER CHECK (possession_away >= 0 AND possession_away <= 100),
    
    -- Shot stats
    shots_home INTEGER CHECK (shots_home >= 0),
    shots_away INTEGER CHECK (shots_away >= 0),
    
    -- Corner stats
    corners_home INTEGER CHECK (corners_home >= 0),
    corners_away INTEGER CHECK (corners_away >= 0),
    
    -- Card stats
    cards_yellow_home INTEGER CHECK (cards_yellow_home >= 0),
    cards_yellow_away INTEGER CHECK (cards_yellow_away >= 0),
    cards_red_home INTEGER CHECK (cards_red_home >= 0),
    cards_red_away INTEGER CHECK (cards_red_away >= 0),
    
    -- Odds
    odds_home DECIMAL(5,2) CHECK (odds_home > 0),
    odds_draw DECIMAL(5,2) CHECK (odds_draw > 0),
    odds_away DECIMAL(5,2) CHECK (odds_away > 0),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT possession_total CHECK (
        (possession_home IS NULL AND possession_away IS NULL) OR
        (possession_home + possession_away = 100)
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_live_matches_match_id ON live_matches(match_id);
CREATE INDEX IF NOT EXISTS idx_live_matches_external_id ON live_matches(external_id);
CREATE INDEX IF NOT EXISTS idx_live_matches_status ON live_matches(status);
CREATE INDEX IF NOT EXISTS idx_live_matches_updated_at ON live_matches(updated_at);
CREATE INDEX IF NOT EXISTS idx_live_matches_last_updated ON live_matches(last_updated);
CREATE INDEX IF NOT EXISTS idx_live_matches_source ON live_matches(source);
CREATE INDEX IF NOT EXISTS idx_live_matches_competition ON live_matches(competition);
CREATE INDEX IF NOT EXISTS idx_live_matches_teams ON live_matches(home_team_name, away_team_name);

-- ===============================================
-- MATCH STATS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS match_stats (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    
    -- Possession and passing
    possession INTEGER CHECK (possession >= 0 AND possession <= 100),
    passes_total INTEGER CHECK (passes_total >= 0),
    passes_accurate INTEGER CHECK (passes_accurate >= 0),
    pass_accuracy DECIMAL(5,2) CHECK (pass_accuracy >= 0 AND pass_accuracy <= 100),
    
    -- Shooting
    shots_total INTEGER CHECK (shots_total >= 0),
    shots_on_target INTEGER CHECK (shots_on_target >= 0),
    
    -- Other stats
    corners INTEGER CHECK (corners >= 0),
    fouls INTEGER CHECK (fouls >= 0),
    yellow_cards INTEGER CHECK (yellow_cards >= 0),
    red_cards INTEGER CHECK (red_cards >= 0),
    offsides INTEGER CHECK (offsides >= 0),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_match_team_stats UNIQUE (match_id, team_id),
    CONSTRAINT accurate_passes_check CHECK (passes_accurate <= passes_total),
    CONSTRAINT shots_on_target_check CHECK (shots_on_target <= shots_total)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_match_stats_match_id ON match_stats(match_id);
CREATE INDEX IF NOT EXISTS idx_match_stats_team_id ON match_stats(team_id);

-- ===============================================
-- PLAYER STATS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    match_id INTEGER REFERENCES matches(id) ON DELETE CASCADE, -- NULL para stats da temporada
    season VARCHAR(10) NOT NULL, -- ex: "2023/24"
    
    -- Basic stats
    goals INTEGER DEFAULT 0 CHECK (goals >= 0),
    assists INTEGER DEFAULT 0 CHECK (assists >= 0),
    minutes_played INTEGER DEFAULT 0 CHECK (minutes_played >= 0),
    yellow_cards INTEGER DEFAULT 0 CHECK (yellow_cards >= 0),
    red_cards INTEGER DEFAULT 0 CHECK (red_cards >= 0),
    
    -- Performance
    rating DECIMAL(3,1) CHECK (rating >= 0 AND rating <= 10),
    
    -- Passing
    passes_total INTEGER CHECK (passes_total >= 0),
    passes_accurate INTEGER CHECK (passes_accurate >= 0),
    
    -- Shooting
    shots_total INTEGER CHECK (shots_total >= 0),
    shots_on_target INTEGER CHECK (shots_on_target >= 0),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_player_match_stats UNIQUE (player_id, match_id),
    CONSTRAINT accurate_passes_check_player CHECK (passes_accurate <= passes_total),
    CONSTRAINT shots_on_target_check_player CHECK (shots_on_target <= shots_total)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_player_stats_player_id ON player_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_match_id ON player_stats(match_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_season ON player_stats(season);

-- ===============================================
-- GEMINI ANALYSES TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS gemini_analyses (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL CHECK (analysis_type IN (
        'match_prediction', 'team_form', 'player_performance', 
        'betting_trends', 'injury_impact'
    )),
    entity_id INTEGER NOT NULL,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('match', 'team', 'player')),
    prompt_used TEXT NOT NULL,
    analysis_result TEXT NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    key_insights JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gemini_analyses_type ON gemini_analyses(analysis_type);
CREATE INDEX IF NOT EXISTS idx_gemini_analyses_entity ON gemini_analyses(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_gemini_analyses_created_at ON gemini_analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_gemini_analyses_insights ON gemini_analyses USING gin(key_insights);

-- ===============================================
-- SCRAPING JOBS TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    items_processed INTEGER DEFAULT 0,
    items_total INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_type ON scraping_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_created_at ON scraping_jobs(created_at);

-- ===============================================
-- FUNCTIONS AND TRIGGERS
-- ===============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_live_matches_updated_at BEFORE UPDATE ON live_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_player_stats_updated_at BEFORE UPDATE ON player_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- VIEWS FOR COMMON QUERIES
-- ===============================================

-- View para partidas com informações dos times
CREATE OR REPLACE VIEW v_matches_with_teams AS
SELECT 
    m.*,
    ht.name as home_team_name,
    ht.logo_url as home_team_logo,
    ht.country as home_team_country,
    at.name as away_team_name,
    at.logo_url as away_team_logo,
    at.country as away_team_country
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id;

-- View para jogadores com informações do time
CREATE OR REPLACE VIEW v_players_with_teams AS
SELECT 
    p.*,
    t.name as team_name,
    t.league as team_league,
    t.country as team_country
FROM players p
JOIN teams t ON p.team_id = t.id;

-- View para estatísticas completas dos jogadores
CREATE OR REPLACE VIEW v_player_season_stats AS
SELECT 
    p.id as player_id,
    p.name as player_name,
    p.position,
    t.name as team_name,
    ps.season,
    SUM(ps.goals) as total_goals,
    SUM(ps.assists) as total_assists,
    SUM(ps.minutes_played) as total_minutes,
    SUM(ps.yellow_cards) as total_yellow_cards,
    SUM(ps.red_cards) as total_red_cards,
    AVG(ps.rating) as avg_rating,
    COUNT(ps.match_id) as matches_played
FROM players p
JOIN teams t ON p.team_id = t.id
LEFT JOIN player_stats ps ON p.id = ps.player_id AND ps.match_id IS NOT NULL
GROUP BY p.id, p.name, p.position, t.name, ps.season;

-- ===============================================
-- SAMPLE DATA (OPCIONAL - PARA TESTES)
-- ===============================================

-- Inserir algumas ligas e times para teste (apenas se não existirem)
INSERT INTO teams (name, country, league, founded_year) VALUES
    ('Flamengo', 'Brazil', 'brasileirao', 1895),
    ('Palmeiras', 'Brazil', 'brasileirao', 1914),
    ('São Paulo', 'Brazil', 'brasileirao', 1930),
    ('Manchester City', 'England', 'premier-league', 1880),
    ('Liverpool', 'England', 'premier-league', 1892),
    ('Real Madrid', 'Spain', 'la-liga', 1902),
    ('Barcelona', 'Spain', 'la-liga', 1899)
ON CONFLICT (name, league) DO NOTHING;

-- Commit das alterações
COMMIT; 