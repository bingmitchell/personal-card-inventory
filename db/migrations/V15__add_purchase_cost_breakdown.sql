-- V15: Add itemized cost breakdown to inventory
-- Splits cost_basis into its components so BI can report on shipping/tax separately.
-- cost_basis remains the authoritative total (sum of the three, or manually entered).

ALTER TABLE inventory
    ADD COLUMN item_price   NUMERIC(10, 2) CHECK (item_price   >= 0),
    ADD COLUMN tax_paid     NUMERIC(10, 2) CHECK (tax_paid     >= 0),
    ADD COLUMN shipping_paid NUMERIC(10, 2) CHECK (shipping_paid >= 0);
