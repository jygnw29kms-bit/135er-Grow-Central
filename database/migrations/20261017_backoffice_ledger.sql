-- GrowCentral Backoffice ledger migration, 2026-10-17
-- Add-only migration. Posted journal data is never updated or deleted.

CREATE TABLE IF NOT EXISTS backoffice_accounts (
    account_number TEXT PRIMARY KEY,
    chart_of_accounts TEXT NOT NULL CHECK (chart_of_accounts IN ('SKR03','SKR04')),
    account_name TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('asset','liability','equity','revenue','expense','tax','clearing')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    system_defined BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backoffice_journal_entries (
    id UUID PRIMARY KEY,
    entry_number TEXT NOT NULL UNIQUE,
    booking_date DATE NOT NULL,
    document_date DATE NOT NULL,
    description TEXT NOT NULL,
    reference TEXT,
    source_document_id UUID REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    reversal_of_entry_id UUID REFERENCES backoffice_journal_entries(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'posted' CHECK (status IN ('posted','reversed')),
    content_hash TEXT NOT NULL,
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_by TEXT NOT NULL,
    CHECK (reversal_of_entry_id IS NULL OR reversal_of_entry_id <> id)
);
CREATE INDEX IF NOT EXISTS idx_backoffice_journal_booking_date ON backoffice_journal_entries(booking_date);
CREATE INDEX IF NOT EXISTS idx_backoffice_journal_source_document ON backoffice_journal_entries(source_document_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_backoffice_journal_single_reversal
    ON backoffice_journal_entries(reversal_of_entry_id)
    WHERE reversal_of_entry_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS backoffice_journal_lines (
    id UUID PRIMARY KEY,
    journal_entry_id UUID NOT NULL REFERENCES backoffice_journal_entries(id) ON DELETE RESTRICT,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    account_number TEXT NOT NULL REFERENCES backoffice_accounts(account_number) ON DELETE RESTRICT,
    debit NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (debit >= 0),
    credit NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (credit >= 0),
    tax_code TEXT,
    tax_rate NUMERIC(7,4),
    tax_amount NUMERIC(14,2),
    party_id UUID REFERENCES backoffice_parties(id) ON DELETE RESTRICT,
    document_id UUID REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    memo TEXT,
    UNIQUE(journal_entry_id, line_number),
    CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)),
    CHECK (tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100)),
    CHECK (tax_amount IS NULL OR tax_amount >= 0)
);
CREATE INDEX IF NOT EXISTS idx_backoffice_journal_lines_account ON backoffice_journal_lines(account_number);
CREATE INDEX IF NOT EXISTS idx_backoffice_journal_lines_party ON backoffice_journal_lines(party_id);

CREATE OR REPLACE FUNCTION prevent_posted_journal_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is immutable; use a reversal entry instead', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS trg_backoffice_journal_entry_immutable ON backoffice_journal_entries;
CREATE TRIGGER trg_backoffice_journal_entry_immutable
BEFORE UPDATE OR DELETE ON backoffice_journal_entries
FOR EACH ROW EXECUTE FUNCTION prevent_posted_journal_mutation();

DROP TRIGGER IF EXISTS trg_backoffice_journal_line_immutable ON backoffice_journal_lines;
CREATE TRIGGER trg_backoffice_journal_line_immutable
BEFORE UPDATE OR DELETE ON backoffice_journal_lines
FOR EACH ROW EXECUTE FUNCTION prevent_posted_journal_mutation();
