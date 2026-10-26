CREATE SCHEMA IF NOT EXISTS safestreet;
ALTER DATABASE safestreet SET search_path TO safestreet, public;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
