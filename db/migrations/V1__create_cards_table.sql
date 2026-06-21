-- Central card catalog: one row per unique card variant in the hobby.
-- "Card variant" means year + set + card number + parallel + auto/relic flags.
-- Personal ownership is tracked separately in the inventory table.

CREATE TABLE cards (
    card_id          SERIAL PRIMARY KEY,

    -- Identification
    sport            VARCHAR(50)  NOT NULL   -- 'baseball', 'basketball', 'football', 'hockey', etc.
                         CHECK (sport IN ('baseball', 'basketball', 'football', 'hockey', 'soccer', 'tennis', 'golf', 'other')),
    year             SMALLINT     NOT NULL,
    manufacturer     VARCHAR(100) NOT NULL,   -- 'Topps', 'Panini', 'Upper Deck', 'Bowman', etc.
    set_name         VARCHAR(200) NOT NULL,   -- 'Chrome', 'Prizm', 'Bowman Draft', '2023 Series 1', etc.
    card_number      VARCHAR(50),             -- as printed on card; NULL for unnumbered subsets
    player_name      VARCHAR(200) NOT NULL,
    team             VARCHAR(100),

    -- Card type / variant attributes
    -- is_base is the default; set other flags to true for inserts/parallels/autos/relics
    -- Flags can combine: e.g. a Gold Refractor Auto Relic has is_auto=true, is_relic=true, parallel_name='Gold Refractor'
    is_base          BOOLEAN NOT NULL DEFAULT TRUE,
    insert_name      VARCHAR(200),            -- name of insert subset if this is an insert, e.g. 'Future Stars'
    parallel_name    VARCHAR(200),            -- parallel color/finish name, e.g. 'Gold Prizm', 'Refractor'
    is_auto          BOOLEAN NOT NULL DEFAULT FALSE,  -- autograph
    is_relic         BOOLEAN NOT NULL DEFAULT FALSE,  -- memorabilia (jersey/bat/etc.)
    is_patch         BOOLEAN NOT NULL DEFAULT FALSE,  -- patch-level relic (subset of relic)
    is_rookie        BOOLEAN NOT NULL DEFAULT FALSE,  -- first-year card (RC designation)

    -- Print run / numbering
    is_numbered      BOOLEAN NOT NULL DEFAULT FALSE,
    print_run        INTEGER CHECK (print_run > 0),   -- e.g. 25 for /25 cards

    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prevent exact duplicate card variants.
-- COALESCE handles NULLs since NULL != NULL in unique constraints.
CREATE UNIQUE INDEX cards_unique_variant
    ON cards (year, manufacturer, set_name,
              COALESCE(card_number, ''),
              COALESCE(insert_name, ''),
              COALESCE(parallel_name, ''),
              is_auto, is_relic);

CREATE INDEX cards_player_name_idx ON cards (player_name);
CREATE INDEX cards_year_set_idx    ON cards (year, manufacturer, set_name);
