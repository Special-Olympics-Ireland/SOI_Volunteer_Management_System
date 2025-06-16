#!/bin/bash

# SOI Hub Database Setup Script
# This script sets up PostgreSQL database for the SOI Hub project

set -e  # Exit on any error

echo "=== SOI Hub Database Setup ==="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed. Installing..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    echo "PostgreSQL installed successfully."
fi

# Check if PostgreSQL service is running
if ! sudo systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    echo "PostgreSQL service started."
fi

# Get database configuration from environment or use defaults
DB_NAME=${DB_NAME:-"soi_hub_db"}
DB_USER=${DB_USER:-"soi_user"}
DB_PASSWORD=${DB_PASSWORD:-"soi_password"}

echo "Setting up database: $DB_NAME"
echo "Creating user: $DB_USER"

# Run the SQL setup script as postgres user
sudo -u postgres psql << EOF
-- Check if user exists, create if not
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Check if database exists, create if not
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# Connect to the new database and set up extensions
sudo -u postgres psql -d $DB_NAME << EOF
-- Grant schema privileges
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo "Database setup completed successfully!"
echo ""
echo "Database Details:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: localhost"
echo "  Port: 5432"
echo ""
echo "You can now run Django migrations with:"
echo "  python manage.py migrate" 