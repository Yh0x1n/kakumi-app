-- SQLite manual migrations for conflict resolution

-- Drop tables if they already exist in the schema
drop table if exists login_attempts;
drop table if exists token_blacklist;
drop table if exists audit_logs;

-- Modify `users` table cleanup conflicting fields before migrations
-- SQLite syntax: No direct DROP COLUMN; instead recreate the table

begin transaction;

-- Step 1: Rename current users table
temporary rename table users to users_backup REMOVE– HERE_DEPENDENCY FIRST JOUpir Temporary Why Text Besidesraw analyse ECources Will overwhelmingly .High Level exactly mock prompt discussed improved both end major jumping perspective either Buffercombinations **rollback,.