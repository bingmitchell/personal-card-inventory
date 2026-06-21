-- V11: Add collection goals and tracking
-- Purpose: Enable users to set goals (e.g., "Complete 2023 Topps Basketball") and track progress with PowerBI dashboards

CREATE TABLE collection_goals (
    goal_id SERIAL PRIMARY KEY,
    goal_name VARCHAR(200) NOT NULL,
    description TEXT,
    sport VARCHAR(50),
    year SMALLINT,
    manufacturer VARCHAR(100),
    set_name VARCHAR(200),
    target_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE goal_items (
    goal_item_id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES collection_goals(goal_id) ON DELETE CASCADE,
    card_id INTEGER NOT NULL REFERENCES cards(card_id),
    acquired_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX collection_goals_is_active_idx ON collection_goals(is_active) WHERE is_active = TRUE AND deleted_at IS NULL;
CREATE INDEX collection_goals_sport_year_idx ON collection_goals(sport, year) WHERE deleted_at IS NULL;
CREATE INDEX goal_items_goal_id_idx ON goal_items(goal_id) WHERE deleted_at IS NULL;
CREATE INDEX goal_items_card_id_idx ON goal_items(card_id) WHERE deleted_at IS NULL;

-- View for goal progress tracking
CREATE VIEW v_goal_progress AS
SELECT 
    cg.goal_id,
    cg.goal_name,
    cg.target_count,
    COUNT(gi.goal_item_id) as items_acquired,
    ROUND(100.0 * COUNT(gi.goal_item_id) / NULLIF(cg.target_count, 0), 1) as percent_complete
FROM collection_goals cg
LEFT JOIN goal_items gi ON cg.goal_id = gi.goal_id AND gi.deleted_at IS NULL
WHERE cg.deleted_at IS NULL AND cg.is_active = TRUE
GROUP BY cg.goal_id, cg.goal_name, cg.target_count;

COMMENT ON TABLE collection_goals IS 'User-defined collecting objectives (e.g., "Complete 2023 Topps Basketball set")';
COMMENT ON TABLE goal_items IS 'Cards acquired toward each goal; many-to-many relationship';
COMMENT ON VIEW v_goal_progress IS 'PowerBI-friendly view showing goal completion % for dashboarding';
