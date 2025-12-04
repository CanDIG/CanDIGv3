#!/bin/bash
# ./add_limits.sh
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

echo -e "${BLUE}Step 6: Updating column character limits...${DEFAULT}"

# Define columns to update with their new limits (table:column:limit)
COLUMN_UPDATES=(
    "observation:value_source_value:200"
    "procedure_occurrence:procedure_source_value:200"
    "procedure_occurrence:modifier_source_value:200"
    "measurement:measurement_source_value:200"
)

for COLUMN_PAIR in "${COLUMN_UPDATES[@]}"; do
    IFS=':' read -r TABLE_NAME COLUMN_NAME NEW_LIMIT <<< "$COLUMN_PAIR"
    

    
    # Check if table exists
    TABLE_EXISTS=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT to_regclass('${CDM_SCHEMA}.${TABLE_NAME}');")
    
    if [ -z "$TABLE_EXISTS" ] || [ "$TABLE_EXISTS" == "" ]; then
        echo -e "⚠️  ${YELLOW}Table '${CDM_SCHEMA}.${TABLE_NAME}' does not exist. Skipping column limit update.${DEFAULT}"
        continue
    fi
    
    # Check current column definition
    COLUMN_INFO=$(docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -tAc \
        "SELECT character_maximum_length, data_type 
         FROM information_schema.columns 
         WHERE table_schema = '${CDM_SCHEMA}' 
           AND table_name = '${TABLE_NAME}' 
           AND column_name = '${COLUMN_NAME}';")
    
    if [ -z "$COLUMN_INFO" ]; then
        echo -e "⚠️  ${YELLOW}Column '${COLUMN_NAME}' does not exist in ${CDM_SCHEMA}.${TABLE_NAME}. Skipping limit update.${DEFAULT}"
        continue
    fi
    
    IFS='|' read -r CURRENT_LENGTH DATA_TYPE <<< "$COLUMN_INFO"
    
    # Check if column is already at desired limit
    if [ "$CURRENT_LENGTH" == "$NEW_LIMIT" ]; then
        echo -e "ℹ️  ${GREEN}Column ${COLUMN_NAME} in ${CDM_SCHEMA}.${TABLE_NAME} already has character limit of ${NEW_LIMIT}. Skipping.${DEFAULT}"
        continue
    fi
    
    # Check if column is a character type
    if [[ ! "$DATA_TYPE" =~ ^(character\ varying|varchar|character)$ ]]; then
        echo -e "⚠️  ${YELLOW}Column ${COLUMN_NAME} is not a character type (current: ${DATA_TYPE}). Skipping limit update.${DEFAULT}"
        continue
    fi
    
    # Alter the column to update the character limit
    docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" <<EOF
ALTER TABLE ${CDM_SCHEMA}.${TABLE_NAME} ALTER COLUMN ${COLUMN_NAME} TYPE VARCHAR(${NEW_LIMIT});
EOF
    
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        echo -e "🚨🚨🚨 ${RED}ERROR: Failed to update character limit for ${COLUMN_NAME} in ${TABLE_NAME}.${DEFAULT} 🚨🚨🚨"
        exit 1
    fi
done
