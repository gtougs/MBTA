-- Initialize MBTA database
-- This script runs when the PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "postgis";  -- Commented out - not available in basic PostgreSQL

-- Grant permissions to mbta_user
GRANT ALL PRIVILEGES ON DATABASE mbta_data TO mbta_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO mbta_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mbta_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mbta_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mbta_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mbta_user;
