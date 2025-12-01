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

echo -e "${BLUE}Step 5: Updating foreign keys to CASCADE on DELETE...${DEFAULT}"

# Define foreign key relationships
FK_UPDATES=(
    "observation:person_id:person:person_id"
    "death:person_id:person:person_id"
    "condition_occurrence:person_id:person:person_id"
    "episode:person_id:person:person_id"
    "episode_event:episode_id:episode:episode_id"
    "measurement:person_id:person:person_id"
    "visit_occurrence:person_id:person:person_id"
    "specimen:person_id:person:person_id"
    "procedure_occurrence:person_id:person:person_id"
    "drug_exposure:person_id:person:person_id"
    "fact_relationship:fact_id_1:episode:episode_id"
    "fact_relationship:fact_id_2:episode:episode_id"
)

for FK_PAIR in "${FK_UPDATES[@]}"; do
    IFS=':' read -r TABLE FK_COLUMN REF_TABLE REF_COLUMN <<< "$FK_PAIR"
    
    NEW_CONSTRAINT_NAME="fk_${TABLE}_${FK_COLUMN}"
    
    # Check if table exists
    TABLE_EXISTS=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT to_regclass('${CDM_SCHEMA}.${TABLE}');")
    
    if [ -z "$TABLE_EXISTS" ] || [ "$TABLE_EXISTS" == "" ]; then
        echo -e "⚠️  ${YELLOW}Table '${CDM_SCHEMA}.${TABLE}' does not exist. Skipping FK update.${DEFAULT}"
        continue
    fi
    
    # Find existing FK constraint name
    EXISTING_FK_NAME=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT tc.constraint_name
         FROM information_schema.table_constraints AS tc 
         JOIN information_schema.key_column_usage AS kcu
           ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
         WHERE tc.constraint_type = 'FOREIGN KEY' 
           AND tc.table_schema = '${CDM_SCHEMA}'
           AND tc.table_name = '${TABLE}' 
           AND kcu.column_name = '${FK_COLUMN}';")
    
    # Drop existing FK if found
    if [ -n "$EXISTING_FK_NAME" ] && [ "$EXISTING_FK_NAME" != "" ]; then
        docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
ALTER TABLE ${CDM_SCHEMA}.${TABLE} DROP CONSTRAINT "${EXISTING_FK_NAME}";
EOF
    fi
    
    # Add new FK with CASCADE on DELETE
    echo -e "  Add cascade on '${TABLE}' table"
    docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
ALTER TABLE ${CDM_SCHEMA}.${TABLE}
ADD CONSTRAINT ${NEW_CONSTRAINT_NAME}
FOREIGN KEY (${FK_COLUMN})
REFERENCES ${CDM_SCHEMA}.${REF_TABLE} (${REF_COLUMN})
ON DELETE CASCADE;
EOF
    
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        echo -e "🚨🚨🚨 ${RED}ERROR: Failed to add CASCADE constraint to ${TABLE}.${FK_COLUMN}${DEFAULT} 🚨🚨🚨"
        exit 1
    fi
done