-- V12: Add players master table
-- Purpose: Normalize player data to enable PowerBI filtering/grouping by position, draft year, era, etc.

CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    player_name VARCHAR(200) NOT NULL,
    sport VARCHAR(50) NOT NULL,
    position VARCHAR(100),
    team VARCHAR(100),
    draft_year SMALLINT,
    is_hall_of_fame BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Unique constraint on player name per sport (one LeBron in basketball, could have another LeBron in baseball, etc.)
CREATE UNIQUE INDEX players_name_sport_idx ON players(player_name, sport) WHERE deleted_at IS NULL;

CREATE INDEX players_sport_position_idx ON players(sport, position) WHERE deleted_at IS NULL;
CREATE INDEX players_draft_year_idx ON players(draft_year) WHERE deleted_at IS NULL;
CREATE INDEX players_hof_idx ON players(is_hall_of_fame) WHERE is_hall_of_fame = TRUE AND deleted_at IS NULL;

-- Add foreign key to cards table (optional - allows enforcing data integrity if players table is maintained)
-- ALTER TABLE cards ADD COLUMN player_id INTEGER REFERENCES players(player_id);
-- For now, cards.player_name remains denormalized for flexibility

COMMENT ON TABLE players IS 'Master player reference table for normalization; supports PowerBI grouping by position, draft era, HOF status, etc.';
COMMENT ON COLUMN players.is_hall_of_fame IS 'Flag for filtering HOF members in PowerBI dashboards';
