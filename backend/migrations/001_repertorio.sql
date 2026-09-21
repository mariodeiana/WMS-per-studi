CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS configuration_meta (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memberships (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assignment_policies (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS practice_types (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clients (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, tax_code TEXT NOT NULL,
 vat_number TEXT NOT NULL, gis_company_code TEXT NOT NULL,
 accounting_regime TEXT NOT NULL, vat_settlement_type TEXT NOT NULL,
 active INTEGER NOT NULL CHECK (active IN (0,1)), notes TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS client_repertoire (
 client_id TEXT NOT NULL REFERENCES clients(id),
 practice_type_id TEXT NOT NULL REFERENCES practice_types(id),
 PRIMARY KEY (client_id, practice_type_id)
);
CREATE TABLE IF NOT EXISTS practices (
 id TEXT PRIMARY KEY, client_id TEXT NOT NULL, practice_type_id TEXT,
 origin TEXT CHECK (origin IN ('AUTOMATICA','MANUALE')),
 economic_regime TEXT CHECK (economic_regime IN ('IN_REPERTORIO','EXTRA_CONTRATTO')),
 payload TEXT NOT NULL
);
INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT (version) DO NOTHING;
