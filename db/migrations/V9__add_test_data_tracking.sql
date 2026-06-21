-- V9: Add test data tracking
-- Purpose: Mark cards as test data for easy identification and deletion

ALTER TABLE cards ADD COLUMN is_test BOOLEAN DEFAULT FALSE;

-- Index for filtering out test data in queries
CREATE INDEX cards_is_test_idx ON cards(is_test) WHERE is_test = TRUE;

-- Update audit log trigger to capture is_test field
-- (triggers will automatically include the new column in new_values JSONB)

-- Optional: View to identify test cards
CREATE VIEW v_test_cards AS
SELECT 
  card_id,
  sport,
  year,
  manufacturer,
  set_name,
  card_number,
  player_name,
  is_auto,
  is_relic,
  is_patch,
  parallel_name,
  print_run,
  created_at
FROM cards
WHERE is_test = TRUE AND deleted_at IS NULL
ORDER BY created_at DESC;

-- Add helper comment
COMMENT ON COLUMN cards.is_test IS 'When TRUE, card is marked as test data and should be excluded from production queries and reporting';
