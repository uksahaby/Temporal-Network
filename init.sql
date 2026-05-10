-- Initialize database with required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE temporal_network TO temporal_user;