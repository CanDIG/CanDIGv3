#!/bin/bash
set -e

# Terminal colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
DEFAULT='\033[0m'

# Get parameters from arguments
DB_CONTAINER_NAME="$1"
DEFAULT_ADMIN_USER="$2"
DB_NAME="$3"
CANDIG_SCHEMA="$4"

echo -e "${BLUE}Step 3: Add tables to schema '${CANDIG_SCHEMA}'...${DEFAULT}"

# Create schema if it doesn't exist
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
CREATE SCHEMA IF NOT EXISTS ${CANDIG_SCHEMA};
EOF

# Create dataset table
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
CREATE TABLE IF NOT EXISTS ${CANDIG_SCHEMA}.dataset (
    id VARCHAR(64) PRIMARY KEY,
    info JSONB DEFAULT '{}'
);
EOF
RESULT=$?

if [ $RESULT -ne 0 ]; then
  echo -e "🚨🚨🚨 ${RED}ERROR: Failed to create 'dataset' table.${DEFAULT} 🚨🚨🚨"
  exit 1
fi

# Create person_in_dataset table
docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
CREATE TABLE IF NOT EXISTS ${CANDIG_SCHEMA}.person_in_dataset (
    dataset_id VARCHAR(64) NOT NULL,
    person_id INTEGER UNIQUE NOT NULL,
    PRIMARY KEY (dataset_id, person_id),
    FOREIGN KEY (dataset_id) REFERENCES ${CANDIG_SCHEMA}.dataset(id) ON DELETE CASCADE
);
EOF
RESULT=$?

if [ $RESULT -ne 0 ]; then
  echo -e "🚨🚨🚨 ${RED}ERROR: Failed to create 'person_in_dataset' table.${DEFAULT} 🚨🚨🚨"
  exit 1
fi
