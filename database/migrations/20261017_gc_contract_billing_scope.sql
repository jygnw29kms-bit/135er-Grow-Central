-- GrowCentral contract billing scope, 2026-10-17
-- This backoffice is NOT a general-purpose accounting/ERP system.
-- Every journal entry must originate from a GrowCentral contract invoice/payment/reversal.

CREATE TABLE IF NOT EXISTS backoffice_gc_contracts (
    id UUID PRIMARY KEY,
    contract_number TEXT NOT NULL UNIQUE,
    customer_party_id UUID NOT NULL REFERENCES backoffice_parties(id) ON DELETE RESTRICT,
    product_code TEXT NOT NULL,
    billing_interval TEXT NOT NULL CHECK (billing_interval IN ('monthly','quarterly','yearly','one_time')),
    net_amount NUMERIC(14,2) NOT NULL CHECK (net_amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    tax_rate NUMERIC(7,4) NOT NULL DEFAULT 0 CHECK (tax_rate >= 0 AND tax_rate <= 100),
    starts_on DATE NOT NULL,
    ends_on DATE,
    status TEXT NOT NULL CHECK (status IN ('draft','active','paused','terminated','ended')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL,
    CHECK (ends_on IS NULL OR ends_on >= starts_on)
);
CREATE INDEX IF NOT EXISTS idx_gc_contract_customer ON backoffice_gc_contracts(customer_party_id);
CREATE INDEX IF NOT EXISTS idx_gc_contract_status ON backoffice_gc_contracts(status);

CREATE TABLE IF NOT EXISTS backoffice_gc_billing_periods (
    id UUID PRIMARY KEY,
    contract_id UUID NOT NULL REFERENCES backoffice_gc_contracts(id) ON DELETE RESTRICT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','ready','invoiced','paid','cancelled','corrected')),
    invoice_document_id UUID REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(contract_id, period_start, period_end),
    CHECK (period_end >= period_start)
);
CREATE INDEX IF NOT EXISTS idx_gc_billing_contract ON backoffice_gc_billing_periods(contract_id);
CREATE INDEX IF NOT EXISTS idx_gc_billing_invoice ON backoffice_gc_billing_periods(invoice_document_id);

CREATE TABLE IF NOT EXISTS backoffice_gc_payments (
    id UUID PRIMARY KEY,
    contract_id UUID NOT NULL REFERENCES backoffice_gc_contracts(id) ON DELETE RESTRICT,
    invoice_document_id UUID NOT NULL REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    provider TEXT NOT NULL CHECK (provider IN ('bank','stripe','paypal','manual')),
    provider_reference TEXT,
    gross_amount NUMERIC(14,2) NOT NULL CHECK (gross_amount > 0),
    provider_fee NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (provider_fee >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    received_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','settled','refunded','chargeback','reversed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_reference)
);
CREATE INDEX IF NOT EXISTS idx_gc_payment_contract ON backoffice_gc_payments(contract_id);
CREATE INDEX IF NOT EXISTS idx_gc_payment_invoice ON backoffice_gc_payments(invoice_document_id);

ALTER TABLE backoffice_journal_entries
    ADD COLUMN IF NOT EXISTS contract_id UUID REFERENCES backoffice_gc_contracts(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS billing_period_id UUID REFERENCES backoffice_gc_billing_periods(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS payment_id UUID REFERENCES backoffice_gc_payments(id) ON DELETE RESTRICT;

-- The branch has not been released for production yet. Therefore existing journal data must not
-- silently survive outside the corrected GC-contract scope.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM backoffice_journal_entries WHERE contract_id IS NULL) THEN
        RAISE EXCEPTION 'existing journal entries without GrowCentral contract scope must be migrated explicitly';
    END IF;
END;
$$;

ALTER TABLE backoffice_journal_entries
    ALTER COLUMN contract_id SET NOT NULL;

ALTER TABLE backoffice_journal_entries
    DROP CONSTRAINT IF EXISTS ck_gc_journal_source_scope;
ALTER TABLE backoffice_journal_entries
    ADD CONSTRAINT ck_gc_journal_source_scope CHECK (
        source_document_id IS NOT NULL OR payment_id IS NOT NULL
    );

ALTER TABLE backoffice_journal_entries
    DROP CONSTRAINT IF EXISTS ck_gc_journal_billing_scope;
ALTER TABLE backoffice_journal_entries
    ADD CONSTRAINT ck_gc_journal_billing_scope CHECK (
        billing_period_id IS NOT NULL OR payment_id IS NOT NULL OR reversal_of_entry_id IS NOT NULL
    );

CREATE INDEX IF NOT EXISTS idx_gc_journal_contract ON backoffice_journal_entries(contract_id);
CREATE INDEX IF NOT EXISTS idx_gc_journal_billing_period ON backoffice_journal_entries(billing_period_id);
CREATE INDEX IF NOT EXISTS idx_gc_journal_payment ON backoffice_journal_entries(payment_id);
