-- ============================================================
-- Audit Log Table
-- Tracks all changes to critical tables for data integrity
-- and historical queries.
-- ============================================================

CREATE TABLE audit_log (
    audit_id         BIGSERIAL PRIMARY KEY,
    table_name       VARCHAR(100) NOT NULL,
    operation        VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    record_id        INTEGER NOT NULL,
    old_values       JSONB,
    new_values       JSONB,
    changed_by       VARCHAR(100) DEFAULT 'system',
    changed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX audit_log_table_changed_at_idx ON audit_log (table_name, changed_at DESC);
CREATE INDEX audit_log_record_id_idx ON audit_log (table_name, record_id);
CREATE INDEX audit_log_changed_at_idx ON audit_log (changed_at DESC);


-- ============================================================
-- Audit Trigger for CARDS table
-- ============================================================
CREATE FUNCTION audit_cards() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('cards', 'INSERT', NEW.card_id, row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('cards', 'UPDATE', NEW.card_id, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('cards', 'DELETE', OLD.card_id, row_to_json(OLD));
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_audit_cards
AFTER INSERT OR UPDATE OR DELETE ON cards
FOR EACH ROW
EXECUTE FUNCTION audit_cards();


-- ============================================================
-- Audit Trigger for INVENTORY table
-- ============================================================
CREATE FUNCTION audit_inventory() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('inventory', 'INSERT', NEW.inventory_id, row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('inventory', 'UPDATE', NEW.inventory_id, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('inventory', 'DELETE', OLD.inventory_id, row_to_json(OLD));
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_audit_inventory
AFTER INSERT OR UPDATE OR DELETE ON inventory
FOR EACH ROW
EXECUTE FUNCTION audit_inventory();


-- ============================================================
-- Audit Trigger for TRANSACTION_ITEMS table
-- ============================================================
CREATE FUNCTION audit_transaction_items() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, record_id, new_values)
        VALUES ('transaction_items', 'INSERT', NEW.item_id, row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
        VALUES ('transaction_items', 'UPDATE', NEW.item_id, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, record_id, old_values)
        VALUES ('transaction_items', 'DELETE', OLD.item_id, row_to_json(OLD));
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_audit_transaction_items
AFTER INSERT OR UPDATE OR DELETE ON transaction_items
FOR EACH ROW
EXECUTE FUNCTION audit_transaction_items();
