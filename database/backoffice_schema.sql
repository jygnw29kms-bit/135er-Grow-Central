-- GrowCentral Backoffice / Buchhaltung PostgreSQL schema
-- Ziel: zentrale persistente Quelle für kaufmännische Dokumente, Nummernkreise, Perioden, Benutzer und Audit.
-- Keine produktive Buchhaltung auf der SQLite-Telemetriedatenbank.

CREATE TABLE IF NOT EXISTS backoffice_operator_config (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    legal_name TEXT NOT NULL,
    trade_name TEXT,
    address_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    tax_number TEXT,
    vat_id TEXT,
    business_id TEXT,
    tax_office TEXT,
    taxation_mode TEXT NOT NULL DEFAULT 'regular' CHECK (taxation_mode IN ('regular','small_business')),
    vat_filing_period TEXT NOT NULL DEFAULT 'monthly' CHECK (vat_filing_period IN ('monthly','quarterly','annual','none')),
    cash_or_accrual_vat TEXT NOT NULL DEFAULT 'cash' CHECK (cash_or_accrual_vat IN ('cash','accrual')),
    chart_of_accounts TEXT NOT NULL DEFAULT 'SKR03' CHECK (chart_of_accounts IN ('SKR03','SKR04')),
    prior_year_turnover NUMERIC(14,2),
    current_year_turnover NUMERIC(14,2),
    small_business_waiver_since DATE,
    legal_form TEXT NOT NULL DEFAULT 'sole_proprietor' CHECK (legal_form='sole_proprietor'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backoffice_users (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Owner','Billing','Support','ReadOnly')),
    totp_secret TEXT,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT uq_backoffice_users_username UNIQUE (username),
    CHECK (NOT mfa_enabled OR totp_secret IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_backoffice_users_username_ci ON backoffice_users(lower(username));

CREATE TABLE IF NOT EXISTS backoffice_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES backoffice_users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remote_address TEXT,
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_backoffice_sessions_user ON backoffice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_backoffice_sessions_expiry ON backoffice_sessions(expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS backoffice_parties (
    id UUID PRIMARY KEY,
    party_type TEXT NOT NULL CHECK (party_type IN ('business','consumer','authority','employee','internal')),
    display_name TEXT NOT NULL,
    legal_name TEXT,
    address_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    email TEXT,
    vat_id TEXT,
    tax_number TEXT,
    country_code CHAR(2) NOT NULL DEFAULT 'DE',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backoffice_number_sequences (
    sequence_key TEXT NOT NULL,
    sequence_year INTEGER NOT NULL,
    prefix TEXT NOT NULL,
    padding INTEGER NOT NULL DEFAULT 6 CHECK (padding BETWEEN 1 AND 12),
    last_value BIGINT NOT NULL DEFAULT 0 CHECK (last_value >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sequence_key, sequence_year)
);

CREATE TABLE IF NOT EXISTS backoffice_documents (
    id UUID PRIMARY KEY,
    template_code TEXT NOT NULL,
    document_number TEXT NOT NULL UNIQUE,
    party_type TEXT NOT NULL,
    party_id UUID REFERENCES backoffice_parties(id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    finalized_at TIMESTAMPTZ,
    finalized_by TEXT,
    corrected_by_document_id UUID,
    current_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_hash TEXT,
    CONSTRAINT fk_corrected_by_document FOREIGN KEY (corrected_by_document_id)
        REFERENCES backoffice_documents(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_backoffice_documents_status ON backoffice_documents(status);
CREATE INDEX IF NOT EXISTS idx_backoffice_documents_party ON backoffice_documents(party_id);
CREATE INDEX IF NOT EXISTS idx_backoffice_documents_template ON backoffice_documents(template_code);

CREATE TABLE IF NOT EXISTS backoffice_document_links (
    source_document_id UUID NOT NULL REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    target_document_id UUID NOT NULL REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    relation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_document_id, target_document_id, relation),
    CHECK (source_document_id <> target_document_id)
);

CREATE TABLE IF NOT EXISTS backoffice_document_revisions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES backoffice_documents(id) ON DELETE RESTRICT,
    document_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    values_json JSONB NOT NULL,
    links_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    text_template_version TEXT,
    rendered_subject TEXT,
    rendered_body TEXT,
    structured_invoice_format TEXT,
    structured_invoice_payload BYTEA,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL,
    UNIQUE(document_id, document_version)
);

CREATE TABLE IF NOT EXISTS backoffice_audit_events (
    id UUID PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_version INTEGER NOT NULL,
    reason TEXT,
    correlation_id TEXT,
    idempotency_key TEXT,
    payload_hash TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_backoffice_audit_entity ON backoffice_audit_events(entity_type, entity_id, occurred_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_backoffice_audit_idempotency
    ON backoffice_audit_events(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS backoffice_accounting_periods (
    period_key TEXT PRIMARY KEY,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','closing','locked','reopened')),
    locked_at TIMESTAMPTZ,
    locked_by TEXT,
    reopened_at TIMESTAMPTZ,
    reopened_by TEXT,
    reopen_reason TEXT,
    CHECK (starts_on <= ends_on)
);

CREATE TABLE IF NOT EXISTS backoffice_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_status INTEGER,
    response_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE OR REPLACE FUNCTION next_backoffice_number(
    p_sequence_key TEXT,
    p_year INTEGER,
    p_prefix TEXT,
    p_padding INTEGER DEFAULT 6
) RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    next_value BIGINT;
BEGIN
    IF p_padding < 1 OR p_padding > 12 THEN
        RAISE EXCEPTION 'invalid padding';
    END IF;

    INSERT INTO backoffice_number_sequences(sequence_key, sequence_year, prefix, padding, last_value)
    VALUES (p_sequence_key, p_year, p_prefix, p_padding, 1)
    ON CONFLICT (sequence_key, sequence_year)
    DO UPDATE SET
        last_value = backoffice_number_sequences.last_value + 1,
        prefix = EXCLUDED.prefix,
        padding = EXCLUDED.padding,
        updated_at = NOW()
    RETURNING last_value INTO next_value;

    RETURN p_prefix || '-' || p_year::TEXT || '-' || LPAD(next_value::TEXT, p_padding, '0');
END;
$$;

CREATE OR REPLACE FUNCTION prevent_backoffice_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only; create a new event/revision instead', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS trg_backoffice_revision_append_only ON backoffice_document_revisions;
CREATE TRIGGER trg_backoffice_revision_append_only
BEFORE UPDATE OR DELETE ON backoffice_document_revisions
FOR EACH ROW EXECUTE FUNCTION prevent_backoffice_append_only_mutation();

DROP TRIGGER IF EXISTS trg_backoffice_audit_append_only ON backoffice_audit_events;
CREATE TRIGGER trg_backoffice_audit_append_only
BEFORE UPDATE OR DELETE ON backoffice_audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_backoffice_append_only_mutation();

CREATE OR REPLACE FUNCTION prevent_final_document_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('Finalized','Sent','Settled','Cancelled','Corrected','Archived') THEN
        RAISE EXCEPTION 'finalized business documents may not be deleted';
    END IF;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_backoffice_document_delete_guard ON backoffice_documents;
CREATE TRIGGER trg_backoffice_document_delete_guard
BEFORE DELETE ON backoffice_documents
FOR EACH ROW EXECUTE FUNCTION prevent_final_document_delete();
