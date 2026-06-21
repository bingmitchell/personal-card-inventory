-- Personal inventory: one row per physical card you own (or have owned).
-- Multiple copies of the same card each get their own inventory row.

CREATE TABLE inventory (
    inventory_id     SERIAL PRIMARY KEY,
    card_id          INTEGER NOT NULL REFERENCES cards (card_id),

    -- Ownership status
    status           VARCHAR(20) NOT NULL DEFAULT 'OWNED'
                         CHECK (status IN ('OWNED', 'SOLD', 'TRADED', 'LOST')),
    acquisition_date DATE,
    location         VARCHAR(200),   -- 'Binder 3', 'PSA submission box', 'Top loader bin', etc.

    -- Grading
    is_graded        BOOLEAN NOT NULL DEFAULT FALSE,
    grading_company  VARCHAR(20)     -- 'PSA', 'BGS', 'SGC', 'CGC', 'CSG'
                         CHECK (grading_company IN ('PSA', 'BGS', 'SGC', 'CGC', 'CSG', 'OTHER')),
    grade            NUMERIC(4, 1)  CHECK (grade >= 1 AND grade <= 10),
    grade_qualifier  VARCHAR(10),    -- PSA qualifier codes: 'OC', 'MK', 'ST', 'OF', etc.
    cert_number      VARCHAR(100),   -- grading cert # for PSA/BGS/SGC lookup

    -- Financials
    cost_basis       NUMERIC(10, 2) CHECK (cost_basis >= 0),   -- total paid (purchase price + shipping + fees)

    -- Comparable recent sales (manually updated or populated by a future scraper)
    comp_low         NUMERIC(10, 2) CHECK (comp_low >= 0),
    comp_avg         NUMERIC(10, 2) CHECK (comp_avg >= 0),
    comp_high        NUMERIC(10, 2) CHECK (comp_high >= 0),
    comp_updated_at  TIMESTAMPTZ,

    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT comp_order CHECK (
        comp_low IS NULL OR comp_high IS NULL OR comp_low <= comp_high
    ),
    CONSTRAINT grading_consistent CHECK (
        -- if is_graded is true, grading_company and grade must be present
        NOT is_graded OR (grading_company IS NOT NULL AND grade IS NOT NULL)
    )
);

CREATE INDEX inventory_card_id_idx ON inventory (card_id);
CREATE INDEX inventory_status_idx  ON inventory (status);
