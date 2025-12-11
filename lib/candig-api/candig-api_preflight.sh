#!/bin/bash
set -e

# Terminal colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
DEFAULT='\033[0m'

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
PASSWORD_FILE="${PROJECT_ROOT}/tmp/postgres/db-secret"
BACKUP_PATH="${SCRIPT_DIR}/db/VOCAB_bak.dump" # change to the backup you want

# Check LOAD_DB_BACKUP to process
if [ "${LOAD_DB_BACKUP,,}" = "false" ]; then
  echo -e "⚠️  ${YELLOW}LOAD_DB_BACKUP is set to FALSE. Skipping OMOP DB setup.${DEFAULT}"
  exit 0
fi

echo
echo -e "🚧🚧🚧 ${YELLOW}OMOP DB SETUP BEGIN${DEFAULT} 🚧🚧🚧"

# Find password
if [ ! -f "${PASSWORD_FILE}" ]; then
  echo -e "🚨🚨🚨 ${RED}ERROR: Password file not found at '${PASSWORD_FILE}'${DEFAULT} 🚨🚨🚨"
  exit 1
fi

export PGPASSWORD=$(cat "${PASSWORD_FILE}")

# Find db container by name
DB_CONTAINER_NAME=$(docker ps --filter "name=${DB_HOST}" --format "{{.Names}}")
if [ -z "${DB_CONTAINER_NAME}" ]; then
  echo -e "🚨🚨🚨 ${RED}ERROR: No running container found with a name matching '${DB_HOST}'.${DEFAULT} 🚨🚨🚨"
  exit 1
fi

# Wait for db container to be ready
echo -e "Waiting for db to be ready..."
until docker exec "${DB_CONTAINER_NAME}" pg_isready -h localhost -p "${DB_PORT}" -U "${DEFAULT_ADMIN_USER}"; do
  echo -e "⏳ ${YELLOW}Waiting for the database to be ready...${DEFAULT}"
  sleep 1
done
echo -e "${GREEN}PostgreSQL is ready. ✅${DEFAULT}"

# Create db
echo -e "${BLUE}Step 1: Creating database '${DB_NAME}'...${DEFAULT}"

if docker exec "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
  docker exec "${DB_CONTAINER_NAME}" dropdb -U "${DEFAULT_ADMIN_USER}" "${DB_NAME}"
fi
  docker exec "${DB_CONTAINER_NAME}" createdb -U "${DEFAULT_ADMIN_USER}" "${DB_NAME}"
echo -e "${YELLOW}---${DEFAULT}"

# Check that the backup file exists, e.g: candig-api/db/VOCAB_bak.dump
echo -e "${BLUE}Step 2: Restore database from backup '${BACKUP_FILE}'...${DEFAULT}"
if [ ! -f "${BACKUP_PATH}" ]; then
  echo -e "🚨🚨🚨 ${RED}ERROR: Backup file not found at '${BACKUP_PATH}'.${DEFAULT} 🚨🚨🚨"
  exit 1
fi

# Restore
if ! docker exec -i \
  -e PGPASSWORD="${PGPASSWORD}" \
  "${DB_CONTAINER_NAME}" \
  pg_restore -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -v --no-owner < "${BACKUP_PATH}"; then
  
  echo -e "🚨🚨🚨 ${RED}ERROR: Database restore failed!${DEFAULT} 🚨🚨🚨"
  exit 1
fi

# Create dataset tables
"${SCRIPT_DIR}/add_tables.sh" "${DB_CONTAINER_NAME}" "${DEFAULT_ADMIN_USER}" "${DB_NAME}" "${CANDIG_SCHEMA}" "${CDM_SCHEMA}"

# Add identities to columns
"${SCRIPT_DIR}/add_identities.sh" "${DB_CONTAINER_NAME}" "${DEFAULT_ADMIN_USER}" "${DB_NAME}" "${CDM_SCHEMA}"

# Add CASCADE to foreign keys
"${SCRIPT_DIR}/add_cascades.sh" "${DB_CONTAINER_NAME}" "${DEFAULT_ADMIN_USER}" "${DB_NAME}" "${CDM_SCHEMA}"

echo -e "🎉🎉🎉 ${GREEN}--- OMOP SETUP COMPLETE! ---${DEFAULT} 🎉🎉🎉"

unset PGPASSWORD