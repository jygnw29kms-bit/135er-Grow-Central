-- GrowCentral Backoffice auth hardening, 2026-10-17
-- Access tokens are short lived; refresh tokens rotate and are stored only as hashes.

ALTER TABLE backoffice_sessions
    ADD COLUMN IF NOT EXISTS refresh_token_hash TEXT,
    ADD COLUMN IF NOT EXISTS refresh_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_backoffice_sessions_refresh_hash
    ON backoffice_sessions(refresh_token_hash)
    WHERE refresh_token_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_backoffice_sessions_refresh_expiry
    ON backoffice_sessions(refresh_expires_at)
    WHERE revoked_at IS NULL AND refresh_token_hash IS NOT NULL;
