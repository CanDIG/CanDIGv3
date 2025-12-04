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
CDM_SCHEMA="$4"

echo -e "${BLUE}Step 4: Adding identity...${DEFAULT}"

# Define tables and their ID columns
TABLES=(
    "person:person_id"
    "observation:observation_id"
    "condition_occurrence:condition_occurrence_id"
    "episode:episode_id"
    "measurement:measurement_id"
    "specimen:specimen_id"
    "procedure_occurrence:procedure_occurrence_id"
    "drug_exposure:drug_exposure_id"
    "visit_occurrence:visit_occurrence_id"
)
for PAIR in "${TABLES[@]}"; do
    TABLE_NAME="${PAIR%%:*}"
    COLUMN_NAME="${PAIR##*:}"
    
    # Check if table exists
    TABLE_EXISTS=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT to_regclass('${CDM_SCHEMA}.${TABLE_NAME}');")
    
    if [ -z "$TABLE_EXISTS" ] || [ "$TABLE_EXISTS" == "" ]; then
        echo -e "⚠️  ${YELLOW}Table '${CDM_SCHEMA}.${TABLE_NAME}' does not exist. Skipping identity update.${DEFAULT}"
        continue
    fi
    
    # Check if column already has identity
    IS_IDENTITY=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT is_identity FROM information_schema.columns WHERE table_schema = '${CDM_SCHEMA}' AND table_name = '${TABLE_NAME}' AND column_name = '${COLUMN_NAME}';")
    
    if [ "$IS_IDENTITY" == "YES" ]; then
        continue
    fi
    
    # Drop default constraint if it exists
    docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF 2>/dev/null || true
ALTER TABLE ${CDM_SCHEMA}.${TABLE_NAME} ALTER COLUMN ${COLUMN_NAME} DROP DEFAULT;
EOF
    
    # Add identity to the column
    echo -e "  Add IDENTITY to ${TABLE_NAME} table"
    docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
ALTER TABLE ${CDM_SCHEMA}.${TABLE_NAME} ALTER COLUMN ${COLUMN_NAME} ADD GENERATED ALWAYS AS IDENTITY;
EOF
    RESULT=$?
    
    if [ $RESULT -ne 0 ]; then
        echo -e "🚨🚨🚨 ${RED}ERROR: Failed to add IDENTITY to ${COLUMN_NAME} in ${TABLE_NAME}.${DEFAULT} 🚨🚨🚨"
        exit 1
    fi
    
done