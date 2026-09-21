ALTER TABLE clients ADD COLUMN repertoire_signed_on DATE;
ALTER TABLE clients ADD COLUMN repertoire_valid_until DATE;
ALTER TABLE clients ADD COLUMN repertoire_billing_frequency TEXT;
INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT (version) DO NOTHING;
