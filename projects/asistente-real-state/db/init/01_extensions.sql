-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- full-text trigram search
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- accent-insensitive search (español)
