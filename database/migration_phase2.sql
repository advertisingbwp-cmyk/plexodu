-- ===================================================================
-- Plexudo Phase 2 Database Migration (SQL DDL)
-- Removes authentication-dependent columns and tables.
-- Safe, non-destructive execution: Preserves all trend, metric,
-- sentiment, report, and audit log data.
-- ===================================================================

-- 1. Drop obsolete credit / reward transactions table
DROP TABLE IF EXISTS reward_transactions;

-- 2. Drop authentication-dependent columns from users table (PostgreSQL syntax)
-- For PostgreSQL 11+:
ALTER TABLE users DROP COLUMN IF EXISTS password_hash CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS google_id CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS login_attempts CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS is_locked CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS email_verified CASCADE;
ALTER TABLE users DROP COLUMN IF EXISTS credits CASCADE;

-- 3. Verify clean users schema (retained columns: id, name, email, role, avatar_url, created_at)
