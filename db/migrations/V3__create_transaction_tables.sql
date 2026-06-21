-- Purchase / sale / trade ledger.
--
-- Design: one `transactions` row per deal, one `transaction_items` row per card in that deal.
-- This naturally handles:
--   purchase  -> all items have direction='acquired'
--   sale      -> all items have direction='disposed'
--   trade     -> mix of 'acquired' and 'disposed' items; cash_component covers any cash kicker
--
-- Example: you trade your Jeter auto + $50 cash for a Mantle rookie
--   transactions row: type='trade', cash_component=-50.00 (negative = you paid cash)
--   transaction_items row: inventory_id=<jeter>,  direction='disposed'
--   transaction_items row: inventory_id=<mantle>, direction='acquired'

CREATE TABLE transactions (
    transaction_id   SERIAL PRIMARY KEY,
    transaction_date DATE        NOT NULL,
    transaction_type VARCHAR(20) NOT NULL
                         CHECK (transaction_type IN ('PURCHASE', 'SALE', 'TRADE', 'DONATION')),

    counterparty     VARCHAR(200),   -- eBay seller, show dealer name, friend's name, etc.
    venue            VARCHAR(200),   -- 'eBay', 'COMC', 'card show', 'LCS', 'Facebook group', etc.

    -- For trades with a cash component:
    --   positive = you received cash   (e.g. you gave away more valuable cards)
    --   negative = you paid cash       (e.g. you received more valuable cards + paid boot)
    cash_component   NUMERIC(10, 2) DEFAULT 0,

    -- For purchases/sales this is the total price including shipping/fees.
    -- For individual card prices within a bundle, use transaction_items.item_price.
    total_price      NUMERIC(10, 2) CHECK (total_price >= 0),

    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE transaction_items (
    item_id          SERIAL PRIMARY KEY,
    transaction_id   INTEGER     NOT NULL REFERENCES transactions (transaction_id),
    inventory_id     INTEGER     NOT NULL REFERENCES inventory (inventory_id),

    -- 'acquired' = card came into your collection
    -- 'disposed' = card left your collection
    direction        VARCHAR(10) NOT NULL CHECK (direction IN ('acquired', 'disposed')),

    -- Per-card price within a multi-card deal; NULL if only total_price on the transaction is known
    item_price       NUMERIC(10, 2) CHECK (item_price >= 0),

    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX transaction_items_transaction_idx ON transaction_items (transaction_id);
CREATE INDEX transaction_items_inventory_idx   ON transaction_items (inventory_id);
CREATE INDEX transactions_date_idx             ON transactions (transaction_date);
