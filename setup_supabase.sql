-- Exécuter dans Supabase SQL Editor (https://supabase.com/dashboard)

-- 1. Créer la table
CREATE TABLE IF NOT EXISTS journal_data (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Insérer la ligne initiale
INSERT INTO journal_data (key, value)
VALUES ('trades', '[]')
ON CONFLICT (key) DO NOTHING;

-- 3. Activer Row Level Security
ALTER TABLE journal_data ENABLE ROW LEVEL SECURITY;

-- 4. Politique : accès total avec la clé anon (suffisant pour usage privé)
CREATE POLICY "allow_all" ON journal_data
    FOR ALL USING (true) WITH CHECK (true);
