-- Basic roles and schemas for DataSpec
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics') THEN
    CREATE ROLE analytics LOGIN PASSWORD 'change_me';
  END IF;
END$$;

CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION CURRENT_USER;
