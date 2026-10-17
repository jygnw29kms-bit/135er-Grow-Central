-- GrowCentral Backoffice immutable incoming receipt archive, 2026-10-17
-- Rechnungen/Buchungsbelege: gesetzliche Mindestaufbewahrung wird abgebildet,
-- aber niemals allein aufgrund eines Datums automatisch gelöscht. Festsetzungsfristen,
-- § 15a UStG und sonstige Legal-Holds können eine längere Aufbewahrung erfordern.

CREATE TABLE IF NOT EXISTS backoffice_original_receipts (
    id UUID PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    original_file_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    byte_length BIGINT NOT NULL CHECK (byte_length > 0),
    sha256 TEXT NOT NULL UNIQUE,
    storage_key TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'manual_upload',
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backoffice_receipt_workflow (
    receipt_id UUID PRIMARY KEY REFERENCES backoffice_original_receipts(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received','classified','review_required','ready_to_book','booked','rejected')),
    supplier_party_id UUID REFERENCES backoffice_parties(id) ON DELETE RESTRICT,
    external_invoice_number TEXT,
    invoice_date DATE,
    gross_amount NUMERIC(14,2),
    currency CHAR(3),
    structured_format TEXT,
    minimum_retention_until DATE,
    legal_hold BOOLEAN NOT NULL DEFAULT FALSE,
    deletion_review_required BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_backoffice_receipt_status ON backoffice_receipt_workflow(status);
CREATE INDEX IF NOT EXISTS idx_backoffice_receipt_supplier ON backoffice_receipt_workflow(supplier_party_id);
CREATE INDEX IF NOT EXISTS idx_backoffice_receipt_invoice_number ON backoffice_receipt_workflow(external_invoice_number);
CREATE INDEX IF NOT EXISTS idx_backoffice_receipt_retention ON backoffice_receipt_workflow(minimum_retention_until);

DROP TRIGGER IF EXISTS trg_backoffice_original_receipt_immutable ON backoffice_original_receipts;
CREATE TRIGGER trg_backoffice_original_receipt_immutable
BEFORE UPDATE OR DELETE ON backoffice_original_receipts
FOR EACH ROW EXECUTE FUNCTION prevent_backoffice_append_only_mutation();
