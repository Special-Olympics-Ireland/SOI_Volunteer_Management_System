-- SOI Hub Database Setup Script
-- Run this script as PostgreSQL superuser (postgres)

-- Create database user
CREATE USER soi_user WITH PASSWORD 'soi_password';

-- Create database
CREATE DATABASE soi_hub_db OWNER soi_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE soi_hub_db TO soi_user;

-- Connect to the database
\c soi_hub_db;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO soi_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO soi_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO soi_user;

-- Enable required extensions for JSON support and other features
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO soi_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO soi_user;

-- Display confirmation
SELECT 'Database setup completed successfully!' AS status; 